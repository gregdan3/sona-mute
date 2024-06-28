# PDM
from sonatoki.ilo import Ilo
from sonatoki.Configs import CorpusConfig

ILO = Ilo(**CorpusConfig)
ILO._Ilo__scoring_filters[0].tokens -= {"we", "i", "u", "ten", "to"}
