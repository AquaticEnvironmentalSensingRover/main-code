from lib.sensors.gps_read import GPSRead
from lib.database.mongo_write import MongoWrite
import sys
import time

mongo = MongoWrite(sys.argv[1], sys.argv[2])

gpsSensor = GPSRead()

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
    try:
        location = gpsSensor.readLocationData()
        mongo.write({"atype":"GPS", "vertype": 1.0, "ts": time.time()
                    , "param" : {"lat":location.lat,"lon":location.lon}
                    , "paramunit": "{degLat,degLon}", "comments" : "testing"
                    , "tags": ["gps", "test"]})
                        
        time.sleep(1)
    except ValueError:
        pass
    except KeyboardInterrupt:
        gpsSensor.close()
        quit()
gpsSensor.close()