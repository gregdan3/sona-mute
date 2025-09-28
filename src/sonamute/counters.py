# STL
import itertools
from sys import intern
from uuid import UUID
from typing import Tuple, TypeVar
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Generator

# LOCAL
from sonamute.ilo import ILO
from sonamute.utils import fake_uuid
from sonamute.smtypes import (
    Stats,
    Message,
    Sentence,
    Attribute,
    PreMessage,
    StatsCounter,
    SortedSentence,
)
from sonamute.sources.generic import PlatformFetcher, is_countable

T = TypeVar("T")


AVG_SENT_LEN = 4.13557
AVG_SENT_LEN_5X = 5 * AVG_SENT_LEN
AVG_SENT_LEN_50X = 50 * AVG_SENT_LEN

MED_SENT_LEN = 3
MED_SENT_LEN_5X = 5 * MED_SENT_LEN
MED_SENT_LEN_50X = 50 * MED_SENT_LEN


def window_iter(iterable: Iterable[T], n: int) -> Iterable[tuple[T, ...]]:
    teed = itertools.tee(iterable, n)
    for i in range(1, n):
        for j in range(i):
            _ = next(teed[i], None)
            # offset start by position

    # ends when any iter is empty; all groups will be same size
    return zip(*teed)


def window_iter_terms(iterable: Iterable[str], n: int) -> Iterable[str]:
    for item in window_iter(iterable, n):
        yield intern(" ".join(item))


def window_iter_range(
    iterable: Iterable[T],
    n: int,
) -> Iterator[tuple[tuple[T, ...], tuple[int, int]]]:
    teed = itertools.tee(iterable, n)
    for i in range(1, n):
        for _ in range(i):
            next(teed[i], None)  # offset each iterator

    for idx, group in enumerate(zip(*teed)):
        yield group, (idx, idx + n)


def window_iter_terms_range(
    iterable: Iterable[str], n: int
) -> Iterator[Tuple[str, Tuple[int, int]]]:
    for tup, idx_range in window_iter_range(iterable, n):
        yield intern(" ".join(tup)), idx_range


def clean_string(content: str) -> str:
    """
    GelDB-specific string pre-processing.
    I note all changes; none of them are semantic.
    """

    content = content.replace("\xad", "")
    # `\xad` is the discretionary hyphen; optional to print so not semantic
    content = content.replace("\0", "")
    # i have no earthly idea how this could happen; i'm reading json
    return content


def process_msg(msg: PreMessage) -> Message:
    """
    For GelDB inserts. Turns a PreMessage into a Message, including all sentences.
    """
    is_counted = is_countable(msg)
    msg["content"] = clean_string(msg["content"])
    msg_scorecard = ILO.make_scorecard(msg["content"])
    msg_score = msg_scorecard["score"]

    sentences: list[Sentence] = []
    for scorecard in ILO.make_scorecards(msg["content"]):
        if not scorecard["cleaned"]:
            continue  # omit empty sentences
        sentence = Sentence(
            words=scorecard["cleaned"],
            score=scorecard["score"],
        )
        sentences.append(sentence)

    # it's okay to have no sentences
    final_msg: Message = {
        **msg,
        "score": msg_score,
        "sentences": sentences,
        "is_counted": is_counted,
    }
    return final_msg


def process_msgs(msgs: Iterable[PreMessage]) -> Generator[Message, None, None]:
    for msg in msgs:
        msg = process_msg(msg)
        yield msg


def counted(msgs: Iterable[Message]) -> Generator[Message, None, None]:
    for msg in msgs:
        if msg["is_counted"]:
            yield msg


def sentences_of(
    msgs: Generator[Message, None, None],
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
    sents: Generator[Sentence, None, None],
) -> Generator[list[str], None, None]:
    for sent in sents:
        yield sent["words"]


def lowered(
    sents: Generator[list[str], None, None],
) -> Generator[list[str], None, None]:
    for sent in sents:
        sent = [word.lower() for word in sent]
        yield sent


def countables(
    source: PlatformFetcher,
) -> Generator[SortedSentence, None, None]:

    # why did i write this
    msgs = source.get_messages()
    msgs = process_msgs(msgs)
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


def get_sentence_stats(
    sents: Iterable[SortedSentence],
    max_term_len: int,
    max_min_sent_len: int,
) -> StatsCounter:
    freqs: StatsCounter = defaultdict(lambda: Stats({"hits": 0, "authors": set()}))

    def add_freq(
        term_len: int,
        msl: int,
        term: str,
        attr: Attribute,
        author: UUID,
    ):
        freq = freqs[(term_len, msl, term, attr)]
        freq["hits"] += 1
        freq["authors"].add(author)

    for sent in sents:
        words = sent["words"]
        author = sent["author"]
        sent_len = len(words)
        if not sent_len or is_nonsense(sent_len, words):
            continue

        term_len_cap = min(max_term_len, sent_len) + 1
        msl_cap = min(max_min_sent_len, sent_len) + 1
        for term_len in range(1, term_len_cap):
            terms = window_iter_terms_range(words, term_len)
            for term, (start, end) in terms:
                is_start = start == 0
                is_end = end == sent_len
                for msl in range(term_len, msl_cap):
                    # NOTE: if max_msl is less than max_term_len
                    # this will not go past terms of length max_msl
                    # terms of must be in sentences of at least their length
                    add_freq(term_len, msl, term, Attribute.All, author)
                    if is_start:
                        add_freq(term_len, msl, term, Attribute.SentenceStart, author)
                    if is_end:
                        add_freq(term_len, msl, term, Attribute.SentenceEnd, author)

    return freqs
