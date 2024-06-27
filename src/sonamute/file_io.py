# STL
import os
import json
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
JSONable = JSON | tuple[JSON, ...]


class TupleJSONEncoder(json.JSONEncoder):
    @override
    def encode(self, o: JSONable):
        if isinstance(o, dict):
            new_o = {}
            for k, v in o.items():
                if isinstance(k, tuple):
                    new_key = " ".join(k)
                    new_o[new_key] = v
                else:
                    new_o[k] = v
            return super().encode(new_o)
        return super().encode(o)


def try_load_json(filename: str) -> DiscordJSON | None:
    with open(filename, "r") as f:
        content = None
        try:
            content = orjson.loads(f.read())
        except orjson.JSONDecodeError:
            # TODO: print failing file? log leve?
            pass
    return content


def is_webhook(m: DiscordJSON) -> bool:
    if not m["author"]["isBot"]:
        return False
    # must be a bot

    has_roles = not not m["author"]["roles"]
    has_discrim = m["author"]["discriminator"] != "0000"

    # webhooks cannot have roles or have discrim other than 0000
    # NOTE: some webhooks are still not pk users! discohook for example
    # NOTE: it is currently unknown whether a bot can omit its discrim
    return not (has_roles or has_discrim)


class PlatformFetcher:
    @abstractmethod
    def get_messages(self) -> Generator[PreMessage, None, None]: ...


class DiscordFetcher(PlatformFetcher):
    root: str
    __seen: set[int] = set()

    def __init__(self, root: str):
        self.root = root

    def get_discord_file(self):
        for root, _, files in os.walk(self.root):
            # we don't need dirs

            for filename in files:
                if not filename.endswith(".json"):
                    continue

                data = try_load_json(os.path.join(root, filename))
                if not data:
                    continue
                if "messageCount" not in data:
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
                # discord IDs are globally unique across all objects
                if _id in self.__seen:
                    continue
                self.__seen.add(_id)

                author_id = int(m["author"]["id"])
                author_name: str = m["author"]["name"]
                is_bot: bool = m["author"]["isBot"]
                is_webhook_: bool = is_webhook(m)
                author: Author = {
                    "_id": author_id,
                    "name": author_name,
                    "platform": platform,
                    "is_bot": is_bot,
                    "is_webhook": is_webhook_,
                    # NOTE: If an author is a webhook, we know to check it later in PluralKit
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

        self.__seen = set()
