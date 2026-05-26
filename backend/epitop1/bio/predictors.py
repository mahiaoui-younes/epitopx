"""
Individual residue-level property predictors for B-cell linear epitope prediction.

Each predictor class wraps a single physicochemical or structural propensity
scale and exposes a common interface::

    predictor.predict(sequence) -> np.ndarray   # smoothed profile
    predictor.raw_scores(sequence) -> np.ndarray  # un-smoothed per-residue

All predictors are independently reusable and stateless.

Predictors implemented
----------------------
1. **ParkerHydrophilicityPredictor** — Parker et al. (1986)
2. **EminiAccessibilityPredictor** — Emini et al. (1985)
3. **KarplusSchulzFlexibilityPredictor** — Karplus & Schulz (1985)
4. **ChouFasmanBetaTurnPredictor** — Chou & Fasman (1978)
5. **KolaskarTongaonkarAntigenicityPredictor** — Kolaskar & Tongaonkar (1990)

References
----------
Parker JMR, Guo D & Hodges RS (1986) Biochemistry 25:5425-5432.
Emini EA et al. (1985) J Virol 55:836-839.
Karplus PA & Schulz GE (1985) Naturwissenschaften 72:212-213.
Chou PY & Fasman GD (1978) Adv Enzymol Relat Areas Mol Biol 47:45-148.
Kolaskar AS & Tongaonkar PC (1990) FEBS Lett 276:172-174.
"""

from __future__ import annotations

import numpy as np

from bio.scales import (
    PARKER_HYDROPHILICITY_SCALE,
    EMINI_SURFACE_ACCESSIBILITY_SCALE,
    KARPLUS_SCHULZ_FLEXIBILITY_SCALE,
    CHOU_FASMAN_BETA_TURN_SCALE,
    KOLASKAR_TONGAONKAR_ANTIGENICITY_SCALE,
    BEPIPRED_PROPENSITY_SCALE,
    LEVITT_COIL_SCALE,
    WELLING_ANTIGENICITY_SCALE,
    DISORDER_PROPENSITY_SCALE,
    AAP_PROPENSITY_SCALE,
    DIPEPTIDE_PROPENSITY,
    JANIN_SURFACE_SCALE,
)
from bio.sliding_window import (
    sequence_to_scores,
    sliding_window_mean,
    sliding_window_product,
)


# ---------------------------------------------------------------------------
# 1) Parker Hydrophilicity
# ---------------------------------------------------------------------------

class ParkerHydrophilicityPredictor:
    """Parker et al. (1986) HPLC-derived hydrophilicity predictor.

    Sliding-window arithmetic mean of scale values.
    Higher → more hydrophilic → more likely surface-exposed.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7, original publication).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = PARKER_HYDROPHILICITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw Parker hydrophilicity values."""
        return sequence_to_scores(sequence, self.scale, default=0.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed hydrophilicity profile (sliding window mean)."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 2) Emini Surface Accessibility
# ---------------------------------------------------------------------------

class EminiAccessibilityPredictor:
    """Emini et al. (1985) surface accessibility predictor.

    Uses the multiplicative formula:

    .. math::

        S_i = \\left(\\prod_{j \\in W} f_j\\right) \\times 0.37^{-n}

    Values > 1.0 suggest surface exposure.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 6, original publication).
    """

    def __init__(self, window_size: int = 6) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = EMINI_SURFACE_ACCESSIBILITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue fractional surface probabilities."""
        return sequence_to_scores(sequence, self.scale, default=0.50)

    def predict(self, sequence: str) -> np.ndarray:
        """Multiplicative surface accessibility profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_product(raw, self.window_size)


# ---------------------------------------------------------------------------
# 3) Karplus & Schulz Flexibility
# ---------------------------------------------------------------------------

class KarplusSchulzFlexibilityPredictor:
    """Karplus & Schulz (1985) backbone flexibility predictor.

    B-factor-derived scale normalised around 1.0.  Values > 1.0
    indicate higher backbone flexibility (loop/coil regions).

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = KARPLUS_SCHULZ_FLEXIBILITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw flexibility values."""
        return sequence_to_scores(sequence, self.scale, default=1.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed flexibility profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 4) Chou & Fasman Beta-Turn
# ---------------------------------------------------------------------------

class ChouFasmanBetaTurnPredictor:
    """Chou & Fasman (1978) beta-turn propensity predictor.

    P(turn) values — higher indicates higher beta-turn propensity.
    Beta turns are strongly associated with antigenic sites because
    they protrude from the protein surface.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = CHOU_FASMAN_BETA_TURN_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw beta-turn propensity values."""
        return sequence_to_scores(sequence, self.scale, default=1.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed beta-turn propensity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 5) Kolaskar & Tongaonkar Antigenicity
# ---------------------------------------------------------------------------

class KolaskarTongaonkarAntigenicityPredictor:
    """Kolaskar & Tongaonkar (1990) antigenicity predictor.

    Empirical scale based on the frequency of amino acids in known
    epitopes.  The original threshold is ``mean + 0.025 × std``.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = KOLASKAR_TONGAONKAR_ANTIGENICITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw antigenicity values."""
        return sequence_to_scores(sequence, self.scale, default=1.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed antigenicity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)

    def get_threshold(self, sequence: str) -> float:
        """Kolaskar & Tongaonkar antigenic threshold.

        ``threshold = mean + 0.025 × std`` of smoothed scores.
        """
        profile = self.predict(sequence)
        return float(np.mean(profile) + 0.025 * np.std(profile))


# ---------------------------------------------------------------------------
# 6) BepiPred Epitope Propensity
# ---------------------------------------------------------------------------

class BepiPredPropensityPredictor:
    """BepiPred-1.0 (Larsen et al. 2006) propensity predictor.

    Uses a hidden-Markov-model-derived propensity scale trained on
    curated epitope data.  Positive values indicate epitope propensity.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 9, wider than others to capture
        the contextual signal encoded in the HMM-derived scale).
    """

    def __init__(self, window_size: int = 9) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = BEPIPRED_PROPENSITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw BepiPred propensity values."""
        return sequence_to_scores(sequence, self.scale, default=0.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed BepiPred propensity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 7) Levitt Coil Propensity (secondary structure disorder)
# ---------------------------------------------------------------------------

class LevittCoilPredictor:
    """Levitt (1978) coil/disorder propensity predictor.

    Higher values indicate stronger preference for coil/loop
    conformations, which are strongly associated with B-cell
    epitopes on the protein surface.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = LEVITT_COIL_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw coil propensity values."""
        return sequence_to_scores(sequence, self.scale, default=1.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed coil propensity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 8) Welling Antigenicity
# ---------------------------------------------------------------------------

class WellingAntigenicityPredictor:
    """Welling et al. (1985) antigenicity predictor.

    Based on antigen frequency analysis of known epitopes.
    Captures complementary antigenic signal to Kolaskar-Tongaonkar.
    Positive values indicate antigenic propensity.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = WELLING_ANTIGENICITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw Welling antigenicity values."""
        return sequence_to_scores(sequence, self.scale, default=0.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed Welling antigenicity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 9) Disorder Propensity
# ---------------------------------------------------------------------------

class DisorderPropensityPredictor:
    """Simplified IUPred-like disorder propensity predictor.

    Intrinsically disordered regions are enriched in B-cell epitopes
    because they are flexible and surface-exposed.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 9, wider captures disorder context).
    """

    def __init__(self, window_size: int = 9) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = DISORDER_PROPENSITY_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw disorder propensity values."""
        return sequence_to_scores(sequence, self.scale, default=0.0)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed disorder propensity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 10) AAP (Amino Acid Pair) Propensity — ABCPred-style
# ---------------------------------------------------------------------------

class AAPairPropensityPredictor:
    """ABCPred-inspired amino acid pair propensity predictor.

    Uses dipeptide frequency enrichment in known B-cell epitopes
    to score each residue position. Each residue gets the average
    of its left-pair and right-pair propensities from the
    DIPEPTIDE_PROPENSITY table.

    Parameters
    ----------
    window_size : int
        Sliding window size for smoothing (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = AAP_PROPENSITY_SCALE
        self.dipeptide = DIPEPTIDE_PROPENSITY

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue AAP propensity using dipeptide context."""
        seq = sequence.upper()
        n = len(seq)
        if n == 0:
            return np.array([], dtype=np.float64)

        scores = np.zeros(n, dtype=np.float64)
        for i in range(n):
            # Single AA propensity
            base = self.scale.get(seq[i], 0.0)
            # Left dipeptide
            left_pair = 0.0
            if i > 0:
                dp = seq[i-1] + seq[i]
                left_pair = self.dipeptide.get(dp, 0.0)
            # Right dipeptide
            right_pair = 0.0
            if i < n - 1:
                dp = seq[i] + seq[i+1]
                right_pair = self.dipeptide.get(dp, 0.0)
            scores[i] = base + 0.5 * (left_pair + right_pair)
        return scores

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed AAP propensity profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)


# ---------------------------------------------------------------------------
# 11) Janin Surface Exposure
# ---------------------------------------------------------------------------

class JaninSurfacePredictor:
    """Janin (1979) surface exposure propensity predictor.

    Based on fraction of amino acid surface exposed in folded proteins.
    Provides complementary surface information to Emini.

    Parameters
    ----------
    window_size : int
        Sliding window size (default 7).
    """

    def __init__(self, window_size: int = 7) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self.window_size = window_size
        self.scale = JANIN_SURFACE_SCALE

    def raw_scores(self, sequence: str) -> np.ndarray:
        """Per-residue raw Janin surface values."""
        return sequence_to_scores(sequence, self.scale, default=0.5)

    def predict(self, sequence: str) -> np.ndarray:
        """Smoothed Janin surface exposure profile."""
        raw = self.raw_scores(sequence)
        return sliding_window_mean(raw, self.window_size)
