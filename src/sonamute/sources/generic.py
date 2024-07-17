# STL
from abc import abstractmethod
from typing import Any
from collections.abc import Generator

# LOCAL
from sonamute.db import Author, Community, PreMessage

NULL_CONTAINER = 0
# I know this is a sin.
# But EdgeDB is doing that thing where nulls are implicitly omitted from any `filter`,
# even `NOT` filters for which nulls should intuitively match.
# Tacking on an `OR exists` made the query significantly slower,
# so now I'm using 0 for null.
# May god have mercy on my soul.


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
