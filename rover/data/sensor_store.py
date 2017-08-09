from aesrdevicelib.sensors.gps_read import GPSRead
from aesrdevicelib.sensors.tsys01 import TSYS01
from aesrdevicelib.sensors.ms5837 import MS5837
from aesrdevicelib.sensors.vernier_odo import VernierODO
from aesrdevicelib.sensors.bme280 import BME280
from aesrdevicelib.other.tca9548a import TCA9548A
from pymongo.database import Database
from typing import Tuple, Any
import inspect
import threading
import time
import sys
import datetime
from . import data_source


class SensorStore:
    class StartError(Exception):
        def __init__(self, *args, **kwargs):
            # Call the base class constructor
            super().__init__(*args, **kwargs)

    def value_replace_scan(self, value):
        if isinstance(value, list):
            new_value = []
            for ii in range(len(value)):
                new_value.append(self.value_replace_scan(value[ii]))
        elif value is not None:
            new_value = 'Ok'
        else:
            new_value = None

        return new_value

    def create_device(self, atype, param_unit, sensor, read_func, args=None, kwargs=None, data_aq_func=None, itype=None, description=None,
                      vertype=1.0):
        dev_name = atype
        if itype is not None:
            dev_name += "-{}".format(itype)

        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}

        if inspect.isclass(sensor):
            try:
                device = sensor(*args, **kwargs)
                print(dev_name + " device was successfully initialized!")
            except Exception as e:
                print("Failed setting up " + dev_name + " device ({})".format(e))
                return None
        else:
            device = sensor

        if not callable(read_func):
            read_func = getattr(device, read_func)
        if data_aq_func is not None:
            def new_func():
                getattr(device, data_aq_func)()
                return read_func()
            func = new_func
        else:
            func = read_func
        return (device, data_source.DataSource(self.device_mongo, self.status_mongo, self.logger, func, atype,
                                               param_unit, itype, description, vertype))

    @staticmethod
    def read_device(dev: Tuple[Any, data_source.DataSource]):
        if dev is not None:
            dev[1].read_store()

    def __init__(self, mongo_db: Database, logger, *args, gps: GPSRead=None):
        self.logger = logger

        self.device_mongo = mongo_db['data']
        self.status_mongo = mongo_db['status']

        # =================Sensor Creation=================
        self.devices = {}

        print("\n===============>Sensor Setup<================")
        try:
            tca = TCA9548A()
        except:
            self.logger.exception("TCA Multiplexer failed to start", extra={'type': 'DEVICE', 'device': 'TCA9549A',
                                                                            'state': False})
        else:
            #tca.select_channel(0),
            self.devices['temperature'] = self.create_device('temp', 'C', TSYS01, 'read',
                                                             kwargs={'pre_func': tca.select_channel, 'pre_func_args': (0,)})

            self.devices['pressure'] = self.create_device('pres', {'pres': 'mbar', 'temp': 'degC'}, MS5837,
                                                          'pressure', data_aq_func='read') # kwargs={'pre_func': tca.select_channel,
                                                                              #'pre_func_args': (0,)}

            self.devices['bathyenv'] = self.create_device('bathyenv', 'humidity', BME280, 'get_humidity',
                                                          kwargs={'i2c_address': 0x77, 'pre_func': tca.select_channel, 'pre_func_args': (2,)}, data_aq_func='read_data')

        self.devices['odo'] = self.create_device('odo', {'rawADC': 'Raw value from ADC', 'mgL': 'Oxygen level in mg/L'},
                                                 VernierODO, 'read', vertype=1.1)

        if gps is None:
            gps = GPSRead
            self.external_gps = False
        else:
            self.external_gps = True

        self.devices['gps'] = self.create_device('gps', {'lat': 'latitude', 'lon': 'longitude'}, gps,
                                                 'readLocationData', itype='main', vertype=1.1)

        print("=============================================\n")

        # Print sensors
        print("\n===============>Sensor List<=================")

        # Get keys and values of the "devices" dictionary separately
        keys = []
        values = []
        for k, v in self.devices.items():
            keys.append(k)
            values.append(v)

        # Run value replace scan with the values to format for printing
        print_values = self.value_replace_scan(values)

        # Use printing values for "devicesPrint"
        for ii, key in enumerate(keys):
            print(str(key) + ": " + str(print_values[ii]))
        print("=============================================\n")

    def read(self):
        # {
        #  ver : <float>
        #  atype: <String>,
        #  itype: <Integer> ,
        #  vertype : <float> ,
        #  ts : <timestamp> , # using simple time.time() initially but should change
        #  param : <format depends on atype>
        #  comment : <String> ,
        #  message : <String>
        # }

        for n, s in self.devices.items():
            if isinstance(s, list):
                for i in s:
                    self.read_device(i)
            else:
                self.read_device(s)

    def close_devices(self):
        if self.external_gps is False and not self.devices['gps'] is None:
            self.devices['gps'][0].close()


class SensorStoreThreaded(SensorStore, threading.Thread):
    def __init__(self, mongo_db, logger, *args, read_delay: int=1, gps: GPSRead = None, **kwargs):
        self.running = True
        self.read_delay = read_delay
        super().__init__(mongo_db, logger, gps=gps)
        threading.Thread.__init__(self, *args, **kwargs)

    def run(self):
        try:
            while self.running:
                self.read()
                time.sleep(self.read_delay)
        finally:
            self.close_devices()

    def close(self):
        self.running = False
        self.join()
