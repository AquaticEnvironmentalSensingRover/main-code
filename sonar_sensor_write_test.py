from lib.sensors.mb7047 import MB7047
from lib.database.mongo_write import MongoWrite
import time, sys

mongo = MongoWrite(sys.argv[1], sys.argv[2])

sensor = MB7047()

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
    # read data from sensor (measured in centimeters)
    data = sensor.read()
    
    mongo.write({"atype":"SONAR", "vertype": 1.0, "ts": time.time()
                , "param" : data, "paramunit": "cm"
                , "comments" : "testing", "tags": ["sonar", "depth", "test"]})
                        
    time.sleep(1)