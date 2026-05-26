"""
Global scoring engine for B linear epitope prediction.

Combines all individual bioinformatics scores into a unified
global score per residue:

    GLOBAL_SCORE = w1 * hydrophilicity + w2 * surface_accessibility
                 + w3 * flexibility + w4 * antigenicity
                 - w5 * hydrophobicity

All scores are min-max normalized to [0, 1] before combination.
The final profile is smoothed with a configurable sliding window.

References:
    Pellequer JL & Westhof E (1993) An empirical comparison of
    continuous epitope prediction methods. Methods Enzymol 237:1-11.

    Saha S & Raghava GPS (2006) Prediction of continuous B-cell
    epitopes in an antigen using recurrent neural network.
    Proteins 65:40-48.
"""

import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field

from core.hydrophilicity import HoppWoodsPredictor
from core.hydrophobicity import KyteDoolittlePredictor
from core.flexibility import KarplusSchulzPredictor
from core.accessibility import EminiPredictor
from core.antigenicity import KolaskarTongaonkarPredictor
from config import SCORING_WEIGHTS, WINDOW_SIZES


@dataclass
class ResidueScore:
    """Complete score profile for a single residue."""
    position: int           # 1-indexed position
    amino_acid: str         # One-letter code
    hydrophilicity: float   # Hopp & Woods
    hydrophobicity: float   # Kyte & Doolittle
    flexibility: float      # Karplus & Schulz
    accessibility: float    # Emini et al.
    antigenicity: float     # Kolaskar & Tongaonkar
    structural_sasa: float  # PDB-derived SASA (0 if no PDB)
    global_score: float     # Combined normalized score
    is_exposed: bool        # Surface-exposed flag


class GlobalScorer:
    """
    Combines multiple bioinformatics scores into a unified
    epitope prediction score per residue.
    """

    def __init__(
        self,
        weights: Dict[str, float] = None,
        window_sizes: Dict[str, int] = None,
    ):
        """
        Initialize the global scorer.

        Args:
            weights: Scoring weights (defaults from config).
            window_sizes: Sliding window sizes (defaults from config).
        """
        self.weights = weights or SCORING_WEIGHTS
        self.window_sizes = window_sizes or WINDOW_SIZES

        # Initialize predictors with configured window sizes
        self.hydrophilicity_predictor = HoppWoodsPredictor(
            self.window_sizes.get("hydrophilicity", 7)
        )
        self.hydrophobicity_predictor = KyteDoolittlePredictor(
            self.window_sizes.get("hydrophobicity", 9)
        )
        self.flexibility_predictor = KarplusSchulzPredictor(
            self.window_sizes.get("flexibility", 7)
        )
        self.accessibility_predictor = EminiPredictor(
            self.window_sizes.get("accessibility", 6)
        )
        self.antigenicity_predictor = KolaskarTongaonkarPredictor(
            self.window_sizes.get("antigenicity", 7)
        )

    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        """
        Robust normalization to [0, 1] range using percentile clipping.

        Uses 2nd and 98th percentiles to avoid extreme outliers
        (e.g., TM regions) from dominating the normalization.

        Args:
            arr: Input array.

        Returns:
            Normalized array clipped to [0, 1].
        """
        if len(arr) == 0:
            return arr
        p2 = np.percentile(arr, 2)
        p98 = np.percentile(arr, 98)
        if p98 - p2 < 1e-10:
            # Fallback to min-max
            min_val = np.min(arr)
            max_val = np.max(arr)
            if max_val - min_val < 1e-10:
                return np.full_like(arr, 0.5)
            return (arr - min_val) / (max_val - min_val)
        normalized = (arr - p2) / (p98 - p2)
        return np.clip(normalized, 0.0, 1.0)

    def compute_all_profiles(
        self, sequence: str
    ) -> Dict[str, np.ndarray]:
        """
        Compute all individual bioinformatics profiles.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Dict with raw score arrays for each method.
        """
        sequence = sequence.upper().strip()

        profiles = {
            "hydrophilicity": self.hydrophilicity_predictor.predict(sequence),
            "hydrophobicity": self.hydrophobicity_predictor.predict(sequence),
            "flexibility": self.flexibility_predictor.predict(sequence),
            "accessibility": self.accessibility_predictor.predict(sequence),
            "antigenicity": self.antigenicity_predictor.predict(sequence),
        }

        return profiles

    def compute_global_score(
        self,
        sequence: str,
        structural_sasa: np.ndarray = None,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Compute the global combined score for each residue.

        GLOBAL_SCORE = w1 * norm(hydrophilicity)
                     + w2 * norm(surface_accessibility)
                     + w3 * norm(flexibility)
                     + w4 * norm(antigenicity)
                     - w5 * norm(hydrophobicity)

        If structural SASA is provided, it is blended with the
        Emini accessibility score (50/50 by default).

        Args:
            sequence: Protein sequence.
            structural_sasa: Per-residue SASA from PDB (optional).

        Returns:
            Tuple of (global_scores, raw_profiles).
        """
        sequence = sequence.upper().strip()
        n = len(sequence)

        # Compute all raw profiles
        profiles = self.compute_all_profiles(sequence)

        # Normalize each profile to [0, 1]
        norm_hydrophilicity = self._normalize(profiles["hydrophilicity"])
        norm_hydrophobicity = self._normalize(profiles["hydrophobicity"])
        norm_flexibility = self._normalize(profiles["flexibility"])
        norm_accessibility = self._normalize(profiles["accessibility"])
        norm_antigenicity = self._normalize(profiles["antigenicity"])

        # Blend structural SASA with Emini accessibility if available
        if structural_sasa is not None and len(structural_sasa) == n:
            norm_struct_sasa = self._normalize(structural_sasa)
            # Blend: 50% Emini + 50% structural SASA
            combined_accessibility = (
                0.5 * norm_accessibility + 0.5 * norm_struct_sasa
            )
        elif structural_sasa is not None and len(structural_sasa) > 0:
            # Length mismatch: use only Emini
            combined_accessibility = norm_accessibility
        else:
            combined_accessibility = norm_accessibility

        # Apply weights
        w = self.weights
        global_scores = (
            w["w1_hydrophilicity"] * norm_hydrophilicity
            + w["w2_surface_accessibility"] * combined_accessibility
            + w["w3_flexibility"] * norm_flexibility
            + w["w4_antigenicity"] * norm_antigenicity
            - w["w5_hydrophobicity"] * norm_hydrophobicity
        )

        # Smooth global scores
        smooth_window = self.window_sizes.get("global_smoothing", 9)
        if n >= smooth_window:
            half_w = smooth_window // 2
            smoothed = np.zeros(n)
            for i in range(n):
                start = max(0, i - half_w)
                end = min(n, i + half_w + 1)
                smoothed[i] = np.mean(global_scores[start:end])
            global_scores = smoothed

        # Re-normalize final score to [0, 1]
        global_scores = self._normalize(global_scores)

        # Add normalized profiles to output
        profiles["norm_hydrophilicity"] = norm_hydrophilicity
        profiles["norm_hydrophobicity"] = norm_hydrophobicity
        profiles["norm_flexibility"] = norm_flexibility
        profiles["norm_accessibility"] = combined_accessibility
        profiles["norm_antigenicity"] = norm_antigenicity
        profiles["global_score"] = global_scores

        if structural_sasa is not None:
            profiles["structural_sasa"] = structural_sasa

        return global_scores, profiles

    def get_residue_scores(
        self,
        sequence: str,
        structural_sasa: np.ndarray = None,
    ) -> list:
        """
        Get detailed score for each residue.

        Args:
            sequence: Protein sequence.
            structural_sasa: Per-residue SASA from PDB (optional).

        Returns:
            List of ResidueScore objects.
        """
        sequence = sequence.upper().strip()
        global_scores, profiles = self.compute_global_score(
            sequence, structural_sasa
        )

        scores = []
        for i, aa in enumerate(sequence):
            # Determine exposure based on available data
            is_exposed = True
            if structural_sasa is not None and i < len(structural_sasa):
                is_exposed = structural_sasa[i] >= 0.25
            else:
                is_exposed = profiles["accessibility"][i] >= 1.0

            scores.append(ResidueScore(
                position=i + 1,
                amino_acid=aa,
                hydrophilicity=float(profiles["hydrophilicity"][i]),
                hydrophobicity=float(profiles["hydrophobicity"][i]),
                flexibility=float(profiles["flexibility"][i]),
                accessibility=float(profiles["accessibility"][i]),
                antigenicity=float(profiles["antigenicity"][i]),
                structural_sasa=float(
                    structural_sasa[i]
                    if structural_sasa is not None and i < len(structural_sasa)
                    else 0.0
                ),
                global_score=float(global_scores[i]),
                is_exposed=is_exposed,
            ))

        return scores
