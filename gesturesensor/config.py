~import os
import json
import paho.mqtt.client as mqtt

config = {}
numpersons = {}
sentpayload = {}
client = mqtt.Client()

def init():
    global config
    # Home Assistant Add-on lưu cấu hình ở `/data/options.json`
    with open('/data/options.json', 'r') as file:
        config = json.load(file)

    for camera in config['frigate_cameras']:
        numpersons[camera] = 0
        sentpayload[camera] = ""

