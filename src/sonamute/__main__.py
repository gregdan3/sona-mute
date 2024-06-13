# STL
import os
import json
import asyncio
import argparse
from collections import Counter

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import CorpusConfig, IsipinEpikuConfig
from sonatoki.Scorers import Scaling, SoftScaling
from sonatoki.Cleaners import Lowercase, ConsecutiveDuplicates
from sonatoki.Tokenizers import SentTokenizer, WordTokenizer

# LOCAL
from sonamute.db import Message, Sentence, MessageDB
from sonamute.file_io import DiscordFetcher

F = "/home/gregdan3/communities/discord/ma-pona-pi-toki-pona-05-06/"


ignored_authors = {
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

ignored_containers = {
    316066233755631616,  # mapona/jaki
    786041291707777034,  # mapona/ako
}


def main(argv: argparse.Namespace):
    ilo = Ilo(**CorpusConfig)
    ilo._Ilo__scoring_filters[0].tokens -= {"we", "i", "u", "ten", "to"}

    # NOTE: i will need to .lower() all inputs to counters later
    db = MessageDB("edgedb", "DXZnIcATtDoSB3mjgfWrm8I4", "localhost", 10700)
    discord = DiscordFetcher(F)

    # counter: dict[str, int] = Counter()

    i = 0
    for msg in discord.get_messages():
        # TODO: check early to see if the message is in the DB

        if not msg["content"]:
            continue  # ignore empty messages
        if msg["author"]["_id"] in ignored_authors:
            continue
        if msg["container"] in ignored_containers:
            continue

        content = ilo.preprocess(msg["content"])
        sentences: list[Sentence] = []
        for sentence in SentTokenizer.tokenize(content):
            processed, tokenized, filtered, cleaned, score, result = ilo._is_toki_pona(
                sentence
            )
            if cleaned:  # omit empty sentences
                sentences.append(Sentence(words=cleaned))

        final_msg: Message = {**msg, "sentences": sentences}

        try:
            msg_uuid = db.insert_message(final_msg)
        except Exception as e:
            print(msg)
            print(repr(msg))
            raise (e)
        i += 1

        if i % 10000 == 0:
            print("Processed %s messages" % i)

    print("Final total: %s messages" % i)

    # sorted_counter = {
    #     k: v
    #     for k, v in sorted(counter.items(), key=lambda i: i[1], reverse=True)
    #     if v > 100
    # }
    # print(json.dumps(sorted_counter, indent=2, ensure_ascii=False))


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
