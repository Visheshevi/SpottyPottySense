import paho.mqtt.client as mqtt
import sys
import os
import logging

sys.path.append('/home/serverthebest/Projects/Spotty Sense/SpottyPottySense/piServerService') 
from spotify_start_on_device import spotify_token, spotify_device_id, setup_headers, request_device_to_play_spotify

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"mqtt_listener_servide_log.log")
logging.basicConfig(filename=log_file, level=logging.DEBUG)

#MQTT BROKER SETTINGS
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883  # Default MQTT Port
MQTT_TOPIC = "YOUR_MQTT_TOPIC"
MQTT_USERNAME = "USERNAME"
MQTT_PASSWORD = "PASSWORD"


# MQTT client setup
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
	logging.info(f"Connected with result code {rc}")
	client.subscribe(MQTT_TOPIC)
	
def on_message(client, userdata, msg):
	payload = msg.payload.decode("utf-8")
	logging.info(f"Received message: {payload}")
	headers = setup_headers(spotify_token, spotify_device_id)
	request_device_to_play_spotify(headers)
	
	
# Setup Calback functions
client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Connect to MQTT broker
client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)

client.loop_start()

try:
	while True:
		pass

except KeyboardInterrupt:
		client.loop_stop()
		client.disconnect()
		logging.info("MQTT listener stopped")
		
