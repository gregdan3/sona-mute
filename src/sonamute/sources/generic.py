# STL
from abc import abstractmethod
from typing import Any
from collections.abc import Generator

# LOCAL
from sonamute.db import Author, Community, PreMessage


class PlatformFetcher:
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
