# STL
from enum import Enum, IntEnum
from uuid import UUID
from typing import TypedDict, NotRequired
from datetime import datetime


# Copy of Attribute enum in GelDB and PostgreSQL
# see also db/default.esdl, db/default.sql
class Attribute(Enum):
    All = "All"
    Start = "Start"
    End = "End"
    Full = "Full"
    Long = "Long"
    Short = "Short"
    Inner = "Inner"

    Subject = "Subject"
    Verb = "Verb"
    Object = "Object"
    PrepositionalObject = "PrepositionalObject"

    Head = "Head"
    Modifier = "Modifier"
    Preposition = "Preposition"
    Preverb = "Preverb"
    Noun = "Noun"
    Particle = "Particle"

    TransitiveVerb = "TransitiveVerb"
    IntransitiveVerb = "IntransitiveVerb"
    PrepositionalVerb = "PrepositionalVerb"


# For sqlite
ATTRIBUTE_IDS = {attribute: i for i, attribute in enumerate(Attribute)}


# frequency generation
class Stats(TypedDict):
    hits: int
    authors: set[UUID]


StatsCounter = dict[tuple[int, str, Attribute], Stats]


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


class GelFrequency(TypedDict):
    text: str
    term_len: int

    attr: Attribute
    community: UUID
    day: datetime
    hits: int
    authors: list[UUID]


# sqlite generation
class SQLTerm(TypedDict):
    text: str
    len: int


class SQLFrequency(TypedDict):
    # NOTE: exactly one of term or term_id are required.
    term: SQLTerm
    term_id: NotRequired[int]
    attr: int
    day: int
    hits: int
    authors: int
