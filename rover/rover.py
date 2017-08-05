import logging
from log4mongo.handlers import MongoHandler
from aesrdevicelib.sensors.gps_read import GPSRead
from aesrdatabaselib.main_util import generateTimeName
from pymongo import MongoClient
import time
from .thruster_control import BLUEESC_COM_I2C


MONGO_HOST = {'host': 'localhost', 'port': 27017}


class AESRover:
    def __init__(self, sensor_store=False, thruster_control=False, blue_esc_com=BLUEESC_COM_I2C):
        print("=====Initializing rover=====\n")
        # Generate db for run:
        self.db_name = generateTimeName()  # TODO
        print("Mongo Database Name: {}\n\n".format(self.db_name))

        # Mongo Client setup:
        print("Creating mongo client...", end='', flush=True)
        self.mongo_client = MongoClient(**MONGO_HOST)  # MongoClient setup
        self.mongo_db = self.mongo_client[self.db_name]
        time.sleep(1)
        print("\rSuccessfully created mongo client.")

        # Logger setup:
        print("Creating logger...", end='', flush=True)
        try:
            self.logger = logging.getLogger('AESR')
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(logging.StreamHandler())  # Prints to console
            self.logger.addHandler(MongoHandler(database_name=self.db_name, collection='log', **MONGO_HOST))
            self.logger.info("Initialized logger.", extra={'type': 'START'})
        except:
            print("\rFailed to create logger.\n")
            raise
        print("\rSuccessfully created logger.\n")

        # GPS Setup:
        print("Creating gps...", end='', flush=True)
        try:
            self.gps = GPSRead()
            print("\r", end='')
            self.logger.info("Successfully created gps.", extra={'type': 'DEVICE', 'n': 'gps', 'state': True})
        except:
            self.gps = None
            print("\r", end='')
            self.logger.exception("Failed to create gps.\n---WILL NOT ENABLE AUTO OR RECORD POSITION---",
                                  extra={'type': 'DEVICE', 'n': 'gps', 'state': False})

        print("\n\n====MODULE INITIALIZATION:====")
        if sensor_store is True:
            print("Creating sensor store...", end='', flush=True)
            from .data import sensor_store as sstore
            self.sensor_store = sstore.SensorStoreThreaded(self.mongo_db, gps=self.gps)
            print("\rSuccessfully created sensor store.")
            self.logger.info("Sensor Store: ENABLED", extra={'type': 'MODULE', 'n': 'sensor_store', 'state': True})
        else:
            self.logger.info("Sensor Store: DISABLED", extra={'type': 'MODULE', 'n': 'sensor_store', 'state': False})
            self.sensor_store = None

        print("\n")

        if thruster_control is True:
            print("Creating thruster control...")
            from .control_server import control_server
            self.control_server = control_server.ControlServer('0.0.0.0', 8000, logger=self.logger,
                                                               blue_esc_com=blue_esc_com, gps=self.gps,
                                                               mongo_db=self.mongo_client)
            print("Successfully created thruster control.")
            self.logger.info("Thruster Control: ENABLED",
                             extra={'type': 'MODULE', 'n': 'thruster_control', 'state': True})
        else:
            self.logger.info("Thruster Control: DISABLED",
                             extra={'type': 'MODULE', 'n': 'thruster_control', 'state': False})
            self.control_server = None

    def close(self):
        if self.gps is not None:
            self.gps.close()
        self.mongo_client.close()

    def run(self, close_onexit=True):
        try:
            if self.sensor_store is not None:  # Start sensor store (if enabled)
                self.sensor_store.start()

            if self.control_server is not None:  # Start control server (if enabled)
                self.control_server.run_server()
            else:
                while True:  # No control server to block thread, so manually do it.
                    time.sleep(0.2)
        finally:
            if self.sensor_store is not None:
                self.sensor_store.close()  # Stop sensor thread
            if close_onexit is True:
                self.close()  # Close devices and such
            self.logger.debug("Rover EXIT", extra={'type': 'EXIT'})
            print("Rover EXIT")
