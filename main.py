import random
import requests
import json

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Replace the values below with your own credentials
client_id = '159ebc178c6c47edacedca15239cfd9b'
client_secret = 'aa615c28f70b4c488f5b3365f70a2c32'

# Authenticate with the Spotify API using the client credentials flow
def recom_song(emotion_inp):
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth_manager)

    # Search for playlists or tracks based on an emotion
    emotion = emotion_inp # Replace with the desired emotion
    results = sp.search(q=emotion, type='track')
    # with open('response.json', 'w') as json_file:
    #     json.dump(results, json_file)

    # Get the details of the tracks in the playlists or tracks
    tracks = []
    for item in results['tracks']['items']:
        track = item['external_urls']['spotify']
        tracks.append(track)
    # for playlist in results['playlists']['items']:
    #     tracks += sp.playlist_tracks(playlist['id'], fields='items(track(name,artists(name),album(name),preview_url))')['items']

    # Print the details of each track
    return tracks