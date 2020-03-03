import time
import numpy as np

import board
import busio
import digitalio
from adafruit_servokit import ServoKit
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import threading

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput, Button
from bokeh.plotting import figure

DEBUG = True

mux_io = [None] * 4
mux_io[0] = digitalio.DigitalInOut(board.D23)
mux_io[1] = digitalio.DigitalInOut(board.D22)
mux_io[2] = digitalio.DigitalInOut(board.D27)
mux_io[3] = digitalio.DigitalInOut(board.D17)

for ii, io in enumerate(mux_io):
    io.switch_to_output()

i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS.ADS1015(i2c)
adc_mux = AnalogIn(adc, ADS.P0)
white_cal = [0]*8
black_cal = [5]*8

adc_lock = threading.Lock()

def get_reflectivity(chan):
    chan = int(chan)
    global mux_io
    global adc_mux
    global adc_lock
    mux = 1-np.array(list(f"{chan:04b}"), dtype=int)
    adc_lock.acquire()
    for ii, io in enumerate(mux_io):
        io.value = mux[ii]
    time.sleep(0.001)
    voltage = adc_mux.voltage
    adc_lock.release()
    return voltage

def get_normalized_reflectivity(chan):
    global white_cal
    global black_cal
    
    return (get_reflectivity(chan) - black_cal[chan]) / (white_cal[chan] - black_cal[chan])

brightness_idx = np.arange(8)
brightness = [get_normalized_reflectivity(c) for c in range(8)]
t = np.array([])
error = np.array([])

brightness_plot_source = ColumnDataSource(data=dict(sensor=brightness_idx, brightness=brightness))
time_plot_source = ColumnDataSource(data=dict(t=t, e=error))

# Set up plots
brightness_plot = figure(plot_height=150, plot_width=400, title="Reflectivity", x_range=[0, 7], y_range=[0, 1])
brightness_plot.line('sensor', 'brightness', source=brightness_plot_source, line_width=3)
brightness_plot.circle('sensor', 'brightness', source=brightness_plot_source, size=8, fill_color="white", line_width=2)

time_plot = figure(plot_height=400, plot_width=400, title="Signals")
time_plot.line('t', 'e', source=time_plot_source, line_width=3, line_alpha=0.6)

def update_plots(attrname=None, old=None, new=None):
    global brightness
    global error
    global brightness_plot_source
    brightness_plot_source.data = dict(sensor=brightness_idx, brightness=brightness)
    time_plot_source.data = dict(t=t, e=error)


def cal_white(attrname=None, old=None, new=None):
    global white_cal
    white_cal = [get_reflectivity(c) for c in range(8)]
    update_plots()

def cal_black(attrname=None, old=None, new=None):
    global black_cal
    black_cal = [get_reflectivity(c) for c in range(8)]
    update_plots()

cal_white_button = Button(label="Cal White")
cal_white_button.on_click(cal_white)
cal_black_button = Button(label="Cal Black")
cal_black_button.on_click(cal_black)

controls = column(cal_white_button, cal_black_button)

curdoc().add_root(row(controls, brightness_plot, time_plot, width=800))
curdoc().title = "TriangleBot Control Panel"
curdoc().add_periodic_callback(update_plots, 250)

def control_thread():
    global brightness
    global t
    global error
    sample_interval = 0.01
    while True:
        # TODO: replace sleep statement with something that doesn't depend on execution time of loop
        time.sleep(sample_interval)
        if len(t) == 0:
            this_time = 0
        else: 
            this_time = t[-1] + sample_interval

        brightness = np.clip([get_normalized_reflectivity(c) for c in range(8)], 0, 1)
        line_position = np.sum((1 - brightness) * (np.arange(8) - 3.5))/np.sum(1-brightness)
        # TODO: implement control stuff and drive outputs

        t = np.append(t, this_time)
        error = np.append(error, line_position)

        if DEBUG:
            for b in brightness:
                print(f"{b:1.2f}\t", end="")
            print(f"{line_position:+1.2f}", end="")
            print()


control_thread = threading.Thread(target=control_thread)
control_thread.start()


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

