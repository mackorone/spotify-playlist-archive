#!/usr/bin/env python3

import argparse
import base64
import collections
import datetime
import os
import re
import subprocess
import urllib.parse

import requests


Playlist = collections.namedtuple(
    "Playlist",
    [
        "id",
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

aliases_dir = "playlists/aliases"
plain_dir = "playlists/plain"
pretty_dir = "playlists/pretty"
cumulative_dir = "playlists/cumulative"
export_dir = "playlists/export"


class InvalidAccessTokenError(Exception):
    pass


class InvalidPlaylistError(Exception):
    pass


class PrivatePlaylistError(Exception):
    pass


class Spotify:

    BASE_URL = "https://api.spotify.com/v1"
    REDIRECT_URI = "http://localhost:8000"

    def __init__(self, client_id, client_secret, user_token=None):
        if user_token:
            self._token = self._get_user_access_token(
                client_id, client_secret, user_token
            )
        else:
            self._token = self._get_access_token(client_id, client_secret)
            self._user_id = None

        self._session = requests.Session()
        self._session.headers = {
            "Authorization": "Bearer {}".format(self._token)
        }

        if user_token:
            self._user_id = self.get_current_user_id()
        else:
            self._user_id = None

    def add_items(self, playlist_id, track_ids):
        # Group the tracks in batches of 100, since that's the limit.
        for i in range(0, len(track_ids), 100):
            track_uris = [
                "spotify:track:{}".format(track_id)
                for track_id in track_ids[i:i+100]
            ]
            response = self._session.post(
                self._post_tracks_href(playlist_id),
                json={
                    "uris": track_uris
                }
            ).json()
            error = response.get("error")
            if error:
                raise Exception(
                    "Failed to add tracks to playlist, error: {}".formt(error)
                )

    def change_playlist_details(self, playlist_id, name, description):
        response = self._session.put(
            self._change_playlist_details_href(playlist_id),
            json={
                "name": name,
                "description": description,
                "public": True,
                "collaborative": False,
            }
        )
        return response.status_code == 200

    def create_playlist(self, name):
        if self._user_id is None:
            raise Exception(
                "Creating playlists requires logging in!"
            )

        response = self._session.post(
            self._create_playlist_href(self._user_id),
            json={
                "name": name,
                "public": True,
                "collaborative": False,
            }
        ).json()

        print(response)


        return Playlist(
            id=response["id"],
            name=response["name"],
            description=None,
            url=self._get_url(response["external_urls"]),
            tracks=[]
        )

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

    @classmethod
    def _get_user_access_token(cls, client_id, client_secret, refresh_token):
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            auth=(client_id, client_secret),
        ).json()

        error = response.get("error")
        if error:
            print(response)
            raise Exception("Failed to get access token: {}".format(error))

        access_token = response.get("access_token")
        if not access_token:
            raise Exception("Invalid access token: {}".format(access_token))

        token_type = response.get("token_type")
        if token_type != "Bearer":
            raise Exception("Invalid token type: {}".format(token_type))

        return access_token

    @classmethod
    def get_user_refresh_token(cls, client_id, client_secret, authorization_code):
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": cls.REDIRECT_URI,
            },
            auth=(client_id, client_secret),
        ).json()

        error = response.get("error")
        if error:
            print(response)
            raise Exception("Failed to get access token: {}".format(error))

        refresh_token = response.get("refresh_token")
        if not refresh_token:
            raise Exception("Invalid refresh token: {}".format(refresh_token))

        token_type = response.get("token_type")
        if token_type != "Bearer":
            raise Exception("Invalid token type: {}".format(token_type))

        return refresh_token

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
        id = response["id"]
        name = name.replace("/", "\\")
        description = response["description"]
        tracks = self._get_tracks(playlist_id)

        return Playlist(
            id=id,
            url=url,
            name=name,
            description=description,
            tracks=tracks
        )

    def get_current_user_id(self):
        response = self._make_request(self._get_current_user_href())
        return response["id"]

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
    def _get_current_user_href(cls):
        return cls.BASE_URL + "/me"

    @classmethod
    def _create_playlist_href(cls, user_id):
        return cls.BASE_URL + "/users/{}/playlists".format(user_id)

    @classmethod
    def _change_playlist_details_href(cls, playlist_id):
        return cls.BASE_URL + "/playlists/{}".format(playlist_id)

    @classmethod
    def _get_playlist_href(cls, playlist_id):
        rest = "/playlists/{}?fields=id,external_urls,name,description"
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    @classmethod
    def _post_tracks_href(cls, playlist_id):
        return cls.BASE_URL + "/playlists/{}/tracks".format(playlist_id)

    @classmethod
    def _get_tracks_href(cls, playlist_id):
        rest = (
            "/playlists/{}/tracks?fields=next,items.track(id,external_urls,"
            "duration_ms,name,album(external_urls,name),artists)"
        )
        template = cls.BASE_URL + rest
        return template.format(playlist_id)

    def _make_request(self, href, params=None):
        return self._session.get(
            href,
            params=None,
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
    def plain(cls, playlist_id, playlist, export_playlist=None):
        lines = [cls._plain_line_from_track(track) for track in playlist.tracks]
        # Sort alphabetically to minimize changes when tracks are reordered
        sorted_lines = sorted(lines, key=lambda line: line.lower())
        header = [playlist.name, playlist.description, ""]
        return "\n".join(header + sorted_lines)

    @classmethod
    def pretty(cls, playlist_id, playlist, export_playlist=None):
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
            export_url=export_playlist.url if export_playlist else None,
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
    def cumulative(cls, now, prev_content, playlist_id, playlist, export_playlist=None):
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
            export_url=export_playlist.url if export_playlist else None,
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
        export_url=None,
    ):
        if is_cumulative:
            pretty = cls._link("pretty", URL.pretty(playlist_name))
            cumulative = "cumulative"
        else:
            pretty = "pretty"
            cumulative = cls._link("cumulative", URL.cumulative(playlist_name))

        if export_url:
            export = " ({})".format(cls._link("re-exported", export_url))
        else:
            export = ""

        return [
            "{} - {}{} - {} ({})".format(
                pretty,
                cumulative,
                export,
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


def update_files(now, export=False):
    if export:
        user_token = os.getenv("SPOTIFY_USER_TOKEN")
        if not user_token:
            raise Exception(
                "SPOTIFY_USER_TOKEN is required for the export feature, "
                "obtain it by logging in first."
            )
    else:
        user_token = None
    spotify = Spotify(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        user_token=user_token,
    )

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
    playlists = {} # Save for later use.
    exported = {}  # Maps playlist id to exported playlist
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
            playlists[playlist_id] = playlist

            # TODO: Move the export code?
            export_playlist = None
            if export:
                export_path = os.path.join(export_dir, playlist_id)
                try:
                    with open(export_path) as f:
                        export_id = f.read().strip()
                except FileNotFoundError:
                    export_id = None

                if export_id is None:
                    print("Creating export playlist for: {}".format(playlist_id))
                    export_playlist = spotify.create_playlist(playlist.name)

                    # Creating the export dir should only be needed once.
                    os.mkdir(export_dir)

                    with open(export_path, 'w') as f:
                        f.write(export_playlist.id)
                else:
                    export_playlist = spotify.get_playlist(export_id, [])
                exported[playlist_id] = export_playlist

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

                kwargs = {
                    # Note: None if export is False
                    "export_playlist": export_playlist
                }
                if flag:
                    args = [now, prev_content, playlist_id, playlist]
                else:
                    args = [playlist_id, playlist]

                content = func(*args, **kwargs)
                if content == prev_content:
                    print("No changes to file: {}".format(path))
                else:
                    print("Writing updates to file: {}".format(path))
                    with open(path, "w") as f:
                        f.write(content)

    if export:
        export_playlists(now, playlists, exported, spotify)

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


def export_playlists(now, playlists, exported, spotify):
    # TODO: Not sure if this is the best way of doing
    # it. update_playlists is currently responsible of *creating* the
    # playlists since the export id is needed in the output
    # files. However, the main *publish* logic is put here.

    user_id = spotify.get_current_user_id()
    for playlist_id, playlist in playlists.items():
        try:
            export_playlist = exported[playlist_id]
        except KeyError:
            print("No export id for playlist: {}".format(playlist_id))
            continue

        # TODO: Add last updated
        # TODO: Add since
        description = "Playlist containing all tracks from {}.".format(
            playlist.name
        )
        name = "{} (archive)".format(playlist.name)

        print(
            "Updating playlist details for: {} (exported as {})".format(
                playlist_id,
                export_playlist.id
            )
        )
        spotify.change_playlist_details(
            export_playlist.id,
            name,
            description
        )

        old_tracks = {
            t.id for t in export_playlist.tracks
        }
        new_tracks = [
            t.id
            for t in playlist.tracks
            if t.id not in old_tracks
        ]

        spotify.add_items(export_playlist.id, new_tracks)


def login(now):
    # Login OAuth flow.
    #
    # 1. Opens the authorize url in the default browser (on Linux).
    # 2. Sets up an HTTP server on port 8000 to listen for the
    #    callback.
    # 3. Requests a refresh token for the user and prints it.

    # Build the target URL
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    query_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": Spotify.REDIRECT_URI,
        "scope": "playlist-modify-public",
    }
    target_url = "https://accounts.spotify.com/authorize?{}".format(
        urllib.parse.urlencode(query_params)
    )

    # Print and try to open the URL in the default browser.
    print("Opening the following URL in a browser (at least trying to):")
    print(target_url)
    os.system("xdg-open '{}'".format(target_url))

    # Set up a temporary HTTP server and listen for the callback
    from http import HTTPStatus
    from http.server import BaseHTTPRequestHandler
    import socketserver

    code = []

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request_url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(request_url.query)
            code.append(q['code'][0])

            self.send_response(HTTPStatus.OK)
            self.end_headers()
            self.wfile.write(b"OK!")

    PORT = 8000
    httpd = socketserver.TCPServer(("", PORT), RequestHandler)
    httpd.handle_request()
    httpd.server_close()

    code = code[0]

    # Request a refresh token given the authorization code.
    refresh_token = Spotify.get_user_refresh_token(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        authorization_code=code,
    )

    print(
        "Refresh token, store this somewhere safe and use for "
        "the export feature:"
    )
    print(refresh_token)


def main():
    parser = argparse.ArgumentParser("Snapshot Spotify playlists")

    subparsers = parser.add_subparsers(dest="action")

    update_parser = subparsers.add_parser(
        "update",
        help=(
            "Refresh playlist information and optionally push "
            "and export the new info."
        )
    )
    update_parser.add_argument(
        "--push",
        action="store_true",
        help="Commit and push updated playlists"
    )
    update_parser.add_argument(
        "--export",
        action="store_true",
        help="Publish archive playlists to Spotify, requires user login."
    )

    login_parser = subparsers.add_parser(
        "login",
        help=(
            "Obtain a user token through the OAuth flow (necessary in order"
            " to use the export feature)."
        )
    )


    args = parser.parse_args()
    now = datetime.datetime.now()

    if args.action == "update":
        update_files(now, export=args.export)
    elif args.action == "login":
        login(now)

    print("Done")


if __name__ == "__main__":
    main()
