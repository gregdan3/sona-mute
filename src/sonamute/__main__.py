# STL
import os
import json
import asyncio
import argparse
import itertools
from uuid import UUID
from typing import Any, Generic, TypeVar, final
from collections import Counter
from collections.abc import Generator

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import CorpusConfig
from sonatoki.Scorers import Scaling, SoftScaling
from sonatoki.Cleaners import Lowercase, ConsecutiveDuplicates
from sonatoki.Tokenizers import SentTokenizer, WordTokenizer

# LOCAL
from sonamute.db import Message, Sentence, MessageDB, PreMessage
from sonamute.file_io import DiscordFetcher

T = TypeVar("T")

F = "/home/gregdan3/communities/discord/ma-pona-pi-toki-pona-05-06/"


IGNORED_AUTHORS = {
    159985870458322944,  # mee6
    204255221017214977,  # YAGPDB
    235148962103951360,  # carlbot
    239631525350604801,  # pancake.gg
    242730576195354624,  # autajja
    268478587651358721,  # rss feeder
    302050872383242240,  # disboard
    368362411591204865,  # meljin
    417529406500896779,  # nadeko
    426044472078499851,  # tatsu
    426055530201481236,  # kiwabot
    429305856241172480,  # esmBot
    466378653216014359,  # pluralkit
    507518503813775400,  # ilo pona, ?
    557628352828014614,  # tickets
    585271178180952064,  # colorbot
    633565743103082527,  # discohook
    655390915325591629,  # starboard
    657389259149541386,  # barista
    660591224482168842,  # qbot
    712086611097157652,  # sala na, old sitelen pona bot
    775481703028228096,  # ilo pi musi toki, ?
    790443487912656916,  # ilo musi Ako
    865485974254911518,  # another minecraft bot
    870715447136366662,  # thread watcher
    896482193570938901,  # la zgmii
    901910020701163522,  # linku
    911674351248613426,  # bebberkonnie
    993236979665862806,  # mappo
    1079265734456250439,  # kose kata
    1098442116931272866,  # (my) ilo pi toki pona taso
    1175442172112289923,  # (my) ilo pi kama sona
    1193285230774202370,  # minecraft bot
    189702078958927872,  # erisbot
}

IGNORED_CONTAINERS = {
    316066233755631616,  # mapona/jaki
    786041291707777034,  # mapona/ako
}
ILO = Ilo(**CorpusConfig)
ILO._Ilo__scoring_filters[0].tokens -= {"we", "i", "u", "ten", "to"}

DB = MessageDB("edgedb", "DXZnIcATtDoSB3mjgfWrm8I4", "localhost", 10700)
DISCORD = DiscordFetcher(F)


def clean_string(content: str) -> str:
    """
    EdgeDB-specific string pre-processing.
    I note all changes; none of them are semantic.
    """

    content = content.replace("\xad", "")
    # `\xad` is the discretionary hyphen, which is a character is optional to print
    return content


def ignorable(msg: PreMessage) -> bool:
    # TODO: make this per-platform?
    if not msg["content"]:
        return True  # ignore empty messages
    if msg["author"]["_id"] in IGNORED_AUTHORS:
        return True
    if msg["container"] in IGNORED_CONTAINERS:
        return True
    return False


def process_msg(msg: PreMessage) -> Message:
    msg["content"] = clean_string(msg["content"])
    content = ILO.preprocess(msg["content"])

    sentences: list[Sentence] = []
    for sentence in SentTokenizer.tokenize(content):
        processed, tokenized, filtered, cleaned, score, result = ILO._is_toki_pona(
            sentence
        )
        if cleaned:  # omit empty sentences
            sentences.append(Sentence(words=cleaned, score=score))

    # it's okay to have no sentences
    final_msg: Message = {**msg, "sentences": sentences}
    return final_msg


async def insert_raw_msg(msg: PreMessage) -> UUID | None:
    if ignorable(msg):
        return
    # TODO: check early to see if the message is in the DB

    processed = process_msg(msg)
    try:
        msg_uuid = await DB.insert_message(processed)
        return msg_uuid
    except Exception as e:
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

    # NOTE: i will need to .lower() all inputs to counters later
    # counter: dict[str, int] = Counter()

    BATCH_SIZE = 250
    i = 0
    for batch in batch_generator(DISCORD.get_messages(), BATCH_SIZE):
        inserts = [insert_raw_msg(msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += BATCH_SIZE

        if i % 10000 == 0:
            print("Processed %s messages" % i)

    print("Final total: %s messages" % i)

    # sorted_counter = {
    #     k: v
    #     for k, v in sorted(counter.items(), key=lambda i: i[1], reverse=True)
    #     if v > 100
    # }
    # print(json.dumps(sorted_counter, indent=2, ensure_ascii=False))


def main(argv: argparse.Namespace):
    asyncio.run(amain(argv))


if __name__ == "__main__":

    def existing_directory(dir_path: str) -> str:
        if os.path.isdir(dir_path):
            return dir_path
        raise NotADirectoryError(dir_path)

    parser = argparse.ArgumentParser()
    _ = parser.add_argument(
        "--log-level",
        help="Set the log level",
        type=str.upper,
        dest="log_level",
        default="INFO",
        choices=["NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )

    # LOG_FORMAT = (
    #     "[%(asctime)s] [%(filename)12s:%(lineno)-4s] [%(levelname)8s] %(message)s"
    # )
    LOG_FORMAT = "%(message)s"

    # logging.basicConfig(format=LOG_FORMAT)
    # logger = logging.getLogger("sonatoki.ilo")
    # logger.setLevel(logging.DEBUG)

    ARGV = parser.parse_args()
    main(ARGV)
