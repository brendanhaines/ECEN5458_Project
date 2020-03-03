#!/bin/sh

# TODO: replace this origin with something generated from IP address
export BOKEH_ALLOW_WS_ORIGIN=192.168.4.1:5006

bokeh serve hwtest.py
