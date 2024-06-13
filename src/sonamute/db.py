# STL
import logging
from enum import IntEnum
from uuid import UUID
from typing import TypedDict, NotRequired
from datetime import datetime
from functools import cache

# PDM
import edgedb
from edgedb import Client, RetryOptions

LOG_FORMAT = (
    "[%(asctime)s] [%(filename)14s:%(lineno)-4s] [%(levelname)8s]   %(message)s"
)
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

LOG = logging.getLogger()


class KnownPlatforms(IntEnum):
    Other = 0
    Discord = 1
    Telegram = 2
    Reddit = 3
    Forum = 4
    Publication = 5
    Twitter = 6


class Platform(TypedDict):
    _id: int
    name: str


class Community(TypedDict):
    _id: int
    name: str
    platform: Platform


class Author(TypedDict):
    _id: int
    name: str
    platform: Platform


class Sentence(TypedDict):
    words: list[str]
    is_toki_pona: NotRequired[bool]


class PreMessage(TypedDict):
    _id: int
    community: Community
    container: int
    author: Author
    postdate: datetime
    content: str


class Message(PreMessage):
    sentences: list[Sentence]  # implicitly the Sentence type


def build_url(username: str, password: str, host: str, port: int) -> str:
    return f"edgedb://{username}:{password}@{host}:{port}"
def clean_string(content: str) -> str:
    content = content.replace("\xad", "")
    # this is a discretionary hyphen, and edgedb won't accept it
    return content


def create_client(username: str, password: str, host: str, port: int) -> Client:
    url = build_url(username, password, host, port)
    client = edgedb.create_client(
        dsn=url,
        tls_security="insecure",
        timeout=10000,
    )
    client.with_retry_options(options=RetryOptions(attempts=5))
    return client


PLAT_INSERT = """
INSERT Platform {
    _id := <int64>$_id,
    name := <str>$name,
} unless conflict on ._id
else (select Platform filter Platform._id = <int64>$_id)"""

COMM_INSERT = """
INSERT Community {
    _id := <int64>$_id,
    name := <str>$name,
    platform := <Platform>$platform,
} unless conflict on (._id, .platform)
else (select Community filter Community._id = <int64>$_id)"""

AUTH_INSERT = """
INSERT Author {
    _id := <int64>$_id,
    name := <str>$name,
    platform := <Platform>$platform,
} unless conflict on (._id, .platform)
else (select Author filter Author._id = <int64>$_id)"""

MSG_INSERT = """
INSERT Message {
    _id := <int64>$_id,
    community := <Community>$community,
    container := <int64>$container,
    author := <Author>$author,
    postdate := <std::datetime>$postdate,
    content := <str>$content,
    sentences := { %s },
} unless conflict on (._id, .community)
else (select Message filter Message._id = <int64>$_id)"""
# NOTE: sentences must be subbed in

SENT_INSERT = """(INSERT Sentence {words := <array<str>>%s})"""
# NOTE: would be $sentence, but then we'd have repeat vars


def make_sent_subquery(sentences: list[Sentence]) -> str:
    outputs: list[str] = []
    for s in sentences:
        outputs.append(f"{SENT_INSERT}" % s["words"])
    return ",\n".join(outputs)


# ESCAPE_SEQUENCE_RE = re.compile(r'''
#     ( \\U........      # 8-digit hex escapes
#     | \\u....          # 4-digit hex escapes
#     | \\x..            # 2-digit hex escapes
#     | \\[0-7]{1,3}     # Octal escapes
#     | \\N\{[^}]+\}     # Unicode characters by name
#     | \\[\\'"abfnrtv]  # Single-character escapes
#     )''', re.UNICODE | re.VERBOSE)
#
# def decode_escapes(s):
#     def decode_match(match):
#         return codecs.decode(match.group(0), 'unicode-escape')
#
#     return ESCAPE_SEQUENCE_RE.sub(decode_match, s)


class MessageDB:
    client: Client

    def __init__(self, username: str, password: str, host: str, port: int) -> None:
        self.client = create_client(username, password, host, port)

    # really just some hot dogshit code.
    @cache
    def __insert_platform(self, _id: int, name: str) -> UUID:
        result = self.client.query(
            query=PLAT_INSERT,
            _id=_id,
            name=name,
        )
        return result[0].id

    def insert_platform(self, platform: Platform) -> UUID:
        if isinstance(platform, UUID):
            # this is an artifact of insert_platform being called twice
            return platform
        result = self.__insert_platform(**platform)
        return result

    @cache
    def __insert_author(self, _id: int, name: str, platform: UUID) -> UUID:
        result = self.client.query(
            query=AUTH_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )
        return result[0].id

    def insert_author(self, author: Author) -> UUID:
        platform_id = self.insert_platform(author["platform"])
        author["platform"] = platform_id
        return self.__insert_author(**author)

    @cache
    def __insert_community(self, _id: int, name: str, platform: UUID) -> UUID:
        result = self.client.query(
            query=COMM_INSERT,
            _id=_id,
            name=name,
            platform=platform,
        )
        return result[0].id

    def insert_community(self, community: Community) -> UUID:
        platform_id = self.insert_platform(community["platform"])
        community["platform"] = platform_id
        return self.__insert_community(**community)

    def __insert_message(
        self,
        _id: int,
        community: UUID,
        author: UUID,
        postdate: datetime,
        content: str,
        sentences: list[Sentence],
        container: int | None = None,
    ) -> UUID:
        content = clean_string(content)
        sent_subquery = make_sent_subquery(sentences)
        # print(content)
        # print(repr(content))
        return self.client.query(
            query=MSG_INSERT % sent_subquery,
            _id=_id,
            community=community,
            author=author,
            postdate=postdate,
            content=content,
            container=container,
        )

    def insert_message(self, message: Message) -> UUID:
        author_id = self.insert_author(message["author"])
        message["author"] = author_id

        community_id = self.insert_community(message["community"])
        message["community"] = community_id

        return self.__insert_message(**message)
