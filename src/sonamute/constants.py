# STL
from datetime import UTC, datetime

# LOCAL
from sonamute.smtypes import KnownPlatforms

IGNORED_CONTAINERS_MAP = {
    KnownPlatforms.Discord.value: {
        316066233755631616,  # mapona/jaki
        759969963992940585,  # ma pona/jaki lawa
        786041291707777034,  # mapona/ako
        842196795756249118,  # ma pona/invite lawa
        895303838662295572,  # maponasewi/tokinanpa; this is a pluralkit user.
        914305039764426772,  # ma pali/wikipesija
        1128714905932021821,  # mamusi/ako
        1187212477155528804,  # mapona/toki-suli/musitokipiantesitelenwan
        1031260120904114316,  # ma ante/animal farm spam thing
    }
}

IGNORED_AUTHORS_MAP = {
    KnownPlatforms.Discord.value: {
        937872123085602896,  # old wikipesija logger
        1074390249981096047,  # wikipesija logger
        1135620786183491725,  # old ma musi minecraft logger
        1135634171734261830,  # ma musi minecraft logger
        1213156131006845020,  # sona.pona.la logger
        950311805845139506,  # "o sitelen lon lipu sina"
        790443487912656916,  # ilo ako
    }
}


EPOCH_INIT = datetime(2001, 8, 8, tzinfo=UTC)
NDAYS = 7 * 4

MAX_TERM_LEN = 6
MIN_HITS_NEEDED = 40
MIN_SENTS_NEEDED = 20
LONG_SENTENCE_LEN = 4
