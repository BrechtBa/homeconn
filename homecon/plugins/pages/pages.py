#!/usr/bin/env python3

import logging
import json
import time

from pydal import DAL, Field

from homecon.core.event import Event
from homecon.core.pages.pages import Group, Page, Section, Widget, IPagesManager, MemoryObjectManager, MemoryPagesManager
from homecon.core.plugins.plugin import BasePlugin


logger = logging.getLogger(__name__)


class DALObjectManager(MemoryObjectManager):
    def __init__(self, db, table, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db = db
        self._table = table

        # load objects into memory
        for row in self._db().select(self._table.ALL):
            obj = self.row_to_obj(row)
            self._objects[obj.id] = obj

    def row_to_obj(self, row):
        raise NotImplementedError


class DALGroupManager(DALObjectManager):
    def row_to_obj(self, row):
        id = row.pop('id')
        name = row.pop('name')
        return self._object_factory(self, id, name, **row)


class DALPageManager(DALObjectManager):
    def row_to_obj(self, row):
        id = row.pop('id')
        name = row.pop('name')
        page = row.pop('name')
        return self._object_factory(self, id, name, **row)


class DALPagesManager(MemoryPagesManager):
    def __init__(self, folder: str, uri: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._db = DAL(uri, folder=folder)
        self._groups_table = self._db.define_table(
            'page_groups',
            Field('name', type='string', default='', unique=True),
            Field('config', type='string', default='{}'),
            Field('order', type='integer', default=0),
        )

    def get_group(self, path=None, id=None):
        if id is not None:
            db_entry = table(id)
            db.close()
        elif path is not None:
            parts = path.split('/')
            db_entry = table(name=parts[-1])
            db.close()
        else:
            logger.error("id or path must be supplied")
            return None
        if db_entry is not None:
            return cls(**db_entry.as_dict())
        else:
            return None

    def add_group(self, name, config=None, order=None):
        """
        Add a group
        """
        # check if it already exists
        entry = self._groups_table(name=name)
        if entry is None:
            id = self._groups_table.insert(name=name, config=json.dumps(config or {}), order=order)
            self._db.commit()

            # FIXME error checking
            obj = self.get_group(id=id)
            logger.debug('added group')
            Event.fire('group_added', {'group': object}, 'Group')
        else:
            obj = cls(**entry.as_dict())
        return obj

    def clear(self):
        db, table = Widget.get_table()
        table.drop()
        db.commit()
        db.close()

        db, table = Section.get_table()
        table.drop()
        db.commit()
        db.close()

        db, table = Page.get_table()
        table.drop()
        db.commit()
        db.close()

        db, table = Group.get_table()
        table.drop()
        db.commit()
        db.close()


class Pages(BasePlugin):
    """
    Notes
    -----
    A homecon app is structured using groups, pages, sections and widgets

    """
    def __init__(self, *args, now=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_update_timestamp = now or time.time()

    def start(self):
        # set defaults
        if len(self._pages_manager.all_groups()) == 0 and len(self._pages_manager.all_pages()) == 0 and \
                len(self._pages_manager.all_sections()) == 0 and len(self._pages_manager.all_widgets()) == 0:
            g0 = self._pages_manager.add_group('home', config={'title': 'Home'})
            g1 = self._pages_manager.add_group('central', config={'title': 'Central'})
            g2 = self._pages_manager.add_group('ground_floor', config={'title': 'Ground floor'})
            g3 = self._pages_manager.add_group('first_floor', config={'title': 'First floor'})

            p0 = self._pages_manager.add_page('home', g0, config={'title': 'Home', 'icon': 'blank'})
            p1 = self._pages_manager.add_page('heating', g1, config={'title': 'Heating', 'icon': 'sani_heating'})
            p2 = self._pages_manager.add_page('kitchen', g2, config={'title': 'Kitchen', 'icon': 'scene_dinner'})
            p3 = self._pages_manager.add_page('bathroom', g3, config={'title': 'Bathroom', 'icon': 'scene_bath'})
            p4 = self._pages_manager.add_page('master_bedroom', g3, config={'title': 'Master Bedroom', 'icon': 'scene_sleeping'})

            s0 = self._pages_manager.add_section('time', p0, config={'type': 'underlined'})
            self._pages_manager.add_widget('w0', s0, 'clock', config={})
            self._pages_manager.add_widget('w1', s0, 'date', config={})

            s1 = self._pages_manager.add_section('weather', p0, config={'type': 'underlined'})
            self._pages_manager.add_widget('w0', s1, 'weather-block', config={'daily': True, 'timeoffset': 0})
            self._pages_manager.add_widget('w1', s1, 'weather-block', config={'daily': True, 'timeoffset': 24})
            self._pages_manager.add_widget('w2', s1, 'weather-block', config={'daily': True, 'timeoffset': 48})
            self._pages_manager.add_widget('w3', s1, 'weather-block', config={'daily': True, 'timeoffset': 72})

            s2 = self._pages_manager.add_section('lights', p2, config={'type': 'raised', 'title': 'Lights'})
            self._pages_manager.add_widget('w0', s2, 'switch', config={'icon': 'light_light', 'state': 10})

            # s3 = Section.add('shading', p2, config={'type': 'collapsible', 'title': 'Shading'})
            # Widget.add('w0', s3, 'shading')

        logger.debug('Pages plugin initialized')

    def get_menu(self):
        """
        Return the data required to make the menu
        """
        menu = []
        groups = self._pages_manager.all_groups()
        for group in sorted(groups, key=lambda x: group.order):
            if not group.path == 'home':
                menu.append({
                    'path': group.path,
                    'config': group.config,
                    'pages': [{'id': page.id, 'path': page.path, 'config': page.config} for page in group.pages]
                })
        return menu

    def listen_pages_timestamp(self, event):
        # FIXME check permissions
        event.reply({'id': event.data['id'], 'value': self._last_update_timestamp})

    def listen_pages_pages(self, event):
        # FIXME check permissions
        d = self._pages_manager.serialize(self._state_manager)
        event.reply({'id': event.data['id'], 'value': {'timestamp': self._last_update_timestamp, 'groups': d}})

    def listen_pages_export(self, event):
        # FIXME check permissions
        d = self._pages_manager.serialize(self._state_manager, convert_state_ids_to_paths=True)
        event.reply({'id': event.data['id'], 'value': d})

    def listen_pages_import(self, event):
        # FIXME check permissions
        if 'value' in event.data:
            self.import_pages(event.data['value'])
            # FIXME send pages to all connected clients this should be independent of the websocket plugin.
            #  so there should be a IIOManager in core which is accessible through the plugins
            d = self._pages_manager.serialize(self._state_manager)
            self.fire('websocket_send', data={'timestamp': self._last_update_timestamp, 'groups': d})

    def import_pages(self, groups: dict):
        self._pages_manager.clear()
        self._pages_manager.deserialize(groups)
        self._last_update_timestamp = time.time()
