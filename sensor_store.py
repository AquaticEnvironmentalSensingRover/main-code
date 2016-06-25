from lib.sensors.mcp9808 import MCP9808
from lib.sensors.ms5803 import MS5803
from lib.sensors.gps_read import GPSRead
from lib.sensors.mb7047 import MB7047
from lib.sensors.ads1115 import ADS1115
from lib.database.mongo_write import MongoWrite
from datetime import datetime
import time, sys

mongo = MongoWrite(datetime.now().strftime("AESR_%Y%m%dT%H%M%S"), "data")
print "Connected to mongoDB server successfully!"

tempSensors = []
tempSensors.append(MCP9808(0x18))
tempSensors.append(MCP9808(0x18+4))
tempSensors.append(MCP9808(0x18+1))
tempSensors.append(MCP9808(0x18+2))
tempSensors.append(MCP9808(0x18+3))

pressureSensor = MS5803()

sonarSensor = MB7047()

adsDevice = ADS1115()

gpsSensor = GPSRead()

print "Sensors created successfully!"
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
        try:
            location = gpsSensor.readLocationData()
            mongo.write({"atype":"GPS", "vertype": 1.0, "ts": time.time()
                        , "param" : {"lat":location.lat,"lon":location.lon}
                        , "paramunit": "{degLat,degLon}", "comments" : "testing"
                        , "tags": ["gps", "test"]})
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            mongo.write({"atype":"ALERT", "vertype": 1.0, "itype":"GPS"
                        , "ts": time.time(), "param":str(sys.exc_info()[0])})
        
        # PRESSURE Sensor
        try:
            pData = pressureSensor.read()
            mongo.write({"atype":"PRESR", "vertype": 1.0, "ts": time.time()
                        , "param" : {"pressure":pData["mbar"],"temp":pData["temp"]}
                        , "paramunit": {"pressure":"mbar", "temp":"degC"}
                        , "comments" : "testing", "tags": ["pressure", "test"]})
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            mongo.write({"atype":"ALERT", "vertype": 1.0, "itype":"PRESR"
                        , "ts": time.time(), "param":str(sys.exc_info()[0])})
        
        # TEMPERATURE Sensor
        try:
            for ii, tempSensor in enumerate(tempSensors):
                tData = tempSensor.read()
                mongo.write({"atype":"TEMP", "itype": ii, "vertype": 1.0
                            , "ts": time.time(), "param" : tData
                            , "paramunit": "degC", "comments" : "testing"
                            , "tags": ["temp", "test"]})
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            mongo.write({"atype":"ALERT", "vertype": 1.0, "itype":"TEMP"
                        , "ts": time.time(), "param":str(sys.exc_info()[0])})
        
        # SONAR Sensor
        try:
            sData = sonarSensor.read()
            mongo.write({"atype":"SONAR", "vertype": 1.0, "ts": time.time()
                        , "param" : sData, "paramunit": "cm"
                        , "comments" : "testing", "tags": ["sonar", "depth", "test"]})
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            mongo.write({"atype":"ALERT", "vertype": 1.0, "itype":"SONAR"
                        , "ts": time.time(), "param":str(sys.exc_info()[0])})
        
        # ADS for Optical Dissolved Oxygen Sensor
        try:
            oData = adsDevice.read()
            mongo.write({"atype":"ODO", "vertype": 1.0, "ts": time.time()
                        , "param" : oData, "paramunit": "rawADC"
                        , "comments" : "testing"
                        , "tags": ["oxygen", "dissolved", "ADC"]})
        except KeyboardInterrupt:
            raise sys.exc_info()
        except:
            mongo.write({"atype":"ALERT", "vertype": 1.0, "itype":"SONAR"
                        , "ts": time.time(), "param":str(sys.exc_info()[0])})

        time.sleep(1)
except KeyboardInterrupt:
    gpsSensor.close()
    raise sys.exc_info()