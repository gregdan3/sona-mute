# STL
from datetime import UTC, datetime

IGNORED_CONTAINERS = {
    316066233755631616,  # ma pona/jaki
    786041291707777034,  # ma pona/ako
    914305039764426772,  # ma pali/wikipesija
    1128714905932021821,  # ma musi/ako
    # The acrophobia bot is troublesome, because users trigger it with a phrase in toki pona.
    # Repeated uses push every word in "ilo o ako" up by >10,000 uses, changing their relative rankings even for o.
}

# TODO: reintroduce for non-pk webhooks?
IGNORED_AUTHORS = {}

EPOCH_INIT = datetime(2001, 8, 8, tzinfo=UTC)
NDAYS = 7 * 4
