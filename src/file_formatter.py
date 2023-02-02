#!/usr/bin/env python3

import dataclasses
import datetime
import json
from typing import List, Mapping, Tuple

from plants.markdown import MarkdownEscapedString
from playlist_id import PlaylistID
from playlist_types import CumulativePlaylist, Playlist, Track
from url import URL


class Formatter:

    TRACK_NO = "No."
    TITLE = "Title"
    ARTISTS = "Artist(s)"
    ALBUM = "Album"
    LENGTH = "Length"
    ADDED = "Added"
    REMOVED = "Removed"

    ARTIST_SEPARATOR = ", "

    @classmethod
    def readme(cls, prev_content: str, playlists: Mapping[PlaylistID, Playlist]) -> str:
        old_lines = prev_content.splitlines()
        prefix = "## Playlists"
        index = next(i for i, line in enumerate(old_lines) if line.startswith(prefix))
        header = prefix + MarkdownEscapedString(f" ({len(playlists)})")

        playlist_tuples: List[Tuple[str, str]] = []
        for playlist_id, playlist in playlists.items():
            name_stripped = playlist.unique_name.strip()
            text = MarkdownEscapedString(name_stripped)
            link = cls._link(text, URL.pretty(playlist_id))
            playlist_tuples.append((name_stripped, f"- {link}"))
        playlist_lines = [text for key, text in sorted(playlist_tuples)]

        new_lines = old_lines[:index] + [header, ""] + playlist_lines
        return "\n".join(new_lines) + "\n"

    @classmethod
    def metadata_json(cls, playlists: Mapping[PlaylistID, Playlist]) -> str:
        metadata_dict = {}
        for playlist_id, playlist in playlists.items():
            playlist_dict = dataclasses.asdict(playlist)
            del playlist_dict["tracks"]
            metadata_dict[playlist_id] = playlist_dict
        return json.dumps(
            metadata_dict,
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def plain(cls, playlist_id: PlaylistID, playlist: Playlist) -> str:
        lines = [cls._plain_line_from_track(track) for track in playlist.tracks]
        # Sort alphabetically to minimize changes when tracks are reordered
        sorted_lines = sorted(lines, key=lambda line: line.lower())
        header = [playlist.unique_name, playlist.description, ""]
        return "\n".join(header + sorted_lines) + "\n"

    @classmethod
    def pretty(cls, playlist_id: PlaylistID, playlist: Playlist) -> str:
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
            playlist_name=playlist.unique_name,
            playlist_url=playlist.url,
            playlist_id=playlist_id,
            playlist_description=playlist.description,
            is_cumulative=False,
        )
        num_likes = playlist.num_followers
        if num_likes is None:
            num_likes_string = "??? likes"
        else:
            num_likes_string = f"{num_likes:,} like" + ("s" if num_likes > 1 else "")
        num_songs = len(playlist.tracks)
        lines += [
            "{} - {} - {} - {}".format(
                cls._link(
                    MarkdownEscapedString(playlist.owner.name), playlist.owner.url
                ),
                num_likes_string,
                f"{num_songs:,} song" + ("s" if num_songs > 1 else ""),
                cls._format_duration_english(
                    sum(track.duration_ms for track in playlist.tracks)
                ),
            ),
            "",
            line_template.format(*columns),
            divider_line,
        ]

        for i, track in enumerate(playlist.tracks):
            lines.append(
                line_template.format(
                    i + 1,
                    cls._link(MarkdownEscapedString(track.name), track.url),
                    cls.ARTIST_SEPARATOR.join(
                        [
                            cls._link(MarkdownEscapedString(artist.name), artist.url)
                            for artist in track.artists
                        ]
                    ),
                    cls._link(MarkdownEscapedString(track.album.name), track.album.url),
                    cls._format_duration(track.duration_ms),
                )
            )

        lines.append("")
        lines.append(f"Snapshot ID: `{playlist.snapshot_id}`")

        return "\n".join(lines) + "\n"

    @classmethod
    def cumulative(
        cls,
        playlist_id: PlaylistID,
        playlist: CumulativePlaylist,
    ) -> str:
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
        lines = cls._markdown_header_lines(
            playlist_name=playlist.name,
            playlist_url=playlist.url,
            playlist_id=playlist_id,
            playlist_description=playlist.description,
            is_cumulative=True,
        )

        num_songs = len(playlist.tracks)
        info_line = "{} - {}".format(
            f"{num_songs:,} song" + ("s" if num_songs > 1 else ""),
            cls._format_duration_english(
                sum(track.duration_ms for track in playlist.tracks)
            ),
        )

        lines += [
            info_line,
            "",
            line_template.format(*columns),
            divider_line,
        ]

        for i, track in enumerate(playlist.tracks):
            date_added = str(track.date_added)
            if track.date_added_asterisk:
                date_added += "\\*"
            lines.append(
                line_template.format(
                    # Title
                    cls._link(MarkdownEscapedString(track.name), track.url),
                    # Artists
                    cls.ARTIST_SEPARATOR.join(
                        [
                            cls._link(MarkdownEscapedString(artist.name), artist.url)
                            for artist in track.artists
                        ]
                    ),
                    # Album
                    cls._link(MarkdownEscapedString(track.album.name), track.album.url),
                    # Length
                    cls._format_duration(track.duration_ms),
                    # Added
                    date_added,
                    # Removed
                    track.date_removed or "",
                )
            )

        lines.append("")
        lines.append(
            f"\\*This playlist was first scraped on {playlist.date_first_scraped}. "
            "Prior content cannot be recovered."
        )

        return "\n".join(lines) + "\n"

    @classmethod
    def _markdown_header_lines(
        cls,
        playlist_name: str,
        playlist_url: str,
        playlist_id: PlaylistID,
        playlist_description: str,
        is_cumulative: bool,
    ) -> List[str]:
        if is_cumulative:
            pretty = cls._link(MarkdownEscapedString("pretty"), URL.pretty(playlist_id))
            cumulative = "cumulative"
        else:
            pretty = "pretty"
            cumulative = cls._link(
                MarkdownEscapedString("cumulative"), URL.cumulative(playlist_id)
            )

        return [
            "{} - {} - {} - {}".format(
                pretty,
                cumulative,
                cls._link(MarkdownEscapedString("plain"), URL.plain(playlist_id)),
                cls._link(
                    MarkdownEscapedString("githistory"), URL.plain_history(playlist_id)
                ),
            ),
            "",
            "### {}".format(
                cls._link(MarkdownEscapedString(playlist_name), playlist_url)
            ),
            "",
            # Some descriptions end with newlines, strip to clean them up
            "> {}".format(MarkdownEscapedString(playlist_description.strip())),
            "",
        ]

    @classmethod
    def _plain_line_from_track(cls, track: Track) -> str:
        return "{} -- {} -- {}".format(
            track.name,
            cls.ARTIST_SEPARATOR.join([artist.name for artist in track.artists]),
            track.album.name,
        )

    @classmethod
    def _link(cls, text: MarkdownEscapedString, url: str) -> str:
        if not url:
            return text
        return f"[{text}]({url})"

    @classmethod
    def _format_duration(cls, duration_ms: int) -> str:
        seconds = int(duration_ms // 1000)
        timedelta = str(datetime.timedelta(seconds=seconds))

        index = 0
        # Strip leading zeros but always include the minutes digit
        while index < len(timedelta) - 4 and timedelta[index] in "0:":
            index += 1

        return timedelta[index:]

    @classmethod
    def _format_duration_english(cls, duration_ms: int) -> str:
        second_ms = 1000
        minute_ms = 60 * second_ms
        hour_ms = 60 * minute_ms
        day_ms = 24 * hour_ms

        days = duration_ms // day_ms
        duration_ms -= days * day_ms
        hours = duration_ms // hour_ms
        duration_ms -= hours * hour_ms
        minutes = duration_ms // minute_ms
        duration_ms -= minutes * minute_ms
        seconds = duration_ms // second_ms

        if not (days or hours or minutes):
            return f"{seconds} sec"
        if not (days or hours):
            return f"{minutes} min {seconds} sec"
        if not days:
            return f"{hours} hr {minutes} min"
        return f"{days:,} day {hours} hr {minutes} min"
