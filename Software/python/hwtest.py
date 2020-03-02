import time
import numpy as np

import board
import busio
import digitalio
from adafruit_servokit import ServoKit
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput
from bokeh.plotting import figure

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
        
        return (get_reflectivity(chan) - black_cal[chan]) / (white_cal[chan] - black_cal[chan])

    brightness_idx = np.arange(8)
    brightness = [get_normalized_reflectivity(c) for c in range(8)]
    plt_source = ColumnDataSource(data=dict(x=brightness_idx, y=brightness))
    # Set up plot
    plot = figure(plot_height=400, plot_width=400, title="my sine wave",
                tools="crosshair,pan,reset,save,wheel_zoom",
                x_range=[0, 4*np.pi], y_range=[-2.5, 2.5])

    plot.line('x', 'y', source=plt_source, line_width=3, line_alpha=0.6)

    def update_data(attrname, old, new):
        brightness = [get_normalized_reflectivity(c) for c in range(8)]
        plt_source.data = dict(x=brightness_idx, y=brightness)

    curdoc().add_root(plot)
    curdoc().title = "test"



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
    
