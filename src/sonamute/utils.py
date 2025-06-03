# stdlib
import os
import asyncio
import hashlib
import itertools
from uuid import UUID
from typing import Any, TypeVar, Callable, Optional, Iterable, Generator, Coroutine
from datetime import datetime, timedelta

# project deps
import dotenv

T = TypeVar("T")


def load_envvar(envvar: str, default: Optional[str] = None) -> str:
    # load .env vars if not already loaded
    dotenv.load_dotenv(override=False)
    val = os.getenv(envvar)
    if val:
        return val
    if default is not None:
        return default
    raise EnvironmentError(f"{envvar} not found in env")


def fake_id(s: str) -> int:
    # md5 hash -> int
    return int(hashlib.md5(s.encode("utf-8")).hexdigest(), 16)


def fake_uuid(s: str) -> UUID:
    # uuid from hash
    return UUID(int=fake_id(s))


def now() -> str:
    # current time as string
    return datetime.now().strftime("%m-%d %H:%M:%S")


def days_in_range(start: datetime, end: datetime) -> Generator[tuple[datetime, datetime], None, None]:
    # yields (day_start, day_end) from start to end
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    while start < end:
        step = start + timedelta(days=1)
        yield start, step
        start = step


def ndays_in_range(start: datetime, end: datetime, n: int, parity_date: datetime) -> Generator[tuple[datetime, datetime], None, None]:
    # yields n-day windows aligned with parity_date
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end.replace(hour=0, minute=0, second=0, microsecond=0)

    offset = (start - parity_date).days % n
    range_start = start - timedelta(days=offset)
    if range_start > start:
        range_start -= timedelta(days=n)

    while range_start <= end:
        range_end = range_start + timedelta(days=n)
        yield range_start, range_end
        range_start = range_end


def adjust_month(d: datetime, delta: int = 0) -> datetime:
    # shift date by delta months, snap to 1st of month
    total_months = d.year * 12 + d.month - 1 + delta
    year, month = divmod(total_months, 12)
    return datetime(year, month + 1, 1, tzinfo=d.tzinfo)


def months_in_range(start: datetime, end: datetime) -> Generator[tuple[datetime, datetime], None, None]:
    # yields (month_start, month_end) for each month in range
    start = adjust_month(start)
    end = adjust_month(end)

    while start <= end:
        next_month = adjust_month(start, 1)
        yield start, next_month
        start = next_month


def round_to_prev_epoch(d: datetime) -> datetime:
    # snap back to aug 1st of this or previous year
    aug = datetime(d.year, 8, 1, tzinfo=d.tzinfo)
    return aug if d >= aug else datetime(d.year - 1, 8, 1, tzinfo=d.tzinfo)


def round_to_next_epoch(d: datetime) -> datetime:
    # snap forward to aug 1st of this or next year
    aug = datetime(d.year, 8, 1, tzinfo=d.tzinfo)
    return datetime(d.year + 1, 8, 1, tzinfo=d.tzinfo) if d >= aug else aug


def epochs_in_range(start: datetime, end: datetime) -> Generator[tuple[datetime, datetime], None, None]:
    # yields (aug 1, next aug 1) pairs covering range
    start = round_to_prev_epoch(start)
    end = round_to_next_epoch(end)

    while start < end:
        next_epoch = round_to_next_epoch(start)
        yield start, next_epoch
        start = next_epoch


def batch_iter(iterator: Iterable[T], batch_size: int) -> Generator[list[T], None, None]:
    # yields chunks of items of given size
    it = iter(iterator)
    while batch := list(itertools.islice(it, batch_size)):
        yield batch


async def gather_batch(
    func: Callable[[T, Any], Coroutine[Any, Any, Any]],
    items: Iterable[T],
    batch_size: int,
    *args: Any,
    **kwargs: Any,
) -> list[Any]:
    # run func on items in async batches
    results = []
    for batch in batch_iter(items, batch_size):
        coros = [func(item, *args, **kwargs) for item in batch]
        results.extend(await asyncio.gather(*coros))
    return results

