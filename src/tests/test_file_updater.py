#!/usr/bin/env python3

import datetime
import pathlib
import tempfile
import textwrap
from typing import Optional, TypeVar
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, call, patch, sentinel

from alias import Alias
from file_manager import FileManager, MalformedAliasError, UnexpectedFilesError
from file_updater import FileUpdater
from plants.unittest_utils import UnittestUtils
from playlist_id import PlaylistID
from playlist_types import Owner, Playlist
from spotify import FailedRequestError

T = TypeVar("T")


class TestUpdateFiles(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.mock_get_env = UnittestUtils.patch(
            self,
            "plants.environment.Environment.get_env",
            new_callable=Mock,
        )
        self.mock_get_env.side_effect = lambda name: {
            "SPOTIFY_CLIENT_ID": "client_id",
            "SPOTIFY_CLIENT_SECRET": "client_secret",
        }[name]

        self.mock_spotify_class = UnittestUtils.patch(
            self,
            "file_updater.Spotify",
            new_callable=Mock,
        )
        self.mock_spotify_class.get_access_token = AsyncMock()
        self.mock_spotify_class.return_value.shutdown = AsyncMock()

        self.mock_update_files_impl = UnittestUtils.patch(
            self, "file_updater.FileUpdater._update_files_impl", new_callable=AsyncMock
        )

    async def test_error(self) -> None:
        self.mock_update_files_impl.side_effect = Exception
        with self.assertRaises(Exception):
            await FileUpdater.update_files(
                now=sentinel.now,
                file_manager=sentinel.file_manager,
                auto_register=sentinel.auto_register,
                update_readme=sentinel.update_readme,
            )
        self.mock_spotify_class.return_value.shutdown.assert_called_once_with()
        self.mock_spotify_class.return_value.shutdown.assert_awaited_once()

    async def test_success(self) -> None:
        await FileUpdater.update_files(
            now=sentinel.now,
            file_manager=sentinel.file_manager,
            auto_register=sentinel.auto_register,
            update_readme=sentinel.update_readme,
        )
        self.mock_get_env.assert_has_calls(
            [
                call("SPOTIFY_CLIENT_ID"),
                call("SPOTIFY_CLIENT_SECRET"),
            ]
        )
        self.mock_spotify_class.get_access_token.assert_called_once_with(
            client_id="client_id",
            client_secret="client_secret",
        )
        self.mock_spotify_class.get_access_token.assert_awaited_once()
        self.mock_spotify_class.assert_called_once_with(
            self.mock_spotify_class.get_access_token.return_value
        )
        self.mock_update_files_impl.assert_called_once_with(
            now=sentinel.now,
            file_manager=sentinel.file_manager,
            auto_register=sentinel.auto_register,
            update_readme=sentinel.update_readme,
            spotify=self.mock_spotify_class.return_value,
        )
        self.mock_spotify_class.return_value.shutdown.assert_called_once_with()
        self.mock_spotify_class.return_value.shutdown.assert_awaited_once()


class TestUpdateFilesImpl(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.now = datetime.datetime(2021, 12, 15)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_dir = pathlib.Path(self.temp_dir.name)
        self.playlists_dir = self.repo_dir / "playlists"
        self.file_manager = FileManager(self.playlists_dir)

        # Mock the get_published_cumulative_playlists method
        self.mock_get_published_cumulative_playlists = UnittestUtils.patch(
            self,
            "github.GitHub.get_published_cumulative_playlists",
            new_callable=lambda: AsyncMock(return_value={}),
        )

        # Mock the GitUtils methods
        UnittestUtils.patch(
            self,
            "git_utils.GitUtils.any_uncommitted_changes",
            new_callable=lambda: Mock(return_value=False),
        )
        UnittestUtils.patch(
            self,
            "git_utils.GitUtils.get_last_commit_content",
            new_callable=lambda: Mock(return_value=[]),
        )

        # Mock the spotify class
        self.mock_spotify_class = UnittestUtils.patch(
            self,
            "file_updater.Spotify",
            new_callable=Mock,
        )

        # Use AsyncMocks for async methods
        self.mock_spotify = self.mock_spotify_class.return_value
        self.mock_spotify.get_spotify_user_playlist_ids = AsyncMock()
        self.mock_spotify.get_featured_playlist_ids = AsyncMock()
        self.mock_spotify.get_category_playlist_ids = AsyncMock()
        self.mock_spotify.get_playlist = AsyncMock()

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def _update_files_impl(
        self, auto_register: bool = False, update_readme: bool = False
    ) -> None:
        await FileUpdater._update_files_impl(
            now=self.now,
            file_manager=self.file_manager,
            auto_register=auto_register,
            update_readme=update_readme,
            spotify=self.mock_spotify,
        )

    @classmethod
    def _helper(
        cls,
        playlist_id: PlaylistID,
        original_name: str,
        num_followers: int,
    ) -> Playlist:
        return Playlist(
            url=f"url_{playlist_id}",
            original_name=original_name,
            unique_name=original_name,
            description="description",
            tracks=[],
            snapshot_id="snapshot_id",
            num_followers=num_followers,
            owner=Owner(
                url="owner_url",
                name="owner_name",
            ),
        )

    @classmethod
    def _fake_get_playlist(
        cls, playlist_id: PlaylistID, *, alias: Optional[Alias]
    ) -> Playlist:
        return cls._helper(
            playlist_id=playlist_id,
            original_name=alias or f"name_{playlist_id}",
            num_followers=0,
        )

    async def test_empty(self) -> None:
        names = ["registry", "plain", "pretty", "cumulative"]
        for name in names:
            self.assertFalse((self.playlists_dir / name).exists())
        await self._update_files_impl()
        for name in names:
            self.assertTrue((self.playlists_dir / name).exists())
        # Double check exist_ok = True
        await self._update_files_impl()

    async def test_auto_register(self) -> None:
        self.mock_spotify.get_spotify_user_playlist_ids.return_value = {"a", "d"}
        self.mock_spotify.get_featured_playlist_ids.return_value = {"b", "d"}
        self.mock_spotify.get_category_playlist_ids.return_value = {"c", "d"}
        self.mock_spotify.get_playlist.side_effect = self._fake_get_playlist
        for name in "abcd":
            self.assertFalse((self.playlists_dir / "registry" / name).exists())
        await self._update_files_impl(auto_register=True)
        for name in "abcd":
            self.assertTrue((self.playlists_dir / "registry" / name).exists())

    async def test_fixup_aliases(self) -> None:
        self.mock_spotify.get_playlist.side_effect = self._fake_get_playlist
        registry_dir = self.playlists_dir / "registry"
        registry_dir.mkdir(parents=True)
        alias_file = registry_dir / "foo"
        with open(alias_file, "w") as f:
            f.write("\n")
        with open(alias_file, "r") as f:
            self.assertTrue(f.read())
        await self._update_files_impl()
        with open(alias_file, "r") as f:
            self.assertFalse(f.read())

    async def test_invalid_aliases(self) -> None:
        registry_dir = self.playlists_dir / "registry"
        registry_dir.mkdir(parents=True)
        alias_file = registry_dir / "foo"
        for malformed_alias in ["\n\n", "a\nc", " \n"]:
            with open(alias_file, "w") as f:
                f.write(malformed_alias)
            with self.assertRaises(MalformedAliasError):
                await self._update_files_impl()

    async def test_good_alias(self) -> None:
        self.mock_spotify.get_playlist.side_effect = self._fake_get_playlist
        registry_dir = self.playlists_dir / "registry"
        registry_dir.mkdir(parents=True)
        with open(registry_dir / "foo", "w") as f:
            f.write("alias")
        await self._update_files_impl()
        self.mock_spotify.get_playlist.assert_called_once_with("foo", alias="alias")
        with open(self.playlists_dir / "plain" / "foo", "r") as f:
            lines = f.read().splitlines()
        self.assertEqual(lines[0], "alias")

    async def test_duplicate_playlist_names(self) -> None:
        self.mock_spotify.get_playlist.side_effect = [
            self._helper(
                playlist_id=PlaylistID("a"), original_name="name", num_followers=1
            ),
            self._helper(
                playlist_id=PlaylistID("b"), original_name="name", num_followers=2
            ),
            self._helper(
                playlist_id=PlaylistID("c"), original_name="name", num_followers=2
            ),
            self._helper(
                playlist_id=PlaylistID("d"), original_name="name (3)", num_followers=0
            ),
            self._helper(
                playlist_id=PlaylistID("e"), original_name="name (3)", num_followers=0
            ),
            self._helper(
                playlist_id=PlaylistID("f"),
                original_name="name (3) (2)",
                num_followers=1,
            ),
        ]
        registry_dir = self.playlists_dir / "registry"
        registry_dir.mkdir(parents=True)
        for playlist_id in "abcdef":
            (registry_dir / playlist_id).touch()
        await self._update_files_impl()
        for playlist_id, name in [
            ("b", "name"),
            ("c", "name (2)"),
            ("d", "name (3)"),
            ("f", "name (3) (2)"),
            ("e", "name (3) (3)"),
            ("a", "name (4)"),
        ]:
            with open(self.playlists_dir / "plain" / playlist_id, "r") as f:
                lines = f.read().splitlines()
            self.assertEqual(lines[0], name)

    async def test_unexpected_files(self) -> None:
        self.mock_spotify.get_playlist.side_effect = self._fake_get_playlist
        for directory in ["registry", "plain", "pretty", "cumulative"]:
            (self.playlists_dir / directory).mkdir(parents=True)
        (self.playlists_dir / "registry" / "foo").touch()
        for directory, filename in [
            ("plain", "bar"),
            ("plain", "foo.md"),
            ("plain", "foo.json"),
            ("pretty", "foo"),
            ("pretty", "bar.md"),
            ("pretty", "bar.json"),
            ("cumulative", "foo"),
            ("cumulative", "bar.md"),
            ("cumulative", "bar.json"),
        ]:
            path = self.playlists_dir / directory / filename
            path.touch()
            with self.assertRaises(UnexpectedFilesError):
                await self._update_files_impl()
            path.unlink()

    # Patch the logger to suppress log spew
    @patch("file_updater.logger")
    async def test_readme(self, mock_logger: Mock) -> None:
        # +-------------------+---+---+---+---+
        # |     Criteria      | a | b | c | d |
        # +-------------------+---+---+---+---+
        # | Fetch succeeds    | 1 | 1 | 0 | 0 |
        # | Has existing data | 1 | 0 | 1 | 0 |
        # +-------------------+---+---+---+---+

        self.mock_spotify.get_playlist.side_effect = UnittestUtils.side_effect(
            [
                self._fake_get_playlist(PlaylistID("a"), alias=None),
                self._fake_get_playlist(PlaylistID("b"), alias=None),
                FailedRequestError(),
                FailedRequestError(),
            ]
        )

        registry_dir = self.playlists_dir / "registry"
        registry_dir.mkdir(parents=True)
        for playlist_id in "abcd":
            (registry_dir / playlist_id).touch()

        pretty_dir = self.playlists_dir / "pretty"
        pretty_dir.mkdir(parents=True)
        for playlist_id in "ac":
            path = pretty_dir / f"{playlist_id}.json"
            playlist = self._helper(
                playlist_id=PlaylistID(playlist_id),
                original_name=f" name_{playlist_id} ",  # ensure whitespace is stripped
                num_followers=0,
            )
            playlist_json = playlist.to_json()
            with open(path, "w") as f:
                f.write(playlist_json)

        with open(self.repo_dir / "README.md", "w") as f:
            f.write(
                textwrap.dedent(
                    """\
                    prev content

                    ## Playlists

                    - [fizz](buzz)
                    """
                )
            )
        await self._update_files_impl(update_readme=True)
        with open(self.repo_dir / "README.md", "r") as f:
            content = f.read()
        self.assertEqual(
            content,
            textwrap.dedent(
                """\
                prev content

                ## Playlists

                - [name\\_a](/playlists/pretty/a.md)
                - [name\\_b](/playlists/pretty/b.md)
                - [name\\_c](/playlists/pretty/c.md)
                """
            ),
        )

    async def test_success(self) -> None:
        # TODO
        pass
