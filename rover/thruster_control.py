from aesrdevicelib.sensors.gps_read import GPSRead
try:
    from aesrdevicelib.motion.pca9685 import PCA9685
    from aesrdevicelib.motion.blue_esc import BlueESC_I2C, BlueESC_PCA9685
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

AXIS_DEADBAND = 0.2  # meters

FULL_PWR_DISTANCE = 10  # meters
MIN_PWR = 0.05  # out of 1

MAX_MTR_PWR = 0.1

AUTO_LOG_CYCLE_WAIT = 50

INITIAL_DEADBAND = 1  # m
REENGAGE_DEADBAND = 3  # m


def scale_m_distance(m: float):
    if abs(m) < AXIS_DEADBAND:
        return 0
    x = (-1 * FULL_PWR_DISTANCE * MIN_PWR) / (MIN_PWR - 1)  # applied to make m=FULL =>1 and m=0 =>MIN_PWR
    return (m/(FULL_PWR_DISTANCE+x)) + MIN_PWR


def scale_limit(s):
    max_ = 1
    min_ = -max_
    return max(min_, min(max_, s))

BLUEESC_COM_I2C = 1
BLUEESC_COM_PWM_PCA9685 = 2


class ThrusterControl(threading.Thread):
    class BlueESCSetupException(Exception):
        def __init__(self, exception: Exception, *args):
            self.cause = exception
            super().__init__(*args)

    def __init__(self, logger: logging.Logger, *args, blue_esc_com=BLUEESC_COM_I2C, gps: GPSRead=None, **kwargs):
        super().__init__(**kwargs)

        self.name = "ThrusterController"  # Set thread name

        self.AUTO_TARGETS = [{'lat': 41.7357, 'lon': -71.3252}, {'lat': 41.7356, 'lon': -71.325344}]
        self.TARGET_BEARING = 0

        self._DEBUG = False  # will enable if motors fail to initialize

        self.running = False
        self.auto_force_disable = False
        self.auto_target = None
        self.movement = {'x_trans': 0, 'y_trans': 0, 'xy_rot': 0, 'ts': None}  # Trans and rots are gains [-1.0, 1]
        self.on_target = False

        self.motors_disabled_prev = True
        self.auto_cycle_count = 0

        self.logger = logger

        """ ---- DEVICES ---- """
        # BlueESC instances
        self.thrusters = None

        self.blue_esc_com = blue_esc_com
        try:
            if blue_esc_com == BLUEESC_COM_I2C:
                try:
                    thrusters = {}

                    t_failed = False
                    for n,a in {"f": 0x2a, "b": 0x2d, "l": 0x2e, "r": 0x2c}.items():
                        try:
                            thrusters[n] = BlueESC_I2C(a)
                        except IOError:
                            self.logger.exception("Thruster {} (at addr {}), failed to communicate".format(n,a),
                                                  extra={'type': 'DEVICE', 'device': 'BlueEsc', 'addr': a, 'state': False})
                            t_failed = True
                    self.thrusters = thrusters
                    if t_failed is True:
                        raise IOError("One or more thrusters failed.")
                except (IOError, NameError) as e:
                    self.logger.exception("Thruster setup error")
                    raise self.BlueESCSetupException(e)
            elif blue_esc_com == BLUEESC_COM_PWM_PCA9685:
                try:
                    self.p = PCA9685()
                    self.p.set_pwm_freq(300)
                    thrusters = {}

                    for n, c in {"f": 12, "b": 15, "l": 13, "r": 14}.items():
                        thrusters[n] = BlueESC_PCA9685(c, pca9685=self.p)

                    for n, t in thrusters.items():
                        t.enable()

                    self.thrusters = thrusters
                except (IOError, NameError) as e:
                    self.logger.exception(
                        "Failed to communicate to PCA9685 (for BlueESC PWM control). Will disable BlueESCs.",
                        extra={'type': 'DEVICE', 'device': 'PCA9685', 'state': False})
                    raise self.BlueESCSetupException(e)
            else:
                self.logger.warning("Invalid BlueESC communication form selected.",
                                    extra={'type': 'DEVICE', 'device': 'BlueESC', 'state': False})
        except self.BlueESCSetupException as e:
            while True:
                time.sleep(0.01)  # To fix printing order
                d_m = input("Would you like to continue in debug mode [Y/n]: ")
                d_m = d_m.lower()
                if d_m == "" or d_m == "y":
                    self.logger.info("Continuing thruster control in DEBUG mode.",
                                     extra={'type': 'MODULE', 'state': 'DEBUG'})
                    self._DEBUG = True
                    self.blue_esc_com = None
                    self.thrusters = None
                    break
                elif d_m == "n":
                    self.logger.info("Exiting thruster control.",
                                     extra={'type': 'MODULE', 'state': False})
                    raise e.cause
                else:
                    print("Please input 'y'/'Y' or 'n'/'N'.\n")


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
            imu_status = (0,0,0,0)
            while not imu_status[3] == 0x3:
                imu_status = self.imu.get_calibration_status()
                print("\rIMU Calibration Status: {}".format(imu_status), end='', flush=True)
                time.sleep(0.5)
            print()
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
        self.running = False
        self.join()

        if self.blue_esc_com == BLUEESC_COM_PWM_PCA9685:
            for k, v in self.thrusters.items():
                v.disable()
        else:
            self.stop_thrusters()
        if self.external_gps is False and self.gps is not None:
            self.gps.close()

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
                if self.blue_esc_com == BLUEESC_COM_I2C:
                    self.thrusters[k].start_power(v)
                else:
                    self.thrusters[k].set_power(v)
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
                    if loc['lat'] is None or loc['lon'] is None:
                        raise ValueError("No GPS fix")
                except (ValueError, AttributeError, KeyError):
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

                # Calculate distance between target and current loc:
                dist_m = math.sqrt(math.pow(pos_diff_m[0], 2) + math.pow(pos_diff_m[1], 2))

                # Target previously entered, and still in (larger) target deadband zone:
                if self.on_target and dist_m < REENGAGE_DEADBAND:
                    self.stop_thrusters()
                    self.auto_debug_log("Waiting at target [holding] (thrusters disabled)",
                                        extra={'type': 'AUTO', 'n': 'TARGET_WAIT', 'dist': dist_m})
                elif dist_m < INITIAL_DEADBAND:  # Just entered target zone
                    self.on_target = True
                    self.stop_thrusters()
                    self.logger.info("Entered target zone ({} m)-- Disabled motors".format(dist_m),
                                     extra={'type': 'AUTO', 'n': 'ENTERED_TARGET', 'dist': dist_m})
                else:
                    self.on_target = False
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
