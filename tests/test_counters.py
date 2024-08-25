# PDM
import pytest

# LOCAL
from sonamute.counters import overlapping_ntuples, overlapping_phrases


def test_overlapping_ntuples():
    it = [1, 2, 3, 4, 5]

    correct_outputs = [(1, 2, 3), (2, 3, 4), (3, 4, 5)]

    for i, row in enumerate(overlapping_ntuples(it, 3)):
        assert row == correct_outputs[i]


def test_overlapping_phrases():
    ph = ["mi", "sona", "e", "toki", "pona"]

    correct_outputs = ["mi sona e", "sona e toki", "e toki pona"]

    for i, phrase in enumerate(overlapping_phrases(ph, 3)):
        assert phrase == correct_outputs[i]
