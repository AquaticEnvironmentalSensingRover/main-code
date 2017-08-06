from dagurs039 import data, DaguRS039
from dagurs039.config import MotorLayout
import time

d = DaguRS039()
print("Setting config commands on Dagu...", end="", flush=True)
d.basic_cfg(MotorLayout(MotorLayout.INDIV, enc_enable=False), data.lipo_low_bty_preset['3S'], 255, 255, 255, 255)
time.sleep(1)
print("\rFinished setup.", flush=True)

try:
    while True:
        d.set_mtr(0, 0, 0, 0)
        time.sleep(0.2)
        i = input("\nPlease input 'W' for up, and 'S' for down: ")
        i = i.lower()
        if i == 'w':
            print("up")
            d.set_mtr(0, 0, -100, 0)
        elif i == 's':
            print("down")
            d.set_mtr(0, 0, 100, 0)
        else:
            print("Invalid input")
            continue
        time.sleep(1)
finally:
    d.set_mtr(0,0,0,0)
