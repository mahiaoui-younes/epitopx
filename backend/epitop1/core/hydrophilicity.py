"""
Hydrophilicity prediction using Hopp & Woods (1981) scale.

Method: Sliding window average of hydrophilicity values.
Regions with high hydrophilicity are more likely to be surface-exposed
and thus accessible to antibodies.

Reference:
    Hopp TP & Woods KR (1981) Prediction of protein antigenic determinants
    from amino acid sequences. PNAS 78:3824-3828.
"""

import numpy as np
from typing import List, Optional
from .scales import HOPP_WOODS_SCALE, STANDARD_AA


class HoppWoodsPredictor:
    """
    Predicts hydrophilicity profile of a protein sequence
    using the Hopp & Woods (1981) scale with sliding window averaging.
    """

    def __init__(self, window_size: int = 7):
        """
        Initialize the Hopp & Woods predictor.

        Args:
            window_size: Size of the sliding window (default: 7, as recommended
                         by the original publication). Must be odd.
        """
        if window_size < 1:
            raise ValueError("Window size must be >= 1")
        self.window_size = window_size
        self.scale = HOPP_WOODS_SCALE

    def _get_raw_scores(self, sequence: str) -> np.ndarray:
        """
        Get raw hydrophilicity value for each residue.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of hydrophilicity values per residue.
        """
        scores = np.zeros(len(sequence))
        for i, aa in enumerate(sequence.upper()):
            if aa in self.scale:
                scores[i] = self.scale[aa]
            else:
                scores[i] = 0.0  # Unknown residues get neutral score
        return scores

    def predict(self, sequence: str) -> np.ndarray:
        """
        Calculate hydrophilicity profile using sliding window averaging.

        The score at position i is the average of hydrophilicity values
        within the window centered at position i.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of smoothed hydrophilicity scores per residue.

        Raises:
            ValueError: If sequence is empty or too short.
        """
        sequence = sequence.upper().strip()
        if len(sequence) == 0:
            raise ValueError("Sequence is empty")

        raw_scores = self._get_raw_scores(sequence)

        if len(sequence) < self.window_size:
            return raw_scores

        # Sliding window average
        smoothed = np.zeros(len(sequence))
        half_w = self.window_size // 2

        for i in range(len(sequence)):
            start = max(0, i - half_w)
            end = min(len(sequence), i + half_w + 1)
            smoothed[i] = np.mean(raw_scores[start:end])

        return smoothed

    def get_hydrophilic_regions(
        self, sequence: str, threshold: float = 0.0
    ) -> List[dict]:
        """
        Identify contiguous hydrophilic regions above threshold.

        Args:
            sequence: Protein sequence.
            threshold: Minimum hydrophilicity score (default: 0.0).

        Returns:
            List of dicts with 'start', 'end', 'sequence', 'mean_score'.
        """
        scores = self.predict(sequence)
        regions = []
        in_region = False
        start = 0

        for i, score in enumerate(scores):
            if score >= threshold and not in_region:
                in_region = True
                start = i
            elif score < threshold and in_region:
                in_region = False
                region_seq = sequence[start:i]
                region_scores = scores[start:i]
                regions.append({
                    "start": start + 1,  # 1-indexed
                    "end": i,
                    "sequence": region_seq,
                    "mean_score": float(np.mean(region_scores)),
                    "max_score": float(np.max(region_scores)),
                    "length": i - start,
                })

        # Close final region if still open
        if in_region:
            region_seq = sequence[start:]
            region_scores = scores[start:]
            regions.append({
                "start": start + 1,
                "end": len(sequence),
                "sequence": region_seq,
                "mean_score": float(np.mean(region_scores)),
                "max_score": float(np.max(region_scores)),
                "length": len(sequence) - start,
            })

        return regions
