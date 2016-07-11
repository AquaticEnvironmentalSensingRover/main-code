from flask_socketio import SocketIO
from flask import Flask, render_template, send_from_directory
from lib.sensors.blue_esc import BlueESC
from lib.sensors.bno055 import BNO055
from pymongo import MongoClient
import time, os, sys

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
    
    compass = imu.getVector(BNO055.VECTOR_EULER)
    
    print "\n" + str(compass)
    
    torque = (((compass[0] - targetBearing)+180)%360) - 180
    
    # X plane motors
    #motors['n'].startPower(xValue + torque)
    print("N: " + str(xValue + torque))
    #motors['s'].startPower(-xValue + torque)
    print("S: " + str(-xValue + torque))
    
    # Y plane motors
    #motors['e'].startPower(yValue + torque)
    print("E: " + str(yValue + torque))
    #motors['w'].startPower(-yValue + torque)
    print("W: " + str(-yValue + torque))
    
    print xValue, yValue
    
    if not dbCol == None:
        statusData = []
        for data in dbCol.find():
            newData = dict(data)
            del newData[u'_id']
            
            statusData.append(newData)
        socketio.emit("status", statusData)

@socketio.on('poll')
def poll(data):
    global lastConnectTime
    lastConnectTime = time.time()

@socketio.on('disconnect')
def disconnect():
    print('disconnect')
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000)