import logging

LOG = logging.getLogger("sonamute")


class Formatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def configure(level: int | str = logging.INFO) -> logging.Logger:
    if isinstance(level, str):
        level: int = getattr(logging, level.upper())

    LOG.setLevel(level)
    if not LOG.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(Formatter())
        LOG.addHandler(handler)

    return LOG
