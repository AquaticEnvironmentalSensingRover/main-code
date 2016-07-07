from flask_socketio import SocketIO
from flask import Flask, render_template, send_from_directory
import time, os
from lib.sensors.blue_esc import BlueESC

webserverFolderName = "motorwebserver"

app = Flask(__name__, static_folder = webserverFolderName + "/static"
            , template_folder = webserverFolderName + "/templates")

socketio = SocketIO(app)

motor = BlueESC()

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
    gain = 32767/80
    xValue = int(data['x']*gain)
    motor.startPower(xValue)
    print data
    print xValue

@socketio.on('poll')
def poll(data):
    global lastConnectTime
    lastConnectTime = time.time()

@socketio.on('disconnect')
def disconnect():
    print('disconnect')
    
if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=8000)