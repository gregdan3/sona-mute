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

# LOCAL
from sonamute.log import LOG
from sonamute.utils import load_envvar
from sonamute.smtypes import (
    ATTRIBUTE_IDS,
    Stats,
    Message,
    Attribute,
    PlatObjKey,
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
                    min_size=20,  # TODO: too much?
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
            LOG.debug("Connected to DB")
            yield conn

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    @alru_cache(maxsize=32)
    async def insert_platform(self, id: int, name: str) -> int:
        query = """
            INSERT INTO platform (id, name)
            VALUES ($1, $2)
            -- ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
            RETURNING id;
        """
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, id, name)
            assert row  # this always succeeds
            return cast(int, row["id"])

    @alru_cache(maxsize=512)
    async def insert_community(
        self,
        id: UUID,
        platform_id: int,
        name: str,
        *args,
        **kwargs,
    ) -> PlatObjKey:
        query = """
            INSERT INTO community (id, platform_id, name)
            VALUES ($1, $2, $3)
            -- ON CONFLICT (id, platform_id) DO UPDATE SET name = COALESCE(EXCLUDED.name, community.name)
            RETURNING id, platform_id;
        """
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, id, platform_id, name)
            assert row
            return cast(UUID, row["id"]), cast(int, row["platform_id"])

    @alru_cache(maxsize=32768)
    async def insert_author(
        self,
        author_id: int,
        platform_id: int,
        name: str,
        is_bot: bool,
        is_webhook: bool,
    ) -> PlatObjKey:
        query = """
            INSERT INTO author (id, platform_id, name, is_bot, is_webhook)
            VALUES ($1, $2, COALESCE($3, ''), $4, $5)
            -- ON CONFLICT (id, platform_id) DO UPDATE SET
                -- name = EXCLUDED.name,
                -- is_bot = EXCLUDED.is_bot,
                -- is_webhook = EXCLUDED.is_webhook
            RETURNING id, platform_id;
        """
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                query,
                author_id,
                platform_id,
                name,
                is_bot,
                is_webhook,
            )
            assert row
            return row["id"], row["platform_id"]

    async def insert_message(self, message: Message) -> None:
        author = message["author"]
        community = message["community"]
        platform = community["platform"]

        platform_id = await self.insert_platform(**platform)
        community_id, _ = await self.insert_community(
            community["id"], platform_id, community["name"]
        )

        author_id, _ = await self.insert_author(
            author["id"],
            platform_id,
            author["name"],
            author["is_bot"],
            author["is_webhook"],
        )

        async with self.acquire() as conn:
            async with conn.transaction():
                msg_row = await conn.fetchrow(
                    """
                    INSERT INTO message (
                        id, platform_id, author_id, community_id, container_id,
                        postdate, content, score, is_counted
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    -- ON CONFLICT (id, platform_id) DO NOTHING
                    RETURNING id;
                    """,
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
                if not msg_row:
                    return

                sentence_ids: dict[tuple[str, ...], int] = {}
                for words in sorted({s["words"] for s in message["sentences"]}):
                    sent_row = await conn.fetchrow(
                        """
                        INSERT INTO sentence (words)
                        VALUES ($1)
                        ON CONFLICT (words) DO NOTHING
                        RETURNING id;
                        """,
                        words,
                    )
                    if sent_row is None:
                        sent_row = await conn.fetchrow(
                            "SELECT id FROM sentence WHERE words = $1;",
                            words,
                        )

                    assert sent_row  # it necessarily exists now
                    sentence_ids[words] = sent_row["id"]

                for idx, sentence in enumerate(message["sentences"]):
                    await conn.execute(
                        """
                        INSERT INTO message_sentence (message_id, platform_id, sentence_id, idx, score)
                        VALUES ($1, $2, $3, $4, $5)
                        -- ON CONFLICT (message_id, platform_id, idx) DO NOTHING;
                        """,
                        message["id"],
                        platform_id,
                        sentence_ids[sentence["words"]],
                        idx,
                        sentence["score"],
                    )

    async def message_in_db(self, message: PreMessage) -> bool:
        platform_id = message["community"].get("platform", {}).get("id", None)
        async with self.acquire() as conn:
            val = await conn.fetchval(
                "SELECT 1 FROM message WHERE id = $1 AND platform_id = $2;",
                message["id"],
                platform_id,
            )
            return val is not None

    async def get_msg_date_range(self) -> tuple[datetime, datetime]:
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT min(postdate) AS min_d, max(postdate) AS max_d FROM message;"
            )
            if not row or row["min_d"] is None or row["max_d"] is None:
                now_dt = datetime.now()
                return now_dt, now_dt
            return row["min_d"], row["max_d"]

    async def refresh_materialized_views(self) -> None:
        async with self.acquire() as conn:
            await conn.execute("REFRESH MATERIALIZED VIEW tp_user_sentence;")
            await conn.execute("REFRESH MATERIALIZED VIEW non_tp_user_sentence;")

    async def counted_sents_in_range(
        self,
        start: datetime,
        end: datetime,
        passing: bool = True,
    ) -> list[CommSentence]:
        view = "tp_user_sentence" if passing else "non_tp_user_sentence"
        query = f"""
            SELECT
                v.words,
                m.community_id,
                m.platform_id,
                m.author_id
            FROM {view} v
            JOIN message m ON m.id = v.message_id AND m.platform_id = v.platform_id
            WHERE m.postdate >= $1 AND m.postdate < $2;
        """
        async with self.acquire() as conn:
            rows = await conn.fetch(query, start, end)
            return [
                CommSentence(
                    words=[w.lower() for w in row["words"]],
                    community_id=row["community_id"],
                    platform_id=row["platform_id"],
                    author_id=row["author_id"],
                )
                for row in rows
            ]

    async def insert_frequency(self, freq: PGFrequency) -> None:
        async with self.acquire() as conn:
            async with conn.transaction():
                # Upsert term (len is generated by the database)
                term_row = await conn.fetchrow(
                    """
                    INSERT INTO term (words)
                    VALUES ($1)
                    -- ON CONFLICT (words) DO UPDATE SET words = EXCLUDED.words
                    RETURNING id;
                    """,
                    freq["words"],
                )
                term_id = term_row["id"]

                # Upsert context
                day_val = (
                    freq["day"] if isinstance(freq["day"], date) else freq["day"].date()
                )
                ctx_row = await conn.fetchrow(
                    """
                    INSERT INTO context (community_id, platform_id, day, attr)
                    VALUES ($1, $2, $3, $4::attribute)
                    -- ON CONFLICT (community_id, platform_id, day, attr)
                    DO UPDATE SET community_id = EXCLUDED.community_id
                    RETURNING id;
                    """,
                    freq["community_id"],
                    freq["platform_id"],
                    day_val,
                    freq["attr"].value,
                )
                context_id = ctx_row["id"]

                # Upsert frequency
                freq_row = await conn.fetchrow(
                    """
                    INSERT INTO frequency (context_id, term_id, hits)
                    VALUES ($1, $2, $3)
                    -- ON CONFLICT (context_id, term_id)
                    DO UPDATE SET hits = frequency.hits + EXCLUDED.hits
                    RETURNING id;
                    """,
                    context_id,
                    term_id,
                    freq["hits"],
                )
                frequency_id = freq_row["id"]

                # Frequency author records
                author_hits: dict[PlatObjKey, int] = {}
                for auth in freq["authors"]:
                    author_hits[auth] = author_hits.get(auth, 0) + 1

                for (author_id, platform_id), a_hits in author_hits.items():
                    await conn.execute(
                        """
                        INSERT INTO frequency_author (frequency_id, author_id, platform_id, hits)
                        VALUES ($1, $2, $3, $4)
                        -- ON CONFLICT (frequency_id, author_id, platform_id)
                        DO UPDATE SET hits = frequency_author.hits + EXCLUDED.hits;
                        """,
                        frequency_id,
                        author_id,
                        platform_id,
                        a_hits,
                    )

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

    async def count_nontrivial_authors(self, authors: Iterable[PlatObjKey]) -> int:
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
            unique_authors: set[PlatObjKey] = {
                (r["author_id"], r["platform_id"]) for r in rows
            }
            return await self.count_nontrivial_authors(unique_authors)

    async def update_author_tpt_sents(self) -> None:
        async with self.acquire() as conn:
            await self.refresh_materialized_views()
            await conn.execute("""
                UPDATE author a
                SET num_sentences = sub.cnt
                FROM (
                    SELECT m.author_id, m.platform_id, COUNT(ms.sentence_id) AS cnt
                    FROM message m
                    JOIN message_sentence ms ON ms.message_id = m.id AND ms.platform_id = m.platform_id
                    WHERE m.is_counted
                    GROUP BY m.author_id, m.platform_id
                ) sub
                WHERE a.id = sub.author_id AND a.platform_id = sub.platform_id;
                """)
            await conn.execute("""
                UPDATE author a
                SET num_tp_sentences = sub.cnt
                FROM (
                    SELECT m.author_id, m.platform_id, COUNT(*) AS cnt
                    FROM tp_user_sentence tp
                    JOIN message m ON m.id = tp.message_id AND m.platform_id = tp.platform_id
                    GROUP BY m.author_id, m.platform_id
                ) sub
                WHERE a.id = sub.author_id AND a.platform_id = sub.platform_id;
                """)
            await conn.execute("""
                UPDATE community c
                SET num_sentences = sub.cnt
                FROM (
                    SELECT m.community_id, m.platform_id, COUNT(ms.sentence_id) AS cnt
                    FROM message m
                    JOIN message_sentence ms ON ms.message_id = m.id AND ms.platform_id = m.platform_id
                    WHERE m.is_counted
                    GROUP BY m.community_id, m.platform_id
                ) sub
                WHERE c.id = sub.community_id AND c.platform_id = sub.platform_id;
                """)
            await conn.execute("""
                UPDATE community c
                SET num_tp_sentences = sub.cnt
                FROM (
                    SELECT m.community_id, m.platform_id, COUNT(*) AS cnt
                    FROM tp_user_sentence tp
                    JOIN message m ON m.id = tp.message_id AND m.platform_id = tp.platform_id
                    GROUP BY m.community_id, m.platform_id
                ) sub
                WHERE c.id = sub.community_id AND c.platform_id = sub.platform_id;
                """)


def format_freq_pg(
    text: str,
    attr: Attribute,
    community_id: UUID,
    platform_id: int,
    day: date | datetime,
    hits: int,
    authors: set[PlatObjKey],
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
