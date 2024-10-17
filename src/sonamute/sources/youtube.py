# STL
import os
import base64
from typing import Literal, TypedDict, cast
from datetime import UTC, datetime
from collections.abc import Generator

# PDM
from typing_extensions import override

# LOCAL
from sonamute.file_io import try_load_json_file
from sonamute.smtypes import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.sources.generic import NULL_CONTAINER, FileFetcher


class YouTubeVideoFormat(TypedDict):
    pass


class YouTubeVideoThumbnail(TypedDict):
    url: str
    preference: int
    id: str  # of int


class YouTubeComment(TypedDict):
    id: str
    parent: str  # "root" or id of parent
    text: str
    like_count: int
    author_id: str
    author: str  # username
    author_thumbnail: str  # url to avatar
    author_is_uploader: bool
    author_is_verified: bool
    author_url: str
    is_favorited: bool
    _time_text: str
    timestamp: int  # unix time
    is_pinned: bool


class YouTubeJSON(TypedDict):
    id: str
    title: str
    formats: list[YouTubeVideoFormat]
    thumbnails: list[YouTubeVideoThumbnail]
    thumbnail: str
    description: str
    channel_id: str
    channel_url: str
    duration: int
    view_count: int
    age_limit: int
    webpage_url: str
    categories: list[str]
    tags: list[str]
    playable_in_embed: bool
    live_status: str  # "not_live" observed
    _format_sort_fields: list[str]
    # automatic_captions: dict[str, list]
    # subtitles: dict[unknown]
    comment_count: int
    like_count: int
    channel: str  # name of channel as displayable string
    channel_follower_count: int
    channel_is_verified: bool
    uploader: str  # equal to channel?
    uploader_id: str  # actually username
    uploader_url: str
    upload_date: str
    timestamp: int  # unix time
    availability: str  # "public" observed
    webpage_url_basename: str  # "watch"
    webpage_url_domain: str  # "youtube.com"
    extractor: str
    extractor_key: str
    playlist_count: int  # number of vids in playlist
    playlist: str  # name
    playlist_id: str  # name of playlist????
    playlist_title: str
    n_entries: int  # same as playlist_count?
    playlist_index: int  # useless
    display_id: str
    fulltitle: str
    duration_string: str
    is_live: bool
    was_live: bool
    epoch: int  # unix time that is different from timestamp??
    comments: list[YouTubeComment]
    asr: int  # audio sample rate
    filesize: int  # bytes
    format_id: str  # of int
    format_note: str  # resolution
    source_preference: int
    fps: int
    # tons more metadata about video format

    language: str  # langcode, probably 2 if available or 3 if not
    language_preference: int
    # even more metadata about video format


def youtube_id_to_int(yt_id: str) -> int:
    # https://webapps.stackexchange.com/questions/54443
    # youtube's alphabet is different for URL reasons
    b64 = yt_id.replace("-", "+").replace("_", "/")

    # and they omit padding since the IDs are of known length
    # 11 for videos, 22 for channels, 20 for comments
    b64 += "=="

    decoded = base64.b64decode(b64, validate=False)

    _id = int.from_bytes(decoded)

    if len(yt_id) == 11:  # video
        assert _id < 2**64, (yt_id, b64, decoded, _id)
    assert _id < 2**128, (yt_id, b64, decoded, _id)  # everything else
    # NOTE: this assumption fails if the 6 char pad isn't removed

    return _id


def clean_username(raw_name: str) -> str:
    return raw_name.lstrip("@")


def fetch_video_author_name(raw_msg: YouTubeJSON) -> str:
    raw_name = raw_msg.get("uploader_id") or raw_msg.get("uploader")
    # auto-uploaded music videos have no uploader id
    name = clean_username(raw_name)
    return name


def format_video_content(video: YouTubeJSON) -> str:
    title = video.get("fulltitle") or video["title"]
    description = video["description"]
    # TODO: subtitles? the yt-dlp response doesn't have them by default

    to_return = ""
    if title:
        to_return += title
    if description:
        to_return += "\n\n"
        to_return += description

    return to_return


def fetch_comment_id(comment: YouTubeComment) -> int:
    comment_id = comment["id"]

    # if a comment is a reply, its id is parent.child
    if comment["parent"] != "root":
        comment_id = comment_id.split(".")[-1]

    # NOTE: I'm so serious.
    # Top level comments have this, 122.0k / 122.8k of what I have.
    # The others have a *different* pad, although they're already shorter.
    # I found a stackoverflow post from Dec 2017 with this pad too.
    # https://stackoverflow.com/questions/47815604/comment-id-format-has-changed
    if len(comment_id) == 26:
        comment_id = comment_id.removesuffix("AaABAg")

    comment_id = youtube_id_to_int(comment_id)
    return comment_id


def fetch_user_id(
    raw: YouTubeJSON | YouTubeComment, key: Literal["author_id", "channel_id"]
) -> int:
    # when the type checking
    user_id = None
    if "author_id" in raw and key == "author_id":
        user_id = raw[key]
    if "channel_id" in raw and key == "channel_id":
        user_id = raw[key]
    if not user_id:
        raise KeyError(f"{key} not found in raw", raw)

    # NOTE: Again, serious. Every user ID has this.
    # Chopping it brings it into the correct range.
    # Also doesn't change the uniqueness of the key.
    if len(user_id) == 24:
        user_id = user_id.removeprefix("UC")

    user_id = youtube_id_to_int(user_id)
    return user_id


class YouTubeFetcher(FileFetcher):
    platform: Platform = {
        "_id": KnownPlatforms.YouTube.value,
        "name": KnownPlatforms.YouTube.name,
    }
    __seen: set[int] = set()

    @override
    def get_files(self) -> Generator[YouTubeJSON, None, None]:
        for root, _, files in os.walk(self.root):
            for filename in files:
                if not filename.endswith(".json"):
                    continue

                data = cast(
                    YouTubeJSON, try_load_json_file(os.path.join(root, filename))
                )
                if not data:
                    continue

                # not a video
                if "formats" not in data:
                    continue

                yield data

    @override
    def get_community(self, raw_src: YouTubeJSON) -> Community:
        # NOTE: Youtube doesn't have any "communities"
        # I assume that video authors are "communities"
        # since authors tend to draw like-minded audiences
        # Communities do not figure into most analysis anyway,
        # so this is a convention rather than meaningful.
        community_id = fetch_user_id(raw_src, "channel_id")
        community_name = fetch_video_author_name(raw_src)

        return Community(
            {
                "_id": community_id,
                "name": community_name,
                "platform": self.platform,
            }
        )

    @override
    def get_author(self, raw_msg: YouTubeComment | YouTubeJSON) -> Author:

        # video
        if "channel_id" in raw_msg:
            _id = fetch_user_id(raw_msg, "channel_id")
            name = fetch_video_author_name(raw_msg)

        # comment
        elif "author_id" in raw_msg:
            _id = fetch_user_id(raw_msg, "author_id")
            name = clean_username(raw_msg["author"])

        return Author(
            {
                "_id": _id,
                "name": name,
                "platform": self.platform,
                # youtube has neither
                "is_bot": False,
                "is_webhook": False,
            }
        )

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for video in self.get_files():
            # NOTE: We do not check seen on videos, in case a later copy of the same
            # video's metadata includes new comments; we only check whether a comment
            # was seen
            # This is okay so long as video IDs are stable, since the DB doesn't take
            # duplicate messages anyway
            video_id = youtube_id_to_int(video["id"])
            video_postdate = datetime.fromtimestamp(video["timestamp"], tz=UTC)
            video_content = format_video_content(video)

            community = self.get_community(video)
            video_author = self.get_author(video)

            yield PreMessage(
                {
                    "_id": video_id,
                    "author": video_author,
                    "content": video_content,
                    "postdate": video_postdate,
                    "community": community,
                    "container": NULL_CONTAINER,
                }
            )

            # if comments are off, may be omitted
            for comment in video.get("comments", []):

                comment_id = fetch_comment_id(comment)

                if comment_id in self.__seen:
                    continue
                self.__seen.add(comment_id)

                comment_content = comment["text"]
                comment_postdate = datetime.fromtimestamp(comment["timestamp"], tz=UTC)

                comment_author = self.get_author(comment)

                yield PreMessage(
                    {
                        "_id": comment_id,
                        "author": comment_author,
                        "community": community,
                        "container": NULL_CONTAINER,
                        "content": comment_content,
                        "postdate": comment_postdate,
                    }
                )
