# STL
from enum import IntEnum
from uuid import UUID
from typing import TypedDict
from datetime import datetime
from functools import cache

# PDM
import edgedb
from edgedb import Client, RetryOptions


class KnownPlatforms(IntEnum):
    Other = 0
    Discord = 1
    Telegram = 2
    Reddit = 3
    Forum = 4
    Publication = 5
    Twitter = 6


class Platform(TypedDict):
    _id: int
    name: str


class Community(TypedDict):
    _id: int
    name: str
    platform: Platform


class Author(TypedDict):
    _id: int
    name: str
    platform: Platform


class PreMessage(TypedDict):
    _id: int
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    # _id: int
    # community: Community
    # container: int
    # author: Author
    # postdate: datetime
    # content: str
    sentences: list[list[str]]  # implicitly the Sentence type


def build_url(username: str, password: str, host: str, port: int) -> str:
    return f"edgedb://{username}:{password}@{host}:{port}"


def create_client(username: str, password: str, host: str, port: int) -> Client:
    url = build_url(username, password, host, port)
    client = edgedb.create_client(
        dsn=url,
        tls_security="insecure",
        timeout=10000,
    )
    client.with_retry_options(options=RetryOptions(attempts=5))
    return client


PLAT_INSERT = """
INSERT Platform {
    _id := <int64>$_id,
    name := <str>$name,
}
"""

COMM_INSERT = """
INSERT Community {
    _id := <int64>$_id,
    name := <str>$name,
    platform := <Platform>$platform,
}
"""

AUTH_INSERT = """
INSERT Author {
    _id := <int64>$_id,
    name := <str>$name,
    platform := <Platform>$platform,
}
"""

MSG_INSERT = """
INSERT Message {
    _id := <int64>$_id,
    community := <Community>$community_id,
    container := <int64>$container,
    author := <Author>$author_id,
    postdate := <std::datetime>$postdate,
    content := <str>$content,
    %s
}
"""  # NOTE: sentences must be subbed in

SENT_INSERT = """INSERT Sentence {words = <array<str>>%s}"""
# NOTE: would be $sentence, but then we'd have repeat vars


def make_sent_subquery(sentences: list[list[str]]) -> str:
    outputs: list[str] = []
    for s in sentences:
        outputs.append(SENT_INSERT % s)
    return ",\n".join(outputs)


class MessageDB:
    client: Client

    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.client = create_client(username, password, host, port)

    # really just some hot dogshit code.
    @cache
    def __insert_platform(self, _id: int, name: str) -> UUID:
        result = self.client.query(
            query=PLAT_INSERT,
            _id=_id,
            name=name,
        )
        return result

    def insert_platform(self, platform: Platform) -> UUID:
        return self.__insert_platform(**platform)

    @cache
    def __insert_author(self, _id: int, name: str, platform: UUID) -> UUID:
        result = self.client.query(
            query=AUTH_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )
        return result

    def insert_author(self, author: Author) -> UUID:
        platform_id = self.insert_platform(author["platform"])
        author["platform"] = platform_id
        return self.__insert_author(**author)

    @cache
    def __insert_community(self, _id: int, name: str, platform: UUID) -> UUID:
        result = self.client.query(
            query=COMM_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )
        return result

    def insert_community(self, community: Community) -> UUID:
        platform_id = self.insert_platform(community["platform"])
        community["platform"] = platform_id
        return self.__insert_community(**community)

    def __insert_message(
        self,
        _id: int,
        community: UUID,
        author: UUID,
        postdate: datetime,
        content: str,
        sentences: list[list[str]],
        container: int | None = None,
    ) -> UUID:
        sent_subquery = make_sent_subquery(sentences)
        return self.client.query(
            query=MSG_INSERT % sent_subquery,
            _id=_id,
            community=community,
            author=author,
            postdate=postdate,
            content=content,
            container=container,
        )

    def insert_message(self, message: Message) -> UUID:
        author_id = self.insert_author(message["author"])
        community_id = self.insert_community(message["community"])
        message["author"] = author_id
        message["community"] = community_id
        return self.__insert_message(**message)
