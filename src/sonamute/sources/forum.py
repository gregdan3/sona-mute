# STL
import os
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse
from collections.abc import Generator

# PDM
from bs4.element import Tag
from typing_extensions import override

# LOCAL
from sonamute.db import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.utils import T, fake_id
from sonamute.file_io import try_load_html_file
from sonamute.sources.generic import NULL_CONTAINER, FileFetcher

"""
it's really not that bad since all i care about is user generated content, and it's a very straightforward forum
on any given page, there are either posts at the xpath `//div[@class="postbody"]` or no posts, such as on forum index or any given category index
from there, the post body is the text content of `//div[@class="content"]` (i will need to remove any `blockquote` and then strip all html), and the author id `//strong/a[@class="username"]` in the `u` url param of the href
in the yahoo group section, authors aren't forum members and thus have no id- but i can just give them the null id or an id based on their username (probably most wise so long as it's always out of the 2^16 range) and keep going

note: anything before oct 1 2009 is from the yahoo group
    """

FORUM_NAME = "forums.tokipona.org"
YAHOO_GROUP_NAME = "tokipona@yahoogroups.com"

POST_SELECTOR = "div.postbody"

CONTENT_SELECTOR = "div.content"
AUTHOR_SELECTOR = "span.responsive-hide > strong > .username, span.responsive-hide > strong > .username-coloured"
# NOTE: returns either a span or anchor; the text is the username, and if it's an a, the
# href includes a user id in the u param
# and yes, the username and username-coloured classes are mutually exclusive

POST_ID_SELECTOR = "h3 a"
# NOTE: only works inside of postbody

DATE_SELECTOR = "p.author > time"
# NOTE: has a datetime attr in ISO format


# the day the forum replaced the yahoo group
MOVE_DATE = datetime(2009, 10, 1, tzinfo=UTC)


def get_url_param_regex(url: str, key: str, default: T = None) -> str | T:
    search_re = rf"(?:%3F|\?|%26|&){key}=(?P<param>[a-zA-Z0-9]+)(?!(?:&|%26))"

    match = re.search(search_re, url)
    if match:
        return match["param"]
    return default


def get_url_param_parse(url: str, key: str, default: T = None) -> str | T:
    parsed = urlparse(url)
    param = parse_qs(parsed.query).get(key, [])
    if param:
        return param[0]
    return default


def get_url_param_from_a(anchor: Tag, key: str, default: T = None) -> str | T:
    # print("anchor: ", anchor)
    url_list = anchor.get_attribute_list("href")
    # print("url_list: ", url_list)
    if not url_list:
        return default

    url = url_list[0]
    # print("url: ", url)
    if not url:
        return default

    param = get_url_param_parse(url, key)
    # print("param_ps: ", param)
    if param:
        return param

    param = get_url_param_regex(url, key)
    # print("param_re: ", param)
    if param:
        return param

    return default


def get_postdate(raw_src: Tag) -> datetime:
    time_obj = raw_src.select_one(DATE_SELECTOR)
    assert time_obj

    dt_attr = time_obj.get_attribute_list("datetime")
    assert dt_attr
    dt_attr = dt_attr[0]

    postdate = datetime.fromisoformat(dt_attr)  # already UTC
    return postdate


def get_post_text(raw_src: Tag) -> str:
    # blockquotes are replies to previously existing content
    # in a small number of cases, the reply preserves an otherwise deleted message
    blockquotes = raw_src.select("blockquote")
    for elem in blockquotes:
        elem.decompose()

    codeblocks = raw_src.select("div.codebox")
    for elem in codeblocks:
        code = elem.get_text("\n")
        p = Tag(name="p")
        p.string = f"```\n{code}\n```"
        _ = elem.replace_with(p)

    text = raw_src.get_text("\n")
    return text


class ForumFetcher(FileFetcher):
    platform: Platform = {
        "_id": KnownPlatforms.Forum.value,
        "name": KnownPlatforms.Forum.name,
    }
    __seen: set[int] = set()

    @override
    def get_files(self) -> Generator[Tag, None, None]:
        for root, _, files in os.walk(self.root):
            for filename in files:
                if not filename.startswith("viewtopic.php"):
                    continue

                data = try_load_html_file(os.path.join(root, filename))
                if not data:
                    continue

                # there are, at most, 10 posts per page
                # the content isn't going anywhere, so this is fine
                posts = data.select(POST_SELECTOR, limit=10)
                if not posts:
                    continue

                yield from posts

    @override
    def get_community(self, raw_src: Tag) -> Community:
        name = YAHOO_GROUP_NAME

        postdate = get_postdate(raw_src)
        if postdate >= MOVE_DATE:
            name = FORUM_NAME

        community: Community = {
            "_id": fake_id(name),
            "name": name,
            "platform": self.platform,
        }
        return community

    @override
    def get_author(self, raw_msg: Tag) -> Author:
        author_obj = raw_msg.select_one(AUTHOR_SELECTOR)
        assert author_obj, (raw_msg, author_obj)  # TODO: smarter
        author_name = author_obj.text  # name is always present
        assert author_name, (raw_msg, author_obj, author_name)

        author_id = fake_id(author_name)

        author: Author = {
            "_id": author_id,
            "name": author_name,
            "platform": self.platform,
            # there are bots but resp doesn't tell us
            "is_bot": False,
            "is_webhook": False,
        }

        u_param = get_url_param_from_a(author_obj, "u")
        if not u_param:
            return author

        author_id = int(u_param)
        author["_id"] = author_id
        return author

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for post in self.get_files():

            post_id_obj = post.select_one(POST_ID_SELECTOR)
            assert post_id_obj, (post, post_id_obj)

            p_param = get_url_param_from_a(post_id_obj, "p")
            assert p_param, (post, post_id_obj, p_param)
            assert p_param.isnumeric(), p_param
            _id = int(p_param)

            if _id in self.__seen:
                continue
            self.__seen.add(_id)

            author = self.get_author(post)
            community = self.get_community(post)
            postdate = get_postdate(post)

            post_content_obj = post.select_one(CONTENT_SELECTOR)
            assert post_content_obj, (post, _id, post_content_obj)

            content = get_post_text(post_content_obj)

            message: PreMessage = {
                "_id": _id,
                "content": content,
                "container": NULL_CONTAINER,
                "community": community,
                "author": author,
                "postdate": postdate,
            }

            yield message
