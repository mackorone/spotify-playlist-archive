# Developing and Contributing

## Getting API Access

See the Spotify [Web API
Tutorial](https://developer.spotify.com/documentation/web-api/quick-start/).

Put the _client id_ and _client secret_ in the environment variables
`SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` respectively.

## Setting up the Export Feature

In order to use the export feature, where the it re-publishes the
cumulative playlists to spotify, the script needs to have access to a
user. For that to work, the url http://localhost:8000 needs to be
added to the _Redirect URIs_ field of the app settings. When that's
done, getting a token should be as simple as running the script like
this:

```
$ python script.py login
Opening the following URL in a browser (at least trying to):
https://accounts.spotify.com/authorize?client_id=...&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8000&scope=playlist-modify-public
127.0.0.1 - - [05/Jan/2021 20:54:52] "GET /?code=some-secret-code HTTP/1.1" 200 -
Refresh token, store this somewhere safe and use for the export feature:
some-secret-code
```

Put the code in the environment variable `SPOTIFY_USER_TOKEN` to give
the script access to your playlists.

A few notes:
- The script stores the re-exported playlist id in `playlists/export`.
- A playlist is tied to a specific user. If a playlist exists but you
  don't have access to it, you have to remove the corresponding entry
  in `playlists/export` and run the script again.
