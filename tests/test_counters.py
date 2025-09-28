# STL
import json
from uuid import uuid4

# PDM
import pytest

# LOCAL
from sonamute.smtypes import SortedSentence
from sonamute.counters import (
    window_iter,
    window_iter_terms,
    get_sentence_stats,
)


def test_overlapping_ntuples():
    it = [1, 2, 3, 4, 5]

    correct_outputs = [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    for i, row in enumerate(window_iter(it, 3)):
        assert row == correct_outputs[i]


def test_overlapping_terms():
    ph = ["mi", "sona", "e", "toki", "pona"]

    correct_outputs = ["mi sona e", "sona e toki", "e toki pona"]

    for i, term in enumerate(window_iter_terms(ph, 3)):
        assert term == correct_outputs[i]


def test_overlapping_terms_with_markers():
    ph = ["^", "toki", "$"]
    correct_map = {
        1: ["^", "toki", "$"],
        2: ["^ toki", "toki $"],
        3: ["^ toki $"],
    }

    for term_len in range(1, 4):
        for i, term in enumerate(window_iter_terms(ph, term_len)):
            assert term == correct_map[term_len][i]


def test_sentence_markers():
    author = uuid4()
    sents = [
        # SortedSentence({"words": ["toki"], "author": author}),
        # SortedSentence({"words": ["pona"], "author": author}),
        # SortedSentence({"words": ["toki", "pona"], "author": author}),
        SortedSentence(
            {
                "words": [
                    "o",
                    "pana",
                    "wawa",
                    "e",
                    "ni",
                    "tawa",
                    "lupa",
                    "monsi",
                    "sina",
                ],
                "author": author,
            }
        ),
    ]

    metacounter = get_sentence_stats(sents, 7, 7, True)

    dumped = json.dumps(metacounter, indent=2, default=str)

    print(dumped)

    assert True


def test_freq_counter_2():
    author = uuid4()
    sents = [
        # SortedSentence({"words": ["toki"], "author": author}),
        # SortedSentence({"words": ["pona"], "author": author}),
        # SortedSentence({"words": ["toki", "pona"], "author": author}),
        SortedSentence(
            {
                "words": [
                    "o",
                    "pana",
                    "wawa",
                    "e",
                    "ni",
                    "tawa",
                    "lupa",
                    "monsi",
                    "sina",
                ],
                "author": author,
            }
        ),
    ]

    metacounter = get_sentence_stats(sents, 99, 99)
    print(metacounter)
    # dumped = json.dumps(metacounter, indent=2, default=str)
    # print(dumped)
    assert True
