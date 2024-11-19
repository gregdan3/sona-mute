# STL
import os
import shutil
from typing import Any, TypedDict
from datetime import UTC, datetime
from contextlib import asynccontextmanager

# PDM
from sqlalchemy import (
    Text,
    Column,
    Result,
    Integer,
    ForeignKey,
    TextClause,
    PrimaryKeyConstraint,
    text,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.sqlite import Insert as insert

# LOCAL
from sonamute.db import MessageDB, SQLFrequency
from sonamute.utils import batch_iter, epochs_in_range, months_in_range

# we insert 4 items per row; max sql variables is 999 for, reasons,
SQLITE_BATCH = 249
SQLITE_POSTPROCESS = "queries/postprocess/"

Base = declarative_base()


# class Community(Base):
#     __tablename__ = "community"
#     id: Column(Uuid, primary_key=True, nullable=False)
#     name: Column(Text, nullable=False)


class Term(Base):
    __tablename__ = "term"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    len = Column(Integer, nullable=False)
    text = Column(Text, unique=True, nullable=False)


class Monthly(Base):
    __tablename__ = "monthly"

    term_id = Column(Integer, ForeignKey("term.id"), nullable=False)
    # community = Column(Uuid, ForeignKey("community.id"), nullable=False)
    min_sent_len = Column(Integer, nullable=False)  # min words in source sentences
    day = Column(Integer, nullable=False)
    hits = Column(Integer, nullable=False)
    authors = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("term_id", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


class Yearly(Base):
    # NOTE: identical to Freq but with annual epochs and a special day=0 row
    __tablename__ = "yearly"
    term_id = Column(Integer, ForeignKey("term.id"), nullable=False)
    min_sent_len = Column(Integer, nullable=False)
    day = Column(Integer, nullable=True)
    hits = Column(Integer, nullable=False)
    authors = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("term_id", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


class Total(Base):
    __tablename__ = "total"
    day = Column(Integer, nullable=False)
    term_len = Column(Integer, nullable=False)
    min_sent_len = Column(Integer, nullable=False)
    hits = Column(Integer, nullable=False)
    authors = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("term_len", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


class InsertableTerm(TypedDict):
    text: str
    len: int


class FreqDB:
    engine: AsyncEngine
    sgen: async_sessionmaker[AsyncSession]

    def __init__(self, database_file: str):
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{database_file}")
        self.sgen = async_sessionmaker(bind=self.engine, expire_on_commit=True)

    async def __ainit__(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        await self.engine.dispose()

    @asynccontextmanager
    async def session(self):
        async with self.sgen() as s:
            yield s

    async def execute(self, query: TextClause) -> Result[Any]:
        async with self.session() as s:
            result = await s.execute(query)
            await s.commit()
        return result

    async def upsert_term(self, data: list[InsertableTerm]):
        async with self.session() as s:
            stmt = insert(Term).values(data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["text"],
                set_={"text": stmt.excluded.text},
            ).returning(Term.text, Term.id)
            # Can't `do_nothing` because that would return no rows
            result = await s.execute(stmt)
            await s.commit()

        term_id_map: dict[str, int] = dict()
        for term, id in result:
            term_id_map[term] = id
        return term_id_map

    async def insert_freq(self, data: list[SQLFrequency], table: Monthly | Yearly):
        words: list[InsertableTerm] = [d["term"] for d in data]
        term_id_map = await self.upsert_term(words)
        for d in data:
            d["term_id"] = term_id_map[d["term"]["text"]]
            d.pop("term")  # TODO: typing

        async with self.session() as s:
            stmt = insert(table).values(data)
            _ = await s.execute(stmt)
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
            stmt = insert(Total).values(
                term_len=term_len,
                min_sent_len=min_sent_len,
                day=day,
                hits=hits,
                authors=authors,
            )
            _ = await s.execute(stmt)
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
    table: Monthly | Yearly,
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
        term_len,
        min_sent_len,
        start_ts,
        total_hits,
        total_authors,
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
                edb, sdb, term_len, min_sent_len, alltime_start, last_msg_dt, Yearly
            )

            # per-epoch (aug 1-aug 1) ranking data
            for start, end in epochs_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"epoch {start.date()} - {end.date()} (pl {term_len}, msl {min_sent_len})"
                )
                await copy_freqs(edb, sdb, term_len, min_sent_len, start, end, Yearly)

            # periodic frequency data
            for start, end in months_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"period {start.date()} - {end.date()} (pl {term_len}, msl {min_sent_len})"
                )
                await copy_freqs(edb, sdb, term_len, min_sent_len, start, end, Monthly)
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
                query = text(f.read())
            _ = await sdb.execute(query)
