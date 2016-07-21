from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
from lib.sensors.blue_esc import BlueESC
from lib.sensors.bno055 import BNO055
from pymongo import MongoClient
import time, os, sys, math

print "\nImports successfully completed\n"

# Static Variables
DEBUG = True
WEBSERVER_FOLDER_NAME = "motorwebserver"


# Dynamic Variables
app = Flask(__name__, static_folder = WEBSERVER_FOLDER_NAME + "/static"
            , template_folder = WEBSERVER_FOLDER_NAME + "/templates")
socketio = SocketIO(app)

# BlueESC instances
#motors = {"n": BlueESC(0x2a), "s": BlueESC(0x2b), "e": BlueESC(0x2c), "w": BlueESC(0x2d)}

# BNO055 sensor setup
imu = BNO055()
time.sleep(1)
imu.setExternalCrystalUse(True)

lastConnectTime = None

previousStatusData = []

# Get status Collection object from inputted database name
try:
    dbCol = (MongoClient()[sys.argv[1]])["status"]
except:
    dbCol = None

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    """Serve the client-side application."""
    return render_template('index.html')

def getStatusData():
    statusData = []
    for data in dbCol.find().sort([["_id",1]]):
        del data[u'_id']
        statusData.append(data)
    return statusData
    
def normalizeMotorPower(power):
    min_ = 0
    max_ = 600
    return int(max(min_, min(max_, power)))
    
@socketio.on('connect')
def connect():
    print("connect")

# NOTE: When getting data from VirtualJoystick, make sure to check if it is
# "up", "down", "left", or "right" to stop when finger is lifted off
@socketio.on('input')
def inputControl(data):
    targetBearing = 10
    gain = 32767/80
    xValue = int(data['x']*gain)
    yValue = int(data['y']*gain)
    
    compass = imu.getVector(BNO055.VECTOR_MAGNETOMETER)
    
    print "\n" + str(compass)
    currentBearing = math.atan2(compass[1],compass[0])*180/math.pi
    torque = (((currentBearing - targetBearing)+180)%360) - 180
    
    motorPower = {'n': xValue + torque, 's': -xValue + torque
                , 'e': yValue + torque, 'w': -yValue + torque}
    motorPower = {k:normalizeMotorPower(v) for k,v in motorPower.iteritems()}
    
    # X plane motors
    #motors['n'].startPower(motorPower['n'])
    print("N: " + str(motorPower['n']))
    #motors['s'].startPower(motorPower['s'])
    print("S: " + str(motorPower['s']))
    
    # Y plane motors
    #motors['e'].startPower(motorPower['e'])
    print("E: " + str(motorPower['e']))
    #motors['w'].startPower(motorPower['w'])
    print("W: " + str(motorPower['w']))
    
    print xValue, yValue
    
    if not dbCol == None:
        emit("status", getStatusData())

@socketio.on('poll')
def poll(data):
    global lastConnectTime
    lastConnectTime = time.time()

@socketio.on('disconnect')
def disconnect():
    print('disconnect')
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000)