# STL
import os
import asyncio
import argparse
from uuid import UUID

# PDM
from edgedb.errors import EdgeDBError

# LOCAL
from sonamute.db import (
    Message,
    Sentence,
    Frequency,
    MessageDB,
    PreMessage,
    load_messagedb_from_env,
)
from sonamute.ilo import ILO
from sonamute.utils import batch_iter, gather_batch, months_in_range
from sonamute.file_io import DiscordFetcher, PlatformFetcher
from sonamute.counters import phrases_by_length, word_counters_by_min_sent_len
from sonamute.gen_sqlite import make_insertable_freq

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
    if await db.message_in_db(msg):
        return

    processed = process_msg(msg)
    try:
        _ = await db.insert_message(processed)
    except EdgeDBError as e:
        print(msg)
        raise (e)


def sort_by_community(tagged_sents: list) -> dict[UUID, list[list[str]]]:
    output: dict[UUID, list[list[str]]] = dict()
    for s in tagged_sents:
        if s.community not in output:
            output[s.community] = list()
        output[s.community].append(s.words)
    return output


async def amain(argv: argparse.Namespace):
    source = SOURCES[argv.platform](argv.dir)

    db = load_messagedb_from_env()
    batch_size: int = argv.batch_size

    for batch in batch_iter(source.get_messages(), batch_size):
        inserts = [insert_raw_msg(db, msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += batch_size
        if i % 100000 == 0:
            print("Processed %s messages" % i)

    print("Final total: %s messages" % i)
    first_msg_dt, last_msg_dt = await db.get_msg_date_range()
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(start)
        result = await db.counted_sents_in_range(start, end)
        by_community = sort_by_community(result)

        for community, sents in by_community.items():
            counters = word_counters_by_min_sent_len(sents, 6)
            formatted = make_insertable_freq(
                counters,
                community,
                start,
                True,
            )
            await gather_batch(db.insert_frequency, formatted, batch_size)

        # phrase_counters = phrases_by_length(result, 6)
        # formatted = make_insertable_freq(phrase_counters, start, False)
        # await gather_batch(insert_freq, formatted, batch_size, db)


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
