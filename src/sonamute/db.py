# STL
from enum import IntEnum
from uuid import UUID
from typing import TypedDict, cast
from datetime import datetime

# PDM
import edgedb
from edgedb import RetryOptions, AsyncIOClient
from async_lru import alru_cache
from edgedb.asyncio_client import AsyncIOIteration


class KnownPlatforms(IntEnum):
    Other = 0  # unsortable
    Discord = 1
    Telegram = 2
    Facebook = 3
    Reddit = 4
    Twitter = 5
    Instagram = 6
    Tumblr = 7
    YouTube = 8  # somewhat crosses into 'publication'
    # Threads = 9
    # Cohost = 10
    Forum = 100  # generic
    Publication = 200  # generic
    Fediverse = 300


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
    is_bot: bool
    is_webhook: bool


class Sentence(TypedDict):
    words: list[str]
    score: float


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
    client = client.with_retry_options(options=RetryOptions(attempts=25))
    return client


PLAT_SELECT = """
select Platform filter ._id = <int64>$_id
"""

COMM_SELECT = """
select Community filter ._id = <int64>$_id and .platform = <Platform>$platform
"""

MSG_SELECT = """
select Message filter ._id = <int64>$_id and .community = <Community>$community
"""


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
        is_bot := <bool>$is_bot,
        is_webhook := <bool>$is_webhook,
    } unless conflict on (._id, .platform)
    else (
        UPDATE Author
        SET {
            is_bot := <bool>$is_bot,
            is_webhook := <bool>$is_webhook
        }
    )
)
"""

MSG_INSERT = """
select (
    INSERT Message {
        _id := <int64>$_id,
        community := <Community>$community,
        container := <int64>$container,
        author := <Author>$author,
        postdate := <std::datetime>$postdate,
        content := <str>$content
    } unless conflict on (._id, .community))
"""

SENT_INSERT = """
INSERT Sentence {
    message := <Message>$message, 
    words := <array<str>>$words,
    score := <float64>$score
}
"""


class MessageDB:
    client: AsyncIOClient

    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.client = create_client(username, password, host, port)

    @alru_cache
    async def __select_platform(self, _id: int) -> UUID | None:
        result = await self.client.query_single(PLAT_SELECT, _id=_id)
        if not result:
            return
        return cast(UUID, result.id)

    async def select_platform(self, platform: Platform) -> UUID | None:
        return await self.__select_platform(_id=platform["_id"])

    @alru_cache
    async def __insert_platform(
        self,
        tx: AsyncIOIteration,
        _id: int,
        name: str,
    ) -> UUID:
        # TODO: this type is a little bit incorrect; it's an edgedb Object
        result = await tx.query_required_single(
            query=PLAT_INSERT,
            _id=_id,
            name=name,
        )
        found_id = cast(UUID, result.id)
        return found_id

    async def insert_platform(
        self,
        tx: AsyncIOIteration,
        platform: Platform,
    ) -> UUID:
        if isinstance(platform, UUID):
            # insert_platform is called twice so we may mutate platform early
            return platform
        result = await self.__insert_platform(
            tx=tx,
            _id=platform["_id"],
            name=platform["name"],
        )
        return result

    @alru_cache
    async def __insert_author(
        self,
        tx: AsyncIOIteration,
        _id: int,
        name: str,
        is_bot: bool,
        is_webhook: bool,
        platform: UUID,
    ) -> UUID:
        result = await tx.query_required_single(
            query=AUTH_INSERT,
            _id=_id,
            name=name,
            platform=platform,
            is_bot=is_bot,
            is_webhook=is_webhook,
        )

        found_id = cast(UUID, result.id)
        return found_id

    async def insert_author(
        self,
        tx: AsyncIOIteration,
        author: Author,
    ) -> UUID:
        if isinstance(author, UUID):
            return author
        platform_id = await self.insert_platform(tx, author["platform"])
        return await self.__insert_author(
            tx=tx,
            _id=author["_id"],
            name=author["name"],
            is_bot=author["is_bot"],
            is_webhook=author["is_webhook"],
            platform=platform_id,
        )

    @alru_cache
    async def __select_community(self, _id: int, platform: UUID) -> UUID | None:
        result = await self.client.query_single(COMM_SELECT, _id=_id, platform=platform)
        if not result:
            return
        return cast(UUID, result.id)

    async def select_community(self, community: Community) -> UUID | None:
        platform = await self.select_platform(community["platform"])
        if not platform:
            return
        return await self.__select_community(_id=community["_id"], platform=platform)

    @alru_cache
    async def __insert_community(
        self,
        tx: AsyncIOIteration,
        _id: int,
        name: str,
        platform: UUID,
    ) -> UUID:
        result = await tx.query_required_single(
            query=COMM_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )

        found_id = cast(UUID, result.id)
        return found_id

    async def insert_community(
        self,
        tx: AsyncIOIteration,
        community: Community,
    ) -> UUID:
        if isinstance(community, UUID):
            return community
        platform_id = await self.insert_platform(tx, community["platform"])
        return await self.__insert_community(
            # I was ** splatting the dict into this call, but it doesn't work beecause the dicts appear to globally mutate eachother...
            tx=tx,
            _id=community["_id"],
            name=community["name"],
            platform=platform_id,
        )

    async def __insert_sentence(
        self,
        tx: AsyncIOIteration,
        message: UUID,
        words: list[str],
        score: float,
    ):
        _ = await tx.query(
            query=SENT_INSERT,
            message=message,
            words=words,
            score=score,
        )

    @alru_cache
    async def __select_message(self, _id: int, community: UUID) -> UUID | None:
        result = await self.client.query_single(
            MSG_SELECT,
            _id=_id,
            community=community,
        )
        if not result:
            return
        return cast(UUID, result.id)

    async def select_message(self, message: Message | PreMessage) -> UUID | None:
        community = await self.select_community(message["community"])
        if not community:
            return
        return await self.__select_message(_id=message["_id"], community=community)

    async def __insert_message(
        self,
        tx: AsyncIOIteration,
        _id: int,
        community: UUID,
        author: UUID,
        postdate: datetime,
        content: str,
        sentences: list[Sentence],
        container: int | None = None,
    ):
        result = await tx.query_single(
            query=MSG_INSERT,
            _id=_id,
            community=community,
            author=author,
            postdate=postdate,
            content=content,
            container=container,
        )
        if not result:
            # conflict occurred; message exists, so do not write
            return
        found_id = cast(UUID, result.id)

        for sentence in sentences:
            await self.__insert_sentence(
                tx=tx,
                message=found_id,
                words=sentence["words"],
                score=sentence["score"],
            )
        return found_id

    async def insert_message(self, message: Message):
        async for tx in self.client.transaction():
            async with tx:
                # TX required at message level to not orphan partial inserts when erroring

                community_id = await self.insert_community(tx, message["community"])
                author_id = await self.insert_author(tx, message["author"])
                message_id = await self.__insert_message(
                    tx=tx,
                    _id=message["_id"],
                    author=author_id,
                    community=community_id,
                    postdate=message["postdate"],
                    content=message["content"],
                    sentences=message["sentences"],
                    container=message.get("container", None),
                )
