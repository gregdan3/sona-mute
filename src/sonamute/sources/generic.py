# STL
from abc import abstractmethod
from typing import Any
from collections.abc import Generator

# LOCAL
from sonamute.smtypes import Author, Community, PreMessage, KnownPlatforms

NULL_CONTAINER = 0
NULL_AUTHOR = 0
# I know this is a sin.
# But EdgeDB is doing that thing where nulls are implicitly omitted from any `filter`,
# even `NOT` filters for which nulls should intuitively match.
# Tacking on an `OR exists` made the query significantly slower,
# so now I'm using 0 for null.
# May god have mercy on my soul.

IGNORED_CONTAINERS_MAP = {
    KnownPlatforms.Discord.value: {
        316066233755631616,  # mapona/jaki
        786041291707777034,  # mapona/ako
        895303838662295572,  # maponasewi/tokinanpa; this is a pluralkit user.
        1128714905932021821,  # mamusi/ako
        1187212477155528804,  # mapona/toki-suli/musitokipiantesitelenwan
    }
}

IGNORED_AUTHORS_MAP = {
    KnownPlatforms.Discord.value: {
        937872123085602896,  # old wikipesija logger
        1074390249981096047,  # wikipesija logger
        1135620786183491725,  # old ma musi minecraft logger
        1135634171734261830,  # ma musi minecraft logger
        1213156131006845020,  # sona.pona.la logger
        950311805845139506,  # "o sitelen lon lipu sina"
    }
}


def is_countable(msg: PreMessage) -> bool:
    platform_id = msg["community"]["platform"]["_id"]
    ignored_containers = IGNORED_CONTAINERS_MAP.get(platform_id, set())
    if msg["container"] in ignored_containers:
        return False

    ignored_authors = IGNORED_AUTHORS_MAP.get(platform_id, set())
    if msg["author"]["_id"] in ignored_authors:
        return False

    is_bot = msg["author"]["is_bot"]
    is_webhook = msg["author"]["is_webhook"]
    # TODO: do not count webhook messages once pluralkit messages are processed
    if is_bot and not is_webhook:
        return False
    return True


class PlatformFetcher:
    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

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
        self.root = root
        super().__init__()

    @abstractmethod
    def get_files(self) -> Generator[Any, None, None]:
        """Use the specified self.root to fetch and open files"""
