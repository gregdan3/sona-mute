# STL
import asyncio

# PDM
import pytest

# LOCAL
from sonamute.utils import (
    batch_iter,
    gather_batch,
    days_in_range,
    epochs_in_range,
    months_in_range,
)


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
