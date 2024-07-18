# STL
import os
import asyncio
import argparse
from uuid import UUID
from datetime import datetime
from collections import Counter

# PDM
from edgedb.errors import EdgeDBError

# LOCAL
from sonamute.db import (
    Message,
    Sentence,
    Frequency,
    MessageDB,
    PreMessage,
    CommSentence,
    make_insertable_freqs,
    load_messagedb_from_env,
)
from sonamute.cli import SOURCES, menu_handler
from sonamute.ilo import ILO
from sonamute.utils import T, batch_iter, gather_batch, months_in_range
from sonamute.counters import countables, metacount_frequencies
from sonamute.gen_sqlite import generate_sqlite
from sonamute.sources.generic import PlatformFetcher


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


def sort_by_community(tagged_sents: list[CommSentence]) -> dict[UUID, list[list[str]]]:
    output: dict[UUID, list[list[str]]] = dict()
    for s in tagged_sents:
        if s["community"] not in output:
            output[s["community"]] = list()
        output[s["community"]].append(s["words"])
    return output


async def source_to_db(db: MessageDB, source: PlatformFetcher, batch_size: int):
    i = 0
    for batch in batch_iter(source.get_messages(), batch_size):
        inserts = [insert_raw_msg(db, msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += len(inserts)
        if i % 100000 == 0:
            print("Processed %s messages" % i)

    print("Final total: %s messages" % i)


def metacounter_to_insertable_freqs(
    metacounter: dict[int, dict[int, Counter[str]]], community: UUID, day: datetime
) -> list[Frequency]:
    output: list[Frequency] = list()
    for phrase_len, inner in metacounter.items():
        for min_sent_len, counter in inner.items():
            formatted = make_insertable_freqs(
                counter, community, phrase_len, min_sent_len, day
            )
            output.extend(formatted)

    return output


async def sentences_to_frequencies(db: MessageDB, batch_size: int, passing: bool):
    first_msg_dt, last_msg_dt = await db.get_msg_date_range()
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        # NOTE: I originally used days, but this turned out to be excessive effort and impossible to graph usefully
        print(start)
        result = await db.counted_sents_in_range(start, end, passing)
        by_community = sort_by_community(result)
        # TODO: remove community? ehhhhhh

        for community, sents in by_community.items():
            metacounter = metacount_frequencies(sents, 6, 6)
            formatted = metacounter_to_insertable_freqs(metacounter, community, start)
            _ = await gather_batch(db.insert_frequency, formatted, batch_size)


def source_to_frequencies(source: PlatformFetcher):
    metacounter = metacount_frequencies(countables(source), 6, 6)
    return metacounter


def filter_counter(counter: Counter[T], min_val: int = 40) -> Counter[T]:
    return Counter({k: v for k, v in counter.items() if v >= min_val})


def filter_nested_counter(
    counter: dict[int, dict[int, Counter[T]]], min_val: int
) -> dict[int, dict[int, Counter[T]]]:
    for i, counter_i in counter.items():
        for j, counter_j in counter_i.items():
            counter[i][j] = filter_counter(counter_j, min_val)
    return counter


async def amain(argv: argparse.Namespace):
    actions = menu_handler()

    batch_size: int = argv.batch_size
    db = load_messagedb_from_env()
    for sourcedata in actions["sources"]:
        platform = sourcedata["source"]
        root = sourcedata["root"]
        source = SOURCES[platform](root)

        print(f"Fetching {platform} data from {root}")
        await source_to_db(db, source, batch_size)

    if actions["frequency"]:

        print("Regenerating frequency data")
        await sentences_to_frequencies(db, batch_size, True)

    if actions["sqlite"]:
        root = actions["sqlite"]["root"]
        filename = actions["sqlite"]["filename"]
        dbpath = os.path.join(root, filename)

        print(f"Dumping frequency data to {dbpath}")
        await generate_sqlite(db, dbpath)

    # metacounter = source_to_frequencies(source)
    # metacounter = filter_nested_counter(metacounter, 40)
    # dumped = json.dumps(metacounter, indent=2, ensure_ascii=False)
    # print(dumped)
    print("")


def main(argv: argparse.Namespace):
    asyncio.run(amain(argv))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
