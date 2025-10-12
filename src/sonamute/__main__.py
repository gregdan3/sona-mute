# STL
import os
import json
import asyncio
import argparse
from uuid import UUID
from datetime import datetime

# PDM
from gel.errors import EdgeDBError as GelDBError

# LOCAL
from sonamute.db import MessageDB, format_freq_geldb, load_messagedb_from_env
from sonamute.cli import SOURCES, menu_handler
from sonamute.utils import now, fake_uuid, batch_iter, gather_batch, months_in_range
from sonamute.smtypes import (
    ATTRIBUTE_IDS,
    PreMessage,
    CommSentence,
    GelFrequency,
    StatsCounter,
    SortedSentence,
)
from sonamute.counters import countables, process_msg, get_sentence_stats
from sonamute.constants import MAX_TERM_LEN, MIN_HITS_NEEDED
from sonamute.gen_sqlite import generate_sqlite
from sonamute.sources.generic import PlatformFetcher


async def insert_raw_msg(db: MessageDB, msg: PreMessage) -> UUID | None:
    if await db.message_in_db(msg):
        return

    processed = process_msg(msg)
    try:
        _ = await db.insert_message(processed)
    except GelDBError as e:
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


def format_stats(
    stats: StatsCounter,
    community: UUID | None = None,
    day: datetime | None = None,
) -> list[GelFrequency]:
    if community is None:
        community = fake_uuid("")
    if day is None:
        day = datetime.fromtimestamp(0)
    if community or day:
        assert community and day

    output: list[GelFrequency] = list()
    for (term_len, text, attr), item in stats.items():
        formatted = format_freq_geldb(
            text,
            term_len,
            attr,
            community,
            day,
            item["hits"],
            item["authors"],
        )
        output.append(formatted)
    return output


async def db_sents_to_freqs(db: MessageDB, batch_size: int, passing: bool):
    first_msg_dt, last_msg_dt = await db.get_msg_date_range()
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        print(f"gen frequency for {start.date()} - {end.date()}")
        result = await db.counted_sents_in_range(start, end, passing)
        by_community = sort_by_community(result)
        # NOTE: community is used behind the scenes; it's probably too
        # identifying and too much to deliver, but i can still derive useful
        # things from it

        for community, sents in by_community.items():
            stats = get_sentence_stats(sents, MAX_TERM_LEN)
            formatted = format_stats(stats, community, start)
            _ = await gather_batch(db.insert_frequency, formatted, batch_size)


def source_sents_to_freqs(source: PlatformFetcher) -> list[GelFrequency]:
    stats = get_sentence_stats(countables(source), MAX_TERM_LEN)
    stats = format_stats(stats)
    return stats


def filter_freqs(freqs: list[GelFrequency], min_val: int) -> list[GelFrequency]:
    freqs = [f for f in freqs if f["hits"] >= min_val]
    return freqs


def prep_for_dump(stats: list[GelFrequency]) -> list[GelFrequency]:
    for f in stats:
        f["authors"] = len(f["authors"])  # full set would be nonsense
        f["attr"] = ATTRIBUTE_IDS[f["attr"]]  # can't serialize enum
        del f["day"]  # not easy to organize
        del f["community"]  # doesn't do anything

    stats.sort(
        key=lambda f: (
            f["term_len"],  # 1 to n
            f["attr"],  # one for each Attribute member
            -f["hits"],  # highest to lowest
            -f["authors"],  # again highest to lowest
        )
    )
    return stats


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
            stats = source_sents_to_freqs(source)
            stats = filter_freqs(stats, MIN_HITS_NEEDED)
            stats = prep_for_dump(stats)
            # TODO: new function to dump these in a sensible way
            dumped = json.dumps(stats, indent=2, ensure_ascii=False)
            with open(output, "w") as f:
                _ = f.write(dumped)

    if actions["frequency"]:
        print("Regenerating frequency data")
        await db_sents_to_freqs(db, batch_size, True)

    if actions["sqlite"]:
        root = actions["sqlite"]["root"]
        filename = actions["sqlite"]["filename"]
        dbpath = os.path.join(root, filename)
        trimmed_filename = actions["sqlite"]["filename_trimmed"]
        min_date = actions["sqlite"]["min_date"]
        max_date = actions["sqlite"]["max_date"]

        print(f"Dumping frequency data to {dbpath}")
        await generate_sqlite(
            db,
            dbpath,
            trimmed_filename,
            min_date,
            max_date,
            MAX_TERM_LEN,
        )


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
