"""
Surface accessibility prediction using Emini et al. (1985) method.

Method: The surface probability S(i) for a window of length n
centered at position i is calculated as:

    S(i) = (∏ f(j) for j in window) × (0.37)^(-n)

where f(j) is the fractional surface probability of amino acid j.
Values > 1.0 indicate likely surface-exposed regions.

Reference:
    Emini EA, Hughes JV, Perlow DS & Boger J (1985)
    Induction of hepatitis A virus-neutralizing antibody by a
    virus-specific synthetic peptide. J Virol 55:836-839.
"""

import numpy as np
from typing import List
from .scales import EMINI_SCALE


class EminiPredictor:
    """
    Predicts surface accessibility using the Emini et al. (1985) method.
    Based on fractional surface probability of amino acids.
    """

    def __init__(self, window_size: int = 6):
        """
        Initialize the Emini surface accessibility predictor.

        Args:
            window_size: Size of the sliding window (default: 6, as in
                         the original publication).
        """
        if window_size < 1:
            raise ValueError("Window size must be >= 1")
        self.window_size = window_size
        self.scale = EMINI_SCALE

    def _get_fractional_probabilities(self, sequence: str) -> np.ndarray:
        """
        Get fractional surface probability for each residue.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of fractional surface probabilities.
        """
        probs = np.zeros(len(sequence))
        for i, aa in enumerate(sequence.upper()):
            if aa in self.scale:
                probs[i] = self.scale[aa]
            else:
                probs[i] = 0.50  # Neutral probability for unknown
        return probs

    def predict(self, sequence: str) -> np.ndarray:
        """
        Calculate surface accessibility profile.

        For each position i, the surface probability is computed as:
            S(i) = (∏ f(j)) × (0.37)^(-n)

        where the product runs over the window of size n centered at i.

        Args:
            sequence: Protein sequence (single-letter codes).

        Returns:
            Array of surface accessibility scores per residue.
            Values > 1.0 suggest surface-exposed regions.
        """
        sequence = sequence.upper().strip()
        if len(sequence) == 0:
            raise ValueError("Sequence is empty")

        frac_probs = self._get_fractional_probabilities(sequence)
        scores = np.zeros(len(sequence))
        n = self.window_size
        half_w = n // 2
        correction_factor = (0.37) ** (-n)

        for i in range(len(sequence)):
            start = max(0, i - half_w)
            end = min(len(sequence), i + half_w + 1)
            actual_n = end - start

            # Product of fractional probabilities in window
            product = np.prod(frac_probs[start:end])

            # Apply Emini correction factor
            scores[i] = product * (0.37) ** (-actual_n)

        return scores

    def get_exposed_regions(
        self, sequence: str, threshold: float = 1.0
    ) -> List[dict]:
        """
        Identify contiguous surface-exposed regions.

        Args:
            sequence: Protein sequence.
            threshold: Minimum surface probability (default: 1.0).

        Returns:
            List of dicts with exposed region information.
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
