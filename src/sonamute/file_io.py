# STL
import os
import logging
from abc import abstractmethod
from typing import Any, cast
from datetime import datetime
from collections.abc import Mapping, Iterable, Generator

# PDM
import orjson
from typing_extensions import override

# LOCAL
from sonamute.db import Author, Platform, Community, PreMessage, KnownPlatforms

LOG = logging.getLogger()

JSON = str | int | float | Mapping["JSON", "JSON"] | Iterable["JSON"]
DiscordJSON = Mapping[str, Mapping[str, JSON]]  # still inaccurate, but closer


def try_load_json(filename: str) -> DiscordJSON | None:
    with open(filename, "r") as f:
        content = None
        try:
            content = orjson.loads(f.read())
        except orjson.JSONDecodeError:
            # TODO: print failing file? log leve?
            pass
    return content

class PlatformFetcher:
    @abstractmethod
    def get_messages(self) -> Generator[PreMessage, None, None]: ...


class DiscordFetcher(PlatformFetcher):
    root: str

    def __init__(self, root: str):
        self.root = root

    def get_discord_file(self):
        for root, _, files in os.walk(self.root):
            # we don't need dirs

            for filename in files:
                data = try_load_json(os.path.join(root, filename))
                if not data:
                    continue
                yield data

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        platform_id = KnownPlatforms.Discord.value
        platform_name = KnownPlatforms.Discord.name
        platform: Platform = {"_id": int(platform_id), "name": platform_name}

        for f in self.get_discord_file():
            container_id = int(f["channel"]["id"])
            community_id = int(f["guild"]["id"])
            community_name: str = f["guild"]["name"]
            community: Community = {
                "_id": community_id,
                "name": community_name,
                "platform": platform,
            }

            for m in f.get("messages", []):
                _id = int(m["id"])
                author_id = int(m["author"]["id"])
                author_name: str = m["author"]["name"]
                author: Author = {
                    "_id": author_id,
                    "name": author_name,
                    "platform": platform,
                }

                postdate_str: str = m["timestamp"]
                postdate = datetime.fromisoformat(postdate_str)

                content: str = m["content"]
                message: PreMessage = {
                    "_id": _id,
                    "content": content,
                    "container": container_id,
                    "community": community,
                    "author": author,
                    "postdate": postdate,
                }
                yield message
