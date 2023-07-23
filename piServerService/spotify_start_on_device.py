import requests

# Replace these with your actual Spotify OAuth token and device ID
spotify_token = "SPOTIFY_TOKEN"
spotify_device_id = "DEVICE_ID"


def setup_headers(spotify_token, spotify_device_id):
    headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {spotify_token}",
}
    return headers


def request_device_to_play_spotify(heads):
    response = requests.put(f"https://api.spotify.com/v1/me/player/play?device_id={spotify_device_id}", 
    headers=heads)
    
    if response.status_code == 204:
        print("Playback started successfully")
    else:
        print(f"Failed to start playback: {response.content}")
	
