import time
import numpy as np

import board
import busio
import digitalio
from adafruit_servokit import ServoKit
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

if __name__ == "__main__":
    mux_io = [None] * 4
    mux_io[0] = digitalio.DigitalInOut(board.D17)
    mux_io[1] = digitalio.DigitalInOut(board.D27)
    mux_io[2] = digitalio.DigitalInOut(board.D22)
    mux_io[3] = digitalio.DigitalInOut(board.D23)

    for ii, io in enumerate(mux_io):
        io.switch_to_output()

    i2c = busio.I2C(board.SCL, board.SDA)
    adc = ADS.ADS1015(i2c)
    adc_mux = AnalogIn(adc, ADS.P0)

    def get_reflectivity(chan):
        chan = int(chan)
        global mux_io
        global adc_mux
        mux = 1-np.array(list(f"{chan:04b}"), dtype=int)
        for ii, io in enumerate(mux_io):
            io.value = mux[ii]
        return adc_mux.voltage
    
    input("White calibration, press ENTER to continue...")
    white_cal = [get_reflectivity(c) for c in range(8)]
    
    input("Black calibration, press ENTER to continue...")
    black_cal = [get_reflectivity(c) for c in range(8)]

    def get_normalized_reflectivity(chan):
        global white_cal
        global black_cal
        
        return (get_reflectivity(chan) - black_cal) / (white_cal - black_cal)

    while True:
        for ii in range(8):
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
    
