# STL
import json
from enum import IntEnum
from uuid import UUID
from typing import TypedDict, cast
from datetime import datetime
from collections import Counter

# PDM
import edgedb
from edgedb import RetryOptions, AsyncIOClient
from async_lru import alru_cache

# LOCAL
from sonamute.utils import load_envvar
from sonamute.file_io import EdgeDBEncoder


class KnownPlatforms(IntEnum):
    Other = 0  # unsortable

    Discord = 1  # supported
    Telegram = 2  # supported
    # Facebook = 3
    Reddit = 4  # supported
    YouTube = 5  # supported
    # Twitter = 6
    # Instagram = 7
    # Tumblr = 8
    # Mastodon = 9
    # Forum = 100  # generic
    # NOTE: includes Yahoo Groups, kulupu.pona.la, and forums.tokipona.org

    # Publication = 200  # generic
    # NOTE: includes lipu Wikipesija, lipu tenpo, lipu kule

    # Personal = 300


class Platform(TypedDict):
    _id: int
    name: str


class Community(TypedDict):
    _id: int
    name: str
    platform: Platform


class Author(TypedDict):
    _id: int
    name: str | None
    platform: Platform
    is_bot: bool
    is_webhook: bool


class Sentence(TypedDict):
    words: list[str]
    score: float


class CommSentence(TypedDict):
    words: list[str]
    community: UUID
    # author: UUID


class PreMessage(TypedDict):
    _id: int
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    sentences: list[Sentence]


class Frequency(TypedDict):
    text: str
    phrase_len: int
    min_sent_len: int
    community: UUID
    day: datetime
    occurrences: int


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
select Platform filter ._id = <int16>$_id
"""

COMM_SELECT = """
select Community filter ._id = <bigint>$_id and .platform = <Platform>$platform
"""

MSG_SELECT = """
select Message filter ._id = <bigint>$_id and .community = <Community>$community
"""

# author := .message.author.id, 
USER_SENTS_SELECT = """
SELECT %s { community := .message.community.id, words } FILTER
    .message.postdate >= <std::datetime>$start AND
    .message.postdate < <std::datetime>$end
"""
PASSING_USER_SENTS_SELECT = USER_SENTS_SELECT % "TPUserSentence"
FAILING_USER_SENTS_SELECT = USER_SENTS_SELECT % "NonTPUserSentence"


# needs to merge across communities
FREQ_SELECT = """
with
  F := (
    select Frequency {text := .phrase.text}
    filter
      .phrase.length = <int16>$phrase_len
      and .min_sent_len = <int16>$min_sent_len
      and .day >= <std::datetime>$start
      and .day < <std::datetime>$end
  ),
  groups := (
    group F {text, occurrences}
    using text := .text
    by text
  )
  select groups {
    text := .key.text,
    total := sum(.elements.occurrences)
  } order by .total desc
"""

GLOBAL_FREQ_SELECT = """
with
  F := (
    select Frequency {occurrences}
    filter
      .phrase.length = <int16>$phrase_len
      and .min_sent_len = <int16>$min_sent_len
      and .day >= <std::datetime>$start
      and .day < <std::datetime>$end
  ) select sum(F.occurrences);
"""

PLAT_INSERT = """
select (
    INSERT Platform {
        _id := <int16>$_id,
        name := <str>$name,
    } unless conflict on (._id)
else Platform)"""

COMM_INSERT = """
select (
    INSERT Community {
        _id := <bigint>$_id,
        name := <str>$name,
        platform := <Platform>$platform,
    } unless conflict on (._id, .platform)
else Community)"""

AUTH_INSERT = """
select (
    INSERT Author {
        _id := <bigint>$_id,
        name := <optional str>$name,
        platform := <Platform>$platform,
        is_bot := <bool>$is_bot,
        is_webhook := <bool>$is_webhook,
    } unless conflict on (._id, .name, .platform)
else Author)"""

MSG_INSERT = """
select (
    INSERT Message {
        _id := <bigint>$_id,
        community := <Community>$community,
        container := <bigint>$container,
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

FREQ_INSERT = """
INSERT Frequency {
    phrase := (
        INSERT Phrase {
            text := <str>$text,
            length := <int16>$phrase_len,
        } unless conflict on (.text)
        else (Phrase)
    ),
    community := <Community>$community,
    min_sent_len := <int16>$min_sent_len,
    day := <datetime>$day,
    occurrences := <int64>$occurrences,
} unless conflict on (.phrase, .community, .min_sent_len, .day)
else (update Frequency set { occurrences := <int64>$occurrences });
"""
BULK_FREQ_INSERT = """
WITH raw_data := <json>$data,
FOR freq IN json_array_unpack(raw_data) union (
    INSERT Frequency {
        text := <str>freq['text'],
        community := <Community><uuid>freq['community'],
        phrase_len := <int16>freq['phrase_len'],
        min_sent_len := <int16>freq['min_sent_len'],
        day := <datetime>freq['day'],
        occurrences := <int64>freq['occurrences'],
    } unless conflict on (.text, .min_sent_len, .community, .day)
    else (update Frequency set { occurrences := <int64>freq['occurrences'] }));
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

    async def insert_platform(
        self,
        platform: Platform,
    ) -> UUID:
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
        is_bot: bool,
        is_webhook: bool,
        platform: UUID,
    ) -> UUID:
        result = await self.client.query_required_single(
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
        author: Author,
    ) -> UUID:
        if isinstance(author, UUID):
            return author
        platform_id = await self.insert_platform(author["platform"])
        return await self.__insert_author(
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

    async def __insert_sentence(
        self,
        message: UUID,
        words: list[str],
        score: float,
    ):
        _ = await self.client.query(
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
        _id: int,
        community: UUID,
        author: UUID,
        postdate: datetime,
        content: str,
        sentences: list[Sentence],
        container: int | None = None,
    ):
        result = await self.client.query_single(
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
                message=found_id,
                words=sentence["words"],
                score=sentence["score"],
            )
        return found_id

    async def insert_message(self, message: Message):
        community_id = await self.insert_community(message["community"])
        author_id = await self.insert_author(message["author"])
        message_id = await self.__insert_message(
            _id=message["_id"],
            author=author_id,
            community=community_id,
            postdate=message["postdate"],
            content=message["content"],
            sentences=message["sentences"],
            container=message.get("container", None),
        )

    async def insert_frequency(self, freq: Frequency):
        _ = await self.client.query(FREQ_INSERT, **freq)

    async def insert_frequencies(self, freqs: list[Frequency]):
        data = json.dumps(freqs, cls=EdgeDBEncoder)
        _ = await self.client.query(BULK_FREQ_INSERT, data=data)

    ###########################
    async def get_msg_date_range(self) -> tuple[datetime, datetime]:
        """Fetch the earliest and latest date of any message in the DB. Return as a pair `(start, end,)`."""
        min_date = await self.client.query_required_single(
            "SELECT min(Message.postdate)"
        )
        max_date = await self.client.query_required_single(
            "SELECT max(Message.postdate)"
        )
        return min_date, max_date

    async def message_in_db(self, msg: PreMessage) -> bool:
        maybe_id = await self.select_message(msg)
        return not not maybe_id

    async def counted_sents_in_range(
        self,
        start: datetime,
        end: datetime,
        passing: bool = True,
    ) -> list[CommSentence]:
        query = FAILING_USER_SENTS_SELECT
        if passing:
            query = PASSING_USER_SENTS_SELECT

        results = await self.client.query(query, start=start, end=end)
        output: list[CommSentence] = list()

        for result in results:
            out: CommSentence = {
                "words": [word.lower() for word in result.words],
                "community": result.community,
                # "author": result.author,
            }
            output.append(out)
        return output

    async def occurrences_in_range(
        self,
        phrase_len: int,
        min_sent_len: int,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        # word: str | None = None,
    ) -> list[Frequency]:
        query = FREQ_SELECT
        if limit:
            query = FREQ_SELECT + f" limit {limit}"

        results = await self.client.query(
            query,
            phrase_len=phrase_len,
            min_sent_len=min_sent_len,
            start=start,
            end=end,
        )
        formatted = make_sqlite_frequency(
            results,
            phrase_len,
            min_sent_len,
            int(start.timestamp()),
        )
        return formatted

    async def global_occurrences_in_range(
        self,
        phrase_len: int,
        min_sent_len: int,
        start: datetime,
        end: datetime,
        # word: str | None = None,
    ) -> int:
        results = await self.client.query_required_single(
            GLOBAL_FREQ_SELECT,
            phrase_len=phrase_len,
            min_sent_len=min_sent_len,
            start=start,
            end=end,
        )
        # result should be just an integer
        return results


def make_edgedb_frequency(
    counter: Counter[str],
    community: UUID,
    phrase_len: int,
    min_sent_len: int,
    day: datetime,
) -> list[Frequency]:
    word_freq_rows: list[Frequency] = list()
    for text, occurrences in counter.items():
        result = Frequency(
            {
                "text": text,
                "community": community,
                "phrase_len": phrase_len,
                "min_sent_len": min_sent_len,
                "day": day,
                "occurrences": occurrences,
            }
        )
        word_freq_rows.append(result)
    return word_freq_rows


def make_sqlite_frequency(
    data, phrase_len: int, min_sent_len: int, day: int
) -> list[Frequency]:
    output: list[Frequency] = list()
    for item in data:
        d: Frequency = {
            # NOTE: this is intently reduced from EdgeDB's Frequency
            "text": item.text,
            "occurrences": item.total,
            "phrase_len": phrase_len,
            "min_sent_len": min_sent_len,
            "day": day,
        }
        output.append(d)
    return output


def load_messagedb_from_env() -> MessageDB:
    username = load_envvar("EDGEDB_USER")
    password = load_envvar("EDGEDB_PASS")
    host = load_envvar("EDGEDB_HOST")
    port = int(load_envvar("EDGEDB_PORT"))
    DB = MessageDB(username, password, host, port)
    return DB
