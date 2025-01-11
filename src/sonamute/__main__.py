# STL
import os
import json
import asyncio
import argparse
from uuid import UUID
from datetime import datetime
from collections import Counter

# PDM
from edgedb.errors import EdgeDBError

# LOCAL
from sonamute.constants import MAX_MIN_SENT_LEN, MAX_TERM_LEN
from sonamute.db import MessageDB, make_edgedb_frequency, load_messagedb_from_env
from sonamute.cli import SOURCES, menu_handler
from sonamute.ilo import ILO
from sonamute.utils import T, now, batch_iter, gather_batch, months_in_range
from sonamute.smtypes import (
    Message,
    Sentence,
    PreMessage,
    Metacounter,
    CommSentence,
    EDBFrequency,
    SortedSentence,
)
from sonamute.counters import countables, count_frequencies
from sonamute.gen_sqlite import generate_sqlite
from sonamute.sources.generic import PlatformFetcher, is_countable


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
    is_counted = is_countable(msg)
    msg["content"] = clean_string(msg["content"])

    sentences: list[Sentence] = []
    for scorecard in ILO.make_scorecards(msg["content"]):
        if not scorecard["cleaned"]:
            # omit empty sentences
            continue
        sentences.append(
            Sentence(
                words=scorecard["cleaned"],
                score=scorecard["score"],
            )
        )

    # it's okay to have no sentences
    final_msg: Message = {**msg, "sentences": sentences, "is_counted": is_counted}
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


def sort_by_community(
    tagged_sents: list[CommSentence],
) -> dict[UUID, list[SortedSentence]]:
    output: dict[UUID, list[SortedSentence]] = dict()
    for s in tagged_sents:
        if s["community"] not in output:
            output[s["community"]] = list()
        output[s["community"]].append({"words": s["words"], "author": s["author"]})
    return output


async def source_to_db(db: MessageDB, source: PlatformFetcher, batch_size: int):
    i = 0
    for batch in batch_iter(source.get_messages(), batch_size):
        inserts = [insert_raw_msg(db, msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += len(inserts)
        if i % (batch_size * 100) == 0:
            print(f"Processed {i} messages @ {now()}")

    print("Calculating tpt sentences per author...")
    await db.update_author_tpt_sents()

    print(f"Final total: {i} messages @ {now()}")


def counter_to_insertable_freqs(
    metacounter: Metacounter,
    community: UUID,
    day: datetime,
) -> list[EDBFrequency]:
    output: list[EDBFrequency] = list()
    for term_len, inner in metacounter.items():
        for min_sent_len, counter in inner.items():
            formatted = make_edgedb_frequency(
                counter, community, term_len, min_sent_len, day
            )
            output.extend(formatted)

    return output


async def sentences_to_frequencies(db: MessageDB, batch_size: int, passing: bool):
    first_msg_dt, last_msg_dt = await db.get_msg_date_range()
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(f"gen frequency for {start.date()} - {end.date()}")
        result = await db.counted_sents_in_range(start, end, passing)
        by_community = sort_by_community(result)
        # NOTE: community is used behind the scenes; it's probably too
        # identifying and too much to deliver, but i can still derive useful
        # things from it

        for community, sents in by_community.items():
            metacounter = count_frequencies(sents, MAX_TERM_LEN, MAX_MIN_SENT_LEN)
            formatted = counter_to_insertable_freqs(metacounter, community, start)
            _ = await gather_batch(db.insert_frequency, formatted, batch_size)


def source_to_frequencies(source: PlatformFetcher):
    metacounter = count_frequencies(countables(source), MAX_TERM_LEN, MAX_MIN_SENT_LEN)
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
        to_db = sourcedata["to_db"]
        output = sourcedata["output"]

        source = SOURCES[platform](root)

        print(f"Fetching {platform} data from {root}")
        if to_db:
            await source_to_db(db, source, batch_size)
        else:
            assert output  # cli guarantees it exists
            metacounter = source_to_frequencies(source)
            # TODO: this is a bit misleading since i'm really generating frequency data to a file
            metacounter = filter_nested_counter(metacounter, 40)
            dumped = json.dumps(metacounter, indent=2, ensure_ascii=False)
            with open(output, "w") as f:
                _ = f.write(dumped)

    if actions["frequency"]:

        print("Regenerating frequency data")
        await sentences_to_frequencies(db, batch_size, True)

    if actions["sqlite"]:
        root = actions["sqlite"]["root"]
        filename = actions["sqlite"]["filename"]
        dbpath = os.path.join(root, filename)
        trimmed_filename = actions["sqlite"]["filename_trimmed"]
        min_date = actions["sqlite"]["min_date"]
        max_date = actions["sqlite"]["max_date"]

        print(f"Dumping frequency data to {dbpath}")
        await generate_sqlite(db, dbpath, trimmed_filename, min_date, max_date)


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
