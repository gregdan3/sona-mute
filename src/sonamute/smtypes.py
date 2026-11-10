# STL
from enum import Enum, IntEnum
from uuid import UUID
from typing import TypedDict, NotRequired
from datetime import date, datetime


# Copy of Attribute enum in PostgreSQL
# see also db/default.esdl, db/default.sql
class Attribute(Enum):
    All = "All"

    # position
    Start = "Start"
    End = "End"
    Full = "Full"
    Long = "Long"
    Short = "Short"
    Inner = "Inner"

    # parts of speech
    Subject = "Subject"
    Verb = "Verb"
    Object = "Object"
    PrepositionalObject = "PrepositionalObject"
    Predicate = "Predicate"
    Interjection = "Interjection"

    # more specific parts of speech
    TransitiveVerb = "TransitiveVerb"
    IntransitiveVerb = "IntransitiveVerb"
    PrepositionalVerb = "PrepositionalVerb"

    # functions
    Content = "Content"
    Particle = "Particle"
    Head = "Head"
    Modifier = "Modifier"
    Preposition = "Preposition"
    Preverb = "Preverb"
    Noun = "Noun"

    # other
    Unknown = "Unknown"


# For sqlite
ATTRIBUTE_IDS = {attribute: i for i, attribute in enumerate(Attribute)}

PlatformKey = int  # int16
ObjectKey = UUID


# frequency generation for sqlite
class Stats(TypedDict):
    hits: int
    authors: set[int]


Term = tuple[str, ...]
StatsCounter = dict[Term, dict[int, dict[Attribute, int]]]


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
    id: int
    name: str


class Community(TypedDict):
    id: UUID
    platform: NotRequired[Platform]
    name: str


class Author(TypedDict):
    id: UUID
    platform: NotRequired[Platform]
    name: str
    is_bot: bool
    is_webhook: bool


class Sentence(TypedDict):
    words: tuple[str, ...]
    score: float


class CommSentence(TypedDict):
    words: tuple[str, ...]
    community_id: int
    author_id: int


class SortedSentence(TypedDict):
    words: tuple[str, ...]
    author_id: int


class PreMessage(TypedDict):
    id: UUID
    platform: NotRequired[Platform]
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    score: float
    is_counted: bool
    sentences: list[Sentence]


class PGFrequency(TypedDict):
    text: str
    words: tuple[str, ...]

    attr: Attribute
    community_id: UUID
    platform_id: int
    day: date
    hits: int
    authors: list[int]
