import os
from dotenv import load_dotenv
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import sys

def init_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope="playlist-modify-public playlist-modify-private"
    ))

def extract_playlist_id(url, platform):
    if platform == "spotify":
        return url.split("/")[-1].split("?")[0]
    elif platform == "ytmusic":
        if "list=" in url:
            return url.split("list=")[-1]
        else:
            raise ValueError("Invalid YouTube Music playlist URL.")
    return None

def transfer_playlist(ytmusic_url, spotify_url):
    ytmusic = YTMusic()
    sp = init_spotify()

    yt_playlist_id = extract_playlist_id(ytmusic_url, "ytmusic")
    yt_data = ytmusic.get_playlist(yt_playlist_id, limit=100)
    spotify_playlist_id = extract_playlist_id(spotify_url, "spotify")

    print(f"Transferring {len(yt_data['tracks'])} tracks from YouTube Music to Spotify...")

    for track in yt_data['tracks']:
        title = track['title']
        try:
            result = sp.search(q=title, type='track', limit=1)
            items = result['tracks']['items']
            if not items:
                raise Exception("No match found")

            sp_track_id = items[0]['id']
            sp.playlist_add_items(spotify_playlist_id, [sp_track_id])
            print(f"✅ Added: {items[0]['name']}")

        except Exception as e:
            print(f"❌ Skipped: {title} ({e})")

    print("✅ Transfer complete.")

def main(args):
    load_dotenv()
    try:
        transfer_playlist(args["ytmusic_url"], args["spotify_url"])
        os.remove(".cache")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python main.py <ytmusic_playlist_url> <spotify_playlist_url>")
        sys.exit(1)

    args = {
        "ytmusic_url": sys.argv[1],
        "spotify_url": sys.argv[2]
    }
    main(args)
