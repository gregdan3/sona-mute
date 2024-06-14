# STL
from enum import IntEnum
from uuid import UUID
from typing import TypedDict, NotRequired, cast
from datetime import datetime

# PDM
import edgedb
from edgedb import RetryOptions, AsyncIOClient
from async_lru import alru_cache
from edgedb.asyncio_client import AsyncIOIteration


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


class Sentence(TypedDict):
    words: list[str]
    score: NotRequired[float]


class PreMessage(TypedDict):
    _id: int
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    sentences: list[Sentence]  # implicitly the Sentence type


def create_client(username: str, password: str, host: str, port: int) -> AsyncIOClient:
    client = edgedb.create_async_client(
        host=host,
        port=port,
        user=username,
        password=password,
        tls_security="insecure",
        timeout=120,
    )
    client.with_retry_options(options=RetryOptions(attempts=10))
    return client


PLAT_INSERT = """
select (
    INSERT Platform {
        _id := <int64>$_id,
        name := <str>$name,
    } unless conflict on (._id)
else Platform)"""

COMM_INSERT = """
select (
    INSERT Community {
        _id := <int64>$_id,
        name := <str>$name,
        platform := <Platform>$platform,
    } unless conflict on (._id, .platform)
else Community)"""

AUTH_INSERT = """
select (
    INSERT Author {
        _id := <int64>$_id,
        name := <str>$name,
        platform := <Platform>$platform,
    } unless conflict on (._id, .platform)
else Author)
"""

MSG_INSERT = """
INSERT Message {
    _id := <int64>$_id,
    community := <Community>$community,
    container := <int64>$container,
    author := <Author>$author,
    postdate := <std::datetime>$postdate,
    content := <str>$content,
    sentences := { %s },
} unless conflict;
"""
# NOTE: sentences must be subbed in

SENT_INSERT = """(INSERT Sentence {words := <array<str>>%(words)s, score := <float64>%(score)s})"""
# NOTE: would be $sentence, but then we'd have repeat vars


def make_sent_subquery(sentences: list[Sentence]) -> str:
    outputs: list[str] = []
    for s in sentences:
        outputs.append(f"{SENT_INSERT}" % s)
    return ",\n".join(outputs)


class MessageDB:
    client: AsyncIOClient

    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.client = create_client(username, password, host, port)

    # really just some hot dogshit code.
    @alru_cache
    async def __insert_platform(
        self,
        _id: int,
        name: str,
    ) -> UUID:
        # TODO: this type is a little bit incorrect; it's an edgedb Object
        result = await self.client.query_required_single(
            query=PLAT_INSERT,
            _id=_id,
            name=name,
        )
        found_id = cast(UUID, result.id)
        return found_id

    async def insert_platform(self, platform: Platform) -> UUID:
        if isinstance(platform, UUID):
            # insert_platform is called twice so we may mutate platform early
            return platform
        result = await self.__insert_platform(
            _id=platform["_id"],
            name=platform["name"],
        )
        return result

    @alru_cache
    async def __insert_author(
        self,
        _id: int,
        name: str,
        platform: UUID,
    ) -> UUID:
        result = await self.client.query_required_single(
            query=AUTH_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )

        found_id = cast(UUID, result.id)
        return found_id

    async def insert_author(self, author: Author) -> UUID:
        if isinstance(author, UUID):
            return author
        platform_id = await self.insert_platform(author["platform"])
        return await self.__insert_author(
            _id=author["_id"],
            name=author["name"],
            platform=platform_id,
        )

    @alru_cache
    async def __insert_community(
        self,
        _id: int,
        name: str,
        platform: UUID,
    ) -> UUID:
        result = await self.client.query_required_single(
            query=COMM_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )

        found_id = cast(UUID, result.id)
        return found_id

    async def insert_community(
        self,
        community: Community,
    ) -> UUID:
        if isinstance(community, UUID):
            return community
        platform_id = await self.insert_platform(community["platform"])
        return await self.__insert_community(
            # I was ** splatting the dict into this call, but it doesn't work beecause the dicts appear to globally mutate eachother...
            _id=community["_id"],
            name=community["name"],
            platform=platform_id,
        )

    async def __insert_message(
        self,
        _id: int,
        community: UUID,
        author: UUID,
        postdate: datetime,
        content: str,
        sentences: list[Sentence],
        container: int | None = None,
    ):
        sent_subquery = make_sent_subquery(sentences)
        return await self.client.query(
            query=MSG_INSERT % sent_subquery,
            _id=_id,
            community=community,
            author=author,
            postdate=postdate,
            content=content,
            container=container,
        )

    async def insert_message(self, message: Message):
        community_id = await self.insert_community(message["community"])
        author_id = await self.insert_author(message["author"])
        return await self.__insert_message(
            _id=message["_id"],
            author=author_id,
            community=community_id,
            postdate=message["postdate"],
            content=message["content"],
            sentences=message["sentences"],
            container=message.get("container", None),
        )
