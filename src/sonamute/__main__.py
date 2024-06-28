# STL
import os
import asyncio
import argparse
import itertools
from uuid import UUID
from typing import TypeVar
from collections.abc import Generator

# PDM
from edgedb.errors import EdgeDBError

# LOCAL
from sonamute.db import (
    Message,
    Sentence,
    MessageDB,
    PreMessage,
    load_messagedb_from_env,
)
from sonamute.ilo import ILO
from sonamute.file_io import DiscordFetcher, PlatformFetcher

T = TypeVar("T")
SOURCES: dict[str, type[PlatformFetcher]] = {"discord": DiscordFetcher}


def clean_string(content: str) -> str:
    """
    EdgeDB-specific string pre-processing.
    I note all changes; none of them are semantic.
    """

    content = content.replace("\xad", "")
    # `\xad` is the discretionary hyphen; optional to print so not semantic
    content = content.replace("\0", "")
    # i have no earthly idea how this could happen; i'm reading json
    return content


async def in_db(db: MessageDB, msg: PreMessage) -> bool:
    maybe_id = await db.select_message(msg)
    return not not maybe_id


def process_msg(msg: PreMessage) -> Message:
    """
    For EdgeDB inserts. Turns a PreMessage into a Message, including all sentences.
    """
    msg["content"] = clean_string(msg["content"])
    content = ILO.preprocess(msg["content"])

    sentences: list[Sentence] = []
    for _, _, cleaned, score, _ in ILO._are_toki_pona(content):
        if cleaned:  # omit empty sentences
            sentences.append(Sentence(words=cleaned, score=score))

    # it's okay to have no sentences
    final_msg: Message = {**msg, "sentences": sentences}
    return final_msg


async def insert_raw_msg(db: MessageDB, msg: PreMessage) -> UUID | None:
    # NOTE: temporarily taken out for author re-write
    if await in_db(db, msg):
        return

    processed = process_msg(msg)
    try:
        _ = await db.insert_message(processed)
    except EdgeDBError as e:
        print(msg)
        raise (e)


def batch_generator(
    generator: Generator[T, None, None],
    batch_size: int,
) -> Generator[list[T], None, None]:
    while True:
        batch = list(itertools.islice(generator, batch_size))
        if not batch:
            break
        yield batch


async def amain(argv: argparse.Namespace):
    source = SOURCES[argv.platform](argv.dir)

    db = load_messagedb_from_env()
    batch_size: int = argv.batch_size

    i = 0
    for batch in batch_generator(source.get_messages(), batch_size):
        inserts = [insert_raw_msg(db, msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += batch_size
        if i % 100000 == 0:
            print("Processed %s messages" % i)

    print("Final total: %s messages" % i)


def main(argv: argparse.Namespace):
    asyncio.run(amain(argv))


if __name__ == "__main__":

    def existing_directory(dir_path: str) -> str:
        if os.path.isdir(dir_path):
            return dir_path
        raise NotADirectoryError(dir_path)

    parser = argparse.ArgumentParser()
    _ = parser.add_argument(
        "--dir",
        help="A directory to fetch data from.",
        dest="dir",
        required=True,
        type=existing_directory,
    )
    _ = parser.add_argument(
        "--platform",
        help="The format of the data, specified by its original platform.",
        dest="platform",
        required=True,
        choices=SOURCES.keys(),
    )
    _ = parser.add_argument(
        "--batch-size",
        help="How many messages to consume at once from the source.",
        dest="batch_size",
        required=False,
        type=int,
        default=150,
    )

    ARGV = parser.parse_args()
    main(ARGV)
