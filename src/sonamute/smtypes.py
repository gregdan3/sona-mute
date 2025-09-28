# STL
from enum import IntEnum
from uuid import UUID
from typing import TypedDict, NotRequired
from datetime import datetime
from dataclasses import dataclass


class Attr(IntEnum):
    All = 0
    SentenceStart = 1
    SentenceEnd = 2


# frequency generation
class HitsData(TypedDict):
    hits: int
    authors: set[UUID]


class Stats(TypedDict):
    hits: int
    authors: set[UUID]


class RawTerm(TypedDict):
    text: str
    len: int


class Term(RawTerm):
    id: int


class RawFrequency(TypedDict):
    term: Term | RawTerm
    attr: Attr

    min_sent_len: int
    hits: int
    authors: list[UUID] | set[UUID]


class Frequency(RawFrequency):
    community: UUID
    day: datetime


Metacounter = dict[int, dict[int, dict[str, HitsData]]]


# edgedb and sources


class KnownPlatforms(IntEnum):
    Other = 0  # unsortable

    Discord = 1  # supported
    Telegram = 2  # supported
    # Facebook = 3
    Reddit = 4  # supported
    YouTube = 5  # supported
    # Twitter = 6
    # Instagram = 7
    # Tumblr = 8
    # Mastodon = 9
    # Cohost = 10
    Forum = 100  # generic
    # NOTE: includes Yahoo Groups, kulupu.pona.la, and forums.tokipona.org

    Publication = 200  # generic
    # NOTE: includes lipu Wikipesija, lipu tenpo, lipu kule

    # Personal = 300


class Platform(TypedDict):
    _id: int
    name: str


class Community(TypedDict):
    _id: int
    name: str
    platform: Platform


class Author(TypedDict):
    _id: int
    name: str | None
    platform: Platform
    is_bot: bool
    is_webhook: bool


class Sentence(TypedDict):
    words: list[str]
    score: float


class CommSentence(TypedDict):
    words: list[str]
    community: UUID
    author: UUID


class SortedSentence(TypedDict):
    words: list[str]
    author: UUID


class PreMessage(TypedDict):
    _id: int
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    score: float
    is_counted: bool
    sentences: list[Sentence]


class EDBFrequency(TypedDict):
    text: str
    term_len: int

    attr: Attr
    community: UUID
    min_sent_len: int
    day: datetime
    hits: int
    authors: list[UUID]


# sqlite generation
class SQLTerm(TypedDict):
    text: str
    len: int


class InterFreq(TypedDict):
    hits: int
    authors: set[UUID]


class SQLFrequency(TypedDict):
    # NOTE: exactly one of term or term_id are required.
    term: SQLTerm
    term_id: NotRequired[int]
    min_sent_len: int
    day: int
    hits: int
    authors: int
