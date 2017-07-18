from flask_socketio import SocketIO, emit
from flask import Flask, render_template, send_from_directory
from pymongo import MongoClient
from aesrdevicelib.sensors.blue_esc import BlueESC
from aesrdevicelib.sensors.bno055 import BNO055
import time
import os
import sys
import math

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
    def __init__(self, host, port, *args, mongo_db=None):
        # Dynamic Variables
        self.app = Flask(__name__, static_folder=WEBSERVER_FOLDER_NAME + "/static",
                         template_folder=WEBSERVER_FOLDER_NAME + "/templates")

        super().__init__(self.app)

        self.host = host
        self.port = port

        # BlueESC instances
        try:
            self.motors = {"f": BlueESC(0x2a), "b": BlueESC(0x2d), "l": BlueESC(0x2b),
                           "r": BlueESC(0x2c)}
        except IOError:
            print("Motor setup error: " + str(sys.exc_info()[1]))
            print("Disabling motors...")
            self.motors = None

        # BNO055 sensor setup
        try:
            self.imu = BNO055()
            time.sleep(1)
            self.imu.setExternalCrystalUse(True)

            print("Wait for IMU calibration [move it around]...")
            while not self.imu.getCalibration() == (0x03,)*4:
                time.sleep(0.5)
            print("IMU calibration finished.")

        except IOError:
            print("\nIMU setup error: " + str(sys.exc_info()[1]))
            print("Disabling IMU...")
            self.imu = None

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
        self.input_control = self.on('input')(self.input_control)
        self.poll = self.on('poll')(self.poll)
        self.client_disconnect = self.on('disconnect')(self.client_disconnect)

    def run_server(self, **kwargs):
        try:
            super().run(self.app, self.host, self.port, **kwargs)
        except:
            if isinstance(cs.motors, dict):
                for k, v in cs.motors:
                    v.setPower(0)

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
        print("connect")

    # NOTE: When getting data from VirtualJoystick, make sure to check if it is
    # "up", "down", "left", or "right" to stop when finger is lifted off
    def input_control(self, data):
        target_bearing = 10
        gain = 10  # 32767/80
        x_value = int(data['x']*gain)
        y_value = int(data['y']*gain)

        print("\n====================================")
        print("Joy X:", x_value, "|", "Joy Y:", y_value)

        # IMU Compass:
        current_bearing = None
        compass_torque = 0
        if self.imu is not None:
            compass = self.imu.getVector(BNO055.VECTOR_MAGNETOMETER)
            current_bearing = math.atan2(compass[1], compass[0]) * 180 / math.pi
            compass_torque = (((current_bearing - target_bearing) + 180) % 360) - 180

        print("Bearing: " + str(current_bearing))
        print("Compass Torque: " + str(compass_torque))

        # Motor power calculation:
        if CONTROL_MODE == "R":
            torque = x_value
            motor_power = {'f': torque, 'b': -torque,
                           'l': y_value, 'r': y_value}

        else:  # Strafe mode
            torque = compass_torque
            motor_power = {'f': x_value + torque, 'b': x_value - torque,
                           'l': y_value + torque, 'r': y_value - torque}

        print("Torque: " + str(torque))

        motor_power = {key: normalize_motor_power(val) for key, val in motor_power.items()}

        # Print motor speeds:
        print("\nMotors: ")
        print("F: " + str(motor_power['f']))
        print("B: " + str(motor_power['b']))
        print("L: " + str(motor_power['l']))
        print("R: " + str(motor_power['r']))
        print("====================================")

        # Update motor speeds if they were setup correctly:
        if isinstance(self.motors, dict):
            # X plane motors
            self.motors['f'].startPower(motor_power['f'])
            self.motors['b'].startPower(motor_power['b'])

            # Y plane motors
            self.motors['l'].startPower(motor_power['l'])
            self.motors['r'].startPower(motor_power['r'])

        # Emit status data if collection was supplied:
        if self.dbCol is not None:
            emit("status", self.get_status_data())

    def poll(self, data):
        self.lastConnectTime = time.time()

    @staticmethod
    def client_disconnect():
        print('disconnect')

if __name__ == '__main__':
    cs = ControlServer(host="0.0.0.0", port=8000)
    cs.run_server()
