# STL
import asyncio
import argparse
from typing import Literal
from contextlib import asynccontextmanager

# PDM
from sqlalchemy import (
    Text,
    Uuid,
    Column,
    Boolean,
    Integer,
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
from sonamute.db import Frequency, make_insertable_freq, load_messagedb_from_env
from sonamute.utils import batch_iter, days_in_range, epochs_in_range, months_in_range
from sonamute.counters import phrases_by_length, word_counters_by_min_sent_len

Base = declarative_base()


# class Community(Base):
#     __tablename__ = "community"
#     id: Column(Uuid, primary_key=True, nullable=False)
#     name: Column(Text, nullable=False)


class Word(Base):
    # NOTE: misnomer since it will also contain phrases
    __tablename__ = "word"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    word = Column(Text, unique=True, nullable=False)


class WordFrequency(Base):
    __tablename__ = "word_freq"

    word_id = Column(Integer, ForeignKey("word.id"), nullable=False)
    # community = Column(Uuid, ForeignKey("community.id"), nullable=False)
    length = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    is_word = Column(Boolean, nullable=False)
    occurrences = Column(Integer, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("word_id", "length", "day", "is_word"),)


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

    async def upsert_word(self, data: list[dict[Literal["word"], str]]):
        async with self.session() as s:
            stmt = insert(Word).values(data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["word"],
                set_={"word": stmt.excluded.word},
            ).returning(Word.word, Word.id)
            # Can't `do_nothing` because it will cause no rows to return
            result = await s.execute(stmt)
            await s.commit()

        word_id_map: dict[str, int] = dict()
        for word, id in result:
            word_id_map[word] = id
        return word_id_map

    async def insert_word_freq(self, data: list[Frequency]):
        words = [{"word": d["word"]} for d in data]
        word_id_map = await self.upsert_word(words)
        for d in data:  # TODO: typing
            d["word_id"] = word_id_map[d["word"]]
            _ = d.pop("word")

        async with self.session() as s:
            stmt = insert(WordFrequency).values(data)
            _ = await s.execute(stmt)
            await s.commit()

        async with self.session() as s:
            stmt = insert(PhraseFrequency).values(data)
            _ = await s.execute(stmt)
            await s.commit()


async def freqdb_factory(database_file: str) -> FreqDB:
    t = FreqDB(database_file=database_file)
    await t.__ainit__()
    return t


async def amain(argv: argparse.Namespace):
    edgedb = load_messagedb_from_env()
    sqlite_db = await freqdb_factory(argv.db)
    first_msg_dt, last_msg_dt = await edgedb.get_msg_date_range()

    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(start)
        result = await edgedb.counted_sents_in_range(start, end, True)

        word_counters = word_counters_by_min_sent_len(result, 6)
        formatted = make_insertable_word_freq(word_counters, start)
        if not formatted:
            continue

        for batch in batch_iter(formatted, 249):
            # we insert 4 items per row; max sql variables is 999 for, reasons,
            await sqlite_db.insert_word_freq(batch)

        phrase_counters = phrases_by_length(result, 6)
        formatted = make_insertable_phrase_freq(phrase_counters, start)
        if not formatted:
            continue
        for batch in batch_iter(formatted, 249):
            await sqlite_db.insert_phrase_freq(batch)


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
