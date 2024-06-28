# STL
import os

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
