# STL
import os
import json
import asyncio
import argparse
import itertools
from uuid import UUID
from typing import TypeVar
from collections import Counter
from collections.abc import Iterable, Generator

# PDM
from sonatoki.ilo import Ilo
from edgedb.errors import EdgeDBError
from sonatoki.utils import overlapping_ntuples
from sonatoki.Configs import CorpusConfig

# LOCAL
from sonamute.db import Message, Sentence, MessageDB, PreMessage
from sonamute.file_io import DiscordFetcher, PlatformFetcher

T = TypeVar("T")

F = "/home/gregdan3/communities/discord/"


IGNORED_CONTAINERS = {
    316066233755631616,  # ma pona/jaki
    786041291707777034,  # ma pona/ako
    1128714905932021821,  # ma musi/ako
    # The acrophobia bot is troublesome, because users trigger it with a phrase in toki pona.
    # Repeated uses push every word in "ilo o ako" up by >10,000 uses, changing their relative rankings even for o.
}
ILO = Ilo(**CorpusConfig)
ILO._Ilo__scoring_filters[0].tokens -= {"we", "i", "u", "ten", "to"}

DB = MessageDB("edgedb", "cmfc5e73nVQB3JfWPWBBuQ4l", "localhost", 10700)
DISCORD = DiscordFetcher(F)


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


def ignorable(msg: PreMessage) -> bool:
    # TODO: make this per-platform?
    if not msg["content"]:
        return True  # ignore empty messages
    if msg["container"] in IGNORED_CONTAINERS:
        return True
    return False


async def in_db(msg: PreMessage) -> bool:
    maybe_id = await DB.select_message(msg)
    return not not maybe_id


def process_msg(msg: PreMessage) -> Message:
    """
    For EdgeDB inserts. Turns a PreMessage into a Message, including all sentences.
    """
    msg["content"] = clean_string(msg["content"])
    content = ILO.preprocess(msg["content"])

    sentences: list[Sentence] = []
    for _, _, cleaned, score, result in ILO._are_toki_pona(content):
        if cleaned:  # omit empty sentences
            sentences.append(Sentence(words=cleaned, score=score))

    # it's okay to have no sentences
    final_msg: Message = {**msg, "sentences": sentences}
    return final_msg


def countable_msgs(
    msgs: Iterable[PreMessage],
    force_pass: bool = False,
) -> Generator[Message, None, None]:
    """
    Prior frequency counting implementation. Yields Messages from PreMessages.
    Filters to passing sentences unless `force_pass` is True.
    """
    for msg in msgs:
        if ignorable(msg):
            continue
        content = ILO.preprocess(msg["content"])

        sentences: list[Sentence] = []
        for _, _, cleaned, score, result in ILO._are_toki_pona(content):
            if cleaned and (result or force_pass):  # omit empty sentences
                sentences.append(Sentence(words=cleaned, score=score))

        if not sentences:
            continue
        final_msg: Message = {**msg, "sentences": sentences}
        yield final_msg


async def insert_raw_msg(msg: PreMessage) -> UUID | None:
    if ignorable(msg):
        return
    if await in_db(msg):
        return

    processed = process_msg(msg)
    try:
        _ = await DB.insert_message(processed)
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


def freq_counter(
    source: PlatformFetcher,
    min_len: int = 0,
    force_pass: bool = False,
    _max: int = 0,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    counted = 0
    for msg in countable_msgs(source.get_messages(), force_pass=force_pass):
        for sentence in msg["sentences"]:
            if len(sentence) < min_len:
                continue
            counter.update([word.lower() for word in sentence["words"]])

        counted += 1
        if _max and counted >= _max:
            break
    return counter


def ngram_counter(
    source: PlatformFetcher,
    n: int,
    force_pass: bool = False,
    _max: int = 0,
) -> Counter[tuple[str, ...]]:
    counter: Counter[tuple[str, ...]] = Counter()
    counted = 0
    for msg in countable_msgs(source.get_messages(), force_pass=force_pass):
        for sentence in msg["sentences"]:
            sentence = [word.lower() for word in sentence["words"]]
            counter.update(overlapping_ntuples(sentence, n=n))

        counted += 1
        if _max and counted >= _max:
            break

    return counter


async def amain(argv: argparse.Namespace):

    # NOTE: i will need to .lower() all inputs to counters later
    # counter = freq_counter(source=DISCORD)
    # counter = ngram_counter(source=DISCORD, n=6)

    # sorted_counter = {
    #     k: v
    #     for k, v in sorted(counter.items(), key=lambda i: i[1], reverse=True)
    #     if v > 100
    # }
    # print(sorted_counter)
    # TODO: json dump tuples as lists
    # print(json.dumps(sorted_counter, indent=2, ensure_ascii=False))
    # exit()

    BATCH_SIZE = 150
    i = 0
    for batch in batch_generator(DISCORD.get_messages(), BATCH_SIZE):
        inserts = [insert_raw_msg(msg) for msg in batch]
        _ = await asyncio.gather(*inserts)

        i += BATCH_SIZE
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
