#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import inspect
import time
import asyncio
import logging

from . import core
from . import util
#from . import coreplugins
from . import plugins



################################################################################
# create the logger
################################################################################

logFormatter = logging.Formatter('%(asctime)s    %(threadName)-15.15s %(levelname)-8.8s    %(message)s')
logger = logging.getLogger()

basedir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if not os.path.exists( os.path.join(basedir,'log')):
    os.makedirs(os.path.join(basedir,'log'))

if not 'homecon.fileHandler' in [lh.name for lh in logger.handlers]:
    fileHandler = logging.FileHandler(os.path.join(basedir,'log/homecon.log'))
    fileHandler.setFormatter(logFormatter)
    fileHandler.set_name('homecon.fileHandler')
    logger.addHandler(fileHandler)



################################################################################
# HomeCon object
################################################################################
class HomeCon(object): 
    def __init__(self,loglevel='info',printlog=False,demo=False):
        """
        Create a new HomeCon object

        Parameters
        ----------
        loglevel : str
            'info', 'debug', ...

        printlog : boolean
            print the log to the console or not

        """

        self.loglevel = loglevel
        self.printlog = printlog
        self.demo = demo

        ########################################################################
        # set logging properties
        ########################################################################
        if self.printlog:
            if not 'homecon.consoleHandler' in [lh.name for lh in logger.handlers]:
                consoleHandler = logging.StreamHandler()
                consoleHandler.setFormatter(logFormatter)
                consoleHandler.set_name('homecon.consoleHandler')
                logger.addHandler(consoleHandler)

        if self.loglevel=='info':
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        logging.info('Creating HomeCon object')


        ########################################################################
        # demo mode
        ########################################################################
        if self.demo:
            logging.info('Demo mode')
            # clear the databases
            dbname = 'demo_homecon.db'
            dbmeasurementsname = 'demo_homecon_measurements.db'

            try:
                os.remove(dbname)
            except:
                pass

            try:
                os.remove(dbmeasurementsname)
            except:
                pass


            core.database.db = core.database.Database(database=dbname)
            core.database.measurements_db = core.database.Database(database=dbmeasurementsname)
            core.db = core.database.db
            core.measurements_db = core.database.measurements_db

            # update the database in states and components, this is pretty hacky
            core.state.State.db_table = core.database.Table(core.database.db,'states',[
                {'name':'path',   'type':'char(255)',  'null': '',  'default':'',  'unique':'UNIQUE'},
                {'name':'config', 'type':'char(511)',  'null': '',  'default':'',  'unique':''},
                {'name':'value',  'type':'char(255)',  'null': '',  'default':'',  'unique':''},
            ])
            core.state.State.db_history = core.database.Table(core.database.measurements_db,'measurements',[
                {'name':'time',   'type':'INT',   'null': '',  'default':'',  'unique':''},
                {'name':'path',   'type':'TEXT',  'null': '',  'default':'',  'unique':''},
                {'name':'value',  'type':'TEXT',  'null': '',  'default':'',  'unique':''},
            ])

            core.state.states = core.state.States()
            core.states = core.state.states
            tempcomponents = core.component.Components()

            # reregister components
            for componenttype in core.components._component_types.values():
                tempcomponents.register(componenttype)

            core.component.components = tempcomponents
            core.components = core.component.components


        ########################################################################
        # get the event loop and queue
        ########################################################################
        self._loop = asyncio.get_event_loop()

        if self.loglevel == 'debug':
            self._loop.set_debug(True)

        self._queue = core.event.queue #asyncio.Queue(loop=self._loop)


        ########################################################################
        # load core components
        ########################################################################
        self.states = core.states
        self.components = core.components
        self.plugins = core.plugins

        # import plugins
        self.plugins.start_import()

        # load components
        self.components.load()

        # activate all plugins
        self.plugins.start_activate()


        #self.plugins._add_core(coreplugins.states.States)            # load states 1st
        #self.plugins._add_core(coreplugins.components.Components)        # load components 2nd
        #self.plugins._add_core(coreplugins.plugins.Plugins)
        #self.plugins._add_core(coreplugins.authentication.Authentication)
        #self.plugins._add_core(coreplugins.pages.Pages)
        #self.plugins._add_core(coreplugins.schedules.Schedules)
        #self.plugins._add_core(coreplugins.actions.Actions)
        #self.plugins._add_core(coreplugins.measurements.Measurements)
        #self.plugins._add_core(coreplugins.weather.Weather)
        #self.plugins._add_core(coreplugins.building.Building)
        #self.plugins._add_core(coreplugins.systemidentification.Systemidentification)

        # load other plugins


        # demo mode
        #if self.demo:
        #    self.plugins._add_core(coreplugins.demo.Demo)





        # load the websocket
        #self.plugins._add_core(coreplugins.websocket.Websocket)



        logging.info('HomeCon object Initialized')



    def fire(self,event):
        """
        fire an event, mainly used for testing

        """

        async def do_fire(event):
            await self._queue.put(event)

        def do_create_task():
            self._loop.create_task(do_fire(event))

        self._loop.call_soon_threadsafe(do_create_task)



    async def listen(self):
        """
        listen for events in all plugins

        """

        while True:
            event = await self._queue.get()
            logging.debug(event)

            for plugin in self.plugins.values():
                self._loop.call_soon_threadsafe(plugin._listen, event)



    def main(self):

        # Start the event loop
        logging.debug('Starting event loop')

        self._loop.create_task(self.listen())

        self._loop.run_forever()

        logging.info('Homecon stopped\n\n')



    def stop(self):
        logging.info('Stopping HomeCon')

        # cancel all tasks
        for task in asyncio.Task.all_tasks():
            task.cancel()

        # stop the websocket
        self._loop.call_soon_threadsafe(self.coreplugins['websocket'].stop)

        # stop the event loop
        self._loop.stop()
        time.sleep(0.1)




