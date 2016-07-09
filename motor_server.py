from flask_socketio import SocketIO
from flask import Flask, render_template, send_from_directory
import time, os
from lib.sensors.blue_esc import BlueESC
from lib.sensors.bno055 import BNO055

webserverFolderName = "motorwebserver"

app = Flask(__name__, static_folder = webserverFolderName + "/static"
            , template_folder = webserverFolderName + "/templates")

socketio = SocketIO(app)

# BlueESC instances
motors = {"n": BlueESC(0x2a), "s": BlueESC(0x2b), "e": BlueESC(0x2c), "w": BlueESC(0x2d)}

# BNO055 instance
imu = BNO055()
imu.setExternalCrystalUse(True)


lastConnectTime = None
running = True

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
    
    torque = (((compass - targetBearing)+180)%360) - 180
    
    # Y plane motors
    motors['n'].startPower(yValue + torque)
    motors['s'].startPower(-yValue + torque)
    
    # X plane motors
    motors['e'].startPower(xValue + torque)
    motors['w'].startPower(-xValue + torque)
    
    print xValue, yValue

@socketio.on('poll')
def poll(data):
    global lastConnectTime
    lastConnectTime = time.time()

@socketio.on('disconnect')
def disconnect():
    print('disconnect')
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000)