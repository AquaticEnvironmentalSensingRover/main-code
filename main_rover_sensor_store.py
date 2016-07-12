from lib.sensors.mcp9808 import MCP9808
from lib.sensors.ms5803 import MS5803
from lib.sensors.gps_read import GPSRead
from lib.sensors.mb7047 import MB7047
from lib.sensors.vernier_odo import VernierODO
from lib.database.mongo_write import MongoWrite
import lib.main_util as mu
import time, sys

print "\nImports successfully completed\n"

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


try:
    database = sys.argv[1]
except:
    database = mu.generateTimeName()

print "\n================>MongoDB<=================="
print "Using database name: \"" + database + "\"" 

deviceMongo = MongoWrite(database, "data")
print "Connected to device MongoDB server successfully!"

statusMongo = MongoWrite(database, "status")
print "Connected to status MongoDB server successfully!"

print "=============================================\n"

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

print "\n===============>Sensor Setup<================"
tempSensors = []
tempSensors.append(createDevice("Temperature 4", MCP9808, 0x18))       # Thermometer closest to the pi
tempSensors.append(createDevice("Temperature 3", MCP9808, 0x18+4))
tempSensors.append(createDevice("Temperature 2", MCP9808, 0x18+1))
tempSensors.append(createDevice("Temperature 1", MCP9808, 0x18+2))
tempSensors.append(createDevice("Temperature 0", MCP9808, 0x18+3))     # Bottom thermometer
devices["temperature"] = tempSensors

devices["pressure"] = createDevice("Pressure", MS5803)

devices["sonar"] = createDevice("Sonar", MB7047)

devices["odo"] = createDevice("ODO", VernierODO)

devices["gps"] = createDevice("GPS", GPSRead)

print "=============================================\n"

# Print sensors
print "\n===============>Sensor List<================="

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
print "=============================================\n"

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
        readDevice(devices["gps"], "readLocationData", atype = "GPS", itype = "main"
                    , paramUnit = {"lat": "latitude", "lon": "longitude"}
                    , comments = ["Brick Yard Pond"], vertype = 1.1)
                            
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
        
        
        # ODO (Optical Dissolved Oxygen) Sensor
        readDevice(devices["odo"], "read", atype = "ODO", vertype = 1.1
                    , paramUnit = {'rawADC' : 'Raw value from ADC', 'mgL':'Oxygen level in mg/L'}
                    , comments = ["Brick Yard Pond"])
        
        time.sleep(1)
finally:
    if not devices["gps"] == None:
        devices["gps"].close()