# STL
import os
import logging
from abc import abstractmethod
from typing import Any
from datetime import datetime
from collections.abc import Generator

# PDM
import orjson
from typing_extensions import override

# LOCAL
from sonamute.db import Author, Platform, Community, PreMessage, KnownPlatforms

LOG = logging.getLogger()


def clean_content(content: str) -> str:
    content = content.replace("\xad", "")
    # this is a discretionary hyphen, and orjson loads it as an escape sequence instead
    return content


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
                content = clean_content(content)
                # if "\xad" in content:
                #     print(content)

                message: PreMessage = {
                    "_id": _id,
                    "content": content,
                    "container": container_id,
                    "community": community,
                    "author": author,
                    "postdate": postdate,
                }
                yield message
