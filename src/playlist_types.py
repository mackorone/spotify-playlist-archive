#!/usr/bin/env python3

from __future__ import annotations

import dataclasses
import datetime
import json
from typing import List, Optional, Sequence

from playlist_id import PlaylistID


@dataclasses.dataclass(frozen=True)
class Owner:
    url: str
    name: str


@dataclasses.dataclass(frozen=True)
class Album:
    url: str
    name: str


@dataclasses.dataclass(frozen=True)
class Artist:
    url: str
    name: str


@dataclasses.dataclass(frozen=True)
class Track:
    url: str
    name: str
    album: Album
    artists: Sequence[Artist]
    duration_ms: int
    added_at: Optional[datetime.datetime]

    def get_id(self) -> str:
        track_id = self.url.split("/")[-1]
        assert track_id.isalnum(), repr(track_id)
        return track_id


@dataclasses.dataclass(frozen=True)
class Playlist:
    url: str
    # The registered alias, else the name from Spotify, unmodified
    original_name: str
    # A unique name for the playlist, derived from the original name. In most
    # cases, they should be the exact same. When multiple playlists share the
    # same original name, duplicates have a unique suffix, e.g., " (2)".
    unique_name: str
    description: str
    tracks: Sequence[Track]
    # The unqiue identifier for a particular playlist version. Note that for
    # certain personalized playlists, snapshot ID changes with every request
    # because the timestamp of the request is encoded within the ID.
    # (https://artists.spotify.com/blog/our-playlist-ecosystem-is-evolving)
    snapshot_id: str
    num_followers: Optional[int]
    owner: Owner

    @classmethod
    def from_json(cls, content: str) -> Playlist:
        playlist = json.loads(content)
        assert isinstance(playlist, dict)

        playlist_url = playlist["url"]
        assert isinstance(playlist_url, str)

        original_playlist_name = playlist["original_name"]
        assert isinstance(original_playlist_name, str)
        unique_playlist_name = playlist["unique_name"]
        assert isinstance(unique_playlist_name, str)

        description = playlist["description"]
        assert isinstance(description, str)

        snapshot_id = playlist["snapshot_id"]
        assert isinstance(snapshot_id, str)

        num_followers = playlist["num_followers"]
        assert isinstance(num_followers, (int, type(None)))

        assert isinstance(playlist["owner"], dict)
        owner_url = playlist["owner"]["url"]
        assert isinstance(owner_url, str)
        owner_name = playlist["owner"]["name"]
        assert isinstance(owner_name, str)

        tracks: List[Track] = []
        assert isinstance(playlist["tracks"], list)
        for track in playlist["tracks"]:
            assert isinstance(track, dict)

            track_url = track["url"]
            assert isinstance(track_url, str)

            track_name = track["name"]
            assert isinstance(track_name, str)

            assert isinstance(track["album"], dict)
            album_url = track["album"]["url"]
            assert isinstance(album_url, str)
            album_name = track["album"]["name"]
            assert isinstance(album_name, str)

            artists = []
            assert isinstance(track["artists"], list)
            for artist in track["artists"]:
                assert isinstance(artist, dict)
                artist_url = artist["url"]
                assert isinstance(artist_url, str)
                artist_name = artist["name"]
                assert isinstance(artist_name, str)
                artists.append(Artist(url=artist_url, name=artist_name))

            duration_ms = track["duration_ms"]
            assert isinstance(duration_ms, int)

            added_at_string = track["added_at"]
            if added_at_string is None:
                added_at = None
            else:
                assert isinstance(added_at_string, str)
                added_at = datetime.datetime.strptime(
                    added_at_string, "%Y-%m-%d %H:%M:%S"
                )
            assert isinstance(added_at, (datetime.datetime, type(None)))

            tracks.append(
                Track(
                    url=track_url,
                    name=track_name,
                    album=Album(
                        url=album_url,
                        name=album_name,
                    ),
                    artists=artists,
                    duration_ms=duration_ms,
                    added_at=added_at,
                )
            )

        return Playlist(
            url=playlist_url,
            original_name=original_playlist_name,
            unique_name=unique_playlist_name,
            description=description,
            tracks=tracks,
            snapshot_id=snapshot_id,
            num_followers=num_followers,
            owner=Owner(
                url=owner_url,
                name=owner_name,
            ),
        )

    def to_json(self) -> str:
        return json.dumps(
            dataclasses.asdict(self),
            indent=2,
            sort_keys=True,
            default=self.serialize_datetime,
        )

    @classmethod
    def serialize_datetime(cls, obj: object) -> str:
        assert isinstance(obj, datetime.datetime)
        return str(obj)


@dataclasses.dataclass(frozen=True)
class CumulativeTrack:
    url: str
    name: str
    album: Album
    artists: Sequence[Artist]
    duration_ms: int
    # Represents the first date that the track appeared in the playlist, to our
    # best knowledge - we can't know if a track was added and then removed
    # prior to the playlist being scraped
    date_added: datetime.date
    # Indicates that the track belonged to the first version of the playlist
    # that was indexed, but it's too late to go back and check when the track
    # was originally added to the playlist
    date_added_asterisk: bool
    # Represents the most recent date that the track was removed from the
    # playlist, is empty/null if the track is still present
    date_removed: Optional[datetime.date]

    def get_id(self) -> str:
        track_id = self.url.split("/")[-1]
        assert track_id.isalnum(), repr(track_id)
        return track_id


@dataclasses.dataclass(frozen=True)
class CumulativePlaylist:
    url: str
    name: str
    description: str
    tracks: Sequence[CumulativeTrack]
    date_first_scraped: datetime.date
    published_playlist_ids: List[PlaylistID]

    def update(
        self,
        today: datetime.date,
        playlist: Playlist,
        published_playlist_ids: List[PlaylistID],
    ) -> CumulativePlaylist:
        updated_tracks: List[CumulativeTrack] = []
        current_tracks = {track.get_id(): track for track in playlist.tracks}
        previous_tracks = {track.get_id(): track for track in self.tracks}
        for track_id in set(current_tracks) | set(previous_tracks):
            old_data = previous_tracks.get(track_id)
            new_data = current_tracks.get(track_id)
            assert old_data or new_data

            if old_data:
                url = old_data.url
                name = old_data.name
                album = old_data.album
                artists = old_data.artists
                duration_ms = old_data.duration_ms
                date_added = old_data.date_added
                date_added_asterisk = old_data.date_added_asterisk
                date_removed = old_data.date_removed or today

            if new_data:
                url = new_data.url
                name = new_data.name
                album = new_data.album
                artists = new_data.artists
                duration_ms = new_data.duration_ms
                date_added = new_data.added_at.date() if new_data.added_at else today
                date_added_asterisk = False
                date_removed = None
                # If the old date_added is earlier than what Spotify returned, use it
                if old_data and old_data.date_added <= date_added:
                    date_added = old_data.date_added
                    date_added_asterisk = old_data.date_added_asterisk

            updated_tracks.append(
                CumulativeTrack(
                    # pyre-fixme[61]
                    url=url,
                    # pyre-fixme[61]
                    name=name,
                    # pyre-fixme[61]
                    album=album,
                    # pyre-fixme[61]
                    artists=artists,
                    # pyre-fixme[61]
                    duration_ms=duration_ms,
                    # pyre-fixme[61]
                    date_added=date_added,
                    # pyre-fixme[61]
                    date_added_asterisk=date_added_asterisk,
                    # pyre-fixme[61]
                    date_removed=date_removed,
                )
            )

        return CumulativePlaylist(
            url=playlist.url,
            name=playlist.unique_name,
            description=playlist.description,
            tracks=sorted(
                updated_tracks,
                key=lambda track: (
                    track.name.lower(),
                    tuple(artist.name.lower() for artist in track.artists),
                    track.duration_ms,
                    track.get_id(),
                ),
            ),
            date_first_scraped=self.date_first_scraped,
            published_playlist_ids=published_playlist_ids,
        )

    @classmethod
    def from_json(cls, content: str) -> CumulativePlaylist:
        playlist = json.loads(content)
        assert isinstance(playlist, dict)

        playlist_url = playlist["url"]
        assert isinstance(playlist_url, str)

        playlist_name = playlist["name"]
        assert isinstance(playlist_name, str)

        description = playlist["description"]
        assert isinstance(description, str)

        date_first_scraped_string = playlist["date_first_scraped"]
        assert isinstance(date_first_scraped_string, str)
        date_first_scraped = datetime.datetime.strptime(
            date_first_scraped_string, "%Y-%m-%d"
        ).date()
        assert isinstance(date_first_scraped, datetime.date)

        published_playlist_ids = playlist["published_playlist_ids"]
        assert isinstance(published_playlist_ids, list)
        for playlist_id in published_playlist_ids:
            assert isinstance(playlist_id, str)

        cumulative_tracks: List[CumulativeTrack] = []
        assert isinstance(playlist["tracks"], list)
        for track in playlist["tracks"]:
            assert isinstance(track, dict)

            track_url = track["url"]
            assert isinstance(track_url, str)

            track_name = track["name"]
            assert isinstance(track_name, str)

            assert isinstance(track["album"], dict)
            album_url = track["album"]["url"]
            assert isinstance(album_url, str)
            album_name = track["album"]["name"]
            assert isinstance(album_name, str)

            artists = []
            assert isinstance(track["artists"], list)
            for artist in track["artists"]:
                assert isinstance(artist, dict)
                artist_url = artist["url"]
                assert isinstance(artist_url, str)
                artist_name = artist["name"]
                assert isinstance(artist_name, str)
                artists.append(Artist(url=artist_url, name=artist_name))

            duration_ms = track["duration_ms"]
            assert isinstance(duration_ms, int)

            date_added_string = track["date_added"]
            assert isinstance(date_added_string, str)
            date_added = datetime.datetime.strptime(
                date_added_string, "%Y-%m-%d"
            ).date()
            assert isinstance(date_added, datetime.date)

            date_added_asterisk = track["date_added_asterisk"]
            assert isinstance(date_added_asterisk, bool)

            date_removed = None
            date_removed_string = track["date_removed"]
            if date_removed_string is not None:
                assert isinstance(date_removed_string, str)
                date_removed = datetime.datetime.strptime(
                    date_removed_string, "%Y-%m-%d"
                ).date()
                assert isinstance(date_removed, datetime.date)

            cumulative_tracks.append(
                CumulativeTrack(
                    url=track_url,
                    name=track_name,
                    album=Album(
                        url=album_url,
                        name=album_name,
                    ),
                    artists=artists,
                    duration_ms=duration_ms,
                    date_added=date_added,
                    date_added_asterisk=date_added_asterisk,
                    date_removed=date_removed,
                )
            )

        return CumulativePlaylist(
            url=playlist_url,
            name=playlist_name,
            description=description,
            tracks=cumulative_tracks,
            date_first_scraped=date_first_scraped,
            published_playlist_ids=published_playlist_ids,
        )

    def to_json(self) -> str:
        return json.dumps(
            dataclasses.asdict(self),
            indent=2,
            sort_keys=True,
            default=self.serialize_date,
        )

    @classmethod
    def serialize_date(cls, obj: object) -> str:
        assert isinstance(obj, datetime.date)
        return str(obj)
