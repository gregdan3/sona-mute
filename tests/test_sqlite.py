# STL
import sqlite3
import datetime
from uuid import uuid4

# PDM
import pytest

# LOCAL
from sonamute.types import EDBFrequency
from sonamute.gen_sqlite import Monthly, freqdb_factory

SAMPLE_FREQ: EDBFrequency = {
    "text": "sample",
    "term_len": 1,
    "community": uuid4(),
    "day": 400000,
    "occurrences": 99,
    "authors": [uuid4()],
}


@pytest.mark.asyncio
async def test_happy_path():
    sdb = await freqdb_factory(":memory:?cache=shared")
    await sdb.insert_freq([SAMPLE_FREQ], Monthly)

    sdb_raw = sqlite3.connect(":memory:?cache=shared")
    sdb_raw.execute()
