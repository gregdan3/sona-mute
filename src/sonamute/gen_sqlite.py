# STL
import os
import shutil
import asyncio
from typing import Any, TypedDict
from datetime import UTC, datetime
from contextlib import asynccontextmanager
from collections.abc import Callable, Coroutine

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
from sonamute.db import Frequency, MessageDB
from sonamute.utils import batch_iter, epochs_in_range, months_in_range

# we insert 4 items per row; max sql variables is 999 for, reasons,
SQLITE_BATCH = 249
SQLITE_POSTPROCESS = "queries/postprocess/"

Base = declarative_base()


# class Community(Base):
#     __tablename__ = "community"
#     id: Column(Uuid, primary_key=True, nullable=False)
#     name: Column(Text, nullable=False)


class Phrase(Base):
    # NOTE: misnomer since it will also contain words
    __tablename__ = "phrase"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    len = Column(Integer, nullable=False)
    text = Column(Text, unique=True, nullable=False)


class Freq(Base):
    __tablename__ = "frequency"

    phrase_id = Column(Integer, ForeignKey("phrase.id"), nullable=False)
    # community = Column(Uuid, ForeignKey("community.id"), nullable=False)
    min_sent_len = Column(Integer, nullable=False)  # min words in source sentences
    day = Column(Integer, nullable=False)
    occurrences = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("phrase_id", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


class Total(Base):
    __tablename__ = "total"
    day = Column(Integer, nullable=False)
    phrase_len = Column(Integer, nullable=False)
    min_sent_len = Column(Integer, nullable=False)
    occurrences = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("phrase_len", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


# identical to Freq but with annual epochs and a special day=0 row
class Ranks(Base):
    __tablename__ = "ranks"
    phrase_id = Column(Integer, ForeignKey("phrase.id"), nullable=False)
    min_sent_len = Column(Integer, nullable=False)
    day = Column(Integer, nullable=True)
    occurrences = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("phrase_id", "min_sent_len", "day"),
        {"sqlite_with_rowid": False},
    )


class InsertablePhrase(TypedDict):
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
        return result

    async def upsert_word(self, data: list[InsertablePhrase]):
        async with self.session() as s:
            stmt = insert(Phrase).values(data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["text"],
                set_={"text": stmt.excluded.text},
            ).returning(Phrase.text, Phrase.id)
            # Can't `do_nothing` because that would return no rows
            result = await s.execute(stmt)
            await s.commit()

        word_id_map: dict[str, int] = dict()
        for word, id in result:
            word_id_map[word] = id
        return word_id_map

    async def insert_freq(self, data: list[Frequency], table: Freq | Ranks):
        words: list[InsertablePhrase] = [
            {"text": d["text"], "len": d["phrase_len"]} for d in data
        ]
        phrase_id_map = await self.upsert_word(words)
        for d in data:  # TODO: typing
            d["phrase_id"] = phrase_id_map[d["text"]]
            _ = d.pop("text")
            _ = d.pop("phrase_len")

        async with self.session() as s:
            stmt = insert(table).values(data)
            _ = await s.execute(stmt)
            await s.commit()

    async def insert_total(
        self,
        phrase_len: int,
        min_sent_len: int,
        day: int,
        occurrences: int,
    ):
        async with self.session() as s:
            stmt = insert(Total).values(
                phrase_len=phrase_len,
                min_sent_len=min_sent_len,
                day=day,
                occurrences=occurrences,
            )
            _ = await s.execute(stmt)
            await s.commit()


async def freqdb_factory(database_file: str) -> FreqDB:
    t = FreqDB(database_file=database_file)
    await t.__ainit__()
    return t


async def batch_insert(
    formatted: list[Frequency],
    callable: Callable[[list[Frequency]], Coroutine[None, None, None]],
) -> None:
    tasks: list[Coroutine[None, None, None]] = []
    for batch in batch_iter(formatted, SQLITE_BATCH):
        tasks.append(callable(batch))
    _ = await asyncio.gather(*tasks)


async def copy_freqs(
    edb: MessageDB,
    sdb: FreqDB,
    phrase_len: int,
    min_sent_len: int,
    start: datetime,
    end: datetime,
    table: Freq | Ranks,
):
    # all-time ranking data
    results = await edb.occurrences_in_range(
        phrase_len,
        min_sent_len,
        start,
        end,
        # limit=500,
    )
    for batch in batch_iter(results, SQLITE_BATCH):
        await sdb.insert_freq(batch, table)


async def copy_totals(
    edb: MessageDB,
    sdb: FreqDB,
    phrase_len: int,
    min_sent_len: int,
    start: datetime,
    end: datetime,
):
    total_occurrences = await edb.global_occurrences_in_range(
        phrase_len,
        min_sent_len,
        start,
        end,
    )
    start_ts = int(start.timestamp())
    await sdb.insert_total(
        phrase_len,
        min_sent_len,
        start_ts,
        total_occurrences,
    )


async def generate_sqlite(
    edb: MessageDB,
    filename: str,
    trimmed_filename: str,
    max_date: datetime,
):
    sdb = await freqdb_factory(filename)
    first_msg_dt, last_msg_dt = await edb.get_msg_date_range()
    if last_msg_dt > max_date:
        last_msg_dt = max_date

    print("Generating frequency data")
    for phrase_len in range(1, 7):
        print(f"Starting on phrase len of {phrase_len}")
        for min_sent_len in range(phrase_len, 7):
            print(f"Starting on min sent len of {min_sent_len}")

            print(f"all time (pl {phrase_len}, msl {min_sent_len})")
            alltime_start = datetime.fromtimestamp(0, tz=UTC)
            await copy_freqs(
                edb, sdb, phrase_len, min_sent_len, alltime_start, last_msg_dt, Ranks
            )

            # per-epoch (aug 1-aug 1) ranking data
            for start, end in epochs_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"epoch {start.date()} - {end.date()} (pl {phrase_len}, msl {min_sent_len})"
                )
                await copy_freqs(edb, sdb, phrase_len, min_sent_len, start, end, Ranks)

            # periodic frequency data
            for start, end in months_in_range(first_msg_dt, last_msg_dt):
                print(
                    f"period {start.date()} - {end.date()} (pl {phrase_len}, msl {min_sent_len})"
                )
                await copy_freqs(edb, sdb, phrase_len, min_sent_len, start, end, Freq)
                await copy_totals(edb, sdb, phrase_len, min_sent_len, start, end)
                # The totals table exists to convert absolute occurrences to percents on the fly

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
