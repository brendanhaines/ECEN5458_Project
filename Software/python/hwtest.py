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
from bokeh.models import ColumnDataSource, Slider, TextInput, Button
from bokeh.plotting import figure

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
white_cal = [0]*8
black_cal = [5]*8

def get_reflectivity(chan):
    chan = int(chan)
    global mux_io
    global adc_mux
    mux = 1-np.array(list(f"{chan:04b}"), dtype=int)
    for ii, io in enumerate(mux_io):
        io.value = mux[ii]
    return adc_mux.voltage

def get_normalized_reflectivity(chan):
    global white_cal
    global black_cal
    
    return (get_reflectivity(chan) - black_cal[chan]) / (white_cal[chan] - black_cal[chan])

brightness_idx = np.arange(8)
brightness = [get_normalized_reflectivity(c) for c in range(8)]

plt_source = ColumnDataSource(data=dict(x=brightness_idx, y=brightness))

# Set up plot
plot = figure(plot_height=400, plot_width=400, title="my sine wave",
            tools="save",
            x_range=[0, 7], y_range=[0, 5])

plot.line('x', 'y', source=plt_source, line_width=3, line_alpha=0.6)

def update_data(attrname=None, old=None, new=None):
    brightness = [get_normalized_reflectivity(c) for c in range(8)]
    plt_source.data = dict(x=brightness_idx, y=brightness)

def cal_white(attrname=None, old=None, new=None):
    global white_cal
    white_cal = [get_reflectivity(c) for c in range(8)]
    update_data()

def cal_black(attrname=None, old=None, new=None):
    global black_cal
    black_cal = [get_reflectivity(c) for c in range(8)]
    update_data()

cal_white_button = Button(label="Cal White")
cal_white_button.on_click(cal_white)
cal_black_button = Button(label="Cal Black")
cal_black_button.on_click(cal_black)

controls = column(cal_white_button, cal_black_button)

curdoc().add_root(row(controls, plot, width=800))
# curdoc().add_root(row(plot, width=800))
curdoc().title = "test"

# while True:
#     time.sleep(0.1)
#     update_data()


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

