"""
Hydrophobicity prediction using Kyte & Doolittle (1982) scale.

Method: Sliding window average of hydrophobicity values.
Regions with high hydrophobicity are likely buried/transmembrane.
Low hydrophobicity regions are more likely surface-exposed.

Reference:
    Kyte J & Doolittle RF (1982) A simple method for displaying the
    hydropathic character of a protein. J Mol Biol 157:105-132.
"""

import numpy as np
from typing import List
from .scales import KYTE_DOOLITTLE_SCALE


class KyteDoolittlePredictor:
    """
    Predicts hydrophobicity profile using the Kyte & Doolittle (1982) scale.
    """

    def __init__(self, window_size: int = 9):
        """
        Initialize the Kyte & Doolittle predictor.

        Args:
            window_size: Size of the sliding window (default: 9, as recommended
                         by the original publication).
        """
        if window_size < 1:
            raise ValueError("Window size must be >= 1")
        self.window_size = window_size
        self.scale = KYTE_DOOLITTLE_SCALE

    def _get_raw_scores(self, sequence: str) -> np.ndarray:
        """
        Get raw hydrophobicity value for each residue.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of hydrophobicity values per residue.
        """
        scores = np.zeros(len(sequence))
        for i, aa in enumerate(sequence.upper()):
            if aa in self.scale:
                scores[i] = self.scale[aa]
            else:
                scores[i] = 0.0
        return scores

    def predict(self, sequence: str) -> np.ndarray:
        """
        Calculate hydrophobicity profile using sliding window averaging.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of smoothed hydrophobicity scores per residue.
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

    def detect_transmembrane_regions(
        self, sequence: str, threshold: float = 1.6, min_length: int = 15
    ) -> List[dict]:
        """
        Detect potential transmembrane regions based on sustained high
        hydrophobicity. Used for exclusion from epitope candidates.

        Args:
            sequence: Protein sequence.
            threshold: Hydrophobicity threshold for TM detection.
            min_length: Minimum length of TM segment.

        Returns:
            List of dicts with TM region positions.
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
                length = i - start
                if length >= min_length:
                    regions.append({
                        "start": start + 1,
                        "end": i,
                        "sequence": sequence[start:i],
                        "mean_hydrophobicity": float(np.mean(scores[start:i])),
                        "length": length,
                        "type": "transmembrane",
                    })

        if in_region:
            length = len(sequence) - start
            if length >= min_length:
                regions.append({
                    "start": start + 1,
                    "end": len(sequence),
                    "sequence": sequence[start:],
                    "mean_hydrophobicity": float(np.mean(scores[start:])),
                    "length": length,
                    "type": "transmembrane",
                })

        return regions
