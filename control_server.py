from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
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
try:
    from lib.sensors.blue_esc import BlueESC
    motors = {"n": BlueESC(0x2a), "s": BlueESC(0x2b), "e": BlueESC(0x2c), "w": BlueESC(0x2d)}
except:
    print "Motor setup error: " + str(sys.exc_info()[1])
    motors = None

# BNO055 sensor setup
try:
    from lib.sensors.bno055 import BNO055
    imu = BNO055()
    time.sleep(1)
    imu.setExternalCrystalUse(True)
except:
    print "IMU setup error: " + str(sys.exc_info()[1])
    print "Disabling IMU..."
    imu = None

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
    max_ = 600
    min_ = -max_
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
    
    print "\n"
    print xValue, yValue
    
    compass = None
    currentBearing = None
    torque = 0
    if not imu == None:
        compass = imu.getVector(BNO055.VECTOR_MAGNETOMETER)
        currentBearing = math.atan2(compass[1],compass[0])*180/math.pi
        torque = (((currentBearing - targetBearing)+180)%360) - 180
        
    print str(compass)
    
    motorPower = {'n': xValue + torque, 's': -xValue + torque
                , 'e': yValue + torque, 'w': -yValue + torque}
    motorPower = {k:normalizeMotorPower(v) for k,v in motorPower.iteritems()}
    
    print("N: " + str(motorPower['n']))
    print("S: " + str(motorPower['s']))
    print("E: " + str(motorPower['e']))
    print("W: " + str(motorPower['w']))
    
    if type(motors) == type(dict()):
        # X plane motors
        motors['n'].startPower(motorPower['n'])
        motors['s'].startPower(motorPower['s'])
        
        # Y plane motors
        motors['e'].startPower(motorPower['e'])
        motors['w'].startPower(motorPower['w'])
    
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