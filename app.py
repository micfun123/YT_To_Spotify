import os
from dotenv import load_dotenv
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from flask import Flask, request, render_template, redirect, url_for, session, flash, g, Response, stream_with_context
import sys
import time
import json # For sending structured messages if needed, though simple strings will work for this

# Load environment variables from .env file at the very start
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24) # Set a secret key for session management, crucial for Flask's flash messages

# --- Spotify API Configuration and Helper Functions ---

def _get_spotify_oauth_manager():
    """
    Initializes and returns a SpotifyOAuth manager.
    This function does NOT manage the session directly in its constructor
    due to potential version incompatibility. Token management will be manual.
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError("Spotify API credentials (client ID, client secret, redirect URI) are not set in environment variables.")

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="playlist-modify-public playlist-modify-private",
        cache_path=None # No persistent file cache; manage in Flask session
    )

def get_spotify_client():
    """
    Retrieves or initializes a Spotipy client, ensuring authentication.
    Handles token refreshing and redirection for initial authentication.
    If authentication is needed, it returns a Flask redirect response.
    Otherwise, it returns the authenticated spotipy.Spotify client.
    """
    # Use Flask's `g` object for request-local storage to avoid re-initializing
    if 'spotify_client' in g and g.spotify_client is not None:
        return g.spotify_client

    sp_oauth = _get_spotify_oauth_manager()
    token_info = session.get('spotify_token_info', None)

    if not token_info:
        # No token in session, redirect to Spotify for authorization
        auth_url = sp_oauth.get_authorize_url()
        flash("Please authenticate with Spotify to proceed.", "info") # More prominent message
        return redirect(auth_url) # Return redirect response

    # Check if token is expired
    now = int(time.time())
    if token_info and token_info.get('expires_at') and now > token_info['expires_at']:
        try:
            # Token expired, try to refresh
            new_token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['spotify_token_info'] = new_token_info # Update token in session
            flash("Spotify token refreshed.", "info")
            token_info = new_token_info
        except Exception as e:
            # Refresh failed, need to re-authenticate
            session.pop('spotify_token_info', None) # Clear invalid token
            auth_url = sp_oauth.get_authorize_url()
            flash(f"Spotify token refresh failed: {e}. Please re-authenticate.", "error")
            return redirect(auth_url) # Return redirect response
    
    # If we got here, we have a valid (or refreshed) token
    try:
        sp_client = spotipy.Spotify(auth=token_info['access_token'])
        # Store in g for this request
        g.spotify_client = sp_client
        return sp_client
    except Exception as e:
        session.pop('spotify_token_info', None) # Clear invalid token
        flash(f"Error creating Spotify client: {e}. Please re-authenticate.", "error")
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url) # Return redirect response


def extract_playlist_id(url, platform):
    """
    Extracts the playlist ID from a given URL based on the platform.
    """
    if platform == "spotify":
        parts = url.split("/")
        if "playlist" in parts:
            return parts[-1].split("?")[0]
        else:
            raise ValueError("Invalid Spotify playlist URL. Make sure it's a playlist link.")
    elif platform == "ytmusic":
        if "list=" in url:
            return url.split("list=")[-1].split("&")[0]
        else:
            raise ValueError("Invalid YouTube Music playlist URL. It should contain 'list='.")
    return None

def transfer_playlist_generator(ytmusic_url, spotify_url, sp_client):
    """
    Transfers tracks from a YouTube Music playlist to a Spotify playlist.
    This is now a generator function that yields progress messages.
    """
    yield "info:Connecting to YouTube Music API..."
    try:
        ytmusic = YTMusic()
    except Exception as e:
        yield f"error:YouTube Music API Initialization Error: {e}"
        return

    yt_playlist_id = None
    spotify_playlist_id = None

    try:
        yt_playlist_id = extract_playlist_id(ytmusic_url, "ytmusic")
        yield "info:Fetching YouTube Music playlist data..."
        yt_data = ytmusic.get_playlist(yt_playlist_id, limit=100)
        spotify_playlist_id = extract_playlist_id(spotify_url, "spotify")
    except ValueError as e:
        yield f"error:Error extracting playlist ID: {e}"
        return
    except Exception as e:
        yield f"error:Error fetching playlist data: {e}"
        return

    if not yt_data or not yt_data.get('tracks'):
        yield "info:No tracks found in the YouTube Music playlist or playlist is empty."
        yield "complete:No tracks to transfer." # Signal completion
        return

    total_tracks = len(yt_data['tracks'])
    yield f"info:Attempting to transfer {total_tracks} tracks from YouTube Music to Spotify..."

    tracks_to_add = []
    skipped_count = 0
    added_count = 0

    for i, track in enumerate(yt_data['tracks']):
        title = track.get('title')
        if not title:
            yield f"warning:❌ Skipped track {i+1}/{total_tracks}: No title found for an entry."
            skipped_count += 1
            continue

        try:
            yield f"info:Searching Spotify for '{title}'..."
            result = sp_client.search(q=title, type='track', limit=1)
            items = result['tracks']['items']

            if not items:
                raise Exception("No matching track found on Spotify.")

            sp_track_id = items[0]['id']
            sp_track_name = items[0]['name']
            
            tracks_to_add.append(sp_track_id)
            yield f"success:✅ Found match: '{sp_track_name}' (YouTube: '{title}')"

        except Exception as e:
            yield f"warning:❌ Skipped: '{title}' ({e})"
            skipped_count += 1
    
    if tracks_to_add:
        yield f"info:Adding {len(tracks_to_add)} matched tracks to Spotify playlist in batches..."
        try:
            # Spotify API allows adding up to 100 tracks per request
            for i in range(0, len(tracks_to_add), 100):
                batch = tracks_to_add[i:i+100]
                sp_client.playlist_add_items(spotify_playlist_id, batch)
                added_count += len(batch)
                yield f"info:Added batch of {len(batch)} tracks."
            yield f"success:Successfully added {added_count} tracks to Spotify playlist."
        except spotipy.exceptions.SpotifyException as e:
            yield f"error:Error adding tracks to Spotify playlist: {e}. Check playlist ID and permissions."
        except Exception as e:
            yield f"error:An unexpected error occurred while adding tracks: {e}"
    else:
        yield "info:No tracks were found or matched for transfer."

    yield f"info:Transfer process concluded. Added: {added_count}, Skipped: {skipped_count}."
    yield "complete:" # Signal completion to client

# --- Flask Routes ---

@app.route('/', methods=['GET'])
def index():
    """
    Renders the main page with the playlist transfer form.
    Displays any flash messages from previous operations.
    """
    return render_template('index.html')

@app.route('/start_transfer', methods=['POST'])
def start_transfer():
    """
    Receives playlist URLs from the form, stores them in the session,
    and redirects to the transfer progress page.
    Crucially, it first checks Spotify authentication and redirects if needed.
    """
    ytmusic_url = request.form.get('ytmusic_url')
    spotify_url = request.form.get('spotify_url')

    if not ytmusic_url or not spotify_url:
        flash("Please provide both YouTube Music and Spotify playlist URLs.", "error")
        return redirect(url_for('index'))

    # Attempt to get an authenticated Spotify client BEFORE redirecting to progress page.
    # If authentication is needed, get_spotify_client() will return a redirect response.
    sp_client_or_redirect = get_spotify_client()
    if isinstance(sp_client_or_redirect, Response):
        # If get_spotify_client returned a redirect, return it immediately.
        # This will send the user to Spotify's login page.
        return sp_client_or_redirect

    # If we reach here, the Spotify client is authenticated for the current request.
    # Now, store the URLs in the session and proceed to the progress page.
    session['ytmusic_url'] = ytmusic_url
    session['spotify_url'] = spotify_url
    
    return redirect(url_for('show_transfer_progress'))

@app.route('/transfer_progress', methods=['GET'])
def show_transfer_progress():
    """
    Renders the page where live transfer updates will be streamed.
    """
    # Ensure URLs are in session before showing this page
    if 'ytmusic_url' not in session or 'spotify_url' not in session:
        flash("Playlist URLs not found. Please start a new transfer from the home page.", "error")
        return redirect(url_for('index'))
    return render_template('transfer_progress.html')


@app.route('/stream_transfer', methods=['GET'])
def stream_transfer():
    """
    Streams live updates of the playlist transfer process using Server-Sent Events.
    """
    # Retrieve URLs from session
    ytmusic_url = session.get('ytmusic_url')
    spotify_url = session.get('spotify_url')

    if not ytmusic_url or not spotify_url:
        return Response("data:error:Playlist URLs not found in session. Please restart transfer.\n\n", mimetype='text/event-stream')

    # Ensure Spotify client is authenticated before starting the stream
    # If auth is needed here (e.g., token expired after page load),
    # get_spotify_client will return a redirect which is handled below.
    sp_client_or_redirect = get_spotify_client()
    if isinstance(sp_client_or_redirect, Response):
        # If get_spotify_client returned a redirect (meaning auth needed),
        # we can't directly redirect the browser from an SSE stream.
        # Instead, send a message to the client instructing it to redirect.
        return Response("data:auth_needed:Spotify authentication required. Please refresh the page and re-authenticate.\n\n", mimetype='text/event-stream')
    
    sp_client = sp_client_or_redirect

    # Generator for SSE messages
    def generate_messages():
        for message in transfer_playlist_generator(ytmusic_url, spotify_url, sp_client):
            yield f"data:{message}\n\n"
            # Optional: Add a small delay to make updates more visible for testing
            # time.sleep(0.1) 
    
    # Use stream_with_context for Flask to properly handle the generator in a streaming response
    return Response(stream_with_context(generate_messages()), mimetype='text/event-stream')

@app.route('/callback')
def callback():
    """
    Handles the redirect from Spotify after user authentication.
    Exchanges the authorization code for tokens and stores them in the session.
    """
    code = request.args.get('code')
    if not code:
        flash("Spotify authorization failed: No code received.", "error")
        return redirect(url_for('index'))

    sp_oauth = _get_spotify_oauth_manager()
    try:
        token_info = sp_oauth.get_access_token(code)
        session['spotify_token_info'] = token_info
        flash("Successfully authenticated with Spotify! You can now try transferring playlists.", "success")
    except Exception as e:
        flash(f"Spotify authentication failed: {e}. Please ensure your redirect URI is correct in Spotify Developer Dashboard.", "error")
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("Starting Flask app with live update capabilities...")
    print("IMPORTANT: Make sure your .env file contains SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI.")
    print("Ensure your Spotify Developer Dashboard redirect URI is 'http://localhost:5000/callback'.")
    app.run(debug=True,port=5432,host='0.0.0.0')
