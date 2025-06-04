
# YT_To_Spotify

A Python tool to transfer playlists from YouTube Music to Spotify.

## Features

-   Transfer up to 100 tracks per playlist from YouTube Music to Spotify
    
-   Matches tracks by title using Spotify's search API
    
-   Supports both hardcoded URLs and user input
    
-   Clean, modular code structure for easy customization
    

## Requirements

-   Python 3.7 or higher
    
-   Spotify Developer account with a registered application
    
-   Spotify credentials: Client ID, Client Secret, and Redirect URI
    
-   A Spotify playlist (public or private) to receive the transferred tracks
    
-   A YouTube Music playlist URL

## Installation

1.  **Clone the repository:**
```py
git clone https://github.com/micfun123/YT_To_Spotify.git
cd YT_To_Spotify
```

2. **Install the required packages:**
```py
pip install -r requirements.txt
```
3.**Set up your `.env` file:**

Create a `.env` file in the project root directory and add your Spotify credentials:
```
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```
Replace `your_spotify_client_id` and `your_spotify_client_secret` with your actual Spotify API credentials.

4. **Usage:**
```
main.py YtMusicPlaylist SpotifyPlayList
```

## Notes

-   The script transfers up to 100 tracks due to API limitations.
    
-   Tracks are matched by title; discrepancies may occur if there are naming differences.
    
-   Ensure your Spotify playlist is created before running the script.
    

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

-   [ytmusicapi](https://github.com/sigma67/ytmusicapi) for interacting with YouTube Music
    
-   [Spotipy](https://github.com/plamere/spotipy) for Spotify API integration
    
-   [python-dotenv](https://github.com/theskumar/python-dotenv) for managing environment variables
