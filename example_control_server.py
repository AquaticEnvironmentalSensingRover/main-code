from rover.rover import AESRover
from rover.thruster_control import BLUEESC_COM_PWM_PCA9685

if __name__ == '__main__':
    r = AESRover(thruster_control=True, blue_esc_com=BLUEESC_COM_PWM_PCA9685)
    r.run()
