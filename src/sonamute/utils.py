# STL
import os
import asyncio
import itertools
from typing import Any, TypeVar, Callable, Coroutine
from datetime import datetime, timedelta
from collections.abc import Iterable, Iterator, Generator

# PDM
import dotenv
from sonatoki.utils import overlapping_ntuples

T = TypeVar("T")

__has_loaded = False


def load_envvar(envvar: str, default: str | None = None) -> str:
    global __has_loaded
    if not __has_loaded:
        __has_loaded = dotenv.load_dotenv()

    val = os.getenv(envvar)
    if val:
        return val
    if default is not None:
        return default
    raise EnvironmentError(f"No {envvar} found in environment!")


def days_in_range(
    start: datetime,
    end: datetime,
) -> Generator[tuple[datetime, datetime], None, None]:
    """
    Provide a date range as a datetime, rounded to every `date` from `start` to `end`, plus a day for coverage.
    """
    start = datetime(start.year, start.month, start.day, tzinfo=start.tzinfo)
    step = start + timedelta(days=1)
    end = datetime.combine(end, datetime.min.time(), tzinfo=end.tzinfo) + timedelta(
        days=1
    )

    while start <= end:
        yield start, step
        start = step
        step += timedelta(days=1)


def ndays_in_range(
    start: datetime,
    end: datetime,
    n: int,
    parity_date: datetime,
) -> Generator[tuple[datetime, datetime], None, None]:
    """
    Generate all pairs of dates `n` days apart which encompass the given start and
    end dates, with `parity_date` as a specifier for what date the range should be
    calculated from.

    "Encompass" means the first returned date will be the closest matching date before
    `start`, and the last returned date will be the closest matching date after `end`.

    The parity date is necessary because the outcome can change depending on what date
    you begin calculating from. For example, if you choose `n=10`, a start date of
    the May 8th, and a parity date of May 1st, you would get May 1st, 11th, 21st, and 31st.

    However, if your parity date were May 5th instead, you would get May 5th, 15th,
    25th, and June 4th.

    Note: If you choose `n` that is divisible by 7 (the length of a week), the resultant
    periods will roughly correspond with patterns of activity, which is valuable for
    interpreting data in a directly comparable way.
    """
    # re-align ranges with given parity date
    realignment_factor = (start - parity_date).days % n
    range_start = start - timedelta(days=realignment_factor)
    delta = timedelta(days=n)

    # ensure encompassing
    if range_start > start:
        range_start -= delta

    range_end = range_start + delta
    while range_start <= end:
        yield range_start, range_end
        range_start = range_end
        range_end += delta


def round_to_next_month(d: datetime) -> datetime:
    if d.month == 12:
        d = datetime(d.year + 1, 1, 1, tzinfo=d.tzinfo)
    else:
        d = datetime(d.year, d.month + 1, 1, tzinfo=d.tzinfo)

    return d


def months_in_range(
    start: datetime,
    end: datetime,
) -> Generator[tuple[datetime, datetime], None, None]:
    """
    Provide datetimes rounded to the start of every month from `start` to `end`, inclusive.
    """
    start = datetime(start.year, start.month, 1, tzinfo=start.tzinfo)
    step = round_to_next_month(start)
    end = round_to_next_month(end)

    while start < end:
        yield start, step
        start = step
        step = round_to_next_month(start)


def round_to_prev_epoch(d: datetime) -> datetime:
    new = datetime(d.year, 8, 1, tzinfo=d.tzinfo)
    if new > d:
        new = datetime(d.year - 1, 8, 1, tzinfo=d.tzinfo)
    return new


def round_to_next_epoch(d: datetime) -> datetime:
    new = datetime(d.year, 8, 1, tzinfo=d.tzinfo)
    if new <= d:
        new = datetime(d.year + 1, 8, 1, tzinfo=d.tzinfo)
    return new


def epochs_in_range(
    start: datetime,
    end: datetime,
) -> Generator[tuple[datetime, datetime], None, None]:
    """Provide datetimes rounded to the start of every epoch, August 1st, such that `start` and `end` are within the given range"""
    start = round_to_prev_epoch(start)
    step = round_to_next_epoch(start)
    end = round_to_next_epoch(end)

    while start < end:
        yield start, step
        start = step
        step = round_to_next_epoch(start)


def batch_iter(iterator: Iterable[T], batch_size: int) -> Iterable[list[T]]:
    it = iter(iterator)
    while True:
        batch = list(itertools.islice(it, batch_size))
        if not batch:
            break
        yield batch


async def gather_batch(
    callable: Callable[[Any], Coroutine[Any, Any, None]],
    to_batch: Iterable[T],
    batch_size: int,
    *args: Any,
    **kwargs: Any,
) -> list[Any]:
    results = list()
    for batch in batch_iter(to_batch, batch_size):
        gatherables = [callable(item, *args, **kwargs) for item in batch]
        result = await asyncio.gather(*gatherables)
        results.extend(result)
    return results


def overlapping_phrases(iterable: Iterable[str], n: int) -> Iterable[str]:
    return [" ".join(item) for item in overlapping_ntuples(iterable, n)]
