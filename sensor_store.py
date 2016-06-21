from lib.sensors.mcp9808 import MCP9808
from lib.sensors.gps_read import GPSRead
from lib.database.mongo_write import MongoWrite
import sys
import datetime, time

tempSensors = []

tempSensors.append(MCP9808(0x18))
tempSensors.append(MCP9808(0x18+4))
tempSensors.append(MCP9808(0x18+1))
tempSensors.append(MCP9808(0x18+2))
tempSensors.append(MCP9808(0x18+3))

gpsSensor = GPSRead()

mongo = MongoWrite(datetime.now().strftime("AESR-%Y%m%d:%H%M%S"), "data")

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

while True:
    try:
        location = gpsSensor.readLocationData()
        mongo.write({"atype":"GPS", "vertype": 1.0, "ts": time.time()
                    , "param" : {"lat":location.lat,"lon":location.lon}
                    , "paramunit": "{degLat,degLon}", "comments" : "testing"
                    , "tags": ["gps", "test"]})
    except ValueError:
        pass
    
    for ii, tempSensor in enumerate(tempSensors):
        mongo.write({"atype":"TEMP", "itype": ii, "vertype": 1.0
                    , "ts": time.time(), "param" : tempSensor.read()
                    , "paramunit": "degC", "comments" : "testing"
                    , "tags": ["temp", "test"]})    
    time.sleep(1)