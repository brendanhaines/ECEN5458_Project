import time
import numpy as np
from adafruit_servokit import ServoKit
from adafruit_ads1x15 import ads1015

if __name__ == "__main__":
    servos = ServoKit(channels=16).continuous_servo
    servos[0].throttle = 0
    servos[1].throttle = 0
    servos[2].throttle = 0
    time.sleep(1)
    servos[0].throttle = 20
    servos[1].throttle = 20
    servos[2].throttle = 20
    time.sleep(1)
    servos[0].throttle = 0
    servos[1].throttle = 0
    servos[2].throttle = 0
    
    # adc = ads1015()