from lib import sensors, database
import time

tempSensors = []

for ii in range(4):
    tempSensors.append(sensors.mcp9808.MCP9808(0x18+ii))

mongo = database.MongoWrite("test_data1", "tempData")

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
        #mongo.write
        print({"atype":"TEMP", "itype": ii, "vertype": 1.0
                    , "ts": time.time(), "param" : tempSensor.read()
                    , "paramunit": "degC", "comments" : "testing"
                    , "tags": ["temp", "test"]})
                    
    time.sleep(0.5)