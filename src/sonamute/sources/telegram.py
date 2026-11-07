# STL
import os
from uuid import UUID
from typing import Literal, TypedDict, NotRequired, cast
from datetime import UTC, datetime
from collections.abc import Generator

# PDM
from typing_extensions import override

# LOCAL
from sonamute.log import LOG
from sonamute.utils import fake_uuid, int_to_uuid
from sonamute.file_io import try_load_json_file
from sonamute.smtypes import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.sources.generic import NULL_INT_ID, FileFetcher

# TODO: special handling?
ONECHAT_BRIDGE_ID = 128026086
TPT_RULES_BOT_ID = 1534630115

FMT_TEXT_MAP = {
    "bold": "*",
    "italic": "_",
    "underline": "__",
    "strikethrough": "~",
    # "code": "`",
    "spoiler": "||",
}

TelegramDialogType = Literal["public_supergroup", "private_supergroup"]

TelegramMessageType = Literal["message", "service"]

TelegramActorType = Literal["user", "channel"]

TelegramTextEntityType = Literal[
    "blockquote",
    "bold",
    "code",
    "custom_emoji",
    "email",
    "hashtag",
    "italic",
    "link",
    "mention",
    "mention_name",
    "plain",
    "spoiler",
    "strikethrough",
    "text_link",
    "underline",
]

TelegramActionType = Literal[
    "create_channel",
    "boost_apply",
    "edit_group_title",
    "edit_group_photo",
    "group_call",
    "group_call_scheduled",
    "invite_members",
    "join_group_by_link",
    "remove_members",
    "migrate_from_group",
    "pin_message",
    "set_messages_ttl",
]


class TelegramTextEntity(TypedDict):
    type: TelegramTextEntityType
    text: str


class TelegramMessageJSON(TypedDict):
    id: int
    type: TelegramMessageType
    date: str
    date_unixtime: str
    text: str | list[str | TelegramTextEntity]
    text_entities: list[TelegramTextEntity]


class TelegramServiceMessageJSON(TelegramMessageJSON):
    type: Literal["service"]  # type: ignore[i can overwrite with a more specific type]
    actor: str | None
    actor_id: str
    action: TelegramActionType
    title: str


class __TelegramPlainMessageJSON(TelegramMessageJSON):
    type: Literal["message"]  # type: ignore[i can overwrite with a more specific type]
    # from: str
    from_id: str
    forwarded_from: NotRequired[str]

    via_bot: NotRequired[str]

    photo: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]

    file: NotRequired[str]
    filename: NotRequired[str]
    mime_type: NotRequired[str]
    media_type: NotRequired[str]

    performer: NotRequired[str]
    duration_seconds: NotRequired[int]


# This nonsense is just to add a "from" attr despite "from" being reserved
class TelegramPlainMessageJSON(
    __TelegramPlainMessageJSON, TypedDict("FromAdder", {"from": str | None})
): ...


class TelegramJSON(TypedDict):
    name: str
    type: TelegramDialogType
    id: int
    messages: list[TelegramPlainMessageJSON | TelegramServiceMessageJSON]


def split_type_id(id: str) -> tuple[TelegramActorType, int]:
    if id.startswith("user"):
        return "user", int(id[4:])
    if id.startswith("channel"):
        return "channel", int(id[7:])

    raise ValueError("Received unknown actor id %s" % id)


def get_actor_metadata(
    m: TelegramPlainMessageJSON,
) -> tuple[TelegramActorType, int, str | None]:
    if m["type"] == "message":
        actor_type, actor_id = split_type_id(m["from_id"])
        actor_name = m["from"]
    else:
        raise ValueError("Received unknown message type %s" % m["type"])  # type: ignore[basedpyright is right except that my types could be incomplete]

    return actor_type, actor_id, actor_name


def format_tg_markdown_v2(ent: TelegramTextEntity) -> str:
    text = ent["text"]
    if ent["type"] == "mention":
        return f"<{text}>"
    if ent["type"] == "mention_name":
        return f"<@{text}>"
    if ent["type"] == "blockquote":
        return f"> {text}"
    if ent["type"] == "code":
        if "\n" in text:
            return f"```\n{text}\n```"
        return f"`{text}`"

    if ent["type"] in FMT_TEXT_MAP:
        quoter = FMT_TEXT_MAP[ent["type"]]
        return f"{quoter}{text}{quoter}"

    return ent["text"]


def coalesce_text(
    text_entities: list[TelegramTextEntity], do_format: bool = False
) -> str:
    output = ""
    for ent in text_entities:
        if do_format:
            output += format_tg_markdown_v2(ent)
        else:
            output += ent["text"]
    return output


class TelegramFetcher(FileFetcher):
    platform: Platform = {
        "id": KnownPlatforms.Telegram.value,
        "name": KnownPlatforms.Telegram.name,
    }

    @override
    def get_files(self) -> Generator[TelegramJSON, None, None]:
        for root, _, files in os.walk(self.root):
            # we don't need dirs

            for filename in files:
                if not filename.endswith(".json"):
                    LOG.debug(f"Skip telegram file {root}/{filename}; wrong extension")
                    continue

                data = cast(
                    TelegramJSON, try_load_json_file(os.path.join(root, filename))
                )
                if not data:
                    LOG.debug(f"Skip telegram file {root}/{filename}; no data")
                    continue
                if "name" not in data and "type" not in data:
                    LOG.debug(f"Skip telegram file {root}/{filename}; no name or type")
                    continue
                LOG.info(f"Reading telegram file {root}/{filename}")
                yield data

    @override
    def get_community(self, raw_src: TelegramJSON) -> Community:
        return Community(
            {
                "id": int_to_uuid(raw_src["id"]),
                "name": raw_src["name"],
                "platform": self.platform,
            }
        )

    @override
    def get_author(self, raw_msg: TelegramPlainMessageJSON) -> Author:
        author_type, author_id, author_name = get_actor_metadata(raw_msg)
        # author type is either user or channel; no bot info
        author: Author = {
            "id": int_to_uuid(author_id),
            "name": author_name or "",
            "platform": self.platform,
            "is_bot": False,  # we skip service messages, and otherwise can't know,
            "is_webhook": False,  # telegram has no analogue
        }
        return author

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for f in self.get_files():
            community = self.get_community(f)

            for m in f.get("messages", []):
                if m["type"] == "service":
                    continue  # join notifs, channel edits, etc.

                id = int_to_uuid(m["id"])
                # telegram IDs are per-chat, so we check both
                if self.seen(id, community["id"]):
                    continue

                if "forwarded_from" in m:
                    # ignore forwards entirely
                    continue

                author = self.get_author(m)
                if author["id"].int == TPT_RULES_BOT_ID:
                    # this is the only known telegram bot that speaks toki pona
                    author["is_bot"] = True
                if (
                    author["id"].int == ONECHAT_BRIDGE_ID
                    and len(m["text_entities"]) > 1
                ):
                    # we rewrite to reflect the actual author of the message

                    # NOTE: this is a bot, but we have no way to know
                    # is_bot and is_webhook are already false here

                    # name is first bc 1chat bridge always bolds it
                    # assign new name and id over bot's
                    author["name"] = m["text_entities"][0]["text"]
                    author["id"] = fake_uuid(author["name"])
                    # omit name from msg content, and following colon+space
                    m["text_entities"] = m["text_entities"][1:]
                    m["text_entities"][0]["text"] = m["text_entities"][0]["text"][2:]
                    # NOTE: one guy in 2018 broke the bot's formatting
                    # his message is len=1 ... oh well idc

                timestamp = int(m["date_unixtime"])
                postdate = datetime.fromtimestamp(timestamp, tz=UTC)

                content: str = coalesce_text(m["text_entities"], do_format=True)
                message: PreMessage = {
                    "id": id,
                    "content": content,
                    "container": NULL_INT_ID,
                    "community": community,
                    "author": author,
                    "postdate": postdate,
                }

                yield message
