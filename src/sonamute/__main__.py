# STL
import os
import json
import argparse
from collections import Counter

# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import CorpusConfig
from sonatoki.Filters import Numeric, Punctuation
from sonatoki.Scorers import SoftScaling
from sonatoki.Cleaners import Lowercase, ConsecutiveDuplicates
from sonatoki.Tokenizers import SentTokenizer, WordTokenizer

# LOCAL
from sonamute.db import MessageDB
from sonamute.file_io import fetch_discord

F = "/home/gregdan3/communities/discord/ma-pona-pi-toki-pona-05-06/"

KNOWN_BOTS = ["204255221017214977"]


def main(argv: argparse.Namespace):
    ilo = Ilo(**CorpusConfig)
    # TODO: this is silly.
    # i need a slightly differently cleaned output for counting purposes.
    finalizer = Ilo(
        preprocessors=[],
        ignoring_filters=[Numeric, Punctuation],
        scoring_filters=[],
        cleaners=[Lowercase, ConsecutiveDuplicates],
        scorer=SoftScaling,
        passing_score=0.80,
        word_tokenizer=WordTokenizer,
    )

    db = MessageDB("edgedb", "gU5wfFr5BPzlIgy2blnc38dJ", "localhost", 10700)

    counter: dict[str, int] = Counter()
    no_short: dict[str, int] = Counter()
    for msg in fetch_discord(F):
        msg = ilo.preprocess(msg)  # jump ahead to avoid urls, emotes, references
        for sent in SentTokenizer.tokenize(msg):
            processed, tokenized, filtered, cleaned, score, result = ilo._is_toki_pona(
                sent
            )
            if not filtered:
                continue
            # if result and score < 0.86:
            #     print(sent)

            # if result and len(cleaned) >= 3:
            if result:
                # keep every token we discover, but normalized
                discovered = finalizer.filter_tokens(tokenized)
                discovered = finalizer.clean_tokens(discovered)
                counter.update(discovered)
                if len(cleaned) > 3:
                    no_short.update(discovered)

    sorted_counter = {
        k: v for k, v in sorted(counter.items(), key=lambda i: i[1], reverse=True)
    }
    sorted_no_short = {
        k: v for k, v in sorted(no_short.items(), key=lambda i: i[1], reverse=True)
    }
    print(json.dumps(sorted_counter, indent=2, ensure_ascii=False))
    print(json.dumps(sorted_no_short, indent=2, ensure_ascii=False))


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
