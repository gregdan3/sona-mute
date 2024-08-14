# STL
import os
from typing import TypedDict, cast
from datetime import UTC, datetime
from collections.abc import Generator

# PDM
from typing_extensions import override

# LOCAL
from sonamute.db import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.file_io import try_load_json
from sonamute.sources.generic import NULL_CONTAINER, FileFetcher


class RedditSubmission(TypedDict):
    archived: bool
    author: str  # username
    # author_flair_background_color: str | None
    # author_flair_css_class: str | None
    # author_flair_richtext: list
    # author_flair_text: str | None
    # author_flair_text_color: str | None
    # author_flair_type: str
    brand_safe: bool
    can_gild: bool
    contest_mode: bool
    created_utc: int | float | str
    distinguished: str  # "moderator"
    domain: str  # self.tokipona
    edited: bool
    gilded: int
    hidden: bool
    hide_score: bool
    id: str  # b36id
    is_crosspostable: bool
    is_original_content: bool
    is_reddit_media_domain: bool
    is_self: bool
    is_video: bool
    # link_flair_css_class: str | None
    # link_flair_richtext: list
    link_flair_text: str | None
    # link_flair_text_color: str | None
    # link_flair_type: str
    locked: bool
    media: str | None
    media_embed: dict
    no_follow: bool
    num_comments: int
    num_crossposts: int
    over_18: bool
    parent_whitelist_status: None
    permalink: str
    retrieved_on: int
    rte_mode: str  # markdown
    score: int
    secure_media: None
    secure_media_embed: dict
    selftext: str
    send_replies: bool
    spoiler: bool
    stickied: bool
    subreddit: str
    subreddit_id: str  # t5_[b36id]
    subreddit_name_prefixed: str
    subreddit_type: str
    suggested_sort: str | None
    thumbnail: str
    thumbnail_height: int | None
    thumbnail_width: int | None
    title: str
    url: str
    whitelist_status: None

    # seen in latest submission
    author_fullname: str


class RedditComment(TypedDict):
    # seen in earliest comment
    archived: bool
    subreddit: str
    score: int
    # author_flair_css_class: str | None
    author: str  # name
    downs: int
    score_hidden: bool
    distinguished: str | None  # seen "moderator"
    link_id: str  # t3_[b36id]
    controversiality: int
    id: str  # b36id
    gilded: int
    name: str  # t1_[b36id]; b36id is equal to `id`
    subreddit_id: str
    created_utc: str | int | float  # str of int
    ups: int
    retrieved_on: int
    # author_flair_text: str | None
    body: str
    parent_id: str  # t3_[b36id]
    edited: bool

    # seen in latest comment
    all_awardings: list
    approved_at_utc: str | None
    approved_by: None  # not seen with value
    associated_award: None
    # author_flair_richtext: list
    # author_flair_template_id: str | None
    # author_flair_text_color: str | None
    # author_flair_type: str
    author_fullname: str  # t2_[b36id]
    author_is_blocked: bool
    author_patreon_flair: bool
    author_premium: bool
    # banned_at_utc: str | None
    # banned_by: None  # no value seen
    can_gild: bool
    can_mod_post: bool
    # collapsed: bool
    # collapsed_because_crowd_control: bool
    # collapsed_reason: str | None
    # collapsed_reason_code: int | None
    comment_type: None
    gildings: dict[str, int]
    is_submitter: bool
    likes: None
    locked: bool
    # mod_note: str | None
    # mod_reason_by: None
    # mod_reason_title: None
    # mod_reports: list
    no_follow: bool
    num_reports: int
    permalink: str  # url starting from /r/
    removal_reason: str | None
    replies: str  # always empty str?
    report_reasons: list
    saved: bool
    send_replies: bool
    stickied: bool
    subreddit_name_prefixed: str  # r/tokipona
    subreddit_type: str  # public
    top_awarded_type: None
    total_awards_received: int
    treatment_tags: list
    unrepliable_reason: str | None
    updated_on: int
    user_reports: list


RedditJSON = RedditSubmission | RedditComment

B36DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

REDDIT_TYPE_MAP = {
    1: "comment",
    2: "user",
    3: "post",
    4: "message",  # not in my data
    5: "subreddit",
}


def b36decode(b36id: str) -> int:
    return int(b36id, 36)


def b36encode(n: int) -> str:
    if n == 0:
        return "0"
    result: list[str] = []
    while n:
        n, remainder = divmod(n, 36)
        result.append(B36DIGITS[remainder])
    return "".join(reversed(result))


def split_type_id(typed_id: str) -> tuple[int, int]:
    otype, b36id = typed_id.split("_")
    return int(otype[1]), b36decode(b36id)


def format_post(msg: RedditJSON) -> str:
    content = ""
    if title := msg.get("title"):
        content = title
    if selftext := msg.get("selftext"):
        content += "\n\n" + selftext
    if body := msg.get("body"):
        # only exists on comments
        content = body

    # my archive formats < and > like these
    content = content.replace("&gt;", ">")
    content = content.replace("&lt;", "<")
    content = content.replace("&amp;", "&")
    content = content.replace("#x200B", "​")

    return content


class RedditFetcher(FileFetcher):
    platform: Platform = {
        "_id": KnownPlatforms.Reddit.value,
        "name": KnownPlatforms.Reddit.name,
    }
    __seen: set[int] = set()

    @override
    def get_files(self) -> Generator[RedditJSON, None, None]:
        for root, _, files in os.walk(self.root):
            for filename in files:
                if ("comments" not in filename) and ("submissions" not in filename):
                    continue
                if filename.endswith(".zst"):
                    continue
                # TODO: safety checking?
                with open(os.path.join(root, filename), "r") as f:
                    for line in f:
                        data = cast(RedditJSON, try_load_json(line))
                        if not data:
                            continue
                        # NOTE: ONE COMMENT LACKS AN ID. WHY??
                        # if "id" not in data:
                        #     continue
                        if "subreddit" not in data:
                            continue
                        if "subreddit_id" not in data:
                            continue

                        yield data

    @override
    def get_community(self, raw_src: RedditJSON) -> Community:
        community_type, community_id = split_type_id(
            raw_src["subreddit_id"]
        )  # FIXME: incomplete
        community_name = raw_src["subreddit"]

        community: Community = {
            "_id": community_id,
            "name": community_name,
            "platform": self.platform,
        }
        return community

    @override
    def get_author(self, raw_msg: RedditJSON) -> Author:

        author_fullname = raw_msg.get("author_fullname")
        author_id = 0  # null Reddit author
        if author_fullname:
            _, author_id = split_type_id(author_fullname)

        author_name = raw_msg["author"]

        is_bot: bool = False  # there are bots but resp doesn't tell us
        is_webhook_: bool = False

        author: Author = {
            "_id": author_id,
            "name": author_name,
            "platform": self.platform,
            "is_bot": is_bot,
            "is_webhook": is_webhook_,
        }
        return author

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for msg in self.get_files():
            # reddit data is line-by-line
            # so get_files emits each line as json here

            # check if deleted

            _id = b36decode(msg["id"])

            if _id in self.__seen:
                continue
            self.__seen.add(_id)

            # community is stored with each message
            community = self.get_community(msg)
            author = self.get_author(msg)

            content = format_post(msg)

            timestamp = int(msg["created_utc"])
            postdate = datetime.fromtimestamp(timestamp, tz=UTC)

            message: PreMessage = {
                "_id": _id,
                "content": content,
                "container": NULL_CONTAINER,
                "community": community,
                "author": author,
                "postdate": postdate,
            }

            yield message
