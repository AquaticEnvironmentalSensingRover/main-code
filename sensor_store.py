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

def createDevice(deviceType, sensorConstructor, *args, **kwargs):
    try:
        device = sensorConstructor(*args, **kwargs)
        print(deviceType + " device was successfully initialized!")
    except:
        print "Failed setting up " + deviceType + " device"
        device = None
    finally:
        return device


mongo = MongoWrite(datetime.now().strftime("AESR_%Y%m%dT%H%M%S"), "data")
print "Connected to mongoDB server successfully!"


def readDevice(device, readFunctionName, atype, paramUnit
                , comments = [], tags = [], itype = None):
    try:
        if not device == None:
            param = getattr(device, readFunctionName)()
            
            writeData = {"atype": atype, "vertype": 1.0, "ts": time.time()
                        , "param": param, "paramunit": paramUnit
                        , "comments": comments, "tags": tags}
            
            if itype == None:
                writeData["itype"] = itype
            
            mongo.write(writeData)
    except KeyboardInterrupt:
        raise sys.exc_info()
    except:
        mongo.write({"atype": "ALERT", "vertype": 1.0, "itype": atype
                    , "ts": time.time(), "param": str(sys.exc_info()[0])})

# =================Sensor Creation=================
devices = {}

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
print "\nSensors:"

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