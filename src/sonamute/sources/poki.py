# STL
import os
import re
from typing import TypedDict, NotRequired, cast
from datetime import UTC, date, datetime
from collections.abc import Generator

# PDM
import frontmatter
from typing_extensions import override

# LOCAL
from sonamute.utils import fake_id
from sonamute.smtypes import Author, Platform, Community, PreMessage, KnownPlatforms
from sonamute.sources.generic import NULL_AUTHOR, NULL_CONTAINER, FileFetcher

Frontmatter = TypedDict(
    "Frontmatter",
    {
        "title": str,
        "original-title": NotRequired[str],
        "description": NotRequired[str],
        "authors": list[str],
        "translators": NotRequired[list[str]],
        "date": date,
        "tags": NotRequired[list[str]],
        "license": str,
        "sources": list[str],
        "archives": list[str],
        "preprocessing": str | list[str],
    },
)


def coalesce_postdate(s: str | date) -> datetime:
    if isinstance(s, date):  # Handle `datetime.date` input
        return datetime(s.year, s.month, s.day, tzinfo=UTC)

    if re.match(r"^\d{4}-\d{2}$", s):
        s += "-15"
    elif not re.match(r"^\d{4}-\d{2}-\d{2}$", s):  # Invalid format
        raise ValueError(f"Invalid date: {s}. Expected 'YYYY-mm-dd' or 'YYYY-mm'.")
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=UTC)


class PokiLapoFetcher(FileFetcher):
    platform: Platform = {
        "_id": KnownPlatforms.Publication.value,
        "name": KnownPlatforms.Publication.name,
    }
    __seen: set[int] = set()

    @override
    def get_files(self) -> Generator[frontmatter.Post, None, None]:
        for root, _, files in os.walk(self.root):
            for filename in files:
                # TODO: safety checking?
                if not filename.endswith(".md"):
                    continue

                with open(os.path.join(root, filename), "r") as f:
                    data = frontmatter.loads(f.read())
                    if not data or not data.metadata:
                        continue
                    data.metadata = cast(Frontmatter, data.metadata)
                    if not data.metadata.get("date"):
                        continue
                    if not data.content:
                        continue

                    yield data

    @override
    def get_community(self, raw_src: frontmatter.Post) -> Community:
        return Community(
            {
                "_id": self.platform["_id"],
                "name": self.platform["name"],
                "platform": self.platform,
            }
        )

    @override
    def get_author(self, raw_msg: frontmatter.Post) -> Author:
        # NOTE: this is a concession. i cannot multiple-attribute.
        authors: list[str] = raw_msg.metadata.get("authors", list())
        author_name = ""
        author_id = NULL_AUTHOR
        if authors and authors[0]:
            author_name = authors[0]
            author_id = fake_id(author_name)

        author: Author = {
            "_id": author_id,
            "name": author_name,
            "platform": self.platform,
            "is_bot": False,
            "is_webhook": False,
        }
        return author

    @override
    def get_messages(self) -> Generator[PreMessage, None, None]:
        for msg in self.get_files():
            _id = fake_id(msg.content)

            if _id in self.__seen:
                continue
            self.__seen.add(_id)

            # community is stored with each message
            community = self.get_community(msg)
            author = self.get_author(msg)

            postdate = coalesce_postdate(msg.metadata["date"])

            message: PreMessage = {
                "_id": _id,
                "content": msg.content,
                "container": NULL_CONTAINER,
                "community": community,
                "author": author,
                "postdate": postdate,
            }

            yield message
