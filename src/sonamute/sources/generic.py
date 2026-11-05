# STL
from abc import abstractmethod
from uuid import UUID
from typing import Any
from collections.abc import Generator

# LOCAL
from sonamute.log import LOG
from sonamute.utils import int_to_uuid
from sonamute.smtypes import Author, Community, PreMessage
from sonamute.constants import (
    IGNORED_AUTHORS_MAP,
    IGNORED_MESSAGES_MAP,
    IGNORED_CONTAINERS_MAP,
    IGNORED_COMMUNITIES_MAP,
)

NULL_INT_ID = 0
NULL_UUID = int_to_uuid(0)
# I know this is a sin.
# But GelDB is doing that thing where nulls are implicitly omitted from any `filter`,
# even `NOT` filters for which nulls should intuitively match.
# Tacking on an `OR exists` made the query significantly slower,
# so now I'm using 0 for null.
# May god have mercy on my soul.


def is_countable(msg: PreMessage) -> bool:
    platform_id = msg["community"]["platform"]["id"]

    ignored_communities = IGNORED_COMMUNITIES_MAP.get(platform_id, set())
    if msg["community"]["id"].int in ignored_communities:
        return False

    ignored_containers = IGNORED_CONTAINERS_MAP.get(platform_id, set())
    if msg["container"] in ignored_containers:
        return False

    ignored_authors = IGNORED_AUTHORS_MAP.get(platform_id, set())
    if msg["author"]["id"].int in ignored_authors:
        return False

    ignored_messages = IGNORED_MESSAGES_MAP.get(platform_id, {})
    ignored_ranges = ignored_messages.get(msg["container"], [])
    for low_id, high_id in ignored_ranges:
        if low_id <= msg["id"].int and msg["id"].int <= high_id:
            return False

    is_bot = msg["author"]["is_bot"]
    is_webhook = msg["author"]["is_webhook"]
    # TODO: do not count webhook messages once pluralkit messages are processed
    if is_bot and not is_webhook:
        return False
    return True


class PlatformFetcher:
    __seen: set[int]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.__seen = set()

    def seen(self, id: UUID) -> bool:
        if id.int in self.__seen:
            return True
        self.__seen.add(id.int)
        return False

    @abstractmethod
    def get_community(self, raw_src: Any) -> Community: ...

    @abstractmethod
    def get_author(self, raw_msg: Any) -> Author: ...

    @abstractmethod
    def get_message(self, raw_msg: Any) -> PreMessage: ...

    @abstractmethod
    def get_messages(self) -> Generator[PreMessage, None, None]: ...


class FileFetcher(PlatformFetcher):
    root: str

    def __init__(self, root: str):
        super().__init__()
        self.root = root

    @abstractmethod
    def get_files(self) -> Generator[Any, None, None]:
        """Use the specified self.root to fetch and open files"""
