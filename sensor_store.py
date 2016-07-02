from lib.sensors.mcp9808 import MCP9808
from lib.sensors.ms5803 import MS5803
from lib.sensors.gps_read import GPSRead
from lib.sensors.mb7047 import MB7047
from lib.sensors.ads1115 import ADS1115
from lib.database.mongo_write import MongoWrite
from datetime import datetime
import time, sys

def valueReplaceScan(value):
    if type(value) == type(list()):
        newValue = []
        for ii in range(len(value)):
            newValue.append(valueReplaceScan(value[ii]))
    elif not value == None:
            newValue = "Ok"
    else:
        newValue = None
    
    return newValue


database = datetime.now().strftime("AESR_%Y%m%dT%H%M%S")
deviceMongo = MongoWrite(database, "data")
print "Connected to device MongoDB server successfully!"

statusMongo = MongoWrite(database, "status")
print "Connected to status MongoDB server successfully!"

def createDevice(deviceType, sensorConstructor, *args, **kwargs):
    try:
        device = sensorConstructor(*args, **kwargs)
        print(deviceType + " device was successfully initialized!")
    except:
        print "Failed setting up " + deviceType + " device"
        statusMongo.write({"atype": "STARTALERT", "vertype": 1.0, "ts": time.time()
                            , "itype": deviceType, "comments": ["Failed to set up"]
                            , "tags": ["failed", "setup", "set up"]})
        device = None
    finally:
        return device

def readDevice(device, readFunctionName, atype, paramUnit
                , comments = [], tags = [], itype = None, vertype = 1.0):
    try:
        if not device == None:
            # Write device read data to data collection
            param = getattr(device, readFunctionName)()
            writeData = {"atype": atype, "vertype": vertype, "ts": time.time()
                        , "param": param, "paramunit": paramUnit
                        , "comments": comments, "tags": tags}
            if not itype == None:
                writeData["itype"] = itype
            
            deviceMongo.write(writeData)
            
            # Write status to status collection
            writeData = {"atype": atype, "vertype": 1.0, "ts": time.time()
                        , "param": "Ok"}
            if not itype == None:
                writeData["itype"] = itype
            
            statusMongo.write(writeData)
    except KeyboardInterrupt:
        raise sys.exc_info()
    except:
        writeData = {"atype": atype, "vertype": 1.0, "ts": time.time()
                    , "param": str(sys.exc_info()[0])}
        
        if not itype == None:
            writeData["itype"] = itype
        
        statusMongo.write(writeData)

# =================Sensor Creation=================
devices = {}

print "\n============================" 
tempSensors = []
tempSensors.append(createDevice("Temperature 1", MCP9808, 0x18))
tempSensors.append(createDevice("Temperature 2", MCP9808, 0x18+4))
tempSensors.append(createDevice("Temperature 3", MCP9808, 0x18+1))
tempSensors.append(createDevice("Temperature 4", MCP9808, 0x18+2))
tempSensors.append(createDevice("Temperature 5", MCP9808, 0x18+3))
devices["temperature"] = tempSensors

devices["pressure"] = createDevice("Pressure", MS5803)

devices["sonar"] = createDevice("Sonar", MB7047)

devices["adc"] = createDevice("ADC", ADS1115)

devices["gps"] = createDevice("GPS", GPSRead)

# Print sensors
print "============================"
print "\n============================\nSensors:"

# Get keys and values of the "devices" dictionary separately
keys = []
values = []
for k,v in devices.items():
    keys.append(k)
    values.append(v)
   
# Run value replace scan with the values to format for printing
printValues = valueReplaceScan(values)

# Use printing values for "devicesPrint"
for ii, key in enumerate(keys):
    print str(key) + ": " + str(printValues[ii])
print "============================\n"

#{
#  ver : <float>
#  atype: <String>,
#  itype: <Integer> ,
#  vertype : <float> ,
#  ts : <timestamp> , # using simple time.time() initially but should change
#  param : <format depends on atype>
#  comment : <String> ,
#  message : <String>
#}

try:
    while True:
        # GPS
        readDevice(devices["gps"], "readLocationData", atype = "GPS"
                    , paramUnit = {"lat": "latitude", "lon": "longitude"}
                    , comments = ["Brick Yard Pond"])
                            
        # PRESSURE Sensor
        readDevice(devices["pressure"], "read", atype = "PRESR"
                    , paramUnit = {"pressure":"mbar", "temp":"degC"}
                    , comments = ["Brick Yard Pond"])
                
        # TEMPERATURE Sensor
        for ii, tempSensor in enumerate(devices["temperature"]):
            readDevice(tempSensor, "read", atype = "TEMP", itype = ii
                    , paramUnit = "degC"
                    , comments = ["Brick Yard Pond"])
        
        # SONAR Sensor
        readDevice(devices["sonar"], "read", atype = "SONAR"
                    , paramUnit = "cm"
                    , comments = ["Brick Yard Pond"])
        
        
        # ADS for Optical Dissolved Oxygen Sensor
        readDevice(devices["adc"], "read", atype = "ODO"
                    , paramUnit = "rawADC"
                    , comments = ["Brick Yard Pond"])
        
        time.sleep(1)
finally:
    if not devices["gps"] == None:
        devices["gps"].close()