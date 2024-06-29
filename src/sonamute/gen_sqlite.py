# STL
import asyncio
import sqlite3
import argparse
from typing import Generator, TypedDict
from datetime import date, datetime
from contextlib import asynccontextmanager
from collections import Counter

# PDM
from sqlalchemy import (
    Date,
    Enum,
    Text,
    Column,
    String,
    Boolean,
    Integer,
    BigInteger,
    ForeignKey,
    CheckConstraint,
    PrimaryKeyConstraint,
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
from sonamute.db import load_messagedb_from_env
from sonamute.utils import batch_list, days_in_range, epochs_in_range, months_in_range
from sonamute.counters import word_counters_by_min_sent_len

Base = declarative_base()


class WordFreqRow(TypedDict):
    word: str
    min_length: int
    day: datetime  # TODO
    occurrences: int


class PhraseFreqRow(TypedDict):
    phrase: str
    length: int
    day: datetime  # TODO
    occurrences: int


class WordFrequency(Base):
    __tablename__ = "word_freq"

    word = Column(Text, nullable=False)
    min_length = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    occurrences = Column(BigInteger, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("word", "min_length", "day"),)


class PhraseFrequency(Base):
    __tablename__ = "phrase_freq"
    word = Column(Text, nullable=False)
    length = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    occurrences = Column(BigInteger, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("word", "length", "day"),)


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

    async def insert_word(self, data: WordFreqRow | list[WordFreqRow]):
        async with self.session() as s:
            stmt = insert(WordFrequency).values(data)
            _ = await s.execute(stmt)
            await s.commit()

    async def insert_phrase(self, data: PhraseFreqRow | list[PhraseFreqRow]):
        async with self.session() as s:
            stmt = insert(PhraseFrequency).values(data)
            _ = await s.execute(stmt)
            await s.commit()


async def freqdb_factory(database_file: str) -> FreqDB:
    t = FreqDB(database_file=database_file)
    await t.__ainit__()
    return t


def format_insertable_freq(
    counters: dict[int, Counter[str]],
    day: datetime,
) -> list[WordFreqRow]:
    timestamp = int(day.timestamp())
    word_freq_rows: list[WordFreqRow] = list()
    for min_length, counter in counters.items():
        for word, occurrences in counter.items():
            result = WordFreqRow(
                {
                    "day": timestamp,
                    "word": word,
                    "min_length": min_length,
                    "occurrences": occurrences,
                }
            )
            word_freq_rows.append(result)
    return word_freq_rows


async def amain(argv: argparse.Namespace):
    edgedb = load_messagedb_from_env()
    sqlite_db = await freqdb_factory(argv.db)
    first_msg_dt, last_msg_dt = await edgedb.get_msg_date_range()

    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(start)
        result = await edgedb.counted_sents_in_range(start, end)

        counters = word_counters_by_min_sent_len(result, 6)
        formatted = format_insertable_freq(counters, start)
        if formatted:
            for batch in batch_list(formatted, 249):
                # we insert 4 items per row; max sql variables is 999 for, reasons,
                await sqlite_db.insert_word(batch)

        # phrase_lens = [2, 3, 4, 5, 6]
        # for n in phrase_lens:
        #     p = phrase_counter(result, n=n)

        start = end


def main(argv: argparse.Namespace):
    asyncio.run(amain(argv))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    _ = parser.add_argument(
        "--db",
        help="The SQLite DB file to create or update.",
        dest="db",
        required=True,
    )
    ARGV = parser.parse_args()
    main(ARGV)
