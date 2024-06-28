# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import CorpusConfig

ILO = Ilo(**CorpusConfig)
ILO._Ilo__scoring_filters[0].tokens -= {"we", "i", "u", "ten", "to"}
# These are all extremely infrequent in toki pona and make it more difficult to distinguish from English if counted in the dictionary.
# We will still correctly discover them if they are among many other Toki Pona words.
