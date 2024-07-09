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
    if msg["author"]["is_bot"] and not msg["author"]["is_webhook"]:
        return True
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


def phrase_counter(
    sents: list[list[str]],
    phrase_len: int,
    min_sent_len: int,
) -> Counter[str]:
    # save a comparison; sentences shorter than phrase_len can't be counted anyway
    if phrase_len > min_sent_len:
        min_sent_len = phrase_len

    counter: Counter[str] = Counter()
    for sent in sents:
        if len(sent) < min_sent_len:
            continue
        counter.update(overlapping_phrases(sent, n=phrase_len))
    return counter


def word_counter(sents: list[list[str]], min_len: int):
    counter: Counter[str] = Counter()
    for sent in sents:
        if len(sent) < min_len:
            continue  # save some time; can't get any data
        counter.update(sent)
    return counter


def phrases_by_length(
    sents: list[list[str]],
    max_phrase_len: int,  # don't go past 6 ever
) -> dict[int, Counter[str]]:
    counters: dict[int, Counter[str]] = {1: Counter()}
    # this silliness maintains the contract for word_counters_by_min_sent_len
    for sent in sents:
        sent_len = len(sent)
        for phrase_len in range(2, max_phrase_len + 1):
            if sent_len < phrase_len:
                continue
            counters[1].update(overlapping_phrases(sent, phrase_len))
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
