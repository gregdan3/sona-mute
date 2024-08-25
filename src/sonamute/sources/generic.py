# STL
from abc import abstractmethod
from typing import Any
from collections.abc import Generator

# LOCAL
from sonamute.db import Author, Community, PreMessage, KnownPlatforms

NULL_CONTAINER = 0
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
        914305039764426772,  # mapali/wikipesija
        1128714905932021821,  # mamusi/ako
        1187212477155528804,  # mapona/toki-suli/musitokipiantesitelenwan
        895303838662295572,  # maponasewi/tokinanpa
    }
}


def is_countable(msg: PreMessage) -> bool:
    platform_id = msg["community"]["platform"]["_id"]
    ignored_containers = IGNORED_CONTAINERS_MAP.get(platform_id, set())
    if msg["container"] in ignored_containers:
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
