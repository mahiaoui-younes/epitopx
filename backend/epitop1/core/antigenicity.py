"""
Antigenicity prediction using Kolaskar & Tongaonkar (1990) method.

Method: Sliding window average of antigenicity values based on the
frequency of amino acids occurring in known experimentally determined
antigenic determinants. The method achieves ~75% accuracy.

An antigenic peptide is predicted when the average antigenicity value
of a window exceeds 1.0.

Reference:
    Kolaskar AS & Tongaonkar PC (1990) A semi-empirical method for
    prediction of antigenic determinants on protein antigens.
    FEBS Lett 276:172-174.
"""

import numpy as np
from typing import List
from .scales import KOLASKAR_TONGAONKAR_SCALE


class KolaskarTongaonkarPredictor:
    """
    Predicts antigenicity using the Kolaskar & Tongaonkar (1990) scale.
    """

    def __init__(self, window_size: int = 7):
        """
        Initialize the Kolaskar & Tongaonkar predictor.

        Args:
            window_size: Size of the sliding window (default: 7).
        """
        if window_size < 1:
            raise ValueError("Window size must be >= 1")
        self.window_size = window_size
        self.scale = KOLASKAR_TONGAONKAR_SCALE

    def _get_raw_scores(self, sequence: str) -> np.ndarray:
        """
        Get raw antigenicity value for each residue.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of antigenicity values per residue.
        """
        scores = np.zeros(len(sequence))
        for i, aa in enumerate(sequence.upper()):
            if aa in self.scale:
                scores[i] = self.scale[aa]
            else:
                scores[i] = 1.0  # Neutral antigenicity
        return scores

    def predict(self, sequence: str) -> np.ndarray:
        """
        Calculate antigenicity profile using sliding window averaging.

        The Kolaskar & Tongaonkar method uses the average antigenicity
        value of a sliding window. Values > mean + 0.025 × SD are
        considered antigenic in the original paper.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of smoothed antigenicity scores per residue.
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

    def get_antigenic_threshold(self, sequence: str) -> float:
        """
        Calculate the antigenicity threshold as per Kolaskar & Tongaonkar.

        Threshold = average + 0.025 × standard_deviation of all window scores.

        Args:
            sequence: Protein sequence.

        Returns:
            Antigenicity threshold value.
        """
        scores = self.predict(sequence)
        return float(np.mean(scores) + 0.025 * np.std(scores))

    def get_antigenic_regions(
        self, sequence: str, threshold: float = None
    ) -> List[dict]:
        """
        Identify contiguous antigenic regions.

        Args:
            sequence: Protein sequence.
            threshold: Minimum antigenicity score. If None, uses the
                      Kolaskar & Tongaonkar formula.

        Returns:
            List of dicts with antigenic region information.
        """
        scores = self.predict(sequence)
        if threshold is None:
            threshold = self.get_antigenic_threshold(sequence)

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
