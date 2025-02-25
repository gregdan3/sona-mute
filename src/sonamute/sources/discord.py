# STL
import os
from typing import TypedDict, cast
from datetime import datetime
from collections.abc import Generator

# PDM
from typing_extensions import override

# LOCAL
from sonamute.file_io import try_load_json_file
from sonamute.smtypes import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.sources.generic import FileFetcher


class DiscordGuildJSON(TypedDict):
    id: str
    name: str
    iconUrl: str


class DiscordChannelJSON(TypedDict):
    id: str
    type: str
    categoryId: str
    category: str
    name: str
    topic: str | None


class DiscordRoleJSON(TypedDict):
    id: str
    name: str
    color: str
    position: int


class DiscordAuthorJSON(TypedDict):
    id: str
    name: str
    discriminator: str
    nickname: str
    color: str
    isBot: bool
    roles: list[DiscordRoleJSON]
    avatarUrl: str


class DiscordMessageJSON(TypedDict):
    id: str
    type: str
    timestamp: str
    timestampEdited: str | None
    callEndedTimestamp: str | None
    isPinned: bool
    content: str
    author: DiscordAuthorJSON


class DiscordJSON(TypedDict):
    guild: DiscordGuildJSON
    channel: DiscordChannelJSON
    messages: list[DiscordMessageJSON]
    messageCount: int


SYSTEM_MESSAGE_TYPES = {
    # id
    # event name
    "4",
    "ChannelNameChange",
    "6",
    "ChannelPinnedMessage",
    "7",
    "GuildMemberJoin",
    "8",  # boosts and boost tiers
    "GuildBoost",
    "9",
    "GuildBoostTier1",
    "10",
    "GuildBoostTier2",
    "11",
    "GuildBoostTier3",
    "12",
    "ChannelFollowAdd",
    # "20",  # 20 appears to be command prompts generated by bots
    # they're owned by the bot so idc
    "44",
    "PurchaseNotification",
    "46",
    "PollResult",
}


def is_webhook(m: DiscordMessageJSON) -> bool:
    if not m["author"]["isBot"]:
        return False
    # must be a bot

    has_roles = not not m["author"].get("roles")
    has_discrim = m["author"]["discriminator"] != "0000"

    # webhooks cannot have roles or have discrim other than 0000
    # NOTE: some webhooks are still not pk users! discohook for example
    # NOTE: it is currently unknown whether a bot can omit its discrim
    return not (has_roles or has_discrim)


def is_system(m: DiscordMessageJSON) -> bool:
    return m["type"] in SYSTEM_MESSAGE_TYPES


class DiscordFetcher(FileFetcher):
    platform: Platform = {
        "_id": KnownPlatforms.Discord.value,
        "name": KnownPlatforms.Discord.name,
    }
    __seen: set[int] = set()

    @override
    def get_files(self) -> Generator[DiscordJSON, None, None]:
        for root, _, files in os.walk(self.root):
            # we don't need dirs

            for filename in files:
                if not filename.endswith(".json"):
                    continue

                data = cast(
                    DiscordJSON, try_load_json_file(os.path.join(root, filename))
                )
                if not data:
                    continue
                if "messageCount" not in data:
                    continue
                yield data

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for f in self.get_files():
            container_id = int(f["channel"]["id"])
            community_id = int(f["guild"]["id"])
            community_name: str = f["guild"]["name"]
            community: Community = {
                "_id": community_id,
                "name": community_name,
                "platform": self.platform,
            }

            for m in f.get("messages", []):
                if is_system(m):
                    # discord attributes these to a user author
                    # but they're system messages e.g. boosts
                    continue

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
                    "platform": self.platform,
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
