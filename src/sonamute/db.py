# STL
import asyncio
from typing import cast
from uuid import UUID
from datetime import date, datetime
from contextlib import asynccontextmanager
from collections.abc import Iterable, AsyncGenerator

# PDM
import asyncpg
from async_lru import alru_cache

from sonamute.smtypes import StatsCounter

# LOCAL
from sonamute.log import LOG
from sonamute.utils import load_envvar
from sonamute.smtypes import (
    ATTRIBUTE_IDS,
    Stats,
    Message,
    Attribute,
    Term,
    PreMessage,
    PGFrequency,
    CommSentence,
    SQLFrequency,
)
from sonamute.constants import MIN_HITS_NEEDED, MIN_SENTS_NEEDED


class MessageDB:
    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        database: str,
    ) -> None:
        self.username: str = username
        self.password: str = password
        self.host: str = host
        self.port: int = port
        self.database: str = database
        self.pool: asyncpg.Pool | None = None
        self._pool_lock = asyncio.Lock()

    async def get_pool(self) -> asyncpg.Pool:
        async with self._pool_lock:
            if self.pool is None:
                self.pool = await asyncpg.create_pool(
                    user=self.username,
                    password=self.password,
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    min_size=2,  # TODO: too much?
                    max_size=50,
                    server_settings={
                        "application_name": "sonamute",
                    },
                )
                LOG.debug("Created pool with %s connections", self.pool.get_size())
            return self.pool

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # LOG.debug("Connected to DB")
            yield conn

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _fetchrow(
        self, query: str, *args: UUID | int | bool | str | float | datetime
    ) -> asyncpg.Record | None:
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return row

    async def _fetchrow_req(
        self, query: str, *args: UUID | int | bool | str | float | datetime
    ) -> asyncpg.Record:
        row = await self._fetchrow(query, *args)
        assert row is not None
        return row

    @alru_cache(maxsize=2**6)
    async def insert_platform(self, id: int, name: str) -> int:
        query = """
            INSERT INTO platform (id, name)
            VALUES ($1, $2)
            -- ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id;
        """
        row = await self._fetchrow_req(query, id, name)
        return cast(int, row["id"])

    @alru_cache(maxsize=2**10)
    async def insert_community(self, id: UUID, platform_id: int, name: str) -> int:
        query = """
            INSERT INTO community (orig_id, platform_id, name)
            VALUES ($1, $2, $3)
            -- ON CONFLICT (orig_id, platform_id) DO UPDATE SET name = COALESCE(EXCLUDED.name, community.name)
            RETURNING id;
        """
        row = await self._fetchrow_req(query, id, platform_id, name)
        return cast(int, row["id"])

    @alru_cache(maxsize=2**18)
    async def insert_author(
        self,
        author_id: UUID,
        platform_id: int,
        name: str,
        is_bot: bool,
        is_webhook: bool,
    ) -> int:
        # the above cache misses if the user has changed their name
        # but almost all records do not include a name change,
        # and even those that do will cache anyway to the same result
        query = """
            INSERT INTO author (orig_id, platform_id, name, is_bot, is_webhook)
            VALUES ($1, $2, COALESCE($3, ''), $4, $5)
            ON CONFLICT (orig_id, platform_id) DO UPDATE SET
                orig_id = EXCLUDED.orig_id,
                platform_id = EXCLUDED.platform_id
                -- name = EXCLUDED.name,
                -- is_bot = EXCLUDED.is_bot,
                -- is_webhook = EXCLUDED.is_webhook
            RETURNING id
        """
        row = await self._fetchrow_req(
            query, author_id, platform_id, name, is_bot, is_webhook
        )
        return cast(int, row["id"])

    async def insert_message(self, message: Message) -> None:
        author = message["author"]
        author_id = author["id"]
        community = message["community"]
        platform = community["platform"]

        platform_id = await self.insert_platform(platform["id"], platform["name"])
        community_id = await self.insert_community(
            community["id"], platform_id, community["name"]
        )
        # author_id, _ = await self.author_in_db(author_id, platform_id)
        # if not author_id:
        author_id = await self.insert_author(
            author["id"],
            platform_id,
            author["name"],
            author["is_bot"],
            author["is_webhook"],
        )

        msg_insert = """
        INSERT INTO message (orig_id, platform_id, author_id, community_id, container_id, postdate, content, score, is_counted)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        -- ON CONFLICT (orig_id, platform_id) DO NOTHING
        RETURNING id;
        """
        row = await self._fetchrow_req(
            msg_insert,
            message["id"],
            platform_id,
            author_id,
            community_id,
            message.get("container", 0),
            message["postdate"],
            message["content"],
            message["score"],
            message["is_counted"],
        )
        message_id = cast(int, row["id"])

        sent_insert = """
        INSERT INTO sentence (words)
        VALUES ($1)
        ON CONFLICT (words) DO NOTHING
        RETURNING id
        """
        sent_select = "SELECT id FROM sentence WHERE words = $1"
        sentence_ids: dict[tuple[str, ...], int] = {}
        for words in sorted({s["words"] for s in message["sentences"]}):
            sent_row = await self._fetchrow(sent_insert, words)
            if sent_row is None:
                sent_row = await self._fetchrow_req(sent_select, words)
            sentence_ids[words] = sent_row["id"]

        msg_sent_insert = """
        INSERT INTO message_sentence (message_id, sentence_id, idx, score)
        VALUES ($1, $2, $3, $4)
        -- ON CONFLICT (message_id, idx) DO NOTHING
        """
        for idx, sentence in enumerate(message["sentences"]):
            _ = await self._fetchrow(
                msg_sent_insert,
                message_id,
                sentence_ids[sentence["words"]],
                idx,
                sentence["score"],
            )

    async def message_in_db(self, message: PreMessage) -> int | None:
        query = "SELECT id FROM message WHERE orig_id = $1 AND platform_id = $2"
        row = await self._fetchrow(
            query,
            message["id"],
            message["community"]["platform"]["id"],
        )
        if row:
            return cast(int, row["id"])

    async def author_in_db(self, id: UUID, platform_id: int) -> int | None:
        query = "SELECT id FROM author WHERE orig_id = $1 AND platform_id = $2"
        row = await self._fetchrow(query, id, platform_id)
        if row:
            return cast(int, row["id"])

    async def get_msg_date_range(self) -> tuple[datetime, datetime]:
        query = "SELECT min(postdate) AS min_d, max(postdate) AS max_d FROM message"
        row = await self._fetchrow_req(query)
        return row["min_d"], row["max_d"]

    async def refresh_materialized_views(self) -> None:
        views: tuple[str, ...] = (
            "message_sentence_tp",
            "message_sentence_nontp",
            "author_stats",
            "community_stats",
            "monthly_stats",
            "monthly_community_stats",
            "yearly_stats",
            "yearly_community_stats",
        )
        async with self.acquire() as conn:
            for v in views:
                _ = await conn.execute(f"REFRESH MATERIALIZED VIEW {v};")

    async def counted_sents_in_range(
        self,
        start: datetime,
        end: datetime,
        passing: bool = True,
    ) -> list[CommSentence]:
        view: str = "message_sentence_tp" if passing else "message_sentence_nontp"
        query = f"""
            SELECT
                s.words,
                m.community_id,
                m.author_id
            FROM {view} v
            JOIN message m ON m.id = v.message_id
            JOIN sentence s ON s.id = v.sentence_id
            WHERE m.postdate >= $1 AND m.postdate < $2
            ORDER BY m.community_id, m.author_id
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(query, start, end)
            return [
                CommSentence(
                    words=tuple(w.lower() for w in row["words"]),
                    community_id=row["community_id"],
                    author_id=row["author_id"],
                )
                for row in rows
            ]

    @alru_cache(maxsize=2**16)
    async def insert_term(self, words: Term) -> int:
        query = """
        INSERT INTO term (words)
        VALUES ($1)
        -- ON CONFLICT (words) DO UPDATE SET words = EXCLUDED.words
        RETURNING id;
        """
        row = await self._fetchrow_req(query, words)
        return row["id"]

    @alru_cache(maxsize=2**16)
    async def insert_context(
        self,
        community_id: int,
        day: datetime,
        attr: Attribute,
    ) -> int:
        query = """
        INSERT INTO context (community_id, day, attr)
        VALUES ($1, $2, $3::attribute)
        -- ON CONFLICT (community_id, day, attr) DO UPDATE SET community_id = EXCLUDED.community_id
        RETURNING id;
        """
        row = await self._fetchrow_req(query, community_id, day, attr.value)
        return row["id"]

    @alru_cache(maxsize=2**16)
    async def insert_context_author(
        self,
        context_id: int,
        author_id: int,
    ) -> int:
        query = """
        INSERT INTO context_author (context_id, author_id)
        VALUES ($1, $2)
        -- ON CONFLICT (context_id, author_id) DO UPDATE SET context_id = EXCLUDED.context_id
        RETURNING id;
        """
        row = await self._fetchrow_req(
            query,
            context_id,
            author_id,
        )
        return row["id"]

    async def insert_frequencies(
        self,
        community_id: int,
        day: datetime,
        stats: StatsCounter,
    ):
        pass

    async def insert_frequency(
        self,
        words: Term,
        day: datetime,
        community_id: int,
        author_id: int,
        attr: Attribute,
        hits: int,
    ) -> None:
        term_id = await self.insert_term(words)
        context_id = await self.insert_context(community_id, day, attr)
        context_author_id = await self.insert_context_author(context_id, author_id)

        query = """
        INSERT INTO frequency (context_author_id, term_id, hits)
        VALUES ($1, $2, $3)
        ON CONFLICT (context_author_id, term_id) DO UPDATE SET hits = frequency.hits + EXCLUDED.hits
        """

        async with self.acquire() as conn:
            await conn.execute(query, context_author_id, term_id, hits)

    @alru_cache(maxsize=16384)
    async def is_author_counted(self, author_id: int, platform_id: int) -> bool:
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM author
                WHERE id = $1 AND platform_id = $2 AND num_tp_sentences >= $3;
                """,
                author_id,
                platform_id,
                MIN_SENTS_NEEDED,
            )
            return row is not None

    async def count_nontrivial_authors(self, authors: Iterable[int]) -> int:
        counted_authors = 0
        for author_id, platform_id in authors:
            if await self.is_author_counted(author_id, platform_id):
                counted_authors += 1
        return counted_authors

    async def select_freqs_in_range(
        self,
        term_len: int,
        attr: Attribute,
        start: datetime,
        end: datetime,
    ) -> list[SQLFrequency]:
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end

        query = f"""
            SELECT
                array_to_string(t.words, ' ') AS text,
                f.hits,
                fa.author_id,
                fa.platform_id
            FROM frequency f
            JOIN context c ON c.id = f.context_id
            JOIN term t ON t.id = f.term_id
            LEFT JOIN frequency_author fa ON fa.frequency_id = f.id
            WHERE t.len = $1
              AND c.attr = $2::attribute
              AND c.day >= $3
              AND c.day < $4
              AND (
                  SELECT SUM(f_sub.hits)
                  FROM frequency f_sub
                  WHERE f_sub.term_id = t.id
              ) >= {MIN_HITS_NEEDED};
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(query, term_len, attr.value, start_date, end_date)

        merged: dict[str, Stats] = {}
        for r in rows:
            txt = r["text"]
            if txt not in merged:
                merged[txt] = {"hits": 0, "authors": set()}
            merged[txt]["hits"] += r["hits"]
            if r["author_id"] is not None:
                merged[txt]["authors"].add((r["author_id"], r["platform_id"]))

        output: list[SQLFrequency] = []
        for text, result in merged.items():
            counted_authors = await self.count_nontrivial_authors(result["authors"])
            formatted = format_freq_sqlite(
                text=text,
                attr=attr,
                day=start,
                hits=result["hits"],
                authors=counted_authors,
            )
            output.append(formatted)
        return output

    async def total_hits_in_range(
        self,
        term_len: int,
        attr: Attribute,
        start: datetime,
        end: datetime,
    ) -> int:
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end

        query = f"""
            SELECT COALESCE(SUM(f.hits), 0) AS total_hits
            FROM frequency f
            JOIN context c ON c.id = f.context_id
            JOIN term t ON t.id = f.term_id
            WHERE t.len = $1
              AND c.attr = $2::attribute
              AND c.day >= $3
              AND c.day < $4
              AND (
                  SELECT SUM(f_sub.hits)
                  FROM frequency f_sub
                  WHERE f_sub.term_id = t.id
              ) >= {MIN_HITS_NEEDED};
        """
        async with self.acquire() as conn:
            val = await conn.fetchval(query, term_len, attr.value, start_date, end_date)
            return int(val or 0)

    async def total_authors_in_range(
        self,
        term_len: int,
        attr: Attribute,
        start: datetime,
        end: datetime,
    ) -> int:
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end

        query = f"""
            SELECT DISTINCT fa.author_id, fa.platform_id
            FROM frequency_author fa
            JOIN frequency f ON f.id = fa.frequency_id
            JOIN context c ON c.id = f.context_id
            JOIN term t ON t.id = f.term_id
            WHERE t.len = $1
              AND c.attr = $2::attribute
              AND c.day >= $3
              AND c.day < $4
              AND (
                  SELECT SUM(f_sub.hits)
                  FROM frequency f_sub
                  WHERE f_sub.term_id = t.id
              ) >= {MIN_HITS_NEEDED};
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(query, term_len, attr.value, start_date, end_date)
            unique_authors: set[int] = {
                (r["author_id"], r["platform_id"]) for r in rows
            }
            return await self.count_nontrivial_authors(unique_authors)


def format_freq_pg(
    text: str,
    attr: Attribute,
    community_id: UUID,
    platform_id: int,
    day: date | datetime,
    hits: int,
    authors: set[int],
) -> PGFrequency:
    d = day.date() if isinstance(day, datetime) else day
    return PGFrequency(
        {
            "text": text,
            "words": text.split(),
            "attr": attr,
            "community_id": community_id,
            "platform_id": platform_id,
            "day": d,
            "hits": hits,
            "authors": list(authors),
        }
    )


def format_freq_sqlite(
    text: str,
    attr: Attribute,
    day: datetime,
    hits: int,
    authors: int,
) -> SQLFrequency:
    d: SQLFrequency = {
        "term": {
            "text": text,
            "len": len(text.split()),
        },
        "attr": ATTRIBUTE_IDS[attr],
        "day": int(day.timestamp()),
        "hits": hits,
        "authors": authors,
    }
    return d


def load_messagedb_from_env() -> MessageDB:
    username = load_envvar("POSTGRES_USER", "postgres")
    password = load_envvar("POSTGRES_PASSWORD", "postgres")
    host = load_envvar("POSTGRES_HOST", "localhost")
    port = int(load_envvar("POSTGRES_PORT", "5432"))
    database = load_envvar("POSTGRES_DB", "postgres")
    return MessageDB(username, password, host, port, database)
