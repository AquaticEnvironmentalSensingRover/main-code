from lib.sensors.mcp9808 import MCP9808
from lib.sensors.ms5803 import MS5803
from lib.sensors.gps_read import GPSRead
from lib.sensors.mb7047 import MB7047
from lib.sensors.vernier_odo import VernierODO
from lib.database.mongo_write import MongoWrite
import lib.main_util as mu
import time, sys, datetime

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

def lastMatchingStatusData(atype=None, itype=None):
    global statusMongo
    dbCol = statusMongo.dbCol
    for ii in dbCol.find().sort([["_id",1]]):
        newatype = ii.get('atype', None)
        newitype = ii.get('itype', None)
        if (newatype == atype) and (newitype == itype):
            return ii
    return None

def updateStatusData(message, atype=None, itype=None):
    global statusMongo
    dbCol = statusMongo.dbCol
    oldStatusData = lastMatchingStatusData(atype, itype)
    newStatusData = message
    if not oldStatusData == None:
        dbCol.update({'_id':oldStatusData['_id']}, {"$set": newStatusData}, upsert=False)
    else:
        statusMongo.write(newStatusData)

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
    
    currentTime = time.time()
    baseWriteData = {"atype": atype, "ts": currentTime
                , "tss": datetime.datetime.fromtimestamp(currentTime).strftime("%b %d, %Y %H:%M.%S")}
    if not itype == None:
        baseWriteData["itype"] = itype
        
    try:
        if not device == None:
            # Write device read data to data collection
            param = getattr(device, readFunctionName)()
            writeData = dict(baseWriteData)
            writeData["vertype"]= vertype
            writeData["param"]= param
            writeData["paramunit"]= paramUnit
            writeData["comments"]= comments
            writeData["tags"]= tags
            
            deviceMongo.write(writeData)
            
            # Update Status
            writeData = dict(baseWriteData)
            writeData["vertype"]= 1.0
            writeData["param"]= "OK"
            updateStatusData(writeData, atype, itype)
    except KeyboardInterrupt:
        raise sys.exc_info()
    except:
        writeData = dict(baseWriteData)
        writeData["vertype"]= 1.0
        writeData["param"]= str(sys.exc_info()[1])
        
        updateStatusData(writeData, atype, itype)

# =================Sensor Creation=================
devices = {}

print "\n===============>Sensor Setup<================"
tempSensors = []
tempSensors.append(createDevice("Temperature 0", MCP9808, 0x18))       # On its own cable
tempSensors.append(createDevice("Temperature 1", MCP9808, 0x18+1))     # On long cable with pressure sensor
tempSensors.append(createDevice("Temperature 2", MCP9808, 0x18+2))     # Air temperature
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
