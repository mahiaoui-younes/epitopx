"""
Sliding window utilities for sequence-based epitope prediction.

Provides reusable primitives for applying sliding-window averaging
over a per-residue property vector.  Two modes are supported:

    1. **Additive** (default) — arithmetic mean of scale values inside
       the window.  Used by Parker, Karplus-Schulz, Chou-Fasman, and
       Kolaskar-Tongaonkar methods.

    2. **Multiplicative** — product of scale values corrected by
       a normalisation factor, as required by the Emini surface
       accessibility formula.

All functions accept and return NumPy arrays for efficient
downstream numeric processing.

References
----------
Pellequer JL & Westhof E (1993)
    An empirical comparison of continuous epitope prediction methods.
    Methods Enzymol 237:1-11.
"""

from __future__ import annotations

import numpy as np


def sequence_to_scores(
    sequence: str,
    scale: dict[str, float],
    default: float = 0.0,
) -> np.ndarray:
    """Map each residue to its raw scale value.

    Parameters
    ----------
    sequence : str
        Upper-case single-letter amino acid sequence.
    scale : dict[str, float]
        Amino acid → numeric value mapping.
    default : float
        Value for residues not present in *scale*.

    Returns
    -------
    np.ndarray
        1-D array of per-residue raw scores (length = len(sequence)).
    """
    return np.array(
        [scale.get(aa, default) for aa in sequence.upper()],
        dtype=np.float64,
    )


def sliding_window_mean(
    values: np.ndarray,
    window_size: int,
) -> np.ndarray:
    """Sliding window arithmetic mean (edge-padded).

    The window is centred at each position.  At sequence termini the
    window is truncated symmetrically so that every position receives
    a score.

    Parameters
    ----------
    values : np.ndarray
        Per-residue raw values.
    window_size : int
        Must be ≥ 1.  Even values are allowed — the window is
        ``[i - half, i + half]`` where ``half = window_size // 2``.

    Returns
    -------
    np.ndarray
        Smoothed scores (same length as *values*).
    """
    n = len(values)
    if n == 0 or window_size < 1:
        return values.copy()
    if window_size >= n:
        return np.full(n, np.mean(values))

    half = window_size // 2
    smoothed = np.empty(n, dtype=np.float64)
    # Use cumulative sum for O(n) performance
    cumsum = np.concatenate(([0.0], np.cumsum(values)))
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        smoothed[i] = (cumsum[hi] - cumsum[lo]) / (hi - lo)
    return smoothed


def sliding_window_product(
    values: np.ndarray,
    window_size: int,
    correction_base: float = 0.37,
) -> np.ndarray:
    """Multiplicative sliding window as used by the Emini formula.

    .. math::

        S_i = \\left(\\prod_{j \\in W_i} f_j\\right) \\times 0.37^{-|W_i|}

    Parameters
    ----------
    values : np.ndarray
        Per-residue fractional surface probabilities.
    window_size : int
        Sliding window size (Emini default: 6).
    correction_base : float
        Correction factor base (default 0.37 per Emini 1985).

    Returns
    -------
    np.ndarray
        Surface accessibility score per residue.
    """
    n = len(values)
    if n == 0 or window_size < 1:
        return values.copy()

    half = window_size // 2
    scores = np.empty(n, dtype=np.float64)

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        actual_n = hi - lo
        product = np.prod(values[lo:hi])
        scores[i] = product * (correction_base ** (-actual_n))

    return scores


def min_max_normalize(
    values: np.ndarray,
    percentile_clip: tuple[float, float] = (2.0, 98.0),
) -> np.ndarray:
    """Robust min-max normalisation to [0, 1].

    Uses percentile clipping to avoid outlier dominance.

    Parameters
    ----------
    values : np.ndarray
        Raw score array.
    percentile_clip : tuple[float, float]
        Lower and upper percentile bounds for clipping.

    Returns
    -------
    np.ndarray
        Normalised scores in [0, 1].
    """
    if len(values) == 0:
        return values.copy()

    lo = np.percentile(values, percentile_clip[0])
    hi = np.percentile(values, percentile_clip[1])

    if hi - lo < 1e-10:
        vmin, vmax = np.min(values), np.max(values)
        if vmax - vmin < 1e-10:
            return np.full_like(values, 0.5)
        return (values - vmin) / (vmax - vmin)

    normed = (values - lo) / (hi - lo)
    return np.clip(normed, 0.0, 1.0)
