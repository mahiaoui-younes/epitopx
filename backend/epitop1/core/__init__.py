"""
Core package for EpiTop1 - B Linear Epitope Prediction.

Contains all bioinformatics algorithms for epitope prediction:
- Amino acid property scales
- Hydrophilicity (Hopp & Woods, 1981)
- Hydrophobicity (Kyte & Doolittle, 1982)
- Flexibility (Karplus & Schulz, 1985)
- Surface Accessibility (Emini et al., 1985)
- Antigenicity (Kolaskar & Tongaonkar, 1990)
- Global scoring engine
- Epitope selection algorithm
"""

from .scales import (
    HOPP_WOODS_SCALE,
    KYTE_DOOLITTLE_SCALE,
    KARPLUS_SCHULZ_SCALE,
    EMINI_SCALE,
    KOLASKAR_TONGAONKAR_SCALE,
)
from .hydrophilicity import HoppWoodsPredictor
from .hydrophobicity import KyteDoolittlePredictor
from .flexibility import KarplusSchulzPredictor
from .accessibility import EminiPredictor
from .antigenicity import KolaskarTongaonkarPredictor
from .scoring import GlobalScorer
from .epitope_selector import EpitopeSelector

__all__ = [
    "HOPP_WOODS_SCALE",
    "KYTE_DOOLITTLE_SCALE",
    "KARPLUS_SCHULZ_SCALE",
    "EMINI_SCALE",
    "KOLASKAR_TONGAONKAR_SCALE",
    "HoppWoodsPredictor",
    "KyteDoolittlePredictor",
    "KarplusSchulzPredictor",
    "EminiPredictor",
    "KolaskarTongaonkarPredictor",
    "GlobalScorer",
    "EpitopeSelector",
]
