import requests
import sys
import os
import logging
import time
 
millisec = 0
cutoffTime = 5 # In minutes
sys.path.append('/home/serverthebest/Projects/"Spotty Sense"/SpottyPottySense/piServerService')


log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),"mqtt_listener_servide_log.log")
log_dir = os.path.dirname(log_file)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    
logging.basicConfig(filename=log_file, level=logging.DEBUG)

# Replace these with your actual Spotify OAuth token and device ID
spotify_device_id = "SPOTIFY_DEVICE_ID"
spotify_token = "SPOTIFY_TOKEN_NOT_NEEDED"
client_id = "CLIENT_ID"
client_secret = "CLIENT_SECRET"
refresh_token = "REFRESH_TOKEN"


def setup_headers(spotify_token, spotify_device_id):
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {spotify_token}",
    }
    return headers


def request_device_to_play_spotify(heads):
    global spotify_token
    trial = refresh_access_token()
    spotify_token = trial
    
    # Starting spotify depends on the last time it was started. If the last time started was less than 30 minutes, it wont start
    curr_time = int(round(time.time()))
    cutoffTime_seconds = cutoffTime*60
    time_diff = curr_time - (millisec//1000)
    if time_diff > cutoffTime_seconds : 
        logging.info(f"Cuurent Time[{curr_time}], initial time[{millisec}], time difference[{time_diff}]")
        start_spotify()
    else:
        logging.info("Motion detected but I am either already playing or was already commanded to stop playing")

def request_device_to_stop_spotify(heads):
    global spotify_token
    print("1")
    trial = refresh_access_token()
    spotify_token = trial
    heads = setup_headers(spotify_token, spotify_device_id)
    response = requests.get("https://api.spotify.com/v1/me/player", headers=heads)
    if response.status_code == 200:
        playback_data = response.json()
        logging.info(f"Playback response[{playback_data}]")
        if playback_data.get("is_playing"):
            # User is currently playing, so stop playback
            response = requests.put("https://api.spotify.com/v1/me/player/pause", headers=heads)
            if response.status_code == 204:
                logging.info("Stopped Spotify playback")
            else:
                logging.info("Error stopping playback:", response.text)
        else:
            logging.info("User is not currently playing")
    else:
        logging.info("Error getting playback state:", response.text)
	

def start_spotify():
    global millisec
    logging.info("Attempting to start playing spotify in the bathroom")
    heads = setup_headers(spotify_token, spotify_device_id)
    response = requests.put(f"https://api.spotify.com/v1/me/player/play?device_id={spotify_device_id}", headers=heads)
    if response.status_code == 204:
        millisec = int(round(time.time() * 1000))
        logging.info(f"Playback started successfully at time[{time.localtime()}] and millisec[{millisec}]")
    else:
        logging.info(f"Failed to start playback: {response.content}")
   
#def refresh_access_token(refresh_token, client_id, client_secret):
def refresh_access_token():
    refresh_url = "https://accounts.spotify.com/api/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    response = requests.post(refresh_url, data=payload)
    logging.info(response)
    if response.status_code == 200:
        new_access_token = response.json()["access_token"]
        return new_access_token
    else:
        print("Error refreshing access token:", response.text)
        return None
