import paho.mqtt.client as mqtt
import sys
import os
import logging

sys.path.append('YOUR_FILE_PATH') 
from spotify_start_on_device import setup_headers, request_device_to_play_spotify, spotify_token, spotify_device_id,request_device_to_stop_spotify


log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"LOG_FILE_NAME")
log_dir = os.path.dirname(log_file)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
   

   
#spotify_token = refresh_access_token(refresh_token, client_id,client_secret)
'''
if new_access_token:
    # Use the new access token to interact with Spotify
    logging.info("New access token:", new_access_token)
'''
 
logging.basicConfig(filename=log_file, level=logging.DEBUG)


#MQTT BROKER SETTINGS
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883  # Default MQTT Port
MQTT_TOPIC = "motion.in.bathroom"
MQTT_USERNAME = "USER_NAME"
MQTT_PASSWORD = "PASSWORD"


# MQTT client setup
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
	logging.info("Vishesh")
	logging.info(f"spotify_token({spotify_token}")
	logging.info(f"spotify_device_id({spotify_device_id}")
	logging.info(f"Connected with result code {rc}")
	if rc==5:
		logging.info("Connection Refused: Not Authorized")
	client.subscribe(MQTT_TOPIC)
	
def on_message(client, userdata, msg):
	payload = msg.payload.decode("utf-8")
	logging.info(f"Received message: {payload}")
	headers = setup_headers(spotify_token, spotify_device_id)
	if payload == "motion detected":
		request_device_to_play_spotify(headers)
	elif payload == "no motion detected for sometime":
		request_device_to_stop_spotify(headers)
	
	
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
		#logging.info("MQTT listener stopped")
		
