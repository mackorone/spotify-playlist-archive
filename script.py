#!/usr/bin/env python3

import base64
import collections
import datetime
import json
import os
import requests
import subprocess


Playlist = collections.namedtuple(
    "Playlist",
    [
        "url",
        "name",
        "description",
        "tracks",
    ]
)

Track = collections.namedtuple(
    "Track",
    [
        "id",
        "url",
        "duration_ms",
        "name",
        "album",
        "artists",
    ]
)

Album = collections.namedtuple("Album", ["url", "name"])

Artist = collections.namedtuple("Artist", ["url", "name"])


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
        url = self._get_url(response["external_urls"])
        name = response["name"]
        description = response["description"]
        tracks = self._get_tracks(playlist_id)
        return Playlist(url=url,name=name, description=description, tracks=tracks)

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
                url = self._get_url(item["track"]["external_urls"])
                duration_ms = item["track"]["duration_ms"]
                name = item["track"]["name"]
                album = Album(
                    url=self._get_url(item["track"]["album"]["external_urls"]),
                    name=item["track"]["album"]["name"],
                )
                artists = []
                for artist in item["track"]["artists"]:
                    artists.append(Artist(
                        url=self._get_url(artist["external_urls"]),
                        name=artist["name"],
                    ))
                tracks.append(Track(
                    id=id_,
                    url=url,
                    duration_ms=duration_ms,
                    name=name,
                    album=album,
                    artists=artists,
                ))
            tracks_href = response["next"]
        return tracks

    @classmethod
    def _get_url(cls, external_urls):
        return (external_urls or {}).get("spotify")

    @classmethod
    def _get_playlist_href(cls, playlist_id):
        rest = "{}?fields=external_urls,name,description"
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    @classmethod
    def _get_tracks_href(cls, playlist_id):
        rest = (
            "{}/tracks?fields=next,items.track(id,external_urls,"
            "duration_ms,name,album(external_urls,name),artists)"
        )
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    def _make_request(self, href):
        return requests.get(
            href,
            headers={"Authorization": "Bearer {}".format(self._token)},
        ).json()


class Formatter:

    @classmethod
    def raw(cls, playlist_id, playlist):
        tracks = playlist.tracks
        lines = [playlist.name, playlist.description, ""]
        # Sort by ID to minimize raw diffs
        for track in sorted(playlist.tracks, key=lambda track: track.id):
            lines.append("{} -- {} -- {}".format(
                track.name,
                ", ".join([artist.name for artist in track.artists]),
                track.album.name,
            ))
        return "\n".join(lines)

    @classmethod
    def pretty(cls, playlist_id, playlist):
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
                track.album.name,
            ))
        return "\n".join(lines)


def update_files():
    spotify = Spotify(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    # Determine which playlists to scrape from the file names in playlists/raw.
    # This makes it easy to add new a playlist: just touch an empty file like
    # playlists/raw/<playlist_id> and this script will handle the rest.
    for playlist_id in os.listdir("playlists/raw"):
        try:
            playlist = spotify.get_playlist(playlist_id)
        except PrivatePlaylistError:
            print("Removing private playlist: {}".format(playlist_id))
            os.remove("playlists/raw/{}".format(playlist_id))
        except InvalidPlaylistError:
            print("Removing invalid playlist: {}".format(playlist_id))
            os.remove("playlists/raw/{}".format(playlist_id))
        else:
            for dir_, func in [
                ("raw", Formatter.raw),
                ("pretty", Formatter.pretty),
            ]:
                path = "playlists/{}/{}".format(dir_, playlist_id)
                next_content = Formatter.raw(playlist_id, playlist)
                try:
                    prev_content = "".join(open(path).readlines())
                except Exception:
                    prev_content = None
                if next_content == prev_content:
                    print("No changes to file: {}".format(path))
                else:
                    print("Writing updates to file: {}".format(path))
                    with open(path, "w") as f:
                        f.write(new_content)


def run(args):
    print("- Running: {}".format(args))
    result = subprocess.run(
        args=args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print("- Exited with: {}".format(result.returncode))
    return result


def push_updates():
    diff = run(["git", "status", "-s"])
    has_changes = bool(diff.stdout)
    if not has_changes:
        print("No changes, not pushing")
        return

    print("Configuring git")
    config = ["git", "config", "--global"]
    config_name = run(config + ["user.name", "Mack Ward (Bot Account)"])
    config_email = run(config + ["user.email", "mackorone.bot@gmail.com"])
    if config_name.returncode != 0:
        raise Exception("Failed to configure name")
    if config_email.returncode != 0:
        raise Exception("Failed to configure email")

    print("Staging changes")
    add = run(["git", "add", "-A"])
    if add.returncode != 0:
        raise Exception("Failed to stage changes")

    print("Committing changes")
    build = os.getenv("TRAVIS_BUILD_NUMBER")
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    message = "[skip ci] Build #{} ({})".format(build, now_str)
    commit = run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        raise Exception("Failed to commit changes")

    print("Rebasing onto master")
    rebase = run(["git", "rebase", "HEAD", "master"])
    if commit.returncode != 0:
        raise Exception("Failed to rebase onto master")

    print("Removing origin")
    remote_rm = run(["git", "remote", "rm", "origin"])
    if remote_rm.returncode != 0:
        raise Excetion("Failed to remove origin")

    print("Adding new origin")
    # It's ok to print the token, Travis will hide it
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    url = (
        "https://mackorone-bot:{}@github.com/mackorone/"
        "spotify-playlist-archive.git".format(token)
    )
    remote_add = run(["git", "remote", "add", "origin", url])
    if remote_add.returncode != 0:
        raise Exception("Failed to add new origin")

    print("Pushing changes")
    push = run(["git", "push", "origin", "master"])
    if push.returncode != 0:
        raise Exception("Failed to push changes")


def main():
    update_files()
    # push_updates()
    print("Done")


if __name__ == "__main__":
    main()
