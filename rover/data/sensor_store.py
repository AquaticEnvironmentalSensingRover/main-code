from aesrdevicelib.sensors.mcp9808 import MCP9808
from aesrdevicelib.sensors.ms5803 import MS5803
from aesrdevicelib.sensors.gps_read import GPSRead
from aesrdevicelib.sensors.mb7047 import MB7047
from aesrdevicelib.sensors.vernier_odo import VernierODO
from aesrdatabaselib.mongo_write import MongoWrite
import aesrdatabaselib.main_util as mu
import threading
import time
import sys
import datetime


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

    def last_matching_status_data(self, atype=None, itype=None):
        dbCol = self.status_mongo.dbCol
        for ii in dbCol.find().sort([['_id', 1]]):
            new_atype = ii.get('atype', None)
            new_itype = ii.get('itype', None)
            if (new_atype == atype) and (new_itype == itype):
                return ii
        return None

    def update_status_data(self, message, atype=None, itype=None):
        dbCol = self.status_mongo.dbCol
        old_status_data = self.last_matching_status_data(atype, itype)
        new_status_data = message
        if not old_status_data is None:
            dbCol.update({'_id': old_status_data['_id']}, {'$set': new_status_data}, upsert=False)
        else:
            self.status_mongo.write(new_status_data)

    @staticmethod
    def create_device(device_type, sensor_constructor, *args, **kwargs):
        device = None

        try:
            device = sensor_constructor(*args, **kwargs)
            print(device_type + " device was successfully initialized!")
        except:
            print("Failed setting up " + device_type + " device")
        finally:
            return device

    def read_device(self, device, read_function_name, atype, paramUnit
                    , comments=None, tags=None, itype=None, vertype=1.0):
        if comments is None:
            comments = []
        if tags is None:
            tags = []

        current_time = time.time()
        base_write_data = {'atype': atype, 'ts': current_time,
                           'tss': datetime.datetime.fromtimestamp(current_time).strftime('%b %d, %Y %H:%M.%S')}
        if itype is not None:
            base_write_data['itype'] = itype

        try:
            if device is not None:
                # Write device read data to data collection
                param = getattr(device, read_function_name)()
                write_data = dict(base_write_data)
                write_data['vertype'] = vertype
                write_data['param'] = param
                write_data['paramunit'] = paramUnit
                write_data['comments'] = comments
                write_data['tags'] = tags

                self.device_mongo.write(write_data)

                # Update Status
                write_data = dict(base_write_data)
                write_data['vertype'] = 1.0
                write_data['param'] = 'OK'
                self.update_status_data(write_data, atype, itype)
            else:
                raise self.StartError("Start error")
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            write_data = dict(base_write_data)
            write_data['vertype'] = 1.0
            write_data['param'] = str(sys.exc_info()[1])

            self.update_status_data(write_data, atype, itype)

    def __init__(self, *args, gps: GPSRead=None, mongo_db=None):
        if mongo_db is None:
            mongo_db = mu.generateTimeName()

        print("\n================>MongoDB<==================")
        print("Using database name: \"" + mongo_db + "\"")

        self.device_mongo = MongoWrite(mongo_db, 'data')
        print("Connected to device MongoDB server successfully!")

        self.status_mongo = MongoWrite(mongo_db, 'status')
        print("Connected to status MongoDB server successfully!")

        print("=============================================\n")

        # =================Sensor Creation=================
        self.devices = {}

        print("\n===============>Sensor Setup<================")
        self.devices['temperature'] = [
            self.create_device('Temperature 0', MCP9808, 0x18),  # On its own cable
            self.create_device('Temperature 1', MCP9808, 0x18 + 1),  # On long cable with pressure sensor
            self.create_device('Temperature 2', MCP9808, 0x18 + 2)]  # Air temperature

        self.devices['pressure'] = self.create_device('Pressure', MS5803)

        self.devices['sonar'] = self.create_device('Sonar', MB7047)

        self.devices['odo'] = self.create_device('ODO', VernierODO)

        if gps is None:
            self.devices['gps'] = self.create_device('GPS', GPSRead)
        else:
            self.devices['gps'] = gps

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

            # GPS
            self.read_device(self.devices['gps'], 'readLocationData', atype='GPS', itype='main'
                             , paramUnit={'lat': 'latitude', 'lon': 'longitude'}
                             , comments=['Brick Yard Pond'], vertype=1.1)

            # PRESSURE Sensor
            self.read_device(self.devices['pressure'], 'read', atype='PRESR'
                             , paramUnit={'pressure': 'mbar', 'temp': 'degC'}
                             , comments=['Brick Yard Pond'])

            # TEMPERATURE Sensor
            for ii, tempSensor in enumerate(self.devices['temperature']):
                self.read_device(tempSensor, 'read', atype='TEMP', itype=ii
                                 , paramUnit='degC'
                                 , comments=['Brick Yard Pond'])

            # SONAR Sensor
            self.read_device(self.devices['sonar'], 'read', atype='SONAR'
                             , paramUnit='cm', comments=['Brick Yard Pond'])

            # ODO (Optical Dissolved Oxygen) Sensor
            self.read_device(self.devices['odo'], 'read', atype='ODO', vertype=1.1
                             , paramUnit={'rawADC': 'Raw value from ADC', 'mgL': 'Oxygen level in mg/L'}
                             , comments=['Brick Yard Pond'])

    def close_devices(self):
        if not self.devices['gps'] is None:
            self.devices['gps'].close()


class SensorStoreThreaded(SensorStore, threading.Thread):
    def __init__(self, *args, read_delay: int=1, gps: GPSRead = None, mongo_db=None, **kwargs):
        self.running = True
        self.read_delay = read_delay
        super().__init__(gps=gps, mongo_db=mongo_db)
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
