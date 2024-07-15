# STL
import json
from typing import cast
from collections.abc import Mapping, Iterable

# PDM
import orjson
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


def try_load_json(filename: str) -> JSON | None:
    # TODO: what if the file is too large?
    with open(filename, "r") as f:
        content = None
        try:
            content = cast(JSON, orjson.loads(f.read()))
        except orjson.JSONDecodeError:
            # TODO: print failing file? log leve?
            pass
    return content
