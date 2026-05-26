"""
``bio`` — Advanced linear B-cell epitope prediction module.

This package provides a self-contained, scientifically validated
epitope prediction pipeline built entirely from classical
bioinformatics algorithms.  No external APIs or cloud services
are used; all computations run locally.

Submodules
----------
scales
    Amino acid physicochemical property scales.
sliding_window
    Reusable sliding-window primitives (additive & multiplicative).
predictors
    Eight independent residue-level predictors:
      1. Parker hydrophilicity (1986)
      2. Emini surface accessibility (1985)
      3. Karplus-Schulz flexibility (1985)
      4. Chou-Fasman beta-turn propensity (1978)
      5. Kolaskar-Tongaonkar antigenicity (1990)
      6. BepiPred-1.0 propensity (Larsen 2006)
      7. Levitt coil/disorder (1978)
      8. Welling antigenicity (1985)
scoring
    Combined scoring engine that fuses all eight predictors into
    a single per-residue CombinedScore.
epitope_detector
    Identifies candidate epitopes from the CombinedScore profile.
pdb_analysis
    Optional PDB structural support (BioPython SASA).
visualization
    Matplotlib-based score curve plotting with epitope highlights.

Quick-start
-----------
::

    from bio import CombinedScorer, EpitopeDetector

    scorer = CombinedScorer()
    results = scorer.get_residue_results("MKFFYLFVL...")
    detector = EpitopeDetector()
    hits = detector.detect("MKFFYLFVL...", results)

    for h in hits:
        print(f"#{h.rank} {h.start}-{h.end} {h.sequence} score={h.combined_score:.3f}")
"""

# ── Scales ──
from bio.scales import (
    PARKER_HYDROPHILICITY_SCALE,
    EMINI_SURFACE_ACCESSIBILITY_SCALE,
    KARPLUS_SCHULZ_FLEXIBILITY_SCALE,
    CHOU_FASMAN_BETA_TURN_SCALE,
    KOLASKAR_TONGAONKAR_ANTIGENICITY_SCALE,
    STANDARD_AMINO_ACIDS,
)

# ── Sliding window ──
from bio.sliding_window import (
    sequence_to_scores,
    sliding_window_mean,
    sliding_window_product,
    min_max_normalize,
)

# ── Predictors ──
from bio.predictors import (
    ParkerHydrophilicityPredictor,
    EminiAccessibilityPredictor,
    KarplusSchulzFlexibilityPredictor,
    ChouFasmanBetaTurnPredictor,
    KolaskarTongaonkarAntigenicityPredictor,
    BepiPredPropensityPredictor,
    LevittCoilPredictor,
    WellingAntigenicityPredictor,
)

# ── Scoring ──
from bio.scoring import CombinedScorer, ResidueResult

# ── Detection ──
from bio.epitope_detector import EpitopeDetector, EpitopeHit

# ── PDB ──
from bio.pdb_analysis import parse_pdb_sasa, align_structure_to_sequence

# ── Visualization (lazy — optional matplotlib dependency) ──
# Import visualization at use-time because matplotlib is optional.

__all__ = [
    # scales
    "PARKER_HYDROPHILICITY_SCALE",
    "EMINI_SURFACE_ACCESSIBILITY_SCALE",
    "KARPLUS_SCHULZ_FLEXIBILITY_SCALE",
    "CHOU_FASMAN_BETA_TURN_SCALE",
    "KOLASKAR_TONGAONKAR_ANTIGENICITY_SCALE",
    "STANDARD_AMINO_ACIDS",
    # sliding window
    "sequence_to_scores",
    "sliding_window_mean",
    "sliding_window_product",
    "min_max_normalize",
    # predictors
    "ParkerHydrophilicityPredictor",
    "EminiAccessibilityPredictor",
    "KarplusSchulzFlexibilityPredictor",
    "ChouFasmanBetaTurnPredictor",
    "KolaskarTongaonkarAntigenicityPredictor",
    "BepiPredPropensityPredictor",
    "LevittCoilPredictor",
    "WellingAntigenicityPredictor",
    # scoring
    "CombinedScorer",
    "ResidueResult",
    # detection
    "EpitopeDetector",
    "EpitopeHit",
    # PDB
    "parse_pdb_sasa",
    "align_structure_to_sequence",
]
