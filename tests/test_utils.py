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
