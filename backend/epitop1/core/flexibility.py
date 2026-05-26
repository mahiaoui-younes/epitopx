"""
Flexibility prediction using Karplus & Schulz (1985) scale.

Method: Sliding window average of normalized B-factor-derived flexibility values.
Flexible regions tend to be more accessible and immunogenic.

Reference:
    Karplus PA & Schulz GE (1985) Prediction of chain flexibility in proteins.
    Naturwissenschaften 72:212-213.
"""

import numpy as np
from typing import List
from .scales import KARPLUS_SCHULZ_SCALE


class KarplusSchulzPredictor:
    """
    Predicts backbone flexibility using the Karplus & Schulz (1985) scale.
    Based on B-factor analysis of experimentally determined protein structures.
    """

    def __init__(self, window_size: int = 7):
        """
        Initialize the Karplus & Schulz predictor.

        Args:
            window_size: Size of the sliding window (default: 7).
        """
        if window_size < 1:
            raise ValueError("Window size must be >= 1")
        self.window_size = window_size
        self.scale = KARPLUS_SCHULZ_SCALE

    def _get_raw_scores(self, sequence: str) -> np.ndarray:
        """
        Get raw flexibility value for each residue.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of flexibility values per residue.
        """
        scores = np.zeros(len(sequence))
        for i, aa in enumerate(sequence.upper()):
            if aa in self.scale:
                scores[i] = self.scale[aa]
            else:
                scores[i] = 1.0  # Neutral flexibility
        return scores

    def predict(self, sequence: str) -> np.ndarray:
        """
        Calculate flexibility profile using sliding window averaging.

        The Karplus & Schulz flexibility values are already normalized
        around 1.0. Values > 1.0 indicate higher flexibility.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of smoothed flexibility scores per residue.
        """
        sequence = sequence.upper().strip()
        if len(sequence) == 0:
            raise ValueError("Sequence is empty")

        raw_scores = self._get_raw_scores(sequence)

        if len(sequence) < self.window_size:
            return raw_scores

        smoothed = np.zeros(len(sequence))
        half_w = self.window_size // 2

        for i in range(len(sequence)):
            start = max(0, i - half_w)
            end = min(len(sequence), i + half_w + 1)
            smoothed[i] = np.mean(raw_scores[start:end])

        return smoothed

    def get_flexible_regions(
        self, sequence: str, threshold: float = 1.0
    ) -> List[dict]:
        """
        Identify contiguous flexible regions above threshold.

        Args:
            sequence: Protein sequence.
            threshold: Minimum flexibility score (default: 1.0, the scale center).

        Returns:
            List of dicts with region information.
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
                regions.append({
                    "start": start + 1,
                    "end": i,
                    "sequence": sequence[start:i],
                    "mean_score": float(np.mean(scores[start:i])),
                    "length": i - start,
                })

        if in_region:
            regions.append({
                "start": start + 1,
                "end": len(sequence),
                "sequence": sequence[start:],
                "mean_score": float(np.mean(scores[start:])),
                "length": len(sequence) - start,
            })

        return regions
