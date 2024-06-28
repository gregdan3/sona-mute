# STL
import os
from typing import Generator
from datetime import date, datetime, timedelta

# PDM
import dotenv

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


def dates_in_range(start: datetime, end: datetime) -> Generator[datetime, None, None]:
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
