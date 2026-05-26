"""
IEDB B-cell epitope prediction API client.

Queries the free IEDB Tools API (http://tools-api.iedb.org) for
B-cell linear epitope predictions using multiple methods:

- **BepiPred-2.0** (Jespersen et al. 2017) — random-forest model,
  state-of-the-art for sequence-based B-cell epitope prediction.
- **Emini**        — surface accessibility (server-side implementation).
- **Kolaskar-Tongaonkar** — antigenicity.
- **Parker**       — hydrophilicity.
- **Chou-Fasman**  — beta-turn propensity.

The API is free, public, and does not require authentication.

References
----------
Jespersen MC et al. (2017) Nucleic Acids Res 45:W265-W270.
Vita R et al. (2019) Nucleic Acids Res 47:D339-D343.

API docs: http://tools-api.iedb.org/tools_api/bcell/
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── IEDB API configuration ──────────────────────────────────────────────────

IEDB_BCELL_URL = "https://tools-cluster-interface.iedb.org/tools_api/bcell/"

# Methods available on the IEDB B-cell prediction API
IEDB_METHODS = {
    "Bepipred-2.0": "Bepipred-2.0",
    "Emini": "Emini",
    "Kolaskar-Tongaonkar": "Kolaskar-Tongaonkar",
    "Parker": "Parker",
    "Chou-Fasman": "Chou-Fasman",
    "Karplus-Schulz": "Karplus-Schulz",
    "Bepipred": "Bepipred",  # BepiPred 1.0
}

# Maximum sequence length the API accepts per request
IEDB_MAX_SEQ_LEN = 50_000

# Timeout for API requests (seconds)
IEDB_TIMEOUT = 15

# Delay between successive API calls to avoid rate-limiting (seconds)
IEDB_RATE_LIMIT_DELAY = 1.5

# Number of retries per method on transient failures
IEDB_MAX_RETRIES = 1


# ── Helper: HTTP request (uses urllib — no extra dependencies) ──────────────

def _post_iedb(method: str, sequence: str, timeout: int = IEDB_TIMEOUT) -> str:
    """Send a POST request to the IEDB B-cell API and return the raw body.

    Parameters
    ----------
    method : str
        Prediction method name (e.g. "Bepipred-2.0").
    sequence : str
        Single-letter amino-acid sequence.
    timeout : int
        Request timeout in seconds.

    Returns
    -------
    str
        Raw response text.

    Raises
    ------
    RuntimeError
        On HTTP errors or invalid responses.
    """
    import urllib.request
    import urllib.parse
    import urllib.error
    import ssl

    data = urllib.parse.urlencode({
        "method": method,
        "sequence_text": sequence,
    }).encode("utf-8")

    # Build an opener that follows redirects (HTTP → HTTPS)
    # Accept unverified SSL for the IEDB public research API
    ctx = ssl.create_default_context()
    try:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    except Exception:
        pass
    handler = urllib.request.HTTPSHandler(context=ctx)
    redirect_handler = urllib.request.HTTPRedirectHandler()
    opener = urllib.request.build_opener(handler, redirect_handler)

    req = urllib.request.Request(
        IEDB_BCELL_URL,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "EpiTop1/2.0",
        },
    )

    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                raise RuntimeError(
                    f"IEDB API returned HTTP {resp.status} for method={method}"
                )
            return body
    except urllib.error.URLError as exc:
        raise RuntimeError(f"IEDB API request failed ({method}): {exc}") from exc


# ── Response parser ──────────────────────────────────────────────────────────

def _parse_iedb_response(body: str, seq_len: int) -> np.ndarray:
    """Parse the tab-separated IEDB API response into a per-residue array.

    Handles two IEDB response formats:

    **BepiPred-2.0 / BepiPred 1.0** (0-indexed, Score + Assignment)::

        Position\\tResidue\\tScore\\tAssignment
        0\\tM\\t0.523\\t.
        1\\tK\\t0.612\\tE

    **Other methods** (1-indexed, window-based, Score last)::

        Position\\tResidue\\tStart\\tEnd\\tPeptide\\tScore
        3\\tV\\t1\\t6\\tMFVFLV\\t0.146

    Parameters
    ----------
    body : str
        Raw API response text.
    seq_len : int
        Expected sequence length.

    Returns
    -------
    np.ndarray
        Per-residue scores (length = *seq_len*).  Positions not
        present in the response are filled with 0.0.
    """
    scores = np.zeros(seq_len, dtype=np.float64)
    lines = body.strip().splitlines()
    if not lines:
        return scores

    # Detect format from header line
    header = lines[0].strip().lower() if lines else ""
    is_bepipred_format = "assignment" in header  # BepiPred has Assignment column
    # Detect the score column index from header
    score_col = -1  # default: last column
    if header:
        cols = header.split("\t")
        for ci, col_name in enumerate(cols):
            if col_name.strip() == "score":
                score_col = ci
                break

    for line in lines:
        line = line.strip()
        if not line or line.lower().startswith("position") or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            pos = int(parts[0])
            # Extract score from the detected column, fall back to last numeric
            raw_score = parts[score_col] if 0 <= score_col < len(parts) else parts[-1]
            try:
                score = float(raw_score)
            except ValueError:
                # Last column might be non-numeric (e.g. Assignment "E"/"."),
                # try the second-to-last or scan for the Score column
                score = None
                for j in range(len(parts) - 1, 0, -1):
                    try:
                        score = float(parts[j])
                        break
                    except ValueError:
                        continue
                if score is None:
                    continue

            # BepiPred formats use 0-indexed positions
            if is_bepipred_format:
                idx = pos  # already 0-indexed
            else:
                idx = pos - 1  # convert 1-indexed to 0-indexed

            if 0 <= idx < seq_len:
                scores[idx] = score
        except (ValueError, IndexError):
            continue

    return scores


# ── Public API ───────────────────────────────────────────────────────────────

class IEDBBCellPredictor:
    """Query the IEDB B-cell epitope prediction API.

    The predictor caches results per (sequence, method) so that
    repeated calls for the same input are free.

    Parameters
    ----------
    methods : list[str] | None
        Methods to query.  ``None`` → ``["Bepipred-2.0"]``.
    timeout : int
        HTTP timeout per request in seconds.
    enabled : bool
        If ``False``, all methods return zero arrays (offline mode).
    """

    def __init__(
        self,
        methods: list[str] | None = None,
        timeout: int = IEDB_TIMEOUT,
        enabled: bool = True,
    ) -> None:
        self.methods = methods or ["Bepipred-2.0"]
        self.timeout = timeout
        self.enabled = enabled
        self._cache: dict[tuple[str, str], np.ndarray] = {}

    # ---- single-method query ------------------------------------------------

    def predict(self, sequence: str, method: str = "Bepipred-2.0") -> np.ndarray:
        """Return per-residue scores from the IEDB API for one method.

        Parameters
        ----------
        sequence : str
            Protein sequence.
        method : str
            IEDB method name.

        Returns
        -------
        np.ndarray
            Per-residue score array (length = len(sequence)).
        """
        seq = sequence.upper().strip()
        n = len(seq)

        if not self.enabled:
            logger.info("IEDB API disabled — returning zeros for %s", method)
            return np.zeros(n, dtype=np.float64)

        key = (method, seq)
        if key in self._cache:
            return self._cache[key].copy()

        if n > IEDB_MAX_SEQ_LEN:
            logger.warning(
                "Sequence too long for IEDB API (%d > %d) — returning zeros.",
                n, IEDB_MAX_SEQ_LEN,
            )
            return np.zeros(n, dtype=np.float64)

        logger.info("Querying IEDB API: method=%s, len=%d ...", method, n)
        for attempt in range(IEDB_MAX_RETRIES + 1):
            try:
                body = _post_iedb(method, seq, self.timeout)
                scores = _parse_iedb_response(body, n)
                self._cache[key] = scores
                logger.info(
                    "IEDB %s: mean=%.4f, min=%.4f, max=%.4f",
                    method, float(np.mean(scores)),
                    float(np.min(scores)), float(np.max(scores)),
                )
                return scores.copy()
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                if attempt < IEDB_MAX_RETRIES:
                    wait = (attempt + 1) * 3
                    logger.warning(
                        "IEDB API attempt %d/%d failed (%s): %s — retrying in %ds.",
                        attempt + 1, IEDB_MAX_RETRIES + 1, method, exc, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.warning("IEDB API error (%s): %s — returning zeros.", method, exc)
                    return np.zeros(n, dtype=np.float64)
        return np.zeros(n, dtype=np.float64)

    # ---- multi-method query -------------------------------------------------

    def predict_all(
        self, sequence: str
    ) -> dict[str, np.ndarray]:
        """Query all configured methods and return a dict of score arrays.

        Parameters
        ----------
        sequence : str
            Protein sequence.

        Returns
        -------
        dict[str, np.ndarray]
            {method_name: per_residue_scores}.
        """
        results: dict[str, np.ndarray] = {}
        for i, method in enumerate(self.methods):
            results[method] = self.predict(sequence, method)
            # Rate-limit between calls
            if i < len(self.methods) - 1:
                time.sleep(IEDB_RATE_LIMIT_DELAY)
        return results

    # ---- convenience: BepiPred-2.0 epitope calls ----------------------------

    def bepipred2_epitope_mask(
        self,
        sequence: str,
        threshold: float = 0.5,
    ) -> np.ndarray:
        """Return a boolean mask where BepiPred-2.0 score >= *threshold*.

        The default threshold of 0.5 is recommended by Jespersen et al. (2017).

        Parameters
        ----------
        sequence : str
            Protein sequence.
        threshold : float
            Score threshold for epitope residues.

        Returns
        -------
        np.ndarray
            Boolean array (True = epitope residue).
        """
        scores = self.predict(sequence, "Bepipred-2.0")
        return scores >= threshold

    # ---- convenience: consensus across IEDB methods -------------------------

    def iedb_consensus(self, sequence: str) -> np.ndarray:
        """Compute a normalised consensus score across all queried methods.

        For each residue, counts how many methods predict it above
        their respective medians, then normalises to [0, 1].

        Parameters
        ----------
        sequence : str
            Protein sequence.

        Returns
        -------
        np.ndarray
            Per-residue consensus in [0, 1].
        """
        all_scores = self.predict_all(sequence)
        n = len(sequence.upper().strip())
        if not all_scores:
            return np.zeros(n, dtype=np.float64)

        count = np.zeros(n, dtype=np.float64)
        for method, scores in all_scores.items():
            med = np.median(scores)
            count += (scores >= med).astype(np.float64)

        return count / max(len(all_scores), 1)

    # ---- convenience: weighted IEDB combined score --------------------------

    def iedb_combined_score(
        self,
        sequence: str,
        weights: Optional[dict[str, float]] = None,
    ) -> np.ndarray:
        """Compute a weighted combination of all IEDB method scores.

        Each method's scores are min-max normalised independently
        before blending.

        Parameters
        ----------
        sequence : str
            Protein sequence.
        weights : dict[str, float] | None
            Per-method weights.  ``None`` → equal weighting.

        Returns
        -------
        np.ndarray
            Per-residue combined score in [0, 1].
        """
        all_scores = self.predict_all(sequence)
        n = len(sequence.upper().strip())
        if not all_scores:
            return np.zeros(n, dtype=np.float64)

        combined = np.zeros(n, dtype=np.float64)
        total_w = 0.0

        for method, raw in all_scores.items():
            # Min-max normalise
            mn, mx = float(np.min(raw)), float(np.max(raw))
            if mx - mn > 1e-12:
                norm = (raw - mn) / (mx - mn)
            else:
                norm = np.full(n, 0.5)
            w = (weights or {}).get(method, 1.0)
            combined += w * norm
            total_w += w

        if total_w > 0:
            combined /= total_w

        return combined
