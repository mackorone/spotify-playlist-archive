#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import copy
import datetime
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call, patch

import aiohttp

from alias import Alias
from plants.unittest_utils import UnittestUtils
from playlist_id import PlaylistID
from playlist_types import Album, Artist, Owner, Playlist, Track
from spotify import (
    FailedRequestError,
    InvalidDataError,
    RetryBudgetExceededError,
    Spotify,
)


class MockSession(AsyncMock):
    @classmethod
    async def create(cls) -> MockSession:
        mock_session = MockSession()
        await mock_session._init()
        return mock_session

    async def _init(self) -> None:
        # AsyncMock objects beget other AsyncMock objects, but these methods
        # are synchronous so we need initialize them explicitly
        self.get = Mock(return_value=AsyncMock())
        self.post = Mock(return_value=AsyncMock())
        # Allow MockSession objects to be used as async context managers
        async with self as session:
            session.get = self.get
            session.post = self.post


class SpotifyTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.mock_session = await MockSession.create()
        self.mock_get_session = UnittestUtils.patch(
            self,
            "spotify.Spotify._get_session",
            # new_callable returns the replacement for get_session
            new_callable=lambda: Mock(return_value=self.mock_session),
        )
        self.mock_sleep = UnittestUtils.patch(
            self,
            "spotify.Spotify._sleep",
            new_callable=AsyncMock,
        )


class TestGetWithRetry(SpotifyTestCase):
    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_exception(self, mock_logger: Mock) -> None:
        for type_ in [
            aiohttp.client_exceptions.ClientOSError,
            asyncio.exceptions.TimeoutError,
        ]:
            self.mock_session.get.side_effect = type_
            spotify = Spotify("token")
            with self.assertRaises(RetryBudgetExceededError):
                await spotify.get_playlist(PlaylistID("abc123"), alias=None)

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_invalid_response(self, mock_logger: Mock) -> None:
        for data in ["", {}]:
            async with self.mock_session.get.return_value as mock_response:
                mock_response.json.return_value = data
            spotify = Spotify("token")
            with self.assertRaises(RetryBudgetExceededError):
                await spotify.get_playlist(PlaylistID("abc123"), alias=None)

    async def test_failed_request(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {"error": ""}
        spotify = Spotify("token")
        with self.assertRaises(FailedRequestError):
            await spotify.get_playlist(PlaylistID("abc123"), alias=None)

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_server_unavailable(self, mock_logger: Mock) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.status = 500
        spotify = Spotify("token")
        with self.assertRaises(RetryBudgetExceededError):
            await spotify._get_with_retry("href")

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_transient_server_error(self, mock_logger: Mock) -> None:
        mock_responses = [AsyncMock(), AsyncMock()]
        async with mock_responses[0] as mock_response:
            mock_response.status = 500
        async with mock_responses[1] as mock_response:
            mock_response.json.return_value = {"items": [], "next": ""}
        self.mock_session.get.side_effect = mock_responses
        spotify = Spotify("token")
        await spotify._get_with_retry("href")
        self.assertEqual(self.mock_session.get.call_count, 2)
        self.mock_sleep.assert_called_once_with(1)

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_rate_limited(self, mock_logger: Mock) -> None:
        mock_responses = [AsyncMock(), AsyncMock()]
        async with mock_responses[0] as mock_response:
            mock_response.status = 429
            mock_response.headers = {"Retry-After": 4.2}
        async with mock_responses[1] as mock_response:
            mock_response.json.return_value = {"items": [], "next": ""}
        self.mock_session.get.side_effect = mock_responses
        spotify = Spotify("token")
        await spotify._get_with_retry("href")
        self.assertEqual(self.mock_session.get.call_count, 2)
        self.mock_sleep.assert_called_once_with(5)


class TestShutdown(SpotifyTestCase):
    async def test_success(self) -> None:
        spotify = Spotify("token")
        await spotify.shutdown()
        self.mock_session.close.assert_called_once()
        self.mock_sleep.assert_called_once_with(0)


class TestGetSpotifyUserPlaylistIDs(SpotifyTestCase):
    async def test_invalid_data(self) -> None:
        for data in [
            {"items": None},
            {"items": [None]},
            {"items": [{}]},
            {"items": [{"id": None}]},
        ]:
            async with self.mock_session.get.return_value as mock_response:
                mock_response.json.return_value = data
            spotify = Spotify("token")
            self.assertEqual(
                await spotify.get_spotify_user_playlist_ids(),
                set(),
            )

    async def test_success(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.side_effect = [
                {
                    "items": [{"id": "a"}, {"id": "b"}],
                    "next": "next_url",
                },
                {
                    "items": [{"id": "c"}, {"id": "d"}],
                    "next": "",
                },
            ]
        spotify = Spotify("token")
        playlist_ids = await spotify.get_spotify_user_playlist_ids()
        self.assertEqual(playlist_ids, {PlaylistID(x) for x in "abcd"})
        self.mock_session.get.assert_has_calls(
            [
                call("https://api.spotify.com/v1/users/spotify/playlists?limit=50"),
                call("next_url"),
            ]
        )


class TestGetFeaturedPlaylistIDs(SpotifyTestCase):
    async def test_invalid_data(self) -> None:
        for data in [
            {"playlists": None},
            {"playlists": {}},
            {"playlists": {"items": None}},
            {"playlists": {"items": [None]}},
            {"playlists": {"items": [{}]}},
            {"playlists": {"items": [{"id": None}]}},
        ]:
            async with self.mock_session.get.return_value as mock_response:
                mock_response.json.return_value = data
            spotify = Spotify("token")
            self.assertEqual(
                await spotify.get_featured_playlist_ids(),
                set(),
            )

    async def test_success(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.side_effect = [
                {
                    "playlists": {
                        "items": [{"id": "a"}, {"id": "b"}],
                        "next": "next_url",
                    },
                },
                {
                    "playlists": {
                        "items": [{"id": "c"}, {"id": "d"}],
                        "next": "",
                    },
                },
            ]
        spotify = Spotify("token")
        playlist_ids = await spotify.get_featured_playlist_ids()
        self.assertEqual(playlist_ids, {PlaylistID(x) for x in "abcd"})
        self.mock_session.get.assert_has_calls(
            [
                call("https://api.spotify.com/v1/browse/featured-playlists?limit=50"),
                call("next_url"),
            ]
        )


class TestGetCategoryPlaylistIDs(SpotifyTestCase):
    async def test_invalid_data(self) -> None:
        for side_effect in [
            # Invalid categories response
            [{"categories": None}],
            [{"categories": {}}],
            [{"categories": {"items": None}}],
            [{"categories": {"items": [None]}}],
            [{"categories": {"items": [{}]}}],
            [{"categories": {"items": [{"id": None}]}}],
            # Valid categories response, invalid playlists response
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": None},
            ],
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": {}},
            ],
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": {"items": None}},
            ],
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": {"items": [None]}},
            ],
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": {"items": [{}]}},
            ],
            [
                {"categories": {"items": [{"id": "a"}]}},
                {"playlists": {"items": [{"id": None}]}},
            ],
        ]:
            async with self.mock_session.get.return_value as mock_response:
                mock_response.json.side_effect = side_effect
            spotify = Spotify("token")
            self.assertEqual(
                await spotify.get_category_playlist_ids(),
                set(),
            )

    async def test_success(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.side_effect = UnittestUtils.side_effect(
                [
                    {
                        "categories": {
                            "items": [{"id": "category_1"}, {"id": "category_2"}],
                            "next": "next_category_url",
                        },
                    },
                    # Use category_3 to simulate FailedRequestError
                    {
                        "categories": {
                            "items": [{"id": "category_3"}],
                            "next": "",
                        },
                    },
                    # First playlists belonging to category_1
                    {
                        "playlists": {
                            "items": [{"id": "a"}, {"id": "b"}],
                            "next": "next_playlists_url",
                        },
                    },
                    # More playlists belonging to category_1
                    {
                        "playlists": {
                            "items": [{"id": "c"}],
                            "next": "",
                        },
                    },
                    # All playlists belonging to category_2
                    {
                        "playlists": {
                            "items": [{"id": "d"}],
                            "next": "",
                        },
                    },
                    # category_3 doesn't actually exist
                    FailedRequestError(),
                ]
            )
        spotify = Spotify("token")
        playlist_ids = await spotify.get_category_playlist_ids()
        self.assertEqual(playlist_ids, {PlaylistID(x) for x in "abcd"})
        self.mock_session.get.assert_has_calls(
            [
                call("https://api.spotify.com/v1/browse/categories?limit=50"),
                call("next_category_url"),
                call(
                    "https://api.spotify.com/v1/browse/categories/category_1/playlists?"
                    "limit=50"
                ),
                call("next_playlists_url"),
                call(
                    "https://api.spotify.com/v1/browse/categories/category_2/playlists?"
                    "limit=50"
                ),
                call(
                    "https://api.spotify.com/v1/browse/categories/category_3/playlists?"
                    "limit=50"
                ),
            ]
        )


class TestGetPlaylist(SpotifyTestCase):
    @patch("spotify.Spotify._get_tracks", new_callable=AsyncMock)
    # pyre-fixme[30]
    async def test_invalid_data(self, mock_get_tracks: Mock) -> None:
        mock_get_tracks.return_value = []
        valid_data = {
            "name": "playlist_name",
            "description": "playlist_description",
            "external_urls": {
                "spotify": "playlist_url",
            },
            "snapshot_id": "playlist_snapshot_id",
            "followers": {
                "total": 999,
            },
            "owner": {
                "display_name": "owner_name",
                "external_urls": {
                    "spotify": "owner_url",
                },
            },
        }
        overrides = {
            "name": ["", " ", "\n", None, 1],
            "description": [None, 1],
            "external_urls": [None, 1],
            "external_urls.spotify": [1],
            "snapshot_id": [None, 1],
            "followers": [None, 1],
            "followers.total": ["a"],
            "owner": [None, 1],
            "owner.display_name": [None, 1],
            "owner.external_urls": [None, 1],
            "owner.external_urls.spotify": [1],
        }
        for key, values in overrides.items():
            for value in values:
                data = copy.deepcopy(valid_data)
                ref = data
                parts = [(int(x) if x.isdigit() else x) for x in key.split(".")]
                for name in parts[:-1]:
                    ref = ref[name]
                ref[parts[-1]] = value
                async with self.mock_session.get.return_value as mock_response:
                    mock_response.json.return_value = data
                spotify = Spotify("token")
                with self.assertRaises(InvalidDataError):
                    await spotify.get_playlist(PlaylistID("abc123"), alias=None)

    @patch("spotify.Spotify._get_tracks", new_callable=AsyncMock)
    async def test_nonempty_alias(self, mock_get_tracks: AsyncMock) -> None:
        mock_get_tracks.return_value = []
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "name": "playlist_name",
                "description": "",
                "external_urls": {},
                "snapshot_id": "",
                "followers": {
                    "total": 0,
                },
                "owner": {
                    "display_name": "owner_name",
                    "external_urls": {},
                },
            }
            spotify = Spotify("token")
            playlist = await spotify.get_playlist(
                PlaylistID("abc123"), alias=Alias("alias")
            )
            self.assertEqual(playlist.original_name, "alias")
            self.assertEqual(playlist.unique_name, "alias")

    @patch("spotify.Spotify._get_tracks", new_callable=AsyncMock)
    async def test_success(self, mock_get_tracks: AsyncMock) -> None:
        track = Track(
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
            duration_ms=100,
            added_at=datetime.datetime(2021, 12, 25),
        )
        mock_get_tracks.return_value = [track]
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "name": "playlist_name",
                "description": "playlist_description",
                "external_urls": {
                    "spotify": "playlist_url",
                },
                "snapshot_id": "playlist_snapshot_id",
                "followers": {
                    "total": 999,
                },
                "owner": {
                    "display_name": "owner_name",
                    "external_urls": {
                        "spotify": "owner_url",
                    },
                },
            }
        spotify = Spotify("token")
        playlist = await spotify.get_playlist(PlaylistID("abc123"), alias=None)
        self.assertEqual(
            playlist,
            Playlist(
                url="playlist_url",
                original_name="playlist_name",
                unique_name="playlist_name",
                description="playlist_description",
                tracks=[track],
                snapshot_id="playlist_snapshot_id",
                num_followers=999,
                owner=Owner(
                    url="owner_url",
                    name="owner_name",
                ),
            ),
        )


class TestGetTracks(SpotifyTestCase):
    async def test_invalid_data(self) -> None:
        valid_data = {
            "items": [
                {
                    "track": {
                        "duration_ms": 456,
                        "name": "track_name",
                        "album": {
                            "name": "album_name",
                            "external_urls": {
                                "spotify": "album_url",
                            },
                        },
                        "artists": [
                            {
                                "name": "artist_name",
                                "external_urls": {
                                    "spotify": "artist_url",
                                },
                            },
                        ],
                        "external_urls": {
                            "spotify": "track_url",
                        },
                    },
                    "added_at": "2021-12-25T00:00:00Z",
                },
            ],
            "next": "",
        }
        overrides = {
            "items": [None, 1],
            "items.0": [None, 1],
            "items.0.track": [1],
            "items.0.track.external_urls": [None, 1],
            "items.0.track.external_urls.spotify": [1],
            "items.0.track.name": [None, 1],
            "items.0.track.album": [None, 1],
            "items.0.track.album.external_urls": [None, 1],
            "items.0.track.album.external_urls.spotify": [1],
            "items.0.track.album.name": [None, 1],
            "items.0.track.artists": [None, 1],
            "items.0.track.artists.0": [None, 1],
            "items.0.track.artists.0.external_urls": [None, 1],
            "items.0.track.artists.0.external_urls.spotify": [1],
            "items.0.track.artists.0.name": [None, 1],
            "items.0.track.duration_ms": [None, "a"],
            "items.0.added_at": [1],
        }
        for key, values in overrides.items():
            for value in values:
                data = copy.deepcopy(valid_data)
                ref = data
                parts = [(int(x) if x.isdigit() else x) for x in key.split(".")]
                for name in parts[:-1]:
                    ref = ref[name]  # pyre-fixme[6]
                ref[parts[-1]] = value  # pyre-fixme[16]
                async with self.mock_session.get.return_value as mock_response:
                    mock_response.json.return_value = data
                spotify = Spotify("token")
                with self.assertRaises(InvalidDataError):
                    await spotify._get_tracks(PlaylistID("abc123"))

    async def test_empty_playlist(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "items": [],
                "next": "",
            }
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("abc123"))
        self.assertEqual(tracks, [])

    async def test_empty_track(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "items": [{"track": {}}],
                "next": "",
            }
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("abc123"))
        self.assertEqual(tracks, [])

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_empty_track_url(self, logger: Mock) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "items": [{"track": {"external_urls": {"spotify": ""}}}],
                "next": "",
            }
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("abc123"))
        self.assertEqual(tracks, [])

    # Patch the logger to suppress log spew
    @patch("spotify.logger")
    async def test_missing_info(self, logger: Mock) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "items": [
                    {
                        "track": {
                            "duration_ms": 123,
                            "name": "",
                            "album": {
                                "name": "",
                                "external_urls": {},
                            },
                            "artists": [],
                            "external_urls": {"spotify": "track_url"},
                        },
                        "added_at": "1970-01-01T00:00:00Z",
                    },
                ],
                "next": "",
            }
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("abc123"))
        self.assertEqual(
            tracks,
            [
                Track(
                    url="track_url",
                    name="",
                    album=Album(
                        url="",
                        name="",
                    ),
                    artists=[],
                    duration_ms=123,
                    added_at=None,
                )
            ],
        )

    async def test_success(self) -> None:
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.return_value = {
                "items": [
                    {
                        "track": {
                            "duration_ms": 456,
                            "name": "track_name",
                            "album": {
                                "name": "album_name",
                                "external_urls": {
                                    "spotify": "album_url",
                                },
                            },
                            "artists": [
                                {
                                    "name": "artist_name_1",
                                    "external_urls": {
                                        "spotify": "artist_url_1",
                                    },
                                },
                                {
                                    "name": "artist_name_2",
                                    "external_urls": {
                                        "spotify": "artist_url_2",
                                    },
                                },
                            ],
                            "external_urls": {
                                "spotify": "track_url",
                            },
                        },
                        "added_at": "2021-12-25T00:00:00Z",
                    },
                ],
                "next": "",
            }
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("abc123"))
        self.assertEqual(
            tracks,
            [
                Track(
                    url="track_url",
                    name="track_name",
                    album=Album(
                        url="album_url",
                        name="album_name",
                    ),
                    artists=[
                        Artist(
                            name="artist_name_1",
                            url="artist_url_1",
                        ),
                        Artist(
                            name="artist_name_2",
                            url="artist_url_2",
                        ),
                    ],
                    duration_ms=456,
                    added_at=datetime.datetime(2021, 12, 25),
                )
            ],
        )

    @patch("spotify.Spotify._get_tracks_href")
    async def test_pagination(self, mock_get_tracks_href: Mock) -> None:
        mock_get_tracks_href.side_effect = lambda x: x
        async with self.mock_session.get.return_value as mock_response:
            mock_response.json.side_effect = [
                {"items": [], "next": "b"},
                {"items": [], "next": "c"},
                {"items": [], "next": ""},
            ]
        spotify = Spotify("token")
        tracks = await spotify._get_tracks(PlaylistID("a"))
        self.assertEqual(tracks, [])
        self.mock_session.get.assert_has_calls(
            [
                call("a"),
                call("b"),
                call("c"),
            ]
        )


class TestGetAccessToken(SpotifyTestCase):
    async def test_invalid_json(self) -> None:
        async with self.mock_session.post.return_value as mock_response:
            mock_response.json.side_effect = Exception
        with self.assertRaises(InvalidDataError):
            await Spotify.get_access_token("client_id", "client_secret")

    async def test_error(self) -> None:
        async with self.mock_session.post.return_value as mock_response:
            mock_response.json.return_value = {
                "error": "something went wrong",
                "access_token": "token",
                "token_type": "Bearer",
            }
        with self.assertRaises(InvalidDataError):
            await Spotify.get_access_token("client_id", "client_secret")

    async def test_invalid_access_token(self) -> None:
        async with self.mock_session.post.return_value as mock_response:
            mock_response.json.return_value = {
                "access_token": "",
                "token_type": "Bearer",
            }
        with self.assertRaises(InvalidDataError):
            await Spotify.get_access_token("client_id", "client_secret")

    async def test_invalid_token_type(self) -> None:
        async with self.mock_session.post.return_value as mock_response:
            mock_response.json.return_value = {
                "access_token": "token",
                "token_type": "invalid",
            }
        with self.assertRaises(InvalidDataError):
            await Spotify.get_access_token("client_id", "client_secret")

    async def test_success(self) -> None:
        async with self.mock_session.post.return_value as mock_response:
            mock_response.json.return_value = {
                "access_token": "token",
                "token_type": "Bearer",
            }
        token = await Spotify.get_access_token("client_id", "client_secret")
        self.assertEqual(token, "token")
        self.mock_session.post.assert_called_once_with(
            url="https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            headers={"Authorization": "Basic Y2xpZW50X2lkOmNsaWVudF9zZWNyZXQ="},
        )
