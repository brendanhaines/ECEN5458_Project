import time
import numpy as np

import board
import busio
import digitalio
from adafruit_servokit import ServoKit
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

if __name__ == "__main__":
    mux = np.empty(4)
    mux[0] = digitalio.DigitalInOut(board.D17).value
    mux[1] = digitalio.DigitalInOut(board.D27).value
    mux[2] = digitalio.DigitalInOut(board.D22).value
    mux[3] = digitalio.DigitalInOut(board.D23).value

    i2c = busio.I2C(board.SCL, board.SDA)
    adc = ADS.ADS1015(i2c)
    adc_mux = AnalogIn(adc, ADS.P0)

    def get_reflectivity(chan):
        chan = int(chan)
        global mux
        global adc_mux
        mux = np.array(list(f"{chan:04b}"), dtype=int)
        return adc_mux.voltage

    while True:
        for ii in range(1):
            print(f"{get_reflectivity(ii):1.2f}\t", end="")
        print()

    # servos = ServoKit(channels=16).continuous_servo
    # servos[0].throttle = 0
    # servos[1].throttle = 0
    # servos[2].throttle = 0
    # time.sleep(1)
    # servos[0].throttle = 20
    # servos[1].throttle = 20
    # servos[2].throttle = 20
    # time.sleep(1)
    # servos[0].throttle = 0
    # servos[1].throttle = 0
    # servos[2].throttle = 0
    
