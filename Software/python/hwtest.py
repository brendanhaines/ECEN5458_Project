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

# Configure MUX for ADC
mux_io = [None] * 4
mux_io[0] = digitalio.DigitalInOut(board.D23)
mux_io[1] = digitalio.DigitalInOut(board.D22)
mux_io[2] = digitalio.DigitalInOut(board.D27)
mux_io[3] = digitalio.DigitalInOut(board.D17)
for ii, io in enumerate(mux_io):
    io.switch_to_output()

# Configure ADC
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS.ADS1015(i2c)
adc_mux = AnalogIn(adc, ADS.P0)
adc_lock = threading.Lock()

# Configure Servo Driver
servos = ServoKit(channels=16).continuous_servo
servos[0].throttle = 0
servos[1].throttle = 0
servos[2].throttle = 0

# Initialize calibration
# TODO: save cal and load from file by default
white_cal = [0]*8
black_cal = [5]*8

def get_reflectivity(chan):
    global mux_io
    global adc_mux
    global adc_lock
    chan = int(chan)
    mux = 1-np.array(list(f"{chan:04b}"), dtype=int)
    adc_lock.acquire()
    for ii, io in enumerate(mux_io):
        io.value = mux[ii]
    voltage = adc_mux.voltage
    adc_lock.release()
    return voltage

def get_normalized_reflectivity(chan):
    global white_cal
    global black_cal
    return (get_reflectivity(chan) - black_cal[chan]) / (white_cal[chan] - black_cal[chan])

# Initialize brightness data
brightness_idx = np.arange(8)
brightness = [get_normalized_reflectivity(c) for c in range(8)]

# Initialize time data
time_data = np.empty((0, 3)) # [[t, e, c]]

# Create sources for plots
brightness_plot_source = ColumnDataSource(data=dict(sensor=brightness_idx, brightness=brightness))
time_plot_source = ColumnDataSource(data=dict(t=time_data[:,0], e=time_data[:,1], c=time_data[:,2]))

# Set up plots
brightness_plot = figure(plot_height=150, plot_width=400, x_range=[0, 7], y_range=[0, 1])
brightness_plot.line('sensor', 'brightness', source=brightness_plot_source, line_width=3)
brightness_plot.circle('sensor', 'brightness', source=brightness_plot_source, size=8, fill_color="white", line_width=2)

time_plot = figure(plot_height=400, plot_width=800, y_range=[-1, 1])
time_plot.line('t', 'e', source=time_plot_source, line_width=3, line_alpha=0.6, legend_label="e(t)")
time_plot.line('t', 'c', source=time_plot_source, line_width=3, line_alpha=0.6, legend_label="c(t)", line_color = "green")

# Callback functions
def update_plots(attrname=None, old=None, new=None):
    global brightness
    global time_data
    global brightness_plot_source
    brightness_plot_source.data = dict(sensor=brightness_idx, brightness=brightness)
    time_plot_source.data = dict(t=time_data[:,0], e=time_data[:,1], c=time_data[:,2])

def cal_white(attrname=None, old=None, new=None):
    global white_cal
    white_cal = [get_reflectivity(c) for c in range(8)]
    update_plots()

def cal_black(attrname=None, old=None, new=None):
    global black_cal
    black_cal = [get_reflectivity(c) for c in range(8)]
    update_plots()

# GUI elements
cal_white_button = Button(label="Cal White")
cal_white_button.on_click(cal_white)
cal_black_button = Button(label="Cal Black")
cal_black_button.on_click(cal_black)

controls = column(cal_white_button, cal_black_button)
curdoc().add_root(column(row(controls, brightness_plot, width=800), time_plot))
curdoc().title = "TriangleBot Control Panel"
curdoc().add_periodic_callback(update_plots, 250)

# Controller
def control_thread():
    global brightness
    global time_data
    global servos

    sample_interval = 0.01
    base_speed = 0.1
    fir_taps = [0, 0, 0]
    iir_taps = [0, 0]
    time_data = np.zeros((max(len(fir_taps), len(iir_taps)), time_data.shape[1]))

    while True:
        # TODO: replace sleep statement with something that doesn't depend on execution time of loop
        time.sleep(sample_interval)
        if time_data.shape[0] == 0:
            this_time = 0
        else: 
            this_time = time_data[-1, 0] + sample_interval

        # Precompute as much as possible
        c = time_data[:,2]
        e = time_data[:,1]
        new_c = np.sum(fir_taps[1:] * e[-len(fir_taps)+1:]) + np.sum(iir_taps * c[-len(iir_taps):])
        motor_speed = np.array([-1, 1, 0]) * base_speed
        
        # Read error
        brightness = np.clip([get_normalized_reflectivity(c) for c in range(8)], 0, 1)
        line_position = np.sum((1 - brightness) * (np.arange(8) - 3.5)) / np.sum(1-brightness) / 3.5
        if np.isnan(line_position):
            line_position = 0

        # Calculate output
        new_c += fir_taps[0] * line_position
        motor_speed += new_c

        # Update motors
        # for ii in range(3):
        #     servos[ii].throttle = motor_speed[ii]

        # Log data
        new_time_data = [[this_time, line_position, new_c]]
        time_data = np.concatenate((time_data, new_time_data))

        # Print data
        if DEBUG:
            for b in brightness:
                print(f"{b:1.2f}\t", end="")
            print(f"{line_position:+1.2f}", end="")
            print()


# Start controller
# TODO: add start/stop/reset capability to GUI
control_thread = threading.Thread(target=control_thread)
control_thread.start()
