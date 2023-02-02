#!/usr/bin/env python3

import logging
import pathlib
from typing import AbstractSet, Dict, Optional, Set

from alias import Alias, InvalidAliasError
from playlist_id import PlaylistID

logger: logging.Logger = logging.getLogger(__name__)


class MalformedAliasError(Exception):
    pass


class UnexpectedFilesError(Exception):
    pass


class FileManager:
    def __init__(self, playlists_dir: pathlib.Path) -> None:
        self._playlists_dir = playlists_dir

    def ensure_subdirs_exist(self) -> None:
        for directory in [
            self._get_registry_dir(),
            self._get_plain_dir(),
            self._get_pretty_dir(),
            self._get_cumulative_dir(),
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def ensure_registered(self, playlist_ids: AbstractSet[PlaylistID]) -> None:
        registry_dir = self._get_registry_dir()
        for playlist_id in sorted(playlist_ids):
            path = registry_dir / playlist_id
            if not path.exists():
                logger.info(f"Registering playlist: {playlist_id}")
                path.touch()

    def fixup_aliases(self) -> None:
        # GitHub makes it easy to create files that look empty but actually
        # contain a single newline. Normalize them to simplify other logic.
        for path in sorted(self._get_registry_dir().iterdir()):
            with open(path, "r") as f:
                content = f.read()
            if content == "\n":
                logger.info(f"Truncating empty alias: {path.name}")
                with open(path, "w"):
                    pass

    def get_registered_playlists(self) -> Dict[PlaylistID, Optional[Alias]]:
        playlists: Dict[PlaylistID, Optional[Alias]] = {}
        for path in sorted(self._get_registry_dir().iterdir()):
            playlist_id = PlaylistID(path.name)
            with open(path, "r") as f:
                lines = f.read().splitlines()
            if lines:
                if len(lines) != 1:
                    raise MalformedAliasError(f"Malformed alias: {playlist_id}")
                try:
                    alias = Alias(lines[0])
                except InvalidAliasError:
                    raise MalformedAliasError(f"Malformed alias: {playlist_id}")
            else:
                alias = None
            playlists[playlist_id] = alias
        return playlists

    def ensure_no_unexpected_files(self) -> None:
        unexpected_files: Set[pathlib.Path] = set()
        playlist_ids = set(path.name for path in self._get_registry_dir().iterdir())
        for directory, suffixes in [
            (self._get_plain_dir(), [""]),
            (self._get_pretty_dir(), [".md", ".json"]),
            (self._get_cumulative_dir(), [".md", ".json"]),
        ]:
            for path in directory.iterdir():
                if not any(
                    path.name.endswith(suffix)
                    and self._remove_suffix(path.name, suffix) in playlist_ids
                    for suffix in suffixes
                ):
                    unexpected_files.add(path)
        if unexpected_files:
            raise UnexpectedFilesError(f"Unexpected files: {unexpected_files}")

    def get_plain_path(self, playlist_id: PlaylistID) -> pathlib.Path:
        return self._get_plain_dir() / playlist_id

    def get_pretty_json_path(self, playlist_id: PlaylistID) -> pathlib.Path:
        return self._get_pretty_dir() / f"{playlist_id}.json"

    def get_pretty_markdown_path(self, playlist_id: PlaylistID) -> pathlib.Path:
        return self._get_pretty_dir() / f"{playlist_id}.md"

    def get_cumulative_json_path(self, playlist_id: PlaylistID) -> pathlib.Path:
        return self._get_cumulative_dir() / f"{playlist_id}.json"

    def get_cumulative_markdown_path(self, playlist_id: PlaylistID) -> pathlib.Path:
        return self._get_cumulative_dir() / f"{playlist_id}.md"

    def get_metadata_json_path(self) -> pathlib.Path:
        return self._playlists_dir / "metadata.json"

    def get_readme_path(self) -> pathlib.Path:
        return self._playlists_dir.parent / "README.md"

    def _get_registry_dir(self) -> pathlib.Path:
        return self._playlists_dir / "registry"

    def _get_plain_dir(self) -> pathlib.Path:
        return self._playlists_dir / "plain"

    def _get_pretty_dir(self) -> pathlib.Path:
        return self._playlists_dir / "pretty"

    def _get_cumulative_dir(self) -> pathlib.Path:
        return self._playlists_dir / "cumulative"

    @classmethod
    def _remove_suffix(cls, string: str, suffix: str) -> str:
        if not suffix:
            return string
        assert string.endswith(suffix)
        return string[: -len(suffix)]
