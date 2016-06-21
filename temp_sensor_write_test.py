from lib.sensors.mcp9808 import MCP9808
from lib.database.mongo_write import MongoWrite
import sys
import time

tempSensors = []

tempSensors.append(MCP9808(0x18))
tempSensors.append(MCP9808(0x18+4))
tempSensors.append(MCP9808(0x18+1))
tempSensors.append(MCP9808(0x18+2))
tempSensors.append(MCP9808(0x18+3))

mongo = MongoWrite(sys.argv[1], sys.argv[2])

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
    for ii, tempSensor in enumerate(tempSensors):
        mongo.write({"atype":"TEMP", "itype": ii, "vertype": 1.0
                    , "ts": time.time(), "param" : tempSensor.read()
                    , "paramunit": "degC", "comments" : "testing"
                    , "tags": ["temp", "test"]})
                    
    time.sleep(2)