#!/usr/bin/env python3

import datetime
import textwrap
from unittest import TestCase

from playlist_types import (
    Album,
    Artist,
    CumulativePlaylist,
    CumulativeTrack,
    Owner,
    Playlist,
    Track,
)


class TestTrackGetID(TestCase):
    def test_success(self) -> None:
        track = Track(
            url="https://open.spotify.com/track/abc123",
            name="",
            album=Album(
                url="",
                name="",
            ),
            artists=[],
            duration_ms=0,
            added_at=None,
        )
        self.assertEqual(track.get_id(), "abc123")


class TestPlaylistToAndFromJSON(TestCase):
    def test_success(self) -> None:
        playlist = Playlist(
            url="playlist_url",
            original_name="playlist_original_name",
            unique_name="playlist_unique_name",
            description="description",
            tracks=[
                Track(
                    url="track_url",
                    name="track_name",
                    album=Album(
                        url="album_url",
                        name="album_name",
                    ),
                    artists=[
                        Artist(
                            url="artist_url",
                            name="artist_name",
                        )
                    ],
                    duration_ms=1234,
                    added_at=datetime.datetime(2021, 12, 25, 23, 59, 59),
                ),
                Track(
                    url="",
                    name="",
                    album=Album(
                        url="",
                        name="",
                    ),
                    artists=[
                        Artist(
                            url="",
                            name="",
                        )
                    ],
                    duration_ms=0,
                    added_at=None,
                ),
            ],
            snapshot_id="snapshot_id",
            num_followers=999,
            owner=Owner(
                url="owner_url",
                name="owner_name",
            ),
        )
        playlist_json = playlist.to_json()
        self.assertEqual(
            playlist_json,
            textwrap.dedent(
                """\
                {
                  "description": "description",
                  "num_followers": 999,
                  "original_name": "playlist_original_name",
                  "owner": {
                    "name": "owner_name",
                    "url": "owner_url"
                  },
                  "snapshot_id": "snapshot_id",
                  "tracks": [
                    {
                      "added_at": "2021-12-25 23:59:59",
                      "album": {
                        "name": "album_name",
                        "url": "album_url"
                      },
                      "artists": [
                        {
                          "name": "artist_name",
                          "url": "artist_url"
                        }
                      ],
                      "duration_ms": 1234,
                      "name": "track_name",
                      "url": "track_url"
                    },
                    {
                      "added_at": null,
                      "album": {
                        "name": "",
                        "url": ""
                      },
                      "artists": [
                        {
                          "name": "",
                          "url": ""
                        }
                      ],
                      "duration_ms": 0,
                      "name": "",
                      "url": ""
                    }
                  ],
                  "unique_name": "playlist_unique_name",
                  "url": "playlist_url"
                }"""
            ),
        )
        self.assertEqual(playlist, Playlist.from_json(playlist_json))


class TestCumulativeTrackGetID(TestCase):
    def test_success(self) -> None:
        track = CumulativeTrack(
            url="https://open.spotify.com/track/abc123",
            name="",
            album=Album(
                url="",
                name="",
            ),
            artists=[],
            duration_ms=0,
            date_added=datetime.date(1970, 1, 1),
            date_added_asterisk=False,
            date_removed=None,
        )
        self.assertEqual(track.get_id(), "abc123")


class TestCumulativePlaylistUpdate(TestCase):
    def test_just_old_data(self) -> None:
        date_first_scraped = datetime.date(2000, 1, 1)
        date_added = datetime.date(2000, 1, 2)
        other = datetime.date(2000, 1, 3)
        today = datetime.date(2000, 1, 4)
        for date_added_asterisk in [False, True]:
            for date_removed, updated_date_removed in [
                (other, other),
                (None, today),
            ]:
                self.assertEqual(
                    CumulativePlaylist(
                        url="old_playlist_url",
                        name="old_playlist_name",
                        description="old_description",
                        tracks=[
                            CumulativeTrack(
                                url="https://open.spotify.com/track/abc123",
                                name="old_track_name",
                                album=Album(
                                    url="old_album_url",
                                    name="old_album_name",
                                ),
                                artists=[
                                    Artist(
                                        url="old_artist_url",
                                        name="old_artist_name",
                                    )
                                ],
                                duration_ms=1234,
                                date_added=date_added,
                                date_added_asterisk=date_added_asterisk,
                                date_removed=date_removed,
                            ),
                        ],
                        date_first_scraped=date_first_scraped,
                    ).update(
                        today=today,
                        playlist=Playlist(
                            url="new_playlist_url",
                            original_name="new_playlist_name",
                            unique_name="new_playlist_name",
                            description="new_description",
                            tracks=[],
                            snapshot_id="new_snapshot_id",
                            num_followers=999,
                            owner=Owner(
                                url="new_owner_url",
                                name="new_owner_name",
                            ),
                        ),
                    ),
                    CumulativePlaylist(
                        url="new_playlist_url",
                        name="new_playlist_name",
                        description="new_description",
                        tracks=[
                            CumulativeTrack(
                                url="https://open.spotify.com/track/abc123",
                                name="old_track_name",
                                album=Album(
                                    url="old_album_url",
                                    name="old_album_name",
                                ),
                                artists=[
                                    Artist(
                                        url="old_artist_url",
                                        name="old_artist_name",
                                    )
                                ],
                                duration_ms=1234,
                                date_added=date_added,
                                date_added_asterisk=date_added_asterisk,
                                date_removed=updated_date_removed,
                            ),
                        ],
                        date_first_scraped=date_first_scraped,
                    ),
                )

    def test_just_new_data(self) -> None:
        date_first_scraped = datetime.date(2000, 1, 1)
        time_added = datetime.datetime(2000, 1, 2)
        date_added = time_added.date()
        today = datetime.date(2000, 1, 3)
        for added_at, updated_date_added in [
            (time_added, date_added),
            (None, today),
        ]:
            self.assertEqual(
                CumulativePlaylist(
                    url="old_playlist_url",
                    name="old_playlist_name",
                    description="old_description",
                    tracks=[],
                    date_first_scraped=date_first_scraped,
                ).update(
                    today=today,
                    playlist=Playlist(
                        url="new_playlist_url",
                        original_name="new_playlist_name",
                        unique_name="new_playlist_name",
                        description="new_description",
                        tracks=[
                            Track(
                                url="https://open.spotify.com/track/abc123",
                                name="new_track_name",
                                album=Album(
                                    url="new_album_url",
                                    name="new_album_name",
                                ),
                                artists=[
                                    Artist(
                                        url="new_artist_url",
                                        name="new_artist_name",
                                    )
                                ],
                                duration_ms=1234,
                                added_at=added_at,
                            ),
                        ],
                        snapshot_id="new_snapshot_id",
                        num_followers=999,
                        owner=Owner(
                            url="new_owner_url",
                            name="new_owner_name",
                        ),
                    ),
                ),
                CumulativePlaylist(
                    url="new_playlist_url",
                    name="new_playlist_name",
                    description="new_description",
                    tracks=[
                        CumulativeTrack(
                            url="https://open.spotify.com/track/abc123",
                            name="new_track_name",
                            album=Album(
                                url="new_album_url",
                                name="new_album_name",
                            ),
                            artists=[
                                Artist(
                                    url="new_artist_url",
                                    name="new_artist_name",
                                )
                            ],
                            duration_ms=1234,
                            date_added=updated_date_added,
                            date_added_asterisk=False,
                            date_removed=None,
                        ),
                    ],
                    date_first_scraped=date_first_scraped,
                ),
            )

    def test_both_old_and_new_data(self) -> None:
        date_first_scraped = datetime.date(2000, 1, 1)
        date_removed = datetime.date(2000, 1, 4)
        today = datetime.date(2000, 1, 5)
        for (
            old_date_added,
            new_date_added,
            updated_date_added,
            updated_date_added_asterisk,
        ) in [
            (
                # old_date_added < new_date_added
                datetime.date(2000, 1, 2),
                datetime.date(2000, 1, 3),
                # old_date_added and asterisk are preserved
                datetime.date(2000, 1, 2),
                True,
            ),
            (
                # old_date_added == new_date_added
                datetime.date(2000, 1, 2),
                datetime.date(2000, 1, 2),
                # old_date_added and asterisk are preserved
                datetime.date(2000, 1, 2),
                True,
            ),
            (
                # old_date_added > new_date_added
                datetime.date(2000, 1, 3),
                datetime.date(2000, 1, 2),
                # old_date_added and asterisk are replaced
                datetime.date(2000, 1, 2),
                False,
            ),
        ]:
            self.assertEqual(
                CumulativePlaylist(
                    url="old_playlist_url",
                    name="old_playlist_name",
                    description="old_description",
                    tracks=[
                        CumulativeTrack(
                            url="https://open.spotify.com/track/abc123",
                            name="old_track_name",
                            album=Album(
                                url="old_album_url",
                                name="old_album_name",
                            ),
                            artists=[
                                Artist(
                                    url="old_artist_url",
                                    name="old_artist_name",
                                )
                            ],
                            duration_ms=1234,
                            date_added=old_date_added,
                            date_added_asterisk=True,
                            date_removed=date_removed,
                        ),
                    ],
                    date_first_scraped=date_first_scraped,
                ).update(
                    today=today,
                    playlist=Playlist(
                        url="new_playlist_url",
                        original_name="new_playlist_name",
                        unique_name="new_playlist_name",
                        description="new_description",
                        tracks=[
                            Track(
                                url="https://open.spotify.com/track/abc123",
                                name="new_track_name",
                                album=Album(
                                    url="new_album_url",
                                    name="new_album_name",
                                ),
                                artists=[
                                    Artist(
                                        url="new_artist_url",
                                        name="new_artist_name",
                                    )
                                ],
                                duration_ms=5678,
                                added_at=datetime.datetime(
                                    new_date_added.year,
                                    new_date_added.month,
                                    new_date_added.day,
                                ),
                            ),
                        ],
                        snapshot_id="new_snapshot_id",
                        num_followers=999,
                        owner=Owner(
                            url="new_owner_url",
                            name="new_owner_name",
                        ),
                    ),
                ),
                CumulativePlaylist(
                    url="new_playlist_url",
                    name="new_playlist_name",
                    description="new_description",
                    tracks=[
                        CumulativeTrack(
                            url="https://open.spotify.com/track/abc123",
                            name="new_track_name",
                            album=Album(
                                url="new_album_url",
                                name="new_album_name",
                            ),
                            artists=[
                                Artist(
                                    url="new_artist_url",
                                    name="new_artist_name",
                                )
                            ],
                            duration_ms=5678,
                            date_added=updated_date_added,
                            date_added_asterisk=updated_date_added_asterisk,
                            date_removed=None,
                        ),
                    ],
                    date_first_scraped=date_first_scraped,
                ),
            )


class TestCumulativePlaylistToAndFromJSON(TestCase):
    def test_success(self) -> None:
        cumulative_playlist = CumulativePlaylist(
            url="playlist_url",
            name="playlist_name",
            description="description",
            tracks=[
                CumulativeTrack(
                    url="track_url",
                    name="track_name",
                    album=Album(
                        url="album_url",
                        name="album_name",
                    ),
                    artists=[
                        Artist(
                            url="artist_url",
                            name="artist_name",
                        )
                    ],
                    duration_ms=100001,
                    date_added=datetime.date(2021, 12, 27),
                    date_added_asterisk=False,
                    date_removed=datetime.date(2021, 12, 29),
                ),
                CumulativeTrack(
                    url="",
                    name="",
                    album=Album(
                        url="",
                        name="",
                    ),
                    artists=[
                        Artist(
                            url="",
                            name="",
                        )
                    ],
                    duration_ms=0,
                    date_added=datetime.date(2021, 12, 25),
                    date_added_asterisk=True,
                    date_removed=None,
                ),
            ],
            date_first_scraped=datetime.date(2021, 12, 25),
        )
        cumulative_playlist_json = cumulative_playlist.to_json()
        self.assertEqual(
            cumulative_playlist_json,
            textwrap.dedent(
                """\
                {
                  "date_first_scraped": "2021-12-25",
                  "description": "description",
                  "name": "playlist_name",
                  "tracks": [
                    {
                      "album": {
                        "name": "album_name",
                        "url": "album_url"
                      },
                      "artists": [
                        {
                          "name": "artist_name",
                          "url": "artist_url"
                        }
                      ],
                      "date_added": "2021-12-27",
                      "date_added_asterisk": false,
                      "date_removed": "2021-12-29",
                      "duration_ms": 100001,
                      "name": "track_name",
                      "url": "track_url"
                    },
                    {
                      "album": {
                        "name": "",
                        "url": ""
                      },
                      "artists": [
                        {
                          "name": "",
                          "url": ""
                        }
                      ],
                      "date_added": "2021-12-25",
                      "date_added_asterisk": true,
                      "date_removed": null,
                      "duration_ms": 0,
                      "name": "",
                      "url": ""
                    }
                  ],
                  "url": "playlist_url"
                }"""
            ),
        )
        self.assertEqual(
            cumulative_playlist, CumulativePlaylist.from_json(cumulative_playlist_json)
        )
