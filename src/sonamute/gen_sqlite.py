# STL
import asyncio
import argparse
from typing import TypedDict
from contextlib import asynccontextmanager

# PDM
from sqlalchemy import Text, Column, Integer, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.sqlite import Insert as insert

# LOCAL
from sonamute.db import Frequency, MessageDB, load_messagedb_from_env
from sonamute.utils import batch_iter, months_in_range

Base = declarative_base()


# class Community(Base):
#     __tablename__ = "community"
#     id: Column(Uuid, primary_key=True, nullable=False)
#     name: Column(Text, nullable=False)


class Phrase(Base):
    # NOTE: misnomer since it will also contain phrases
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

    __table_args__ = (PrimaryKeyConstraint("phrase_id", "min_sent_len", "day"),)


class Total(Base):
    __tablename__ = "total"
    day = Column(Integer, nullable=False)
    phrase_len = Column(Integer, nullable=False)
    min_sent_len = Column(Integer, nullable=False)
    occurrences = Column(Integer, nullable=False)
    __table_args__ = (PrimaryKeyConstraint("day", "phrase_len", "min_sent_len"),)


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

    async def insert_word_freq(self, data: list[Frequency]):
        words: list[InsertablePhrase] = [
            {"text": d["text"], "len": d["phrase_len"]} for d in data
        ]
        phrase_id_map = await self.upsert_word(words)
        for d in data:  # TODO: typing
            d["phrase_id"] = phrase_id_map[d["text"]]
            _ = d.pop("text")
            _ = d.pop("phrase_len")

        async with self.session() as s:
            stmt = insert(Freq).values(data)
            _ = await s.execute(stmt)
            await s.commit()

    async def insert_total_freq(
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


async def generate_sqlite(edb: MessageDB, filename: str):
    sdb = await freqdb_factory(filename)
    first_msg_dt, last_msg_dt = await edb.get_msg_date_range()

    # limited to months bc that's much more Sensible:tm:
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(start)
        start_ts = int(start.timestamp())
        for phrase_len in range(1, 7):
            for min_sent_len in range(phrase_len, 7):
                result = await edb.occurrences_in_range(
                    phrase_len,
                    min_sent_len,
                    start,
                    end,
                )
                formatted = make_insertable_occurrence(
                    result,
                    phrase_len,
                    min_sent_len,
                    start_ts,
                )

                for batch in batch_iter(formatted, 249):
                    # we insert 4 items per row; max sql variables is 999 for, reasons,
                    await sdb.insert_word_freq(batch)

                total_occurrences = await edb.global_occurrences_in_range(
                    phrase_len,
                    min_sent_len,
                    start,
                    end,
                )
                await sdb.insert_total_freq(
                    phrase_len,
                    min_sent_len,
                    start_ts,
                    total_occurrences,
                )
