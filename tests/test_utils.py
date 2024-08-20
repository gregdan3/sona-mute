# STL
import math
import asyncio
from datetime import datetime

# PDM
import pytest

# LOCAL
from sonamute.utils import (
    batch_iter,
    gather_batch,
    days_in_range,
    ndays_in_range,
    epochs_in_range,
    months_in_range,
)


def test_ndays_in_range():
    start = datetime(2022, 8, 1)
    end = datetime(2024, 8, 31)
    n = 28
    parity_date = datetime(2001, 8, 8)

    r_start = None
    r_end = None
    i = 0
    for r_start, r_end in ndays_in_range(start, end, n, parity_date):
        if i == 0:  # nearest date of proper parity before start
            assert r_start == datetime(2022, 7, 13)

        assert (r_end - r_start).days == n

        i += 1

    # TODO: does this always hold? i don't think so
    assert i == math.ceil((end - start).days / n)


def test_months_in_range():
    start = datetime(2022, 8, 2)
    end = datetime(2024, 8, 30)

    r_start = None
    r_end = None
    i = 0
    for r_start, r_end in months_in_range(start, end):
        if i == 0:
            assert r_start == datetime(2022, 8, 1)

        assert r_start.day == 1
        assert r_end.day == 1
        assert 28 <= (r_end - r_start).days <= 31

        i += 1
    assert r_end == datetime(2024, 9, 1)

    assert i == 25  # one more to be certain of encompassing


def test_batch_list():
    ex = list(range(1, 101))
    batch_size = 10
    for batch in batch_iter(ex, batch_size):
        assert len(batch) == batch_size
        assert batch == sorted(batch)


def test_batch_generator():
    def gen():
        for item in range(1, 101):
            yield item

    batch_size = 10
    for batch in batch_iter(gen(), 10):
        assert len(batch) == batch_size
        assert batch == sorted(batch)


def test_batch_size_mismatch():
    ex = list(range(1, 101))
    batch_size = 17

    batches: list[list[int]] = list()
    for batch in batch_iter(ex, batch_size):
        batches.append(batch)
        assert batch == sorted(batch)

    assert batches[-1][-1] == ex[-1]


def test_batch_iter():
    data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    batch_size = 3
    expected_batches = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]
    result_batches = list(batch_iter(data, batch_size))
    assert (
        result_batches == expected_batches
    ), f"Expected {expected_batches}, but got {result_batches}"
    batch_size = 4
    expected_batches = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10]]
    result_batches = list(batch_iter(data, batch_size))
    assert (
        result_batches == expected_batches
    ), f"Expected {expected_batches}, but got {result_batches}"


@pytest.mark.asyncio
async def test_gather_batch():
    async def square(a: int) -> int:
        await asyncio.sleep(0.025)  #
        return a**2

    ex = list(range(1, 101))
    batch_size = 10

    results = await gather_batch(square, ex, batch_size)
    assert results
    assert len(results) == 100
    assert results == sorted(results)  # because the input was ordered
