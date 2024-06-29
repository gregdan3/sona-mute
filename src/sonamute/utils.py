# STL
import os
import itertools
from typing import TypeVar
from datetime import date, datetime, timedelta
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


def days_in_range(start: datetime, end: datetime) -> Generator[datetime, None, None]:
    """
    Provide datetimes rounded to every `date` from `start` to `end`, plus a day for coverage.
    """
    start = datetime.combine(start, datetime.min.time(), tzinfo=start.tzinfo)
    end = datetime.combine(end, datetime.min.time(), tzinfo=end.tzinfo) + timedelta(
        days=1
    )

    while start <= end:
        yield start
        start += timedelta(days=1)


def round_to_next_month(d: datetime) -> datetime:
    if d.month == 12:
        d = datetime(d.year + 1, 1, 1, tzinfo=d.tzinfo)
    else:
        d = datetime(d.year, d.month + 1, 1, tzinfo=d.tzinfo)

    return d


def months_in_range(start: datetime, end: datetime) -> Generator[datetime, None, None]:
    """
    Provide datetimes rounded to the start of every month from `start` to `end`, inclusive.
    """
    start = datetime(start.year, start.month, 1, tzinfo=start.tzinfo)
    end = round_to_next_month(end)

    while start < end:
        yield start
        start = round_to_next_month(start)


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
