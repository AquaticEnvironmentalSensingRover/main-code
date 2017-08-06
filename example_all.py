from rover import rover
from rover.thruster_control import BLUEESC_COM_PWM_PCA9685

r = rover.AESRover(True, True, blue_esc_com=BLUEESC_COM_PWM_PCA9685)
r.run()
