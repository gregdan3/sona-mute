# STL
from datetime import datetime

# LOCAL
from sonamute.sources.telegram import ONECHAT_BRIDGE_ID, TelegramFetcher


def test_telegram_source():
    source = TelegramFetcher("/home/gregdan3/communities/telegram/")
    earliest = datetime(2016, 3, 1)
    latest = datetime(2024, 7, 30)
    count = 0
    for m in source.get_messages():
        assert m
        assert isinstance(m["_id"], int)

        assert m["author"]
        assert m["author"]["_id"]
        assert isinstance(m["author"]["_id"], int)
        assert (not m["author"]["is_bot"] and not m["author"]["is_webhook"]) or m[
            "author"
        ]["_id"] == ONECHAT_BRIDGE_ID

        assert m["community"]
        assert m["community"]["_id"]
        assert isinstance(m["community"]["_id"], int)

        assert earliest < m["postdate"] < latest
        assert m["author"]["platform"] == m["community"]["platform"]

        count += 1

    print(count)
