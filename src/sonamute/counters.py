# STL
import json
from collections import Counter
from collections.abc import Iterable, Generator

# PDM
from sonatoki.utils import overlapping_ntuples

# LOCAL
from sonamute.db import Message, Sentence, PreMessage
from sonamute.ilo import ILO
from sonamute.utils import overlapping_phrases
from sonamute.file_io import TupleJSONEncoder
from sonamute.constants import IGNORED_CONTAINERS
from sonamute.sources.generic import PlatformFetcher


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
        return True  # ignore empty messages
    if msg["container"] in IGNORED_CONTAINERS:
        return True
    return False


def by_users(msgs: Iterable[PreMessage]) -> Generator[PreMessage, None, None]:
    for msg in msgs:
        if msg["author"]["is_bot"] and not msg["author"]["is_webhook"]:
            continue
        if not msg["content"]:
            continue
        if msg["container"] in IGNORED_CONTAINERS:
            continue
        yield msg


def populate_sents(msgs: Iterable[PreMessage]) -> Generator[Message, None, None]:
    for msg in msgs:
        content = ILO.preprocess(msg["content"])

        sentences: list[Sentence] = []
        for _, _, cleaned, score, result in ILO._are_toki_pona(content):
            if cleaned:  # omit empty sentences
                sentences.append(Sentence(words=cleaned, score=score))

        final_msg: Message = {**msg, "sentences": sentences}
        yield final_msg


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
) -> Generator[list[str], None, None]:

    # why did i write this
    msgs = source.get_messages()
    msgs = by_users(msgs)
    msgs = populate_sents(msgs)
    sents = sentences_of(msgs)
    sents = with_score(sents, 0.8)
    sents = words_of(sents)
    sents = lowered(sents)
    for sent in sents:
        yield sent

    # metacounter = metacount_frequencies(sents, 6, 6)


def sourced_freq_counter(
    source: PlatformFetcher,
    min_len: int = 0,
    force_pass: bool = False,
    _max: int = 0,
) -> Counter[str]:
    counter: Counter[str] = Counter()
    counted = 0
    for msg in populate_sents(source.get_messages(), force_pass=force_pass):
        for sentence in msg["sentences"]:
            if len(sentence["words"]) < min_len:
                continue
            sentence["words"] = [word.lower() for word in sentence["words"]]
            counter.update(sentence["words"])

        counted += 1
        if _max and counted >= _max:
            break
    return counter


def phrase_counter(
    sents: Iterable[list[str]],
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


def metacount_frequencies(
    sents: Iterable[list[str]],
    max_phrase_len: int,
    max_min_sent_len: int,
) -> dict[int, dict[int, Counter[str]]]:
    metacounter: dict[int, dict[int, Counter[str]]] = {
        phrase_len: {
            min_sent_len: Counter()
            for min_sent_len in range(phrase_len, max_min_sent_len + 1)
        }
        for phrase_len in range(1, max_phrase_len + 1)
    }

    for sent in sents:
        sent_len = len(sent)
        if not sent_len:
            continue

        for phrase_len in range(1, max_phrase_len + 1):
            if sent_len < phrase_len:
                continue

            phrases = overlapping_phrases(sent, phrase_len)
            for min_sent_len in range(phrase_len, max_min_sent_len + 1):
                if sent_len >= min_sent_len:
                    metacounter[phrase_len][min_sent_len].update(phrases)

    return metacounter
