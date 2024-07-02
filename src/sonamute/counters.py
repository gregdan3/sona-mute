# STL
import os
import json
import asyncio
import argparse
from collections import Counter
from collections.abc import Iterable, Generator

# PDM
from sonatoki.utils import overlapping_ntuples

# LOCAL
from sonamute.db import Message, Sentence, PreMessage
from sonamute.ilo import ILO
from sonamute.utils import overlapping_phrases
from sonamute.file_io import PlatformFetcher, TupleJSONEncoder
from sonamute.constants import IGNORED_CONTAINERS


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
    # NOTE: using this before, rather than after, databasing was a bad idea
    # i could have excluded these channels (and previously authors) in the analysis step
    # doing this before it impossible to ask certain questions in the database
    if not msg["content"]:
        return True  # ignore empty messages
    if msg["container"] in IGNORED_CONTAINERS:
        return True
    return False


def countable_msgs(
    msgs: Iterable[PreMessage],
    force_pass: bool = False,
) -> Generator[Message, None, None]:
    """
    Prior frequency counting implementation. Yields Messages from PreMessages.
    Filters to passing sentences unless `force_pass` is True.
    """
    for msg in msgs:
        # if ignorable(msg):
        #     continue
        content = ILO.preprocess(msg["content"])

        sentences: list[Sentence] = []
        for _, _, cleaned, score, result in ILO._are_toki_pona(content):
            if cleaned and (result or force_pass):  # omit empty sentences
                sentences.append(Sentence(words=cleaned, score=score))

        if not sentences:
            continue
        final_msg: Message = {**msg, "sentences": sentences}
        yield final_msg


def sourced_ngram_counter(
    source: PlatformFetcher,
    n: int,
    force_pass: bool = False,
    _max: int = 0,
) -> Counter[tuple[str, ...]]:
    counter: Counter[tuple[str, ...]] = Counter()
    counted = 0
    for msg in countable_msgs(source.get_messages(), force_pass=force_pass):
        for sentence in msg["sentences"]:
            if len(sentence["words"]) < n:
                continue  # save some time; can't get any data
            sentence = [word.lower() for word in sentence["words"]]
            counter.update(overlapping_ntuples(sentence, n=n))

        counted += 1
        if _max and counted >= _max:
            break

    return counter


def sourced_freq_counter(
    source: PlatformFetcher,
    min_len: int = 0,
    force_pass: bool = False,
    _max: int = 0,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    counted = 0
    for msg in countable_msgs(source.get_messages(), force_pass=force_pass):
        for sentence in msg["sentences"]:
            if len(sentence["words"]) < min_len:
                continue
            counter.update([word.lower() for word in sentence["words"]])

        counted += 1
        if _max and counted >= _max:
            break
    return counter


def phrase_counter(sents: list[list[str]], n: int):
    counter: Counter[tuple[str, ...]] = Counter()
    for sent in sents:
        if len(sent) < n:
            continue  # save some time; can't get any data
        counter.update(overlapping_ntuples(sent, n=n))
    return counter


def word_counter(sents: list[list[str]], min_len: int):
    counter: Counter[str] = Counter()
    for sent in sents:
        sent = [w.lower() for w in sent]
        if len(sent) < min_len:
            continue  # save some time; can't get any data
        counter.update(sent)
    return counter


def phrases_by_length(
    sents: list[list[str]], max_phrase_len: int
) -> dict[int, Counter[str]]:
    counters: dict[int, Counter[str]] = {
        phrase_len: Counter() for phrase_len in range(2, max_phrase_len + 1)
    }
    for sent in sents:
        sent = [w.lower() for w in sent]

        sent_len = len(sent)
        for phrase_len in range(2, max_phrase_len + 1):
            if sent_len < phrase_len:
                continue
            counters[phrase_len].update(overlapping_phrases(sent, phrase_len))
    return counters


def word_counters_by_min_sent_len(
    sents: list[list[str]],
    max_min_len: int,  # recommendation: do not exceed 6
) -> dict[int, Counter[str]]:
    counters: dict[int, Counter[str]] = {
        min_len: Counter() for min_len in range(1, max_min_len + 1)
    }

    for sent in sents:
        sent = [w.lower() for w in sent]
        sent_len = len(sent)
        for min_len in range(1, max_min_len + 1):
            if sent_len >= min_len:
                counters[min_len].update(sent)

    return counters


async def meta_counter(sents: list[list[str]]):
    min_lens = [1, 2, 3, 4, 5, 6]
    for min_len in min_lens:
        print(f"Starting on frequency of min len {min_len}")
        counter = sourced_freq_counter(source=DISCORD, min_len=min_len)
        result = dump(counter)
        with open(f"word_freq_tpt_min_len_{min_len}.json", "w") as f:
            _ = f.write(result)
        print(f"Finished frequency of min len {min_len}")

    ngrams = [2, 3, 4, 5, 6]
    for n in ngrams:
        print(f"Starting on ngrams of len {n}")
        counter = sourced_ngram_counter(source=DISCORD, n=n)
        result = dump(counter)
        with open(f"ngrams_tpt_size_{n}.json", "w") as f:
            _ = f.write(result)
        print(f"Finished ngrams of len {n}")
