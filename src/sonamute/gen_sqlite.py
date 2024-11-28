# STL
import os
import shutil
from typing import Any, Literal
from datetime import UTC, datetime
from contextlib import asynccontextmanager

# PDM
import aiosqlite
from aiosqlite.core import Connection
from aiosqlite.cursor import Cursor

# LOCAL
from sonamute.db import MessageDB
from sonamute.utils import batch_iter, epochs_in_range, months_in_range
from sonamute.smtypes import SQLTerm, SQLFrequency

# we insert 4 items per row; max sql variables is 999 for, reasons,
SQLITE_BATCH = 249
SQLITE_POSTPROCESS = "queries/postprocess/"

FreqTable = Literal["monthly"] | Literal["yearly"]


async def configure_sqlite(conn: aiosqlite.Connection):
    _ = await conn.execute("PRAGMA foreign_keys = ON;")
    _ = await conn.execute("PRAGMA synchronous = OFF;")
    _ = await conn.execute("PRAGMA journal_mode = MEMORY;")
    _ = await conn.execute("PRAGMA cache_size = 20000;")
    _ = await conn.execute("PRAGMA page_size = 65536;")

    _ = await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS term (
        id INTEGER NOT NULL,
        len INTEGER NOT NULL,
        text TEXT NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (text)
    );
    """
    )

    _ = await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS monthly (
        term_id INTEGER NOT NULL,
        min_sent_len INTEGER NOT NULL,
        day INTEGER NOT NULL,
        hits INTEGER NOT NULL,
        authors INTEGER NOT NULL,
        PRIMARY KEY (term_id, min_sent_len, day),
        FOREIGN KEY (term_id) REFERENCES term(id)
    ) WITHOUT ROWID;
    """
    )

    _ = await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS yearly (
        term_id INTEGER NOT NULL,
        min_sent_len INTEGER NOT NULL,
        day INTEGER,
        hits INTEGER NOT NULL,
        authors INTEGER NOT NULL,
        PRIMARY KEY (term_id, min_sent_len, day),
        FOREIGN KEY (term_id) REFERENCES term(id)
    ) WITHOUT ROWID;
    """
    )

    _ = await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS total (
        day INTEGER NOT NULL,
        term_len INTEGER NOT NULL,
        min_sent_len INTEGER NOT NULL,
        hits INTEGER NOT NULL,
        authors INTEGER NOT NULL,
        PRIMARY KEY (day, term_len, min_sent_len)
    ) WITHOUT ROWID;
    """
    )

    await conn.commit()


class FreqDB:
    def __init__(self, database_file: str):
        self.db_file: str = database_file
        self.conn: Connection | None = None

    async def __ainit__(self):
        async with self.session() as s:
            await configure_sqlite(s)

    async def close(self):
        if self.conn:
            await self.conn.close()

    @asynccontextmanager
    async def session(self):
        if not self.conn:
            self.conn = await aiosqlite.connect(self.db_file)
        yield self.conn

    async def execute(self, query: str) -> Cursor:
        async with self.session() as s:
            result = await s.execute(query)
            await s.commit()
        return result

    async def upsert_term(self, data: list[SQLTerm]):
        result: list[tuple[str, int]] = []
        async with self.session() as s:
            stmt = """
            INSERT INTO term (len, text) VALUES (:len, :text)
            ON CONFLICT (text) DO UPDATE SET len = len
            RETURNING text, id
            """
            # cursor = await s.executemany(stmt, data)
            # while row := await cursor.fetchone():
            #     rows.append(row)

            # result = await cursor.fetchone()
            # rows.append(result)
            # executemany doesn't support returning..
            for d in data:
                cursor = await s.execute(stmt, d)
                returned = await cursor.fetchone()
                result.append(returned)
            await s.commit()

        term_id_map: dict[str, int] = dict()
        for term, id in result:
            term_id_map[term] = id
        return term_id_map

    async def insert_freq(self, data: list[SQLFrequency], table: FreqTable):
        terms = [d["term"] for d in data]
        term_id_map = await self.upsert_term(terms)
        for d in data:
            d["term_id"] = term_id_map[d["term"]["text"]]
            d.pop("term")  # TODO: typing

        async with self.session() as s:
            stmt = f"""
            INSERT INTO {table} (term_id, min_sent_len, day, hits, authors)
            VALUES (:term_id, :min_sent_len, :day, :hits, :authors)
            """
            _ = await s.executemany(stmt, parameters=data)
            await s.commit()

    async def insert_total(
        self,
        term_len: int,
        min_sent_len: int,
        day: int,
        hits: int,
        authors: int,
        # TODO: should there be an object here
    ):
        async with self.session() as s:
            stmt = """
            INSERT INTO total (day, term_len, min_sent_len, hits, authors)
            VALUES (:day, :term_len, :min_sent_len, :hits, :authors)
            """
            _ = await s.execute(
                stmt,
                {
                    "day": day,
                    "term_len": term_len,
                    "min_sent_len": min_sent_len,
                    "hits": hits,
                    "authors": authors,
                },
            )
            await s.commit()


async def freqdb_factory(database_file: str) -> FreqDB:
    t = FreqDB(database_file=database_file)
    await t.__ainit__()
    return t


async def copy_freqs(
    edb: MessageDB,
    sdb: FreqDB,
    term_len: int,
    min_sent_len: int,
    start: datetime,
    end: datetime,
    table: FreqTable,
):
    # all-time ranking data
    results = await edb.select_frequencies_in_range(
        term_len,
        min_sent_len,
        start,
        end,
        # limit=500,
    )
    # TODO: db interface can do its own batching, because values can
    # be added on later
    for batch in batch_iter(results, SQLITE_BATCH):
        await sdb.insert_freq(batch, table)


async def copy_totals(
    edb: MessageDB,
    sdb: FreqDB,
    term_len: int,
    min_sent_len: int,
    start: datetime,
    end: datetime,
):
    total_hits = await edb.global_hits_in_range(
        term_len,
        min_sent_len,
        start,
        end,
    )
    total_authors = await edb.global_authors_in_range(
        term_len,
        min_sent_len,
        start,
        end,
    )

    start_ts = int(start.timestamp())
    await sdb.insert_total(
        term_len=term_len,
        min_sent_len=min_sent_len,
        day=start_ts,
        hits=total_hits,
        authors=total_authors,
    )


async def generate_sqlite(
    edb: MessageDB,
    filename: str,
    trimmed_filename: str,
    min_date: datetime,
    max_date: datetime,
):
    sdb = await freqdb_factory(filename)
    first_msg_dt, last_msg_dt = await edb.get_msg_date_range()
    if first_msg_dt < min_date:
        first_msg_dt = min_date
    if last_msg_dt > max_date:
        last_msg_dt = max_date

    print("Generating frequency data")
    for term_len in range(1, 7):
        print(f"Starting on term len of {term_len}")
        for min_sent_len in range(term_len, 7):
            print(f"Starting on min sent len of {min_sent_len}")

            print(f"all time (pl {term_len}, msl {min_sent_len})")
            alltime_start = datetime.fromtimestamp(0, tz=UTC)
            await copy_freqs(
                edb,
                sdb,
                term_len,
                min_sent_len,
                alltime_start,
                last_msg_dt,
                "yearly",
            )

            # per-epoch (aug 1-aug 1) ranking data
            # TODO: what if the period is smaller than or significantly offset
            # from the epochs
            for start, end in epochs_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"epoch {start.date()} - {end.date()} (pl {term_len}, msl {min_sent_len})"
                )
                await copy_freqs(
                    edb,
                    sdb,
                    term_len,
                    min_sent_len,
                    start,
                    end,
                    "yearly",
                )

            # periodic frequency data
            for start, end in months_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"period {start.date()} - {end.date()} (pl {term_len}, msl {min_sent_len})"
                )
                await copy_freqs(
                    edb,
                    sdb,
                    term_len,
                    min_sent_len,
                    start,
                    end,
                    "monthly",
                )
                await copy_totals(edb, sdb, term_len, min_sent_len, start, end)
                # The totals table exists to convert absolute hits to percents on the fly

    await sdb.close()
    print("Copying database")
    shutil.copy(filename, trimmed_filename)
    sdb = await freqdb_factory(trimmed_filename)

    for root, _, files in os.walk(SQLITE_POSTPROCESS):
        for file in sorted(files):
            file = os.path.join(root, file)
            print(f"Executing {file}")
            with open(file, "r") as f:
                query = f.read()
            _ = await sdb.execute(query)
    await sdb.close()
