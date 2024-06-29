# STL
import os
import itertools
from typing import TypeVar
from datetime import datetime, timedelta
from collections.abc import Generator

# PDM
import dotenv

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
    new = datetime(d.year, 8, 8, tzinfo=d.tzinfo)
    if new > d:
        new = datetime(d.year - 1, 8, 8, tzinfo=d.tzinfo)
    return new


def round_to_next_epoch(d: datetime) -> datetime:
    new = datetime(d.year, 8, 8, tzinfo=d.tzinfo)
    if new <= d:
        new = datetime(d.year + 1, 8, 8, tzinfo=d.tzinfo)
    return new


def epochs_in_range(
    start: datetime,
    end: datetime,
) -> Generator[tuple[datetime, datetime], None, None]:
    """Provide datetimes rounded to the start of every epoch, August 8th, such that `start` and `end` are within the given range"""
    start = round_to_prev_epoch(start)
    step = round_to_next_epoch(start)
    end = round_to_next_epoch(end)

    while start < end:
        yield start, step
        start = step
        step = round_to_next_epoch(start)


def batch_generator(
    generator: Generator[T, None, None],
    batch_size: int,
) -> Generator[list[T], None, None]:
    while True:
        batch = list(itertools.islice(generator, batch_size))
        if not batch:
            break
        yield batch


def batch_list(lst: list[T], batch_size: int) -> Generator[list[T], None, None]:
    for i in range(0, len(lst), batch_size):
        yield lst[i : i + batch_size]
