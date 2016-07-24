from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
from pymongo import MongoClient
import time, os, sys, math

print "\nImports successfully completed\n"

# Static Variables
CONTROL_MODE = "R"
# "R": Rotation mode (Y: Strafe, X: Angle)
# "S": Strafe mode (Y: Strafe, X: Strafe)


DEBUG = True
WEBSERVER_FOLDER_NAME = "motorwebserver"

# Dynamic Variables
app = Flask(__name__, static_folder = WEBSERVER_FOLDER_NAME + "/static"
            , template_folder = WEBSERVER_FOLDER_NAME + "/templates")
socketio = SocketIO(app)

# BlueESC instances
try:
    from lib.sensors.blue_esc import BlueESC
    motors = {"f": BlueESC(0x2a), "b": BlueESC(0x2d), "l": BlueESC(0x2b), "r": BlueESC(0x2c)}
except:
    print "Motor setup error: " + str(sys.exc_info()[1])
    print "Disabling motors..."
    motors = None

# BNO055 sensor setup
try:
    from lib.sensors.bno055 import BNO055
    imu = BNO055()
    time.sleep(1)
    imu.setExternalCrystalUse(True)
except:
    print "\nIMU setup error: " + str(sys.exc_info()[1])
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
    max_ = 10
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
    gain = 10 #32767/80
    xValue = int(data['x']*gain)
    yValue = int(data['y']*gain)
    
    print "\n===================================="
    print "Joy X:", xValue, "|", "Joy Y:", yValue
    
    # IMU Compass:
    compass = None
    currentBearing = None
    compassTorque = 0
    if not imu == None:
        compass = imu.getVector(BNO055.VECTOR_MAGNETOMETER)
        currentBearing = math.atan2(compass[1],compass[0])*180/math.pi
        compassTorque = (((currentBearing - targetBearing)+180)%360) - 180
        
    print "Bearing: " + str(currentBearing)
    print "Compass Torque: " + str(compassTorque)
    
    # Motor power calculation:
    torque = 0
    if CONTROL_MODE == "R":
        torque = xValue
        motorPower = {'f': torque, 'b': -torque
                    , 'l': yValue, 'r': yValue}
        
    else: # Strafe mode
        torque = compassTorque
        motorPower = {'f': xValue + torque, 'b': xValue - torque
                    , 'l': yValue + torque, 'r': yValue - torque}
    
    print "Torque: " + str(compassTorque)
    
    motorPower = {k:normalizeMotorPower(v) for k,v in motorPower.iteritems()}
    
    # Print motor speeds:
    print "\nMotors: "
    print("F: " + str(motorPower['f']))
    print("B: " + str(motorPower['b']))
    print("L: " + str(motorPower['l']))
    print("R: " + str(motorPower['r']))
    print "===================================="
    
    # Update motor speeds if they were setup correctly:
    if type(motors) == type(dict()):
        # X plane motors
        motors['f'].startPower(motorPower['f'])
        motors['b'].startPower(motorPower['b'])
        
        # Y plane motors
        motors['l'].startPower(motorPower['l'])
        motors['r'].startPower(motorPower['r'])
    
    # Emit status data if collection was supplied:
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
    try:
        socketio.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        if type(motors) == type(dict()):
            for k, v in motors:
                motors[k].setPower(0)