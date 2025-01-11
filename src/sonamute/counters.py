# STL
import json
import itertools
from typing import TypeVar
from collections import Counter, defaultdict
from collections.abc import Iterable, Generator

# LOCAL
from sonamute.ilo import ILO
from sonamute.file_io import TupleJSONEncoder
from sonamute.smtypes import (
    Message,
    HitsData,
    Sentence,
    PreMessage,
    Metacounter,
    SortedSentence,
)
from sonamute.constants import IGNORED_AUTHORS, IGNORED_CONTAINERS
from sonamute.sources.generic import PlatformFetcher
from sonamute.utils import fake_uuid

T = TypeVar("T")


AVG_SENT_LEN = 4.13557
AVG_SENT_LEN_5X = 5 * AVG_SENT_LEN
AVG_SENT_LEN_50X = 50 * AVG_SENT_LEN

MED_SENT_LEN = 3
MED_SENT_LEN_5X = 5 * MED_SENT_LEN
MED_SENT_LEN_50X = 50 * MED_SENT_LEN


def overlapping_ntuples(iterable: Iterable[T], n: int) -> Iterable[T]:
    teed = itertools.tee(iterable, n)
    for i in range(1, n):
        for j in range(i):
            _ = next(teed[i], None)
            # offset start by position

    # ends when any iter is empty; all groups will be same size
    return zip(*teed)


def overlapping_terms(iterable: Iterable[str], n: int) -> Iterable[str]:
    return [" ".join(item) for item in overlapping_ntuples(iterable, n)]


def dump(counter: Counter[str] | Counter[tuple[str, ...]]) -> str:
    sorted_counter = {
        k: v for k, v in sorted(counter.items(), key=lambda i: i[1], reverse=True)
    }
    return json.dumps(
        sorted_counter,
        indent=2,
        ensure_ascii=False,
        cls=TupleJSONEncoder,
    )


def ignorable(msg: PreMessage) -> bool:
    if msg["author"]["is_bot"] and not msg["author"]["is_webhook"]:
        return True
    if not msg["content"]:
        return True
    if msg["container"] in IGNORED_CONTAINERS:
        return True
    if msg["author"]["_id"] in IGNORED_AUTHORS:
        return True
    return False


def populate_sents(msgs: Iterable[PreMessage]) -> Generator[Message, None, None]:
    for msg in msgs:
        content = ILO.preprocess(msg["content"])

        sentences: list[Sentence] = []
        for scorecard in ILO._are_toki_pona(content):
            if scorecard["cleaned"]:  # omit empty sentences
                sentences.append(
                    Sentence(
                        words=scorecard["cleaned"],
                        score=scorecard["score"],
                    )
                )

        final_msg: Message = {
            **msg,
            "sentences": sentences,
            "is_counted": not ignorable(msg),
        }
        yield final_msg


def counted(msgs: Iterable[Message]) -> Generator[Message, None, None]:
    for msg in msgs:
        if msg["is_counted"]:
            yield msg


def sentences_of(
    msgs: Generator[Message, None, None]
) -> Generator[Sentence, None, None]:
    for msg in msgs:
        for sent in msg["sentences"]:
            yield sent


def with_score(
    sents: Generator[Sentence, None, None], score: float = 0.8
) -> Generator[Sentence, None, None]:
    for sent in sents:
        if sent["score"] >= score:
            yield sent


def words_of(
    sents: Generator[Sentence, None, None]
) -> Generator[list[str], None, None]:
    for sent in sents:
        yield sent["words"]


def lowered(
    sents: Generator[list[str], None, None]
) -> Generator[list[str], None, None]:
    for sent in sents:
        sent = [word.lower() for word in sent]
        yield sent


def countables(
    source: PlatformFetcher,
) -> Generator[SortedSentence, None, None]:

    # why did i write this
    msgs = source.get_messages()
    msgs = populate_sents(msgs)
    msgs = counted(msgs)
    sents = sentences_of(msgs)
    sents = with_score(sents, 0.8)
    sents = words_of(sents)
    sents = lowered(sents)
    for sent in sents:
        yield {"words": sent, "author": fake_uuid("")}
        # TODO: get actual msg author's name to fake authorship better


def is_nonsense(sent_len: int, sent: list[str]) -> bool:
    """
    Skip a sentence if it is "nonsense," which means
    - "longer than 5x the average" and "mostly a single word", or
    - "longer than 50x the average" (instant disqualification)

    This is intentionally a very weak filter.
    As of writing, there are fewer than 1000 sentences with >=40 words,
    and barely over 100 sentences with >=400 words.

    Given:
    - The average sentence length is ~4.13 (with outliers)
    - The median sentence length is 3,
    - There are nearly 4 million sentences total
    these being "real sentences" worth counting is... unlikely.

    I can't totally dismiss the possibility without manual inspection,
    and I don't want to involve manual inspection if I can avoid it.
    (though statistical inspection would be fine.)
    But I think we can say with extremely high confidence
    that a 40+ word sentence which is >=50% one word is nonsense.

    So, we omit them.
    """

    if sent_len <= AVG_SENT_LEN_5X:
        return False
    if sent_len >= AVG_SENT_LEN_50X:
        return True

    counter = Counter(sent)
    _, count = counter.most_common(n=1)[0]
    # we don't care what the term is

    return (count / sent_len) >= 0.5


def count_frequencies(
    sents: Iterable[SortedSentence],
    max_term_len: int,
    max_min_sent_len: int,
) -> Metacounter:
    # metacounter tracks {term_len: {min_sent_len: {term: {hits: int, authors: int}}}}
    metacounter: Metacounter = {
        term_len: {
            min_sent_len: defaultdict(lambda: HitsData({"hits": 0, "authors": set()}))
            for min_sent_len in range(term_len, max_min_sent_len + 1)
        }
        for term_len in range(1, max_term_len + 1)
    }
    for sent in sents:
        words = sent["words"]
        author = sent["author"]
        sent_len = len(words)
        if not sent_len:
            continue

        if is_nonsense(sent_len, words):
            continue

        for term_len in range(1, max_term_len + 1):
            if sent_len < term_len:
                continue

            terms = overlapping_terms(words, term_len)
            for min_sent_len in range(term_len, max_min_sent_len + 1):
                if not (sent_len >= min_sent_len):
                    continue

                for term in terms:
                    metacounter[term_len][min_sent_len][term]["hits"] += 1
                    metacounter[term_len][min_sent_len][term]["authors"] |= {author}

    return metacounter
