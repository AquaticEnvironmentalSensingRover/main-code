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

MAX_ERRORS = 10
errorAmount = 0

while True:
    try:
        data = sensor.read()
        mongo.write({"atype":"PRESR", "vertype": 1.0, "ts": time.time()
                    , "param" : {"pressure":data["mbar"],"temp":data["temp"]}
                    , "paramunit": {"pressure":"mbar", "temp":"degC"}
                    , "comments" : "testing", "tags": ["pressure", "test"]})
                    
        errorAmount = 0
        time.sleep(1)
    except IOError:
        print("Read write error")
        
        errorAmount += 1
        if errorAmount>=MAX_ERRORS:
            print("The amount of consecutive errors exceded the max amount "
                + " (" + MAX_ERRORS + ")")
            break