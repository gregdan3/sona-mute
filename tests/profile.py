# STL
from time import time
from random import shuffle
from collections.abc import Callable

# LOCAL
from sonamute.counters import get_sentence_stats

sentence = "mi en olin mi li tawa ma mute li kama sona e ijo mute la mi pilin wawa mute lon kama sin lon tomo mi lon olin"


total_sents = 100000
iterations = 1


def create_sentences() -> list[list[str]]:
    sentences: list[list[str]] = list()

    for i in range(total_sents):
        new_sent = sentence.split()
        shuffle(new_sent)
        sentences.append(new_sent)

    return sentences


def profile_elapsed(iterations: int, func: Callable, *args, **kwargs) -> float:
    start = time()

    while iterations:
        func(*args, **kwargs)
        iterations -= 1

    end = time()

    return end - start


def profile_mcf():
    elapsed = profile_elapsed(
        iterations,
        get_sentence_stats,
        sents=create_sentences(),
        max_term_len=6,
    )

    print(elapsed)


def main():
    profile_mcf()


if __name__ == "__main__":
    main()
