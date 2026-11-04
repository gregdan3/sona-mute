# STL
import os
import json
import asyncio
import argparse
from uuid import UUID
from datetime import date, datetime

# PDM
import asyncpg

# LOCAL
from sonamute.db import MessageDB, format_freq_pg, load_messagedb_from_env
from sonamute.cli import SOURCES, menu_handler
from sonamute.log import configure
from sonamute.utils import now, batch_iter, gather_batch, months_in_range
from sonamute.smtypes import (
    ATTRIBUTE_IDS,
    PlatObjKey,
    PreMessage,
    PGFrequency,
    CommSentence,
    StatsCounter,
    SortedSentence,
)
from sonamute.counters import countables, process_msg, get_sentence_stats
from sonamute.constants import MAX_TERM_LEN, MIN_HITS_NEEDED
from sonamute.gen_sqlite import generate_sqlite
from sonamute.sources.generic import NULL_UUID, NULL_INT_ID, PlatformFetcher
from sonamute.log import LOG


async def insert_raw_msg(db: MessageDB, msg: PreMessage) -> None:
    if await db.message_in_db(msg):
        return

    processed = process_msg(msg)
    try:
        await db.insert_message(processed)
    except asyncpg.PostgresError as e:
        LOG.error(msg)
        raise e


def sort_by_community(
    tagged_sents: list[CommSentence],
) -> dict[PlatObjKey, list[SortedSentence]]:
    output: dict[PlatObjKey, list[SortedSentence]] = dict()
    for s in tagged_sents:
        key: PlatObjKey = (s["community"]["id"], s["platform"]["id"])
        if key not in output:
            output[key] = list()
        output[key].append(
            {
                "words": s["words"],
                "author": (s["author"]["id"], s["platform"]["id"]),
            }
        )
    return output


async def source_to_db(db: MessageDB, source: PlatformFetcher, batch_size: int):
    i = 0
    for batch in batch_iter(source.get_messages(), batch_size):
        inserts = [insert_raw_msg(db, msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += len(inserts)
        if i % (batch_size * 100) == 0:
            LOG.info(f"Processed {i} messages @ {now()}")

    LOG.info("Calculating tpt sentences per author...")
    await db.update_author_tpt_sents()

    LOG.info(f"Final total: {i} messages @ {now()}")


def format_stats(
    stats: StatsCounter,
    community_id: UUID = NULL_UUID,
    platform_id: int = NULL_INT_ID,
    day: date | datetime | None = None,
) -> list[PGFrequency]:
    if day is None:
        day = date.fromtimestamp(0)

    output: list[PGFrequency] = list()
    for (term_len, text, attr), item in stats.items():
        formatted = format_freq_pg(
            text=text,
            attr=attr,
            community_id=community_id,
            platform_id=platform_id,
            day=day,
            hits=item["hits"],
            authors=item["authors"],
        )
        output.append(formatted)
    return output


async def db_sents_to_freqs(db: MessageDB, batch_size: int, passing: bool):
    first_msg_dt, last_msg_dt = await db.get_msg_date_range()
    for start, end in months_in_range(first_msg_dt, last_msg_dt):
        LOG.info(f"gen frequency for {start.date()} - {end.date()} @ {now()}")
        result = await db.counted_sents_in_range(start, end, passing)
        by_community = sort_by_community(result)

        for (community_id, platform_id), sents in by_community.items():
            stats = get_sentence_stats(sents, MAX_TERM_LEN)
            formatted = format_stats(stats, community_id, platform_id, start)
            _ = await gather_batch(db.insert_frequency, formatted, batch_size)


def source_sents_to_freqs(source: PlatformFetcher) -> list[PGFrequency]:
    stats = get_sentence_stats(countables(source), MAX_TERM_LEN)
    formatted = format_stats(stats)
    return formatted


def filter_freqs(freqs: list[PGFrequency], min_val: int) -> list[PGFrequency]:
    freqs = [f for f in freqs if f["hits"] >= min_val]
    return freqs


def prep_for_dump(stats: list[PGFrequency]) -> list[dict]:
    output = []
    for f in stats:
        item = {
            "text": f["text"],
            "attr": ATTRIBUTE_IDS[f["attr"]],
            "hits": f["hits"],
            "authors": len(f["authors"]),
        }
        output.append(item)

    output.sort(
        key=lambda f: (
            f["attr"],
            -f["hits"],
            -f["authors"],
        )
    )
    return output


async def amain(argv: argparse.Namespace):
    actions = menu_handler()

    batch_size: int = argv.batch_size
    needs_db = (
        any(source["to_db"] for source in actions["sources"])
        or actions["frequency"]
        or actions["sqlite"]
    )
    db = load_messagedb_from_env() if needs_db else None
    if db:
        _ = await db.get_pool()  # initialize

    try:
        for sourcedata in actions["sources"]:
            platform = sourcedata["source"]
            root = sourcedata["root"]
            to_db = sourcedata["to_db"]
            output = sourcedata["output"]

            source = SOURCES[platform](root)

            LOG.info(f"Fetching {platform} data from {root}")
            if to_db:
                assert db is not None
                await source_to_db(db, source, batch_size)
            else:
                assert output  # cli guarantees it exists
                stats = source_sents_to_freqs(source)
                stats = filter_freqs(stats, MIN_HITS_NEEDED)
                dump_data = prep_for_dump(stats)
                dumped = json.dumps(dump_data, indent=2, ensure_ascii=False)
                with open(output, "w") as f:
                    _ = f.write(dumped)

        if actions["frequency"]:
            LOG.info("Regenerating frequency data")
            assert db is not None
            await db_sents_to_freqs(db, batch_size, True)

        if actions["sqlite"]:
            root = actions["sqlite"]["root"]
            filename = actions["sqlite"]["filename"]
            dbpath = os.path.join(root, filename)
            trimmed_filename = actions["sqlite"]["filename_trimmed"]
            min_date = actions["sqlite"]["min_date"]
            max_date = actions["sqlite"]["max_date"]

            LOG.info(f"Dumping frequency data to {dbpath}")
            assert db is not None
            await generate_sqlite(
                db,
                dbpath,
                trimmed_filename,
                min_date,
                max_date,
                MAX_TERM_LEN,
            )
    finally:
        if db is not None:
            await db.close()


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
    _ = parser.add_argument(
        "--log-level",
        help="Set the log level.",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="INFO",
    )
    ARGV = parser.parse_args()
    configure(ARGV.log_level)
    main(ARGV)
