# STL
import asyncio
import argparse
from typing import Literal
from datetime import datetime
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
from sonamute.db import Frequency, load_messagedb_from_env
from sonamute.utils import batch_iter, days_in_range, epochs_in_range, months_in_range

Base = declarative_base()


# class Community(Base):
#     __tablename__ = "community"
#     id: Column(Uuid, primary_key=True, nullable=False)
#     name: Column(Text, nullable=False)


class Phrase(Base):
    # NOTE: misnomer since it will also contain phrases
    __tablename__ = "phrase"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    text = Column(Text, unique=True, nullable=False)


class Freq(Base):
    __tablename__ = "frequency"

    phrase_id = Column(Integer, ForeignKey("phrase.id"), nullable=False)
    # community = Column(Uuid, ForeignKey("community.id"), nullable=False)
    phrase_len = Column(Integer, nullable=False)  # words in text
    min_sent_len = Column(Integer, nullable=False)  # min words in source sentences
    day = Column(Integer, nullable=False)
    occurrences = Column(Integer, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("phrase_id", "phrase_len", "day"),)


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

    async def upsert_word(self, data: list[dict[Literal["text"], str]]):
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

    async def insert_word_freq(self, data: list[Frequency]):
        words: list[dict[Literal["text"], str]] = [{"text": d["text"]} for d in data]
        phrase_id_map = await self.upsert_word(words)
        for d in data:  # TODO: typing
            d["phrase_id"] = phrase_id_map[d["text"]]
            _ = d.pop("text")

        async with self.session() as s:
            stmt = insert(Freq).values(data)
            _ = await s.execute(stmt)
            await s.commit()


async def freqdb_factory(database_file: str) -> FreqDB:
    t = FreqDB(database_file=database_file)
    await t.__ainit__()
    return t


def make_insertable_occurrence(
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


async def amain(argv: argparse.Namespace):
    edgedb = load_messagedb_from_env()
    sqlite_db = await freqdb_factory(argv.db)
    first_msg_dt, last_msg_dt = await edgedb.get_msg_date_range()

    # TODO: parametrize
    phrase_len = 1
    min_sent_len = 1
    is_word = True

    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        # limited to months bc that's much more Sensible:tm:
        print(start)

        result = await edgedb.occurrences_in_range(phrase_len, min_sent_len, start, end)
        formatted = make_insertable_occurrence(
            result,
            phrase_len,
            min_sent_len,
            int(start.timestamp()),
        )
        if not formatted:
            continue

        for batch in batch_iter(formatted, 249):
            # we insert 4 items per row; max sql variables is 999 for, reasons,
            await sqlite_db.insert_word_freq(batch)


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
