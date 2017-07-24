from aesrdevicelib.sensors.gps_read import GPSRead
try:
    from aesrdevicelib.sensors.blue_esc import BlueESC
    from aesrdevicelib.sensors.bno055 import BNO055
except ImportError:  # SMBus doesn't exist: probably debugging
    print("Can't import BlueESC or/and BNO055. WILL ENTER DEBUG")
from . import util
import threading
import logging
import time
import sys
import math


CONTROL_TIMEOUT = 2  # Seconds

DISTANCE_DEADBAND = 0.1  # meters

FULL_PWR_DISTANCE = 10  # meters
MIN_PWR = 0.05  # out of 1

MAX_MTR_PWR = 20

AUTO_LOG_CYCLE_WAIT = 50


def scale_m_distance(m: float):
    if abs(m) < DISTANCE_DEADBAND:
        return 0
    x = (-1 * FULL_PWR_DISTANCE * MIN_PWR) / (MIN_PWR - 1)  # applied to make m=FULL =>1 and m=0 =>MIN_PWR
    return (m/(FULL_PWR_DISTANCE+x)) + MIN_PWR


def scale_limit(s):
    max_ = 1
    min_ = -max_
    return max(min_, min(max_, s))


class ThrusterControl(threading.Thread):
    def __init__(self, logger: logging.Logger, *args, gps: GPSRead=None, **kwargs):
        super().__init__(**kwargs)

        self.name = "ThrusterController"  # Set thread name

        self.AUTO_TARGETS = [{'lat': 41.73505, 'lon': -71.319}, {'lat': 41.736, 'lon': -71.320}]
        self.TARGET_BEARING = 0

        self._DEBUG = False  # will enable if motors fail to initialize

        self.running = False
        self.auto_force_disable = False
        self.auto_target = None
        self.movement = {'x_trans': 0, 'y_trans': 0, 'xy_rot': 0, 'ts': None}  # Trans and rots are gains [-1.0, 1]

        self.motors_disabled_prev = True
        self.auto_cycle_count = 0

        self.logger = logger

        """ ---- DEVICES ---- """
        # BlueESC instances
        try:
            self.thrusters = {"f": BlueESC(0x2a), "b": BlueESC(0x2d), "l": BlueESC(0x2b),
                              "r": BlueESC(0x2c)}
        except (IOError, NameError):
            self.logger.exception("Thruster setup error (DISABLING THRUSTERS) -- Entering DEBUG MODE")
            self._DEBUG = True
            self.thrusters = None

        # GPS Setup:
        if gps is None:
            self.external_gps = False
            self.logger.warning("No external GPS, attempting to connect.",
                                extra={'type': 'DEVICE', 'device': 'gps', 'state': 'CREATING'})
            try:
                self.gps = GPSRead()
                self.logger.info("Successfully connected to new GPS.",
                                 extra={'type': 'DEVICE', 'device': 'gps', 'state': True})
            except:
                self.gps = None
                self.logger.info("Error connecting to GPS.",
                                 extra={'type': 'DEVICE', 'device': 'gps', 'state': False})
                self.disable_auto_not_debug()  # No gps, no autonomous... (unless in debug mode)
        else:
            self.external_gps = True
            self.gps = gps

        # BNO055 sensor setup
        try:
            self.imu = BNO055()
            time.sleep(1)
            self.imu.set_external_crystal(True)

            self.logger.info("Waiting for IMU calibration [move it around]...",
                             extra={'type': 'DEVICE', 'device': 'IMU', 'state': 'calibration'})
            while not self.imu.getCalibration() == (0x03,) * 4:
                time.sleep(0.5)
            self.logger.info("IMU setup and calibration complete.",
                             extra={'type': 'DEVICE', 'device': 'IMU', 'state': True})
        except (IOError, NameError):
            self.logger.exception("IMU failed to setup -- DISABLING IMU",
                                  extra={'type': 'DEVICE', 'device': 'IMU', 'state': False})
            self.imu = None

            # Force disable autonomous if the IMU failed to initialize (if not in debug mode)
            self.disable_auto_not_debug()

    def disable_auto_not_debug(self):  # Disable auto, if not in debug mode
        if not self._DEBUG:
            self.logger.warning("Disabling autonomous.", extra={'type': 'AUTO', 'state': False})
            self.auto_force_disable = True

    @staticmethod
    def print_debug(*args, **kwargs):
        print("ThrusterControl: DEBUG -", *args, **kwargs)

    def print_only_debug(self, *args, **kwargs):
        if self._DEBUG:
            self.print_debug(*args, **kwargs)

    def start(self):
        self.running = True
        super().start()

    def close(self):
        self.stop_thrusters()
        if self.external_gps is False and self.gps is not None:
            self.gps.close()
        self.running = False
        self.join()

    def stop_thrusters(self):
        self.drive_thrusters(0, 0, 0)

    def manual_control(self, x=0, y=0, rot=0):
        self.movement = {'x_trans': x, 'y_trans': y, 'xy_rot': rot, 'ts': time.time()}

    def drive_thrusters(self, x, y, rot):
        pwrs = {
            'f': MAX_MTR_PWR * scale_limit(x + rot),
            'b': MAX_MTR_PWR * scale_limit(x - rot),
            'l': MAX_MTR_PWR * scale_limit(y + rot),
            'r': MAX_MTR_PWR * scale_limit(y - rot)}

        if all(v == 0 for k,v in pwrs.items()):
            if not self.motors_disabled_prev:
                self.logger.debug("Stop thrusters", extra={'type': 'DEVICE', 'n': 'thrusters', 'state': 'stopped'})
            self.motors_disabled_prev = True
        else:
            self.motors_disabled_prev = False

        if isinstance(self.thrusters, dict):
            for k, v in pwrs.items():
                self.thrusters[k].startPower(v)
        else:
            self.print_debug("Thrusters Power: {}".format(pwrs))

        return pwrs

    def auto_enabled(self) -> bool:
        if self.auto_target is None:
            return False
        return True

    def set_auto_target(self, lat=None, lon=None):
        if lat is None or lon is None:
            self.auto_target = None
        else:
            self.auto_target = {'lat': lat, 'lon': lon}

    def get_next_auto_target(self) -> dict:
        try:
            t = self.AUTO_TARGETS[0]
            del self.AUTO_TARGETS[0]
        except IndexError:
            t = None
        return t

    def next_auto_target(self):
        self.auto_target = self.get_next_auto_target()

    def get_remaining_waypoints(self):
        return len(self.AUTO_TARGETS)

    def disable_auto(self):
        self.print_debug("Auto Disable")
        self.auto_target = None

    def auto_debug_log(self, *args, **kwargs):
        if False and self._DEBUG:
            self.print_debug(*args)
        else:
            if self.auto_cycle_count >= AUTO_LOG_CYCLE_WAIT:
                self.logger.debug(*args, **kwargs)
                self.auto_cycle_count = 0

    def run(self):
        while self.running:
            time.sleep(0.02)
            # Recent control check:
            if self.movement['ts'] is None or ((time.time()-self.movement['ts']) > CONTROL_TIMEOUT):
                self.auto_target = None
                self.stop_thrusters()
                continue

            """--- Contact with control ---"""
            # Check if a control value is not None nor 0 (manual input -> cut off) or the position is incorrect
            #   or auto is not disabled
            if not isinstance(self.auto_target, dict)\
                    or not all((v == 0 or k is 'ts') for k, v in self.movement.items())\
                    or self.auto_force_disable:
                self.auto_target = None
            else:
                """--- Autonomous ---"""

                # Lateral Control:
                try:
                    loc = self.gps.readLocationData()
                except (ValueError, AttributeError):
                    if self._DEBUG:
                        loc = {'lat': 41.735, 'lon': -71.319}
                    else:
                        self.stop_thrusters()
                        self.print_debug("AUTONOMOUS: NO GPS -- STOPPING THRUSTERS!")
                        continue

                # get position differences in meters
                pos_diff_m = util.gps_coord_mdiff((loc['lat'],loc['lon']),
                                                  (self.auto_target['lat'], self.auto_target['lon']))

                # Rotational Control:
                current_bearing = None

                if self.imu is not None:
                    current_bearing = self.imu.read_euler()[0]
                elif self._DEBUG:
                    current_bearing = self.TARGET_BEARING

                if current_bearing is not None:  # If bearing was set by imu or debug value
                    bearing_diff = (((self.TARGET_BEARING-current_bearing) + 180) % 360) - 180
                else:  # IMU not working, but motors are: Disable Autonomous (shouldn't occur, but for safety)
                    self.print_debug("ERROR: REACHED AUTONOMOUS WITH NO IMU?")
                    self.stop_thrusters()
                    continue

                rot_torque = bearing_diff / 180

                mtr_pwrs = self.drive_thrusters(scale_m_distance(pos_diff_m[0]), scale_m_distance(pos_diff_m[1]),
                                                rot_torque)

                # Debug prints: Autonomous
                self.auto_debug_log("Curr Bear: {}, Bear Diff: {}, Rot: {} || Pos Diff (m): ({},{})"
                                    .format(current_bearing, bearing_diff, rot_torque, pos_diff_m[0], pos_diff_m[1]),
                                    extra={'type': 'AUTO', 'n': 'DATA', 'bearing': {'curr': current_bearing, 'diff': bearing_diff},
                                           'torque': rot_torque, 'pos_diff': pos_diff_m, 'mtr_pwrs': mtr_pwrs,
                                           'gps': {'curr': loc, 'target': self.auto_target}})

                self.auto_cycle_count += 1

            if self.auto_target is None:
                self.drive_thrusters(self.movement['x_trans'], self.movement['y_trans'], self.movement['xy_rot'])
