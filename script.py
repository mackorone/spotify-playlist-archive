#!/usr/bin/env python3

import base64
import collections
import json
import os
import requests


Playlist = collections.namedtuple("Playlist", ["name", "description", "tracks"])
Track = collections.namedtuple("Track", ["id", "name", "album", "artists"])


class InvalidAccessTokenError(Exception):
    pass


class InvalidPlaylistError(Exception):
    pass


class PrivatePlaylistError(Exception):
    pass


class Spotify:

    BASE_URL = "https://api.spotify.com/v1/playlists/"

    def __init__(self, client_id, client_secret):
        self._token = self._get_access_token(client_id, client_secret)

    @classmethod
    def _get_access_token(cls, client_id, client_secret):
        joined = "{}:{}".format(client_id, client_secret)
        encoded = base64.b64encode(joined.encode()).decode()
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            headers={"Authorization": "Basic {}".format(encoded)},
        ).json()
        error = response.get("error")
        if error:
            raise Exception("Failed to get access token: {}".format(error))
        access_token = response.get("access_token")
        if not access_token:
            raise Exception("Invalid access token: {}".format(access_token))
        token_type = response.get("token_type")
        if token_type != "Bearer":
            raise Exception("Invalid token type: {}".format(token_type))
        return access_token

    def get_playlist(self, playlist_id):
        playlist_href = self._get_playlist_href(playlist_id)
        response = self._make_request(playlist_href)
        error = response.get("error")
        if error:
            if error.get("status") == 401:
                raise InvalidAccessTokenError
            elif error.get("status") == 403:
                raise PrivatePlaylistError
            elif error.get("status") == 404:
                raise InvalidPlaylistError
            else:
                raise Exception("Failed to get playlist: {}".format(error))
        name = response["name"]
        description = response["description"]
        tracks = self._get_tracks(playlist_id)
        return Playlist(name=name, description=description, tracks=tracks)

    def _get_tracks(self, playlist_id):
        tracks = []
        tracks_href = self._get_tracks_href(playlist_id)
        while tracks_href:
            response = self._make_request(tracks_href)
            error = response.get("error")
            if error:
                raise Exception("Failed to get tracks: {}".format(error))
            for item in response["items"]:
                id_ = item["track"]["id"]
                name = item["track"]["name"]
                album = item["track"]["album"]["name"]
                artists = []
                for artist in item["track"]["artists"]:
                    artists.append(artist["name"])
                tracks.append(Track(
                    id=id_,
                    name=name,
                    album=album,
                    artists=artists,
                ))
            tracks_href = response["next"]
        return tracks

    @classmethod
    def _get_playlist_href(cls, playlist_id):
        rest = "{}?fields=name,description"
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    @classmethod
    def _get_tracks_href(cls, playlist_id):
        rest = "{}/tracks?fields=next,items.track(id,name,album.name,artists)"
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    def _make_request(self, href):
        return requests.get(
            href,
            headers={"Authorization": "Bearer {}".format(self._token)},
        ).json()


def format_playlist(playlist_id, playlist):
    tracks = playlist.tracks
    width = len(str(len(tracks)))
    track_numbers = {tracks[i].id: i + 1 for i in range(len(tracks))}
    lines = [playlist.name, playlist.description, ""]
    # Sort by ID, rather than track number, to minimize diffs
    for track in sorted(playlist.tracks, key=lambda track: track.id):
        lines.append("{}. {} -- {} -- {}".format(
            str(track_numbers[track.id]).zfill(width),
            track.name,
            ", ".join(track.artists),
            track.album,
        ))
    return "\n".join(lines)


def main():
    spotify = Spotify(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    playlists = open("playlist_ids.txt").read().splitlines()
    for playlist_id in playlists:
        try:
            playlist = spotify.get_playlist(playlist_id)
        except PrivatePlaylistError:
            print("Skipping private playlist: {}".format(playlist_id))
        except InvalidPlaylistError:
            print("Skipping invalid playlist: {}".format(playlist_id))
        else:
            new_content = format_playlist(playlist_id, playlist)
            path = "playlists/{}.txt".format(playlist_id)
            try:
                existing_content = "".join(open(path).readlines())
            except Exception:
                existing_content = None
            if new_content == existing_content:
                print("No changes to playlist: {}".format(playlist_id))
            else:
                with open(path, "w") as f:
                    f.write(new_content)
                print("Updated playlist: {}".format(playlist_id))
    print("Done")


if __name__ == "__main__":
    main()
