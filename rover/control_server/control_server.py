from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
from pymongo import MongoClient
from aesrdevicelib.sensors.gps_read import GPSRead
import time
import os
import sys
import math
from ..thruster_control import ThrusterControl

print("\nImports successfully completed\n")

# Static Variables
CONTROL_MODE = "R"
# "R": Rotation mode (Y: Strafe, X: Angle)
# "S": Strafe mode (Y: Strafe, X: Strafe)


DEBUG = True
WEBSERVER_FOLDER_NAME = "motorwebserver"


def normalize_motor_power(power):
    max_ = 10
    min_ = -max_
    return int(max(min_, min(max_, power)))


class ControlServer(SocketIO):
    def __init__(self, host, port, *args, gps: GPSRead=None, mongo_db=None):
        # Dynamic Variables
        self.app = Flask(__name__, static_folder=WEBSERVER_FOLDER_NAME + "/static",
                         template_folder=WEBSERVER_FOLDER_NAME + "/templates")

        super().__init__(self.app)

        self.host = host
        self.port = port

        self.thruster = ThrusterControl(gps=gps)

        self.lastConnectTime = None
        self.previousStatusData = []

        # Get status Collection object from inputted database name
        try:
            self.dbCol = (MongoClient()[mongo_db])["status"]
        except:
            self.dbCol = None

        # Routes:
        self.favicon = self.app.route('/favicon.ico')(self.favicon)
        self.index = self.app.route('/')(self.index)

        # Socket endpoints:
        self.connect = self.on('connect')(self.client_connect)
        self.set_auto_state = self.on('set_auto_state')(self.set_auto_state)
        self.req_auto_state = self.on('req_auto_state')(self.req_auto_state)
        self.input_control = self.on('input')(self.input_control)
        self.poll = self.on('poll')(self.poll)
        self.client_disconnect = self.on('disconnect')(self.client_disconnect)

        # Start motor drive thread:
        self.thruster.start()

    def run_server(self, **kwargs):
        try:
            super().run(self.app, self.host, self.port, **kwargs)
        finally:
            print("Close thruster object:")
            self.thruster.close()
            print("--EXIT--")

    def favicon(self):
        return send_from_directory(os.path.join(self.app.root_path, 'static'),
                                   'favicon.ico',
                                   mimetype='image/vnd.microsoft.icon')

    @staticmethod
    def index():
        """Serve the client-side application."""
        return render_template('index.html')

    def get_status_data(self):
        status_data = []
        for data in self.dbCol.find().sort([["_id", 1]]):
            del data[u'_id']
            status_data.append(data)
        return status_data

    @staticmethod
    def client_connect():
        print("Client Connect")

    def set_auto_state(self, data):
        if data['state'] == 1:
            self.thruster.next_auto_target()
        elif data['state'] == 0:
            self.thruster.disable_auto()

    # NOTE: When getting data from VirtualJoystick, make sure to check if it is
    # "up", "down", "left", or "right" to stop when finger is lifted off
    def input_control(self, data):
        print("Data: {}".format(data))
        # target_bearing = 10
        gain = 1  # 32767/80
        x_value = data['x']*gain
        y_value = data['y']*gain

        print("\n====================================")
        print("Joy X:", x_value, "|", "Joy Y:", y_value)

        self.thruster.manual_control(0, y_value, x_value)

        # Emit status data if collection was supplied:
        if self.dbCol is not None:
            emit("status", self.get_status_data())

    def req_auto_state(self, data):
        d = {'state': self.thruster.auto_enabled(), 'remaining': self.thruster.get_remaining_waypoints()}
        emit("auto_status", d)

    def poll(self, data):
        self.lastConnectTime = time.time()

    @staticmethod
    def client_disconnect():
        print('disconnect')

if __name__ == '__main__':
    cs = ControlServer(host="0.0.0.0", port=8000)
    cs.run_server()
