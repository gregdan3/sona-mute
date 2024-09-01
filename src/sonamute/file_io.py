# STL
import json
from uuid import UUID
from typing import cast
from datetime import datetime
from collections.abc import Mapping, Iterable

# PDM
import orjson
import lxml.html
import lxml.etree
from bs4 import BeautifulSoup
from typing_extensions import override

JSON = str | int | float | Mapping["JSON", "JSON"] | Iterable["JSON"]
JSONable = JSON | tuple[JSON, ...]


class TupleJSONEncoder(json.JSONEncoder):
    @override
    def encode(self, o: JSONable):
        if isinstance(o, dict):
            new_o = {}
            for k, v in o.items():
                if isinstance(k, tuple):
                    new_key = " ".join(k)
                    new_o[new_key] = v
                else:
                    new_o[k] = v
            return super().encode(new_o)
        return super().encode(o)


class EdgeDBEncoder(json.JSONEncoder):
    @override
    def default(self, o: JSONable) -> str:
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super(EdgeDBEncoder, self).default(o)


def try_load_json(data: str) -> JSON | None:
    content = None
    try:
        content = cast(JSON, orjson.loads(data))
    except orjson.JSONDecodeError:
        # TODO: print failing file? log leve?
        pass
    return content


def try_load_json_file(filename: str) -> JSON | None:
    # TODO: what if the file is too large?
    with open(filename, "r") as f:
        content = try_load_json(f.read())
    return content


def try_load_html(data: str):
    content = None
    # try:
    content = BeautifulSoup(data, "lxml")
    # except
    return content


def try_load_html_file(filename: str):
    with open(filename, "r") as f:
        content = try_load_html(f.read())
    return content
