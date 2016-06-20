from lib.sensors.gps_read import GPSRead
from lib.database.mongo_write import MongoWrite
import time

gpsSensor = GPSRead()

mongo = MongoWrite("test_data3", "gpsData")

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
    location = gpsSensor.readLocationData()
    mongo.write({"atype":"GPS", "vertype": 1.0, "ts": time.time()
                , "param" : {"lat":location.lat,"lon":location.lon}
                , "paramunit": "{degLat,degLon}", "comments" : "testing"
                , "tags": ["gps", "test"]})
                    
    time.sleep(1)