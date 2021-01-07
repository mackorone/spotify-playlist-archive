#!/usr/bin/env python3

import argparse
import base64
import collections
import datetime
import os
import re
import subprocess

import requests


Playlist = collections.namedtuple(
    "Playlist",
    [
        "url",
        "name",
        "description",
        "tracks",
    ],
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
    ],
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

    def get_playlist(self, playlist_id, aliases):
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

        # If the playlist has an alias, use it
        if playlist_id in aliases:
            name = aliases[playlist_id]
        else:
            name = response["name"]

        # Playlist names can't have "/" so use "\" instead
        name = name.replace("/", "\\")
        description = response["description"]
        tracks = self._get_tracks(playlist_id)

        return Playlist(url=url, name=name, description=description, tracks=tracks)

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
                    artists.append(
                        Artist(
                            url=self._get_url(artist["external_urls"]),
                            name=artist["name"],
                        )
                    )

                tracks.append(
                    Track(
                        id=id_,
                        url=url,
                        duration_ms=duration_ms,
                        name=name,
                        album=album,
                        artists=artists,
                    )
                )

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

    TRACK_NO = "No."
    TITLE = "Title"
    ARTISTS = "Artist(s)"
    ALBUM = "Album"
    LENGTH = "Length"
    ADDED = "Added"
    REMOVED = "Removed"

    ARTIST_SEPARATOR = ", "
    LINK_REGEX = r"\[(.+?)\]\(.+?\)"

    @classmethod
    def plain(cls, playlist_id, playlist):
        lines = [cls._plain_line_from_track(track) for track in playlist.tracks]
        # Sort alphabetically to minimize changes when tracks are reordered
        sorted_lines = sorted(lines, key=lambda line: line.lower())
        header = [playlist.name, playlist.description, ""]
        return "\n".join(header + sorted_lines)

    @classmethod
    def pretty(cls, playlist_id, playlist):
        columns = [
            cls.TRACK_NO,
            cls.TITLE,
            cls.ARTISTS,
            cls.ALBUM,
            cls.LENGTH,
        ]

        vertical_separators = ["|"] * (len(columns) + 1)
        line_template = " {} ".join(vertical_separators)
        divider_line = "---".join(vertical_separators)
        lines = cls._markdown_header_lines(
            playlist_name=playlist.name,
            playlist_url=playlist.url,
            playlist_id=playlist_id,
            playlist_description=playlist.description,
            is_cumulative=False,
        )
        lines += [
            line_template.format(*columns),
            divider_line,
        ]

        for i, track in enumerate(playlist.tracks):
            lines.append(
                line_template.format(
                    i + 1,
                    cls._link(track.name, track.url),
                    cls.ARTIST_SEPARATOR.join(
                        [cls._link(artist.name, artist.url) for artist in track.artists]
                    ),
                    cls._link(track.album.name, track.album.url),
                    cls._format_duration(track.duration_ms),
                )
            )

        return "\n".join(lines)

    @classmethod
    def cumulative(cls, now, prev_content, playlist_id, playlist):
        today = now.strftime("%Y-%m-%d")
        columns = [
            cls.TITLE,
            cls.ARTISTS,
            cls.ALBUM,
            cls.LENGTH,
            cls.ADDED,
            cls.REMOVED,
        ]

        vertical_separators = ["|"] * (len(columns) + 1)
        line_template = " {} ".join(vertical_separators)
        divider_line = "---".join(vertical_separators)
        header = cls._markdown_header_lines(
            playlist_name=playlist.name,
            playlist_url=playlist.url,
            playlist_id=playlist_id,
            playlist_description=playlist.description,
            is_cumulative=True,
        )
        header += [
            line_template.format(*columns),
            divider_line,
        ]

        # Retrieve existing rows, then add new rows
        rows = cls._rows_from_prev_content(today, prev_content, divider_line)
        for track in playlist.tracks:
            # Get the row for the given track
            key = cls._plain_line_from_track(track).lower()
            row = rows.get(key, {column: None for column in columns})
            rows[key] = row
            # Update row values
            row[cls.TITLE] = cls._link(track.name, track.url)
            row[cls.ARTISTS] = cls.ARTIST_SEPARATOR.join(
                [cls._link(artist.name, artist.url) for artist in track.artists]
            )
            row[cls.ALBUM] = cls._link(track.album.name, track.album.url)
            row[cls.LENGTH] = cls._format_duration(track.duration_ms)

            if not row[cls.ADDED]:
                row[cls.ADDED] = today

            row[cls.REMOVED] = ""

        lines = []
        for key, row in sorted(rows.items()):
            lines.append(line_template.format(*[row[column] for column in columns]))

        return "\n".join(header + lines)

    @classmethod
    def _markdown_header_lines(
        cls,
        playlist_name,
        playlist_url,
        playlist_id,
        playlist_description,
        is_cumulative,
    ):
        if is_cumulative:
            pretty = cls._link("pretty", URL.pretty(playlist_name))
            cumulative = "cumulative"
        else:
            pretty = "pretty"
            cumulative = cls._link("cumulative", URL.cumulative(playlist_name))

        return [
            "{} - {} - {} ({})".format(
                pretty,
                cumulative,
                cls._link("plain", URL.plain(playlist_id)),
                cls._link("githistory", URL.plain_history(playlist_id)),
            ),
            "",
            "### {}".format(cls._link(playlist_name, playlist_url)),
            "",
            "> {}".format(playlist_description),
            "",
        ]

    @classmethod
    def _rows_from_prev_content(cls, today, prev_content, divider_line):
        rows = {}
        if not prev_content:
            return rows

        prev_lines = prev_content.splitlines()
        try:
            index = prev_lines.index(divider_line)
        except ValueError:
            return rows

        for i in range(index + 1, len(prev_lines)):
            prev_line = prev_lines[i]

            try:
                title, artists, album, length, added, removed = (
                    # Slice [2:-2] to trim off "| " and " |"
                    prev_line[2:-2].split(" | ")
                )
            except Exception:
                continue

            key = cls._plain_line_from_names(
                track_name=cls._unlink(title),
                artist_names=[artist for artist in re.findall(cls.LINK_REGEX, artists)],
                album_name=cls._unlink(album),
            ).lower()

            row = {
                cls.TITLE: title,
                cls.ARTISTS: artists,
                cls.ALBUM: album,
                cls.LENGTH: length,
                cls.ADDED: added,
                cls.REMOVED: removed,
            }
            rows[key] = row

            if not row[cls.REMOVED]:
                row[cls.REMOVED] = today

        return rows

    @classmethod
    def _plain_line_from_track(cls, track):
        return cls._plain_line_from_names(
            track_name=track.name,
            artist_names=[artist.name for artist in track.artists],
            album_name=track.album.name,
        )

    @classmethod
    def _plain_line_from_names(cls, track_name, artist_names, album_name):
        return "{} -- {} -- {}".format(
            track_name,
            cls.ARTIST_SEPARATOR.join(artist_names),
            album_name,
        )

    @classmethod
    def _link(cls, text, url):
        if not url:
            return text
        return "[{}]({})".format(text, url)

    @classmethod
    def _unlink(cls, link):
        return re.match(cls.LINK_REGEX, link).group(1)

    @classmethod
    def _format_duration(cls, duration_ms):
        seconds = int(duration_ms // 1000)
        timedelta = str(datetime.timedelta(seconds=seconds))

        index = 0
        while timedelta[index] in [":", "0"]:
            index += 1

        return timedelta[index:]


class URL:

    BASE = (
        "https://github.com/mackorone/spotify-playlist-archive/"
        "blob/master/playlists/"
    )

    @classmethod
    def plain_history(cls, playlist_id):
        plain = cls.plain(playlist_id)
        return plain.replace("github.com", "github.githistory.xyz")

    @classmethod
    def plain(cls, playlist_id):
        return cls.BASE + "plain/{}".format(playlist_id)

    @classmethod
    def pretty(cls, playlist_name):
        sanitized = playlist_name.replace(" ", "%20")
        return cls.BASE + "pretty/{}.md".format(sanitized)

    @classmethod
    def cumulative(cls, playlist_name):
        sanitized = playlist_name.replace(" ", "%20")
        return cls.BASE + "cumulative/{}.md".format(sanitized)


def update_files(now):
    spotify = Spotify(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )

    aliases_dir = "playlists/aliases"
    plain_dir = "playlists/plain"
    pretty_dir = "playlists/pretty"
    cumulative_dir = "playlists/cumulative"

    # Determine which playlists to scrape from the files in playlists/plain.
    # This makes it easy to add new a playlist: just touch an empty file like
    # playlists/plain/<playlist_id> and this script will handle the rest.
    playlist_ids = os.listdir(plain_dir)

    # Aliases are alternative playlists names. They're useful for avoiding
    # naming collisions when archiving personalized playlists, which have the
    # same name for every user. To add an alias, simply create a file like
    # playlists/aliases/<playlist_id> that contains the alternative name.
    aliases = {}
    for playlist_id in os.listdir(aliases_dir):
        alias_path = "{}/{}".format(aliases_dir, playlist_id)
        if playlist_id not in playlist_ids:
            print("Removing unused alias: {}".format(playlist_id))
            os.remove(alias_path)
            continue
        contents = open(alias_path).read().splitlines()
        if len(contents) != 1:
            print("Removing malformed alias: {}".format(playlist_id))
            os.remove(alias_path)
            continue
        aliases[playlist_id] = contents[0]

    readme_lines = []
    for playlist_id in playlist_ids:
        plain_path = "{}/{}".format(plain_dir, playlist_id)

        try:
            playlist = spotify.get_playlist(playlist_id, aliases)
        except PrivatePlaylistError:
            print("Removing private playlist: {}".format(playlist_id))
            os.remove(plain_path)
        except InvalidPlaylistError:
            print("Removing invalid playlist: {}".format(playlist_id))
            os.remove(plain_path)
        else:
            readme_lines.append(
                "- [{}]({})".format(
                    playlist.name,
                    URL.pretty(playlist.name),
                )
            )

            pretty_path = "{}/{}.md".format(pretty_dir, playlist.name)
            cumulative_path = "{}/{}.md".format(cumulative_dir, playlist.name)

            for path, func, flag in [
                (plain_path, Formatter.plain, False),
                (pretty_path, Formatter.pretty, False),
                (cumulative_path, Formatter.cumulative, True),
            ]:
                try:
                    prev_content = "".join(open(path).readlines())
                except Exception:
                    prev_content = None

                if flag:
                    args = [now, prev_content, playlist_id, playlist]
                else:
                    args = [playlist_id, playlist]

                content = func(*args)
                if content == prev_content:
                    print("No changes to file: {}".format(path))
                else:
                    print("Writing updates to file: {}".format(path))
                    with open(path, "w") as f:
                        f.write(content)

    # Sanity check: ensure same number of files in playlists/plain and
    # playlists/pretty - if not, some playlists have the same name and
    # overwrote each other in playlists/pretty OR a playlist ID was changed
    # and the file in playlists/plain was removed and needs to be re-added
    plain_playlists = set()
    for filename in os.listdir(plain_dir):
        with open(os.path.join(plain_dir, filename)) as f:
            plain_playlists.add(f.readline().strip())

    pretty_playlists = set()
    for filename in os.listdir(pretty_dir):
        pretty_playlists.add(filename[:-3])  # strip .md suffix

    missing_from_plain = pretty_playlists - plain_playlists
    missing_from_pretty = plain_playlists - pretty_playlists

    if missing_from_plain:
        raise Exception("Missing plain playlists: {}".format(missing_from_plain))

    if missing_from_pretty:
        raise Exception("Missing pretty playlists: {}".format(missing_from_pretty))

    # Lastly, update README.md
    readme = open("README.md").read().splitlines()
    index = readme.index("## Playlists")
    lines = (
        readme[: index + 1] + [""] + sorted(readme_lines, key=lambda line: line.lower())
    )
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


def push_updates(now):
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
        raise Exception("Failed to remove origin")

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
    parser = argparse.ArgumentParser(description="Snapshot Spotify playlists")
    parser.add_argument(
        "--push",
        help="Commit and push updated playlists",
        action="store_true",
    )
    args = parser.parse_args()
    now = datetime.datetime.now()
    update_files(now)

    if args.push:
        push_updates(now)

    print("Done")


if __name__ == "__main__":
    main()
