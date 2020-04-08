import time
import numpy as np
from scipy import signal
from scipy.signal import TransferFunction

import board
import busio
import digitalio
from adafruit_servokit import ServoKit
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import threading
import os

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TextInput, Button, Paragraph
from bokeh.plotting import figure

DEBUG = False
BAT_MUX_CHAN = 9
VBAT_THRESHOLD = 11.0

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
try:
    white_cal = np.loadtxt('cal_white.txt')
except IOError:
    white_cal = [0]*8

try:
    black_cal = np.loadtxt('cal_black.txt')
except IOError:
    black_cal = [5]*8

def get_mux_adc(chan):
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
    return (get_mux_adc(chan) - black_cal[chan]) / (white_cal[chan] - black_cal[chan])

# Initialize brightness data
brightness_idx = np.arange(8)
brightness = [get_normalized_reflectivity(c) for c in range(8)]

# Initialize time data
time_data = np.empty((0, 3)) # [[t, e, u]]

# Create sources for plots
brightness_plot_source = ColumnDataSource(data=dict(sensor=brightness_idx, brightness=brightness))
time_plot_source = ColumnDataSource(data=dict(t=time_data[:,0], e=time_data[:,1], u=time_data[:,2]))

# Set up plots
brightness_plot = figure(plot_height=150, plot_width=400, x_range=[0, 7], y_range=[0, 1], tools="save")
brightness_plot.line('sensor', 'brightness', source=brightness_plot_source, line_width=3)
brightness_plot.circle('sensor', 'brightness', source=brightness_plot_source, size=8, fill_color="white", line_width=2)

time_plot = figure(plot_height=400, plot_width=800, y_range=[-1, 1], tools="pan,reset,save,wheel_zoom")
time_plot.line('t', 'e', source=time_plot_source, line_width=3, line_alpha=0.6, legend_label="e(t)")
time_plot.line('t', 'u', source=time_plot_source, line_width=3, line_alpha=0.6, legend_label="u(t)", line_color = "green")

# Controller thread
control_thread_run = False

def controller():
    global brightness
    global time_data
    global servos
    global control_thread_run
    global D    # controller model

    # TODO: make these parameters editable via network interface
    if D.dt is None:
        sample_interval = 0.01
    else:
        sample_interval = D.dt
    base_speed = 0.1
    fir_taps = np.append(D.num, 0)
    iir_taps = np.append(D.num[1:], 0)
    # fir_taps = [1, 0, 0]
    # iir_taps = [0, 0]

    motor_directions = [1, -1, 0]
    steering_sign = 1

    print("INFO: Controller started")

    # Initialize
    time_data = np.zeros((max(len(fir_taps), len(iir_taps)), time_data.shape[1]))

    # Precompute
    this_time = 0
    new_u = 0
    motor_speed = np.array(motor_directions) * base_speed

    while control_thread_run:
        # Read error
        brightness = np.clip([get_normalized_reflectivity(c) for c in range(8)], 0, 1)
        line_position = np.sum((1 - brightness) * (np.arange(8) - 3.5)) / np.sum(1-brightness) / 3.5
        if np.isnan(line_position):
            line_position = 0

        # Calculate output
        new_u += fir_taps[0] * line_position
        motor_speed += steering_sign * new_u

        # Update motors
        for ii in range(3):
            servos[ii].throttle = np.clip(motor_speed[ii], -1, 1)

        # Log data
        new_time_data = [[this_time, line_position, new_u]]
        time_data = np.concatenate((time_data, new_time_data))

        # Print data
        if DEBUG:
            for b in brightness:
                print(f"{b:1.2f}\t", end="")
            print(f"{line_position:+1.2f}", end="")
            print()

        # Precompute for next iteration
        this_time = time_data[-1, 0] + sample_interval
        u = time_data[:,2]
        e = time_data[:,1]
        new_u = np.sum(fir_taps[1:] * e[-len(fir_taps)+1:]) - np.sum(iir_taps * u[-len(iir_taps):])
        motor_speed = np.array(motor_directions) * base_speed

        # TODO: replace sleep statement with something that doesn't depend on execution time of loop
        time.sleep(sample_interval)
    
    for ii in range(3):
        servos[ii].throttle = 0

    print("INFO: Controller stopped")

control_thread = None

# Callback functions
def update_plots(attrname=None, old=None, new=None):
    global brightness
    global time_data
    global brightness_plot_source
    global control_thread_run
    if control_thread_run:
        brightness_plot_source.data = dict(sensor=brightness_idx, brightness=brightness)
        time_plot_source.data = dict(t=time_data[:,0], e=time_data[:,1], c=time_data[:,2])
    else:
        brightness = np.clip([get_normalized_reflectivity(c) for c in range(8)], 0, 1)
        brightness_plot_source.data = dict(sensor=brightness_idx, brightness=brightness)

def cal_white(attrname=None, old=None, new=None):
    global white_cal
    white_cal = [get_mux_adc(c) for c in range(8)]
    np.savetxt('cal_white.txt', white_cal)
    update_plots()

def cal_black(attrname=None, old=None, new=None):
    global black_cal
    black_cal = [get_mux_adc(c) for c in range(8)]
    np.savetxt('cal_black.txt', black_cal)
    update_plots()

def start_controller(attrname=None, old=None, new=None):
    global control_thread
    global control_thread_run
    control_thread_run = True
    control_thread = threading.Thread(target=controller)
    control_thread.daemon = True
    control_thread.start()

def stop_controller(attrname=None, old=None, new=None):
    global control_thread
    global control_thread_run
    try:
        control_thread_run = False
        control_thread.join()
        control_thread = None
    except:
        pass

def update_models(attrname=None, old=None, new=None):
    stop_controller()
    try:
        exec("global D\n" + controller_model_text.value)
        print("INFO: controller model updated")
        print(D)
    except:
        print("WARN: invalid controller model")


# GUI elements
vbat_text = Paragraph(text="Battery Voltage: ? V")

cal_white_button = Button(label="Cal White")
cal_white_button.on_click(cal_white)
cal_black_button = Button(label="Cal Black")
cal_black_button.on_click(cal_black)

start_button = Button(label="Start")
start_button.on_click(start_controller)
stop_button = Button(label="Stop")
stop_button.on_click(stop_controller)

# plant_model_text = 
controller_model_text = TextInput(value="D = TransferFunction([1], [1], dt=0.01)")
update_models_button = Button(label="Update models")
update_models_button.on_click(update_models)
update_models()

def update_battery_voltage(attrname=None, old=None, new=None):
    global VBAT_THRESHOLD
    global vbat_text
    vadc = get_mux_adc(BAT_MUX_CHAN)
    # vbat = vadc * (10+1)/1
    vbat = vadc * 12.21/1.022
    vbat_text.text = f"Battery Voltage: {vbat:2.1f}V"
    if vbat < VBAT_THRESHOLD:
        stop_controller()
        print("ERROR: Battery Critically Low")
        # os.system("sudo poweroff")

# sample_interval = 0.01
# base_speed = 0.1
# fir_taps = [1, 0, 0]
# iir_taps = [0, 0]
# controller_sample_interval = TextInput(title="Sample Interval", value=str(sample_interval))
# controller_base_speed = Slider(title="Base Speed", value=base_speed, start=0, end=0.8, step=0.01)
# controller_fir_taps = TextInput(title="FIR taps", value=str(fir_taps))
# controller_iir_taps = TextInput(title="IIR taps", value=str(iir_taps))

controls = column(vbat_text, cal_white_button, cal_black_button, start_button, stop_button)
controller_model = row(controller_model_text, update_models_button)
# controller_settings = column(controller_sample_interval, controller_base_speed, controller_fir_taps, controller_iir_taps)
curdoc().add_root(column(row(controls, brightness_plot, width=800), time_plot, controller_model))#, controller_settings))
curdoc().title = "TriangleBot Control Panel"
curdoc().add_periodic_callback(update_plots, 250)
curdoc().add_periodic_callback(update_battery_voltage, 1000)
