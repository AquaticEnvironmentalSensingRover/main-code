from lib.sensors.ms5803 import MS5803
from lib.database.mongo_write import MongoWrite
import time, sys

mongo = MongoWrite(sys.argv[1], sys.argv[2])

sensor = MS5803()

#{
#  ver : <float>
#  atype: <String>,
#  vertype : <float> ,
#  ts : <timestamp> , # using simple time.time() initially but should change
#  param : <format depends on atype>
#  comment : <String> ,
#  message : <String>
#}

while True:
    data = sensor.read()
    mongo.write({"atype":"PRESR", "vertype": 1.0, "ts": time.time()
                , "param" : {"pressure":data["mbar"],"temp":data["mbar"]}
                , "paramunit": {"pressure":"mbar", "temp":"degC"}
                , "comments" : "testing", "tags": ["pressure", "test"]})
                        
    time.sleep(1)