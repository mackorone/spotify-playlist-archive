#!/usr/bin/env python3

import argparse
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
                track = item["track"]
                if not track:
                    continue
                id_ = track["id"]
                url = self._get_url(track["external_urls"])
                duration_ms = track["duration_ms"]
                name = track["name"]
                album = Album(
                    url=self._get_url(track["album"]["external_urls"]),
                    name=track["album"]["name"],
                )
                artists = []
                for artist in track["artists"]:
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
    def plain(cls, playlist_id, playlist):
        tracks = playlist.tracks
        lines = []
        for track in playlist.tracks:
            lines.append("{} -- {} -- {}".format(
                track.name,
                ", ".join([artist.name for artist in track.artists]),
                track.album.name,
            ))
        # Sort alphabetically to minimize changes when tracks are reordered
        sorted_tracks = sorted(lines, key=lambda line: line.lower())
        header = [playlist.name, playlist.description, ""]
        return "\n".join(header + sorted_tracks)

    @classmethod
    def pretty(cls, playlist_id, playlist):
        tracks = playlist.tracks
        lines = [
            "### {} ({})".format(
                cls._link(playlist.name, playlist.url),
                cls._link(playlist_id, URL.plain(playlist_id)),
            ),
            "",
            "> {}".format(playlist.description),
            "",
            "| No. | Title | Artist(s) | Album | Length |",
            "|-----|-------|-----------|-------|--------|",
        ]
        for i, track in enumerate(playlist.tracks):
            lines.append("| {} | {} | {} | {} | {} |".format(
                i + 1,
                cls._link(track.name, track.url),
                ", ".join([
                    cls._link(artist.name, artist.url)
                    for artist in track.artists
                ]),
                cls._link(track.album.name, track.album.url),
                cls._format_duration(track.duration_ms),
            ))
        return "\n".join(lines)

    @classmethod
    def _link(cls, text, url):
        if not url:
            return text
        return "[{}]({})".format(text, url)

    @classmethod
    def _format_duration(cls, duration_ms):
        seconds = int(duration_ms // 1000)
        timedelta = str(datetime.timedelta(seconds=seconds))
        index = 0
        while timedelta[index] in [":", "0"]:
            index += 1
        return timedelta[index:]


class URL:

    BASE =  (
        "https://github.com/mackorone/spotify-playlist-archive/"
        "blob/master/playlists/"
    )

    @classmethod
    def plain(cls, playlist_id):
        return cls.BASE + "plain/{}".format(playlist_id)

    @classmethod
    def pretty(cls, playlist_name):
        sanitized = playlist_name.replace(" ", "%20")
        return cls.BASE + "pretty/{}.md".format(sanitized)


def update_files():
    spotify = Spotify(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    # Determine which playlists to scrape from the files in playlists/plain.
    # This makes it easy to add new a playlist: just touch an empty file like
    # playlists/plain/<playlist_id> and this script will handle the rest.
    plain_dir = "playlists/plain"
    pretty_dir = "playlists/pretty"
    playlist_ids = os.listdir(plain_dir)
    readme_lines = []
    for playlist_id in playlist_ids:
        plain_path = "{}/{}".format(plain_dir, playlist_id)
        try:
            playlist = spotify.get_playlist(playlist_id)
        except PrivatePlaylistError:
            print("Removing private playlist: {}".format(playlist_id))
            os.remove(plain_path)
        except InvalidPlaylistError:
            print("Removing invalid playlist: {}".format(playlist_id))
            os.remove(plain_path)
        else:
            readme_lines.append("- [{}]({})".format(
                playlist.name,
                URL.pretty(playlist.name),
            ))
            pretty_path = "{}/{}.md".format(pretty_dir, playlist.name)
            for path, func in [
                (plain_path, Formatter.plain),
                (pretty_path, Formatter.pretty),
            ]:
                content = func(playlist_id, playlist)
                try:
                    prev_content = "".join(open(path).readlines())
                except Exception:
                    prev_content = None
                if content == prev_content:
                    print("No changes to file: {}".format(path))
                else:
                    print("Writing updates to file: {}".format(path))
                    with open(path, "w") as f:
                        f.write(content)

    # Sanity check: ensure same number of files in playlists/plain and
    # playlists/pretty - if not, some playlists have the same name and
    # overwrote each other in playlists/pretty
    num_plain_playlists = len(os.listdir(plain_dir))
    num_pretty_playlists = len(os.listdir(pretty_dir))
    if num_plain_playlists != num_pretty_playlists:
        raise Exception("Unequal number of playlists: {} vs {}".format(
            num_plain_playlists,
            num_pretty_playlists,
        ))

    # Lastly, update README.md
    readme = open("README.md").read().splitlines()
    index = readme.index("## Playlists")
    lines = readme[:index + 1] + [""] + sorted(readme_lines)
    with open("README.md", "w") as f:
        f.write("\n".join(lines) + "\n")


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
    parser = argparse.ArgumentParser("Snapshot Spotify playlists")
    parser.add_argument(
        "--push",
        help="Commit and push updated playlists",
        action="store_true",
    )
    args = parser.parse_args()
    update_files()
    if args.push:
        push_updates()
    print("Done")


if __name__ == "__main__":
    main()
