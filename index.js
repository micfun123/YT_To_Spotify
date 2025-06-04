require('dotenv').config();
const SpotifyWebApi = require('spotify-web-api-node');
const YTMusicApi = require('ytmusic-api');

const spotifyApi = new SpotifyWebApi({
  clientId: process.env.SPOTIFY_CLIENT_ID,
  clientSecret: process.env.SPOTIFY_CLIENT_SECRET,
  redirectUri: process.env.SPOTIFY_REDIRECT_URI,
});

// TODO: Add Spotify OAuth flow here
// TODO: Fetch playlist from YTMusic
// TODO: Search & add songs to Spotify playlist

console.log('Project setup complete ✅');
