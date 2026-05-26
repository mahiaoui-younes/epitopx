"""
Combined scoring engine for B-cell linear epitope prediction.

Computes a per-residue **CombinedScore** that fuses five
complementary physicochemical and structural-propensity signals:

.. math::

    \\text{CombinedScore}_i =
        w_1 \\cdot \\hat{H}_i
      + w_2 \\cdot \\hat{A}_i
      + w_3 \\cdot \\hat{F}_i
      + w_4 \\cdot \\hat{B}_i
      + w_5 \\cdot \\hat{T}_i

Where each :math:`\\hat{X}` is the min-max normalised profile and
:math:`w_k` are user-configurable weights.

Optionally, structural solvent-accessible surface area (SASA) from
a PDB file can be blended into the accessibility channel.

The final profile is smoothed with a sliding-window average and
re-normalised to [0, 1].

References
----------
Pellequer JL & Westhof E (1993) Methods Enzymol 237:1-11.
Saha S & Raghava GPS (2006) Proteins 65:40-48.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from bio.predictors import (
    ParkerHydrophilicityPredictor,
    EminiAccessibilityPredictor,
    KarplusSchulzFlexibilityPredictor,
    ChouFasmanBetaTurnPredictor,
    KolaskarTongaonkarAntigenicityPredictor,
    BepiPredPropensityPredictor,
    LevittCoilPredictor,
    WellingAntigenicityPredictor,
    DisorderPropensityPredictor,
    AAPairPropensityPredictor,
    JaninSurfacePredictor,
)
from bio.sliding_window import min_max_normalize, sliding_window_mean

# Optional IEDB API integration
try:
    from bio.iedb_api import IEDBBCellPredictor
    _IEDB_AVAILABLE = True
except ImportError:
    _IEDB_AVAILABLE = False


# ── All 7 IEDB B-cell prediction methods ────────────────────────────────────
# These are queried individually when use_iedb=True.
ALL_IEDB_METHODS = [
    "Bepipred-2.0",            # Random-forest model (strongest)
    "Bepipred",                # HMM-based (BepiPred 1.0)
    "Emini",                   # Surface accessibility
    "Kolaskar-Tongaonkar",     # Antigenicity
    "Parker",                  # Hydrophilicity
    "Chou-Fasman",             # Beta-turn propensity
    "Karplus-Schulz",          # Backbone flexibility
]

# Short keys used in weights / profiles / dataclass fields
IEDB_KEY_MAP = {
    "Bepipred-2.0":        "iedb_bepipred2",
    "Bepipred":            "iedb_bepipred1",
    "Emini":               "iedb_emini",
    "Kolaskar-Tongaonkar": "iedb_kolaskar",
    "Parker":              "iedb_parker",
    "Chou-Fasman":         "iedb_choufasman",
    "Karplus-Schulz":      "iedb_karplus",
}


# ── Default configurable parameters ──────────────────────────────────────────
# Weights are optimised for maximum sensitivity on IEDB-validated epitopes.
# 11 local scoring channels + 7 IEDB API channels = 18 total.

DEFAULT_WEIGHTS: dict[str, float] = {
    # ── 11 local channels (total ≈ 0.65) ──
    "hydrophilicity": 0.06,
    "accessibility": 0.07,
    "flexibility": 0.06,
    "beta_turn": 0.06,
    "antigenicity": 0.08,
    "bepipred": 0.08,
    "coil": 0.05,
    "welling": 0.07,
    "disorder": 0.05,
    "aapair": 0.04,
    "janin": 0.03,
    # ── 7 IEDB API channels (total ≈ 0.35) ──
    "iedb_bepipred2": 0.10,      # BepiPred-2.0  — strongest signal
    "iedb_bepipred1": 0.05,      # BepiPred 1.0  — HMM-based
    "iedb_emini": 0.04,          # Emini surface accessibility
    "iedb_kolaskar": 0.04,       # Kolaskar-Tongaonkar antigenicity
    "iedb_parker": 0.04,         # Parker hydrophilicity
    "iedb_choufasman": 0.04,     # Chou-Fasman beta-turn
    "iedb_karplus": 0.04,        # Karplus-Schulz flexibility
}

DEFAULT_WINDOW_SIZES: dict[str, int] = {
    "hydrophilicity": 7,
    "accessibility": 6,
    "flexibility": 7,
    "beta_turn": 7,
    "antigenicity": 7,
    "bepipred": 9,
    "coil": 7,
    "welling": 7,
    "disorder": 9,
    "aapair": 7,
    "janin": 7,
    "smoothing": 5,
}


# ── Per-residue result container ─────────────────────────────────────────────

@dataclass
class ResidueResult:
    """Score profile for a single residue position."""

    position: int            # 1-indexed
    amino_acid: str
    hydrophilicity: float    # Parker raw
    accessibility: float     # Emini raw
    flexibility: float       # Karplus-Schulz raw
    beta_turn: float         # Chou-Fasman raw
    antigenicity: float      # Kolaskar-Tongaonkar raw
    bepipred: float          # BepiPred-1.0 propensity
    coil: float              # Levitt coil propensity
    welling: float           # Welling antigenicity
    disorder: float          # Disorder propensity
    aapair: float            # AA pair propensity
    janin: float             # Janin surface exposure
    # ── 7 IEDB API channels (0.0 if API unavailable) ──
    iedb_bepipred2: float    # IEDB BepiPred-2.0 (random-forest)
    iedb_bepipred1: float    # IEDB BepiPred 1.0 (HMM)
    iedb_emini: float        # IEDB Emini surface accessibility
    iedb_kolaskar: float     # IEDB Kolaskar-Tongaonkar antigenicity
    iedb_parker: float       # IEDB Parker hydrophilicity
    iedb_choufasman: float   # IEDB Chou-Fasman beta-turn
    iedb_karplus: float      # IEDB Karplus-Schulz flexibility
    structural_sasa: float   # PDB SASA (0.0 if unavailable)
    combined_score: float    # Weighted normalised score [0, 1]
    consensus_count: int     # Number of methods scoring above their median
    is_exposed: bool         # True when accessibility > 1.0 or SASA > 0.25


# ── Scoring engine ───────────────────────────────────────────────────────────

class CombinedScorer:
    """Fuse five predictors into a single per-residue epitope score.

    Parameters
    ----------
    weights : dict[str, float] | None
        Scoring weights (keys: hydrophilicity, accessibility,
        flexibility, beta_turn, antigenicity).  ``None`` → defaults.
    window_sizes : dict[str, int] | None
        Sliding window sizes per predictor plus ``smoothing``.
        ``None`` → defaults.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        window_sizes: dict[str, int] | None = None,
        use_iedb: bool = False,
        iedb_methods: list[str] | None = None,
    ) -> None:
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.window_sizes = window_sizes or dict(DEFAULT_WINDOW_SIZES)
        self.use_iedb = use_iedb and _IEDB_AVAILABLE
        self._iedb: IEDBBCellPredictor | None = None
        if self.use_iedb:
            self._iedb = IEDBBCellPredictor(
                methods=iedb_methods or list(ALL_IEDB_METHODS),
                enabled=True,
            )

        self._hydro = ParkerHydrophilicityPredictor(
            self.window_sizes.get("hydrophilicity", 7)
        )
        self._access = EminiAccessibilityPredictor(
            self.window_sizes.get("accessibility", 6)
        )
        self._flex = KarplusSchulzFlexibilityPredictor(
            self.window_sizes.get("flexibility", 7)
        )
        self._turn = ChouFasmanBetaTurnPredictor(
            self.window_sizes.get("beta_turn", 7)
        )
        self._antig = KolaskarTongaonkarAntigenicityPredictor(
            self.window_sizes.get("antigenicity", 7)
        )
        self._bepipred = BepiPredPropensityPredictor(
            self.window_sizes.get("bepipred", 9)
        )
        self._coil = LevittCoilPredictor(
            self.window_sizes.get("coil", 7)
        )
        self._welling = WellingAntigenicityPredictor(
            self.window_sizes.get("welling", 7)
        )
        self._disorder = DisorderPropensityPredictor(
            self.window_sizes.get("disorder", 9)
        )
        self._aapair = AAPairPropensityPredictor(
            self.window_sizes.get("aapair", 7)
        )
        self._janin = JaninSurfacePredictor(
            self.window_sizes.get("janin", 7)
        )

    # ---- public API ---------------------------------------------------------

    def compute_profiles(
        self, sequence: str,
    ) -> dict[str, np.ndarray]:
        """Compute all raw (un-normalised) profiles.

        Returns a dict with keys:
        ``hydrophilicity``, ``accessibility``, ``flexibility``,
        ``beta_turn``, ``antigenicity``, ``bepipred``, ``coil``.
        """
        seq = sequence.upper().strip()
        profiles = {
            "hydrophilicity": self._hydro.predict(seq),
            "accessibility": self._access.predict(seq),
            "flexibility": self._flex.predict(seq),
            "beta_turn": self._turn.predict(seq),
            "antigenicity": self._antig.predict(seq),
            "bepipred": self._bepipred.predict(seq),
            "coil": self._coil.predict(seq),
            "welling": self._welling.predict(seq),
            "disorder": self._disorder.predict(seq),
            "aapair": self._aapair.predict(seq),
            "janin": self._janin.predict(seq),
        }

        # IEDB API — query all 7 methods individually
        n = len(seq)
        if self._iedb is not None:
            try:
                iedb_results = self._iedb.predict_all(seq)
                for method_name, key in IEDB_KEY_MAP.items():
                    if method_name in iedb_results:
                        profiles[key] = iedb_results[method_name]
                    else:
                        profiles[key] = np.zeros(n, dtype=np.float64)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "IEDB API batch query failed: %s — all IEDB channels zeroed.", exc
                )
                for key in IEDB_KEY_MAP.values():
                    profiles[key] = np.zeros(n, dtype=np.float64)
        else:
            for key in IEDB_KEY_MAP.values():
                profiles[key] = np.zeros(n, dtype=np.float64)

        return profiles

    def compute_combined_score(
        self,
        sequence: str,
        structural_sasa: np.ndarray | None = None,
    ) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        """Compute the combined epitope score per residue.

        Parameters
        ----------
        sequence : str
            Protein sequence (single-letter codes).
        structural_sasa : np.ndarray | None
            Per-residue relative SASA from PDB (optional).

        Returns
        -------
        combined : np.ndarray
            Combined score per residue in [0, 1].
        profiles : dict[str, np.ndarray]
            All raw and normalised profiles.
        """
        seq = sequence.upper().strip()
        n = len(seq)
        profiles = self.compute_profiles(seq)

        # Normalise each profile to [0, 1]
        norm: dict[str, np.ndarray] = {}
        for key in ("hydrophilicity", "flexibility", "beta_turn",
                     "antigenicity", "bepipred", "coil", "welling",
                     "disorder", "aapair", "janin"):
            norm[key] = min_max_normalize(profiles[key])

        # IEDB channels: normalise only if we have real (non-zero) scores
        iedb_keys = list(IEDB_KEY_MAP.values())
        for ik in iedb_keys:
            raw = profiles.get(ik, np.zeros(n))
            if np.any(raw != 0):
                norm[ik] = min_max_normalize(raw)
            else:
                norm[ik] = np.zeros(n, dtype=np.float64)

        # Accessibility: log-compress the multiplicative Emini values
        # before normalisation so that extremely large products do not
        # dominate.  log1p is safe for non-negative Emini scores.
        log_acc = np.log1p(np.clip(profiles["accessibility"], 0.0, None))
        norm["accessibility"] = min_max_normalize(log_acc)

        # Blend structural SASA when available
        if structural_sasa is not None and len(structural_sasa) == n:
            norm_sasa = min_max_normalize(structural_sasa)
            norm["accessibility"] = 0.5 * norm["accessibility"] + 0.5 * norm_sasa

        # ── Consensus count per residue ──
        # How many of the normalised methods score above their own median?
        # This rewards positions where multiple independent methods agree.
        medians = {k: np.median(v) for k, v in norm.items()}
        consensus = np.zeros(n, dtype=np.int32)
        for k, arr in norm.items():
            consensus += (arr >= medians[k]).astype(np.int32)
        # Normalise consensus to [0, 1] for optional blending
        norm_consensus = consensus.astype(np.float64) / len(norm)

        # ── Charged residue density ──
        _CHARGED = set("DEKR")
        charge_density = np.zeros(n, dtype=np.float64)
        charge_window = 7
        ch_half = charge_window // 2
        for i in range(n):
            lo_c = max(0, i - ch_half)
            hi_c = min(n, i + ch_half + 1)
            n_charged = sum(1 for aa in seq[lo_c:hi_c] if aa in _CHARGED)
            charge_density[i] = n_charged / (hi_c - lo_c)

        # Weighted combination
        w = self.weights

        # Determine which IEDB channels are available (have non-zero data)
        iedb_available_keys = [ik for ik in iedb_keys if np.any(norm[ik] != 0)]
        iedb_unavailable_keys = [ik for ik in iedb_keys if ik not in iedb_available_keys]

        # Total IEDB weight that needs to be redistributed to local channels
        total_iedb_residual = sum(w.get(ik, 0.0) for ik in iedb_unavailable_keys)
        n_local = 11  # number of local (non-IEDB) channels
        extra_per_channel = total_iedb_residual / n_local if total_iedb_residual > 0 else 0.0

        # Local channels with redistributed weight
        combined = (
            (w.get("hydrophilicity", 0.06) + extra_per_channel) * norm["hydrophilicity"]
            + (w.get("accessibility", 0.07) + extra_per_channel) * norm["accessibility"]
            + (w.get("flexibility", 0.06) + extra_per_channel) * norm["flexibility"]
            + (w.get("beta_turn", 0.06) + extra_per_channel) * norm["beta_turn"]
            + (w.get("antigenicity", 0.08) + extra_per_channel) * norm["antigenicity"]
            + (w.get("bepipred", 0.08) + extra_per_channel) * norm["bepipred"]
            + (w.get("coil", 0.05) + extra_per_channel) * norm["coil"]
            + (w.get("welling", 0.07) + extra_per_channel) * norm["welling"]
            + (w.get("disorder", 0.05) + extra_per_channel) * norm["disorder"]
            + (w.get("aapair", 0.04) + extra_per_channel) * norm["aapair"]
            + (w.get("janin", 0.03) + extra_per_channel) * norm["janin"]
        )

        # Add available IEDB channels
        for ik in iedb_available_keys:
            combined = combined + w.get(ik, 0.04) * norm[ik]

        # Charged residue density boost (max +8%)
        combined = combined + 0.08 * charge_density

        # Hydrophobic surface antigenicity boost:
        # Moderately hydrophobic regions (0.3-0.6 fraction) that also have
        # good accessibility can be antigenic surface patches
        _HP_RESIDUES = set("AILMFWVP")
        hp_boost = np.zeros(n, dtype=np.float64)
        hp_window = 9
        hp_half = hp_window // 2
        for i in range(n):
            lo_h = max(0, i - hp_half)
            hi_h = min(n, i + hp_half + 1)
            seg = seq[lo_h:hi_h]
            hp_frac = sum(1 for aa in seg if aa in _HP_RESIDUES) / len(seg)
            # Boost moderate hydrophobicity — use antigenicity as gate
            # instead of accessibility to catch membrane-proximal epitopes
            if 0.25 <= hp_frac <= 0.75:
                antig_val = norm["antigenicity"][i] if i < len(norm["antigenicity"]) else 0
                if antig_val > 0.25:  # Must have antigenic potential
                    hp_boost[i] = 0.06 * (1.0 - abs(hp_frac - 0.50) / 0.30)
        combined = combined + hp_boost

        # Apply graduated consensus bonus (up to 18 channels when IEDB active):
        #   5+ methods agree -> +2%     10+ methods agree -> +16%
        #   6+ methods agree -> +4%     11+ methods agree -> +20%
        #   7+ methods agree -> +6%     12+ methods agree -> +24%
        #   8+ methods agree -> +9%     13+ methods agree -> +28%
        #   9+ methods agree -> +12%    14+ methods agree -> +32%
        #                               15+ methods agree -> +36%
        #                               16+ methods agree -> +40%
        n_methods = len(norm)
        consensus_bonus = np.zeros(n, dtype=np.float64)
        consensus_bonus[consensus >= 5] = 0.02
        consensus_bonus[consensus >= 6] = 0.04
        consensus_bonus[consensus >= 7] = 0.06
        consensus_bonus[consensus >= 8] = 0.09
        consensus_bonus[consensus >= 9] = 0.12
        consensus_bonus[consensus >= 10] = 0.16
        consensus_bonus[consensus >= 11] = 0.20
        consensus_bonus[consensus >= 12] = 0.24
        consensus_bonus[consensus >= 13] = 0.28
        consensus_bonus[consensus >= 14] = 0.32
        consensus_bonus[consensus >= 15] = 0.36
        consensus_bonus[consensus >= 16] = 0.40
        combined = combined * (1.0 + consensus_bonus)

        # Terminal exposure boost: first/last 15% of sequence get slight
        # bonus since termini are often surface-exposed and antigenic.
        terminal_zone = max(5, int(n * 0.15))
        terminal_boost = np.zeros(n, dtype=np.float64)
        # Ramp from 0.03 at terminus to 0 at boundary
        for i in range(terminal_zone):
            fade = 1.0 - i / terminal_zone
            terminal_boost[i] = 0.03 * fade
            terminal_boost[n - 1 - i] = max(
                terminal_boost[n - 1 - i], 0.03 * fade
            )
        combined = combined + terminal_boost

        # Amphipathic region boost: residues near a hydrophobic/hydrophilic
        # transition get a small bonus (amphipathic helices are antigenic)
        _HYDROPHOBIC = set("VILFWM")
        _HYDROPHILIC = set("DEKRNQST")
        amphi_boost = np.zeros(n, dtype=np.float64)
        for i in range(1, n - 1):
            left_hydrophobic = seq[i - 1] in _HYDROPHOBIC
            right_hydrophilic = seq[min(i + 1, n - 1)] in _HYDROPHILIC
            left_hydrophilic = seq[i - 1] in _HYDROPHILIC
            right_hydrophobic = seq[min(i + 1, n - 1)] in _HYDROPHOBIC
            if (left_hydrophobic and right_hydrophilic) or \
               (left_hydrophilic and right_hydrophobic):
                amphi_boost[i] = 0.04
        combined = combined + amphi_boost

        # Proline/glycine loop boost: PG, GP, PP motifs are strong turn
        # signals and frequent in epitopes
        pg_boost = np.zeros(n, dtype=np.float64)
        for i in range(n - 1):
            pair = seq[i:i+2]
            if pair in ("PG", "GP", "PP", "NG", "DG", "GN", "GD"):
                pg_boost[i] += 0.02
                pg_boost[i + 1] += 0.02
        combined = combined + pg_boost

        # Charged cluster boost: clusters of 3+ charged/polar residues
        # in a 5-residue window are strong epitope signals
        _CHARGED_POLAR = set("DEKRNQST")
        cluster_boost = np.zeros(n, dtype=np.float64)
        for i in range(n):
            lo_cl = max(0, i - 2)
            hi_cl = min(n, i + 3)
            n_cp = sum(1 for aa in seq[lo_cl:hi_cl] if aa in _CHARGED_POLAR)
            if n_cp >= 3:
                cluster_boost[i] = 0.03 * (n_cp / (hi_cl - lo_cl))
        combined = combined + cluster_boost

        # Smooth
        sw = self.window_sizes.get("smoothing", 9)
        if n >= sw:
            combined = sliding_window_mean(combined, sw)

        # Final normalisation to [0, 1]
        combined = min_max_normalize(combined)

        # Store normalised profiles for downstream use
        for key, arr in norm.items():
            profiles[f"norm_{key}"] = arr
        profiles["combined_score"] = combined
        profiles["consensus_count"] = consensus

        return combined, profiles

    def get_residue_results(
        self,
        sequence: str,
        structural_sasa: np.ndarray | None = None,
    ) -> list[ResidueResult]:
        """Return a :class:`ResidueResult` for every position.

        Parameters
        ----------
        sequence : str
            Protein sequence.
        structural_sasa : np.ndarray | None
            PDB-derived per-residue relative SASA (optional).

        Returns
        -------
        list[ResidueResult]
        """
        seq = sequence.upper().strip()
        n = len(seq)
        combined, profiles = self.compute_combined_score(seq, structural_sasa)

        results: list[ResidueResult] = []
        for i, aa in enumerate(seq):
            sasa_val = (
                float(structural_sasa[i])
                if structural_sasa is not None and i < len(structural_sasa)
                else 0.0
            )
            exposed = (
                structural_sasa[i] >= 0.25
                if structural_sasa is not None and i < len(structural_sasa)
                else profiles["accessibility"][i] >= 1.0
            )
            results.append(
                ResidueResult(
                    position=i + 1,
                    amino_acid=aa,
                    hydrophilicity=float(profiles["hydrophilicity"][i]),
                    accessibility=float(profiles["accessibility"][i]),
                    flexibility=float(profiles["flexibility"][i]),
                    beta_turn=float(profiles["beta_turn"][i]),
                    antigenicity=float(profiles["antigenicity"][i]),
                    bepipred=float(profiles["bepipred"][i]),
                    coil=float(profiles["coil"][i]),
                    welling=float(profiles["welling"][i]),
                    disorder=float(profiles["disorder"][i]),
                    aapair=float(profiles["aapair"][i]),
                    janin=float(profiles["janin"][i]),
                    iedb_bepipred2=float(profiles.get("iedb_bepipred2", np.zeros(n))[i]),
                    iedb_bepipred1=float(profiles.get("iedb_bepipred1", np.zeros(n))[i]),
                    iedb_emini=float(profiles.get("iedb_emini", np.zeros(n))[i]),
                    iedb_kolaskar=float(profiles.get("iedb_kolaskar", np.zeros(n))[i]),
                    iedb_parker=float(profiles.get("iedb_parker", np.zeros(n))[i]),
                    iedb_choufasman=float(profiles.get("iedb_choufasman", np.zeros(n))[i]),
                    iedb_karplus=float(profiles.get("iedb_karplus", np.zeros(n))[i]),
                    structural_sasa=sasa_val,
                    combined_score=float(combined[i]),
                    consensus_count=int(profiles["consensus_count"][i]),
                    is_exposed=bool(exposed),
                )
            )
        return results
