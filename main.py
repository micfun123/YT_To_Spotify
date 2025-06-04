from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import os
from dotenv import load_dotenv

load_dotenv()

# Spotify setup
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="playlist-modify-public playlist-modify-private"
))

# YouTube Music setup
ytmusic = YTMusic()

# Example usage
yt_playlist_id = "PLXXXXXXXXXXXXXXXXXX"  # Replace with your playlist ID
yt_data = ytmusic.get_playlist(yt_playlist_id, limit=100)
spoify_playlist_id = "XXXXXXXXXXXXXXXXXXXX"


for track in yt_data['tracks']:
    title = track['title']
    try:
        spSong = sp.search(q=title, type='track', limit=1)
        spSongURL = spSong['tracks']['items'][0]['external_urls']['spotify']
        SpSongName = spSong['tracks']['items'][0]['name']
        print(f"Found Spotify track: {SpSongName} - {spSongURL}")
        sp.playlist_add_items(spoify_playlist_id, [spSongURL])
    except:
        print(f"{title} was not found")
print("Tracks added to Spotify playlist successfully.")
    

