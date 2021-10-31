#!/usr/bin/env python3
import sys
import os
import logging
import time

from argparse import ArgumentParser
from multiprocessing import Process
from signal import signal, SIGTERM, SIGINT
from logging.handlers import TimedRotatingFileHandler


logger = logging.getLogger(__name__)


# the current file directory
base_path = os.path.dirname(os.path.abspath(__file__))


def configure_(create_folders=True,
               set_static_ip=True, ip=None,
               run_init_script=True, init_script_name='homecon',
               install_ipopt=True, install_knxd=True):
    ################################################################################
    # Install non python dependencies
    ################################################################################
    from homecon import configure

    if create_folders:
        print('### Creating the Homecon folders')
        configure.create_data_folders()

    # set a static ip address
    if set_static_ip:

        setip = False

        if ip is not None:
            print('### Setting static ip address')
            configure.set_static_ip(ip)
            setip = True

        if not setip:
            # use dialogs
            setip = input('Do you want to set a static ip address (yes): ')
            if setip in ['', 'yes', 'y']:
                print('### Setting static ip address')
                configure.set_static_ip()

            elif setip in ['no', 'n']:
                pass
            else:
                raise Exception('{} is not a valid answer, yes/y/no/n'.format(setip))

    # create an initscript
    if run_init_script:
        configure.set_init_script(scriptname=init_script_name)

    # patch pyutilib
    # if not '--nopatchpyutilib' in sys.argv:
    #     print('### Patching the pytuilib')
    #     configure.patch_pyutilib()

    # install knxd
    # if not '--noknxd' in sys.argv:
    #     print('### Installing knxd')
    #     configure.install_knxd()

    # install bonmin
    # if not '--nobonmin' in sys.argv:
    #    if not configure.solver_available('bonmin'):
    #        print('### Installing BONMIN')
    #        configure.install_bonmin()

    # install ipopt
    if install_ipopt:
        if not configure.solver_available('ipopt'):
            print('### Installing IPOPT')
            configure.install_ipopt()

    # install cbc
    # if not '--noglpk' in sys.argv:
    #     if not configure.solver_available('glpk'):
    #         print('### Installing GLPK')
    #         print('installation does not work locally yet and is omitted')
    #         configure.install_glpk()

    # install knxd
    if install_knxd:
        print('### Installing knxd')
        configure.install_knxd()


def serve_app_(appport=None) -> Process:
    from webserver.server import app
    server = Process(target=lambda: app.run(host='0.0.0.0', port=appport))
    server.start()

    return server


def get_homecon():
    """
    create the HomeCon object
    """

    db_dir = os.path.abspath(os.path.join(base_path, 'db'))
    try:
        os.mkdir(db_dir)
    except FileExistsError:
        pass

    from homecon.core.event import EventManager
    from homecon.core.states.dal_state_manager import DALStateManager
    from homecon.core.pages.pages import JSONPagesManager
    from homecon.core.plugins.plugin import MemoryPluginManager
    from homecon.homecon import HomeCon
    from concurrent.futures import ThreadPoolExecutor

    from homecon.plugins.websocket.websocket import Websocket
    from homecon.plugins.states.states import States
    from homecon.plugins.pages.pages import Pages
    from homecon.plugins.alarms.alarms import Alarms
    from homecon.plugins.knx.knx import Knx
    from homecon.plugins.shading.shading import Shading
    from homecon.plugins.computed.computed import Computed

    event_manager = EventManager()
    state_manager = DALStateManager(folder=db_dir, uri='sqlite://homecon.db', event_manager=event_manager)
    pages_manager = JSONPagesManager(os.path.join(db_dir, 'pages.json'))
    plugin_manager = MemoryPluginManager({
        'websocket': Websocket('websocket', event_manager, state_manager, pages_manager),
        'states': States('states', event_manager, state_manager, pages_manager),
        'pages': Pages('pages', event_manager, state_manager, pages_manager),
        'alarms': Alarms('alarms', event_manager, state_manager, pages_manager),
        'shading': Shading('shading', event_manager, state_manager, pages_manager),
        'knx': Knx('knx', event_manager, state_manager, pages_manager),
        'computed': Computed('computed', event_manager, state_manager, pages_manager),
    })
    executor = ThreadPoolExecutor(max_workers=10)

    homecon = HomeCon(event_manager, plugin_manager, executor)
    return homecon


def main(printlog=False, loglevel='INFO', dbloglevel='INFO', httploglevel='INFO',
         demo=False, appport=None, serve_app=True,
         configure=False, create_folders=True,
         set_static_ip=True, ip=None,
         run_init_script=True, init_script_name='homecon',
         install_ipopt=True, install_knxd=True):
    """
    Main entry point.
    """

    # configure logging
    os.makedirs(os.path.join(sys.prefix, 'var', 'log', 'homecon'), exist_ok=True)
    log_formatter = logging.Formatter('%(asctime)s %(levelname)7.7s %(name)-36.36s %(message)s')
    if 'homecon.file_handler' not in [lh.name for lh in logger.handlers]:
        file_handler = TimedRotatingFileHandler(os.path.join(sys.prefix, 'var', 'log', 'homecon', 'homecon.log'),
                                                when="midnight")
        file_handler.setFormatter(log_formatter)
        file_handler.set_name('homecon.file_handler')
        logging.root.handlers.append(file_handler)

    if printlog:
        if 'homecon.console_handler' not in [lh.name for lh in logger.handlers]:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(log_formatter)
            console_handler.set_name('homecon.console_handler')
            logging.root.handlers.append(console_handler)

    logging.root.setLevel(getattr(logging, loglevel))
    logging.getLogger('homecon.core.database').setLevel(getattr(logging, dbloglevel))

    if configure:
        configure_(create_folders=create_folders, set_static_ip=set_static_ip, ip=ip, run_init_script=run_init_script,
                   init_script_name=init_script_name, install_ipopt=install_ipopt, install_knxd=install_knxd)

    else:
        app_server = None
        if serve_app:
            app_server = serve_app_(appport=appport)

        if demo:
            from homecon.demo.__main__ import get_homecon as get_homecon_demo
            homecon = get_homecon_demo()
        else:
            homecon = get_homecon()

        # noinspection PyUnusedLocal
        def stop(signum, frame):
            if not homecon.running:
                sys.exit(1)
            else:
                homecon.stop()
                if app_server is not None:
                    app_server.terminate()
                    time.sleep(2)
                    app_server.kill()
                    app_server.join()

        signal(SIGTERM, stop)
        signal(SIGINT, stop)

        print('\nStarting HomeCon\nPress Ctrl + C to stop\n')
        homecon.start()


if __name__ == '__main__':

    parser = ArgumentParser(description='Homecon')
    parser.add_argument('-l', '--loglevel', type=str, choices=['INFO', 'DEBUG'], default='INFO')
    parser.add_argument('--dbloglevel', type=str, choices=['INFO', 'DEBUG'], default='INFO')
    parser.add_argument('--httploglevel', type=str, choices=['INFO', 'DEBUG'], default='INFO')
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--printlog', action='store_true')
    parser.add_argument('--noapp', dest='serve_app', action='store_false')
    parser.add_argument('--appport', type=int, default=12300)
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--nofolders', dest='create_folders', action='store_false')
    parser.add_argument('--nostaticip', dest='set_static_ip', action='store_false')
    parser.add_argument('--ip', type=str, default=None)
    parser.add_argument('--noinitscript', dest='run_init_script', action='store_false')
    parser.add_argument('--initscriptname', dest='init_script_name', type=str, default='homecon')
    parser.add_argument('--noipopt', dest='install_ipopt', action='store_false')
    parser.add_argument('--noknxd', dest='install_knxd', action='store_false')

    kwargs = vars(parser.parse_args())

    main(**kwargs)

