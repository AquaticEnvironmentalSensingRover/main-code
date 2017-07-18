from aesrdevicelib.sensors.gps_read import GPSRead
from aesrdevicelib.sensors.blue_esc import BlueESC
from aesrdevicelib.sensors.bno055 import BNO055
import threading
import time
import sys
import math


CONTROL_TIMEOUT = 2  # Seconds

FULL_PWR_DISTANCE = 10  # meters
MIN_PWR = 0.05  # out of 1

MAX_MTR_PWR = 20


def scale_m_distance(m: float):
    x = (-1 * FULL_PWR_DISTANCE * MIN_PWR) / (MIN_PWR - 1)  # applied to make m=FULL =>1 and m=0 =>MIN_PWR
    return (m/(FULL_PWR_DISTANCE+x)) + MIN_PWR


def scale_limit(s):
    max_ = 1
    min_ = -max_
    return int(max(min_, min(max_, s)))


class ThrusterControl(threading.Thread):
    def __init__(self, *args, gps: GPSRead=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.running = False
        self.auto_force_disable = False
        self.auto_position = None
        self.movement = {'x_trans': 0, 'y_trans': 0, 'xy_rot': 0, 'ts': None}  # Trans and rots are gains [-1.0, 1]

        """ ---- DEVICES ---- """
        # GPS Setup:
        if gps is None:
            print("No GPS, attempting to connect")
            try:
                self.gps = GPSRead()
                print("Successfully connected GPS")
            except:
                print("Error connecting to GPS")

        # BlueESC instances
        try:
            self.thrusters = {"f": BlueESC(0x2a), "b": BlueESC(0x2d), "l": BlueESC(0x2b),
                              "r": BlueESC(0x2c)}
        except IOError:
            print("Thruster setup error: " + str(sys.exc_info()[1]))
            print("Disabling thrusters...")
            self.thrusters = None

        # BNO055 sensor setup
        try:
            self.imu = BNO055()
            time.sleep(1)
            self.imu.setExternalCrystalUse(True)

            print("Wait for IMU calibration [move it around]...")
            while not self.imu.getCalibration() == (0x03,) * 4:
                time.sleep(0.5)
            print("IMU calibration finished.")

        except IOError:
            print("\nIMU setup error: " + str(sys.exc_info()[1]))
            print("Disabling IMU...")
            self.imu = None

    def start(self):
        self.running = True
        super().start()

    def close(self):
        self.running = False
        self.join()

    def stop_thrusters(self):
        if isinstance(self.thrusters, dict):
            for k, v in self.thrusters:
                self.thrusters[k].setPower(0)

    def manual_control(self, x=0, y=0, rot=0):
        self.movement = {'x_trans': x, 'y_trans': y, 'xy_rot': rot, 'ts': time.time()}

    def drive_thrusters(self, x, y, rot):
        pwrs = {
            'f': MAX_MTR_PWR * scale_limit(y + rot),
            'b': MAX_MTR_PWR * scale_limit(y - rot),
            'l': MAX_MTR_PWR * scale_limit(x + rot),
            'r': MAX_MTR_PWR * scale_limit(x - rot)}

        for k, v in pwrs.items():
            self.thrusters[k].startPower(v)

    def run(self):
        while self.running:
            # Recent control check:
            if self.movement['ts'] is None or ((time.time()-self.movement['ts']) > CONTROL_TIMEOUT):
                self.auto_position = None
                self.stop_thrusters()
                continue

            """--- Contact with control ---"""
            # Check if a control value is not None nor 0 (manual input -> cut off) or the position is incorrect
            #   or auto is not disabled
            if not isinstance(self.auto_position, dict)\
                    or not all((v == 0 or k is 'ts') for k, v in self.movement.items())\
                    or self.auto_force_disable:
                self.auto_position = None
            else:
                """--- Autonomous ---"""
                try:
                    loc = self.gps.readLocationData()
                except ValueError:
                    self.stop_thrusters()
                    print("AUTONOMOUS: NO GPS -- STOPPING THRUSTERS!")
                    continue

                # get position differences in meters
                pos_diff_m = (111320.*math.cos(math.radians(loc['lat']))*(self.auto_position['lon']-loc['lon']),  # x
                              110540. * (self.auto_position['lat'] - loc['lat']))  # y

                self.drive_thrusters(scale_m_distance(pos_diff_m[0]), scale_m_distance(pos_diff_m[1]), 0)
                # TODO: IMU read and angle hold

            if self.auto_position is None:
                self.drive_thrusters(self.movement['x_trans'], self.movement['y_trans'], self.movement['xy_rot'])
