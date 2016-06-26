from lib.sensors.mcp9808 import MCP9808
from lib.sensors.ms5803 import MS5803
from lib.sensors.gps_read import GPSRead
from lib.sensors.mb7047 import MB7047
from lib.sensors.ads1115 import ADS1115
from lib.database.mongo_write import MongoWrite
from datetime import datetime
import time, sys

def createDevice(deviceType, sensorConstructor, *args, **kwargs):
    try:
        device = sensorConstructor(*args, **kwargs)
        print(deviceType + " device was successfully initialized!")
        return device
    except:
        print "Failed setting up " + deviceType + " device"
        return None

mongo = MongoWrite(datetime.now().strftime("AESR_%Y%m%dT%H%M%S"), "data")
print "Connected to mongoDB server successfully!"

tempSensors = []
tempSensors.append(createDevice("temperature 1", MCP9808, 0x18))
tempSensors.append(createDevice("temperature 2", MCP9808, 0x18+4))
tempSensors.append(createDevice("temperature 3", MCP9808, 0x18+1))
tempSensors.append(createDevice("temperature 4", MCP9808, 0x18+2))
tempSensors.append(createDevice("temperature 5", MCP9808, 0x18+3))

pressureSensor = createDevice("pressure", MS5803)

sonarSensor = createDevice("sonar", MB7047)

adsDevice = createDevice("ADS", ADS1115)

gpsSensor = createDevice("GPS", GPSRead)

print "Sensors created!"
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
            if not gpsSensor == None:
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
            if not pressureSensor == None:
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
                if not tempSensor == None:
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
            if not sonarSensor == None:
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
            if not adsDevice == None:
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
finally:
    gpsSensor.close()