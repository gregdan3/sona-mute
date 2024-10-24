# STL
from uuid import UUID
from typing import cast
from datetime import datetime

# PDM
import edgedb
from edgedb import RetryOptions, AsyncIOClient
from async_lru import alru_cache

# LOCAL
from sonamute.utils import load_envvar
from sonamute.smtypes import (
    Author,
    Message,
    HitsData,
    Platform,
    Sentence,
    Community,
    PreMessage,
    CommSentence,
    EDBFrequency,
    SQLFrequency,
)


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
SELECT %s { community := .message.community.id, author := .message.author.id, words } FILTER
    .message.postdate >= <std::datetime>$start AND
    .message.postdate < <std::datetime>$end
"""
PASSING_USER_SENTS_SELECT = USER_SENTS_SELECT % "TPUserSentence"
FAILING_USER_SENTS_SELECT = USER_SENTS_SELECT % "NonTPUserSentence"
# NOTE: we don't omit sentences based on the number of sentences spoken by the
# author, because it would actually omit a huge amount of meaningful data.
# i chose a line of 20 sentences in order to measure authors who are visibly
# "invested", but for actual occurrence of terms, this would omit a fairly large
# number of sentences- around 50k authors speak between 1 and 19 sentences.


# needs to merge across communities
FREQ_SELECT = """
with
  F := (
    select Frequency {text := .term.text}
    filter
      .term.len = <int16>$term_len
      and .min_sent_len = <int16>$min_sent_len
      and .day >= <std::datetime>$start
      and .day < <std::datetime>$end
  ),
  groups := (
    group F {text, hits, authors}
    using text := .text
    by text
  )
  select groups {
    text := .key.text,
    hits := sum(.elements.hits),
    authors := count(.elements.authors filter count(.tp_sentences) >= 20),
  } order by .hits desc;
"""

GLOBAL_HITS_SELECT = """
with
  F := (
    select Frequency {hits}
    filter
      .term.len = <int16>$term_len
      and .min_sent_len = <int16>$min_sent_len
      and .day >= <std::datetime>$start
      and .day < <std::datetime>$end
  ) select sum(F.hits);
"""

GLOBAL_AUTHORS_SELECT = """
with
  F := (
    select Frequency {authors}
    filter
      .term.len = <int16>$term_len
      and .min_sent_len = <int16>$min_sent_len
      and .day >= <std::datetime>$start
      and .day < <std::datetime>$end
  ) select count(F.authors filter count(.tp_sentences) >= 20);
"""  # this is distinct by default. insane. love it.


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
        content := <str>$content,
        is_counted := <bool>$is_counted
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
with term := (
    INSERT Term {
        text := <str>$text,
        len := <int16>$term_len,
    } unless conflict on (.text)
    else (Term)
)
INSERT Frequency {
    term := (SELECT term),
    community := <Community>$community,
    min_sent_len := <int16>$min_sent_len,
    day := <datetime>$day,
    hits := <int64>$hits,
    authors := (
        SELECT Author FILTER
        .id in array_unpack(<array<uuid>>$authors)
    )
}
"""
FREQ_INSERT_CONFLICT = """
unless conflict on (.term, .community, .min_sent_len, .day)
else (update Frequency set { hits := <int64>$hits });
"""  # TODO: optionally add to FREQ_INSERT


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
        is_counted: bool,
        container: int | None = None,
    ):
        result = await self.client.query_single(
            query=MSG_INSERT,
            _id=_id,
            community=community,
            author=author,
            postdate=postdate,
            content=content,
            is_counted=is_counted,
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
            is_counted=message["is_counted"],
            container=message.get("container", None),
        )

    async def insert_frequency(self, freq: EDBFrequency):
        _ = await self.client.query(FREQ_INSERT, **freq)

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
                "author": result.author,
            }
            output.append(out)
        return output

    async def select_frequencies_in_range(
        self,
        term_len: int,
        min_sent_len: int,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        # word: str | None = None,
    ) -> list[SQLFrequency]:
        query = FREQ_SELECT
        if limit:
            query = FREQ_SELECT + f" limit {limit}"

        results = await self.client.query(
            query,
            term_len=term_len,
            min_sent_len=min_sent_len,
            start=start,
            end=end,
        )
        formatted = make_sqlite_frequency(
            results,
            term_len,
            min_sent_len,
            int(start.timestamp()),
        )
        return formatted

    async def global_hits_in_range(
        self,
        term_len: int,
        min_sent_len: int,
        start: datetime,
        end: datetime,
        # word: str | None = None,
    ) -> int:
        result: int = await self.client.query_required_single(
            GLOBAL_HITS_SELECT,
            term_len=term_len,
            min_sent_len=min_sent_len,
            start=start,
            end=end,
        )

        return result

    async def global_authors_in_range(
        self,
        term_len: int,
        min_sent_len: int,
        start: datetime,
        end: datetime,
        # word: str | None = None,
    ) -> int:
        result: int = await self.client.query_required_single(
            GLOBAL_AUTHORS_SELECT,
            term_len=term_len,
            min_sent_len=min_sent_len,
            start=start,
            end=end,
        )

        return result


def make_edgedb_frequency(
    counter: dict[str, HitsData],
    community: UUID,
    term_len: int,
    min_sent_len: int,
    day: datetime,
) -> list[EDBFrequency]:
    word_freq_rows: list[EDBFrequency] = list()
    for text, hits_data in counter.items():
        result = EDBFrequency(
            {
                "text": text,
                "community": community,
                "term_len": term_len,
                "min_sent_len": min_sent_len,
                "day": day,
                "hits": hits_data["hits"],
                "authors": list(hits_data["authors"]),
                # we track it as a set up to this point
                # but edgedb needs a subscriptable type
            }
        )
        word_freq_rows.append(result)
    return word_freq_rows


def make_sqlite_frequency(
    data,
    term_len: int,
    min_sent_len: int,
    day: int,
) -> list[SQLFrequency]:
    # FIXME: what is the actual type of `data`
    output: list[SQLFrequency] = list()
    for item in data:
        d: SQLFrequency = {
            "term": {
                "text": item.text,
                "len": term_len,
            },
            "min_sent_len": min_sent_len,
            "day": day,
            "hits": item.hits,
            "authors": item.authors,
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
