# STL
import os
import json
import logging
import argparse
from collections.abc import Generator

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Filters import (
    Numerics,
    Syllabic,
    NimiLinku,
    Alphabetic,
    ProperName,
    Punctuations,
)
from sonatoki.Scorers import SoftScaling
from sonatoki.Cleaners import ConsecutiveDuplicates
from sonatoki.Tokenizers import sent_tokenize_tok, word_tokenize_tok
from sonatoki.Preprocessors import URLs, DiscordEmotes, DiscordChannels, DiscordMentions

F = "/home/gregdan3/communities/discord/ma-pona-pi-toki-pona/"


def fetch_discord_file() -> Generator[dict, None, None]:
    for file in os.listdir(F):
        with open(F + file, "r") as f:
            content = json.loads(f.read())
            yield content


def fetch_discord_msg(content: dict) -> Generator[str, None, None]:
    for m in content.get("messages", []):
        yield m.get("content")


def main(argv: argparse.Namespace):
    ilo = Ilo(
        preprocessors=[URLs, DiscordEmotes, DiscordChannels, DiscordMentions],
        ignoring_filters=[Numerics, Punctuations],
        scoring_filters=[NimiLinku, Syllabic, ProperName, Alphabetic],
        cleaners=[ConsecutiveDuplicates],
        scorer=SoftScaling,
        tokenizer=word_tokenize_tok,
        passing_score=0.8,
    )
    ilo.logging_threshold = 0.799

    for file in fetch_discord_file():
        for msg in fetch_discord_msg(file):
            for sent in sent_tokenize_tok(msg):
                ilo.is_toki_pona(sent)


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

    logging.basicConfig(format=LOG_FORMAT)
    logger = logging.getLogger("sonatoki.ilo")
    logger.setLevel(logging.DEBUG)

    ARGV = parser.parse_args()
    main(ARGV)
