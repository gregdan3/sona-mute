# STL
import os
from abc import ABCMeta, abstractmethod
from typing import Any
from collections.abc import Generator

# PDM
import orjson
from typing_extensions import override

# LOCAL
from sonamute.db import Author, Platform, Community, PreMessage, KnownPlatforms


class PlatformFetcher:
    @abstractmethod
    def get_messages(self) -> Generator[PreMessage, None, None]: ...


class DiscordFetcher(PlatformFetcher):
    root: str

    def __init__(self, root: str):
        self.root = root

    def get_discord_file(self):
        for file in os.listdir(self.root):
            with open(self.root + file, "r") as f:
                content: dict[str, Any] = orjson.loads(f.read())
                yield content

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        platform_id = KnownPlatforms.Discord.value
        platform_name = KnownPlatforms.Discord.name
        platform: Platform = {"_id": platform_id, "name": platform_name}

        for f in self.get_discord_file():
            community_id = f["guild"]["id"]
            community_name = f["guild"]["name"]
            container = f["channel"]["id"]
            community: Community = {
                "_id": community_id,
                "name": community_name,
                "platform": platform,
            }

            for m in f.get("messages", []):
                _id = m["id"]

                postdate = m["timestamp"]
                author_id = m["author"]["id"]
                author_name = m["author"]["name"]
                content = m["content"]
                author: Author = {
                    "_id": author_id,
                    "name": author_name,
                    "platform": platform,
                }

                message: PreMessage = {
                    "_id": _id,
                    "content": content,
                    "container": container,
                    "community": community,
                    "author": author,
                    "postdate": postdate,
                }
                yield message


def fetch_discord_file(dir: str) -> Generator[dict, None, None]:
    for file in os.listdir(dir):
        # if "tomo-toki [851665652452556840]" not in file:
        #     continue
        # if "toki-pona [301377942062366741]" not in file:
        #     continue
        # if "[316063418253705229]" not in file:
        #     continue
        if "[316066233755631616]" in file:  # jaki
            continue
        if "[786041291707777034]" in file:  # musi Ako
            continue

        with open(dir + file, "r") as f:
            content = orjson.loads(f.read())
            yield content


def fetch_discord_msg(
    content: dict[str, dict], _ignore_authors: list[int] | None = None
) -> Generator[str, None, None]:
    if not _ignore_authors:
        _ignore_authors = list()

    for m in content.get("messages", []):
        if not m:
            continue
        if m["author"]["id"] in _ignore_authors:
            continue

        content = m.get("content")
        if not content:
            continue

        yield content


def fetch_discord(root: str) -> Generator[str, None, None]:
    for file in fetch_discord_file(root):
        for msg in fetch_discord_msg(file):
            yield msg
