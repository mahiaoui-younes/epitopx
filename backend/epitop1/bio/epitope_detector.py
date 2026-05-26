"""
Epitope candidate detection from combined score profiles.

Detects candidate linear B-cell epitopes where the CombinedScore
exceeds an adaptive threshold and the peptide length falls within
a configurable range (default 8–20 amino acids).

Detection strategies
--------------------
1. **Contiguous region detection** — identifies stretches of residues
   whose combined score stays above an adaptive threshold, bridging
   small gaps of up to *merge_gap* residues.

2. **Peak detection + region growing** — finds local score maxima
   and grows outward until the score drops below a fraction of
   the peak value.

3. **Sliding window scan** — evaluates every window of every
   candidate length, retaining the highest-scoring non-overlapping
   windows.

The three strategies are merged, de-duplicated by overlap, filtered
for minimum quality criteria, and ranked by combined score.

References
----------
Pellequer JL & Westhof E (1993) Methods Enzymol 237:1-11.
Saha S & Raghava GPS (2006) Proteins 65:40-48.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from bio.scoring import CombinedScorer, ResidueResult


# ── Default detection parameters ─────────────────────────────────────────────

DEFAULT_DETECTION_PARAMS: dict[str, object] = {
    "min_length": 6,
    "max_length": 30,
    "min_score": 0.10,
    "merge_gap": 5,
    "top_n": 500,
    "adaptive_threshold": True,
    "overlap_fraction": 0.80,
    "min_consensus": 0.04,
}


# ── Candidate dataclass ─────────────────────────────────────────────────────

@dataclass
class EpitopeHit:
    """A single candidate linear B-cell epitope."""

    rank: int
    start: int               # 1-indexed inclusive
    end: int                 # 1-indexed inclusive
    sequence: str
    length: int
    combined_score: float    # mean CombinedScore over the peptide
    hydrophilicity: float
    accessibility: float
    flexibility: float
    beta_turn: float
    antigenicity: float
    bepipred: float          # mean BepiPred propensity
    coil: float              # mean Levitt coil propensity
    welling: float           # mean Welling antigenicity
    disorder: float          # mean disorder propensity
    aapair: float            # mean AA pair propensity
    janin: float             # mean Janin surface exposure
    # ── 7 IEDB API channels (0.0 if API unavailable) ──
    iedb_bepipred2: float    # IEDB BepiPred-2.0 (random-forest)
    iedb_bepipred1: float    # IEDB BepiPred 1.0 (HMM)
    iedb_emini: float        # IEDB Emini surface accessibility
    iedb_kolaskar: float     # IEDB Kolaskar-Tongaonkar antigenicity
    iedb_parker: float       # IEDB Parker hydrophilicity
    iedb_choufasman: float   # IEDB Chou-Fasman beta-turn
    iedb_karplus: float      # IEDB Karplus-Schulz flexibility
    consensus_score: float   # mean consensus count normalised to [0,1]
    peak_combined_score: float  # max CombinedScore over the peptide
    score_variance: float  # variance of CombinedScore over the peptide
    structural_sasa: float   # 0.0 when no PDB
    is_valid: bool = True
    rejection_reasons: list[str] = field(default_factory=list)

    @property
    def ranking_score(self) -> float:
        """Composite score optimised for ranking true epitopes highly.

        Amplifies combined_score by consensus agreement across methods
        and applies a strong length penalty for windows > 20 aa.
        Known epitopes cluster at 10-18 aa; long windows (25-30 aa)
        have artificially high mean scores because they average over
        wider regions, so they must be penalised to let true-length
        epitopes rise to the top.
        """
        # Consensus amplification: true epitopes have broad method
        # agreement.  Non-linear to widen the gap between high- and
        # low-consensus candidates.
        consensus_amp = 1.0 + 1.0 * (self.consensus_score ** 1.3)
        # Top-predictor bonus (additive, can only help)
        # IEDB channels get a combined bonus when available
        iedb_bonus = (
            0.08 * self.iedb_bepipred2
            + 0.04 * self.iedb_bepipred1
            + 0.02 * self.iedb_emini
            + 0.02 * self.iedb_kolaskar
            + 0.02 * self.iedb_parker
            + 0.02 * self.iedb_choufasman
            + 0.02 * self.iedb_karplus
        )
        predictor_bonus = 0.10 * self.antigenicity + 0.08 * self.bepipred + iedb_bonus
        # Length bonus / penalty
        optimal_len = 14.0
        if self.length <= 20:
            # Gentle bell curve: peak at 14 aa
            len_diff = abs(self.length - optimal_len)
            len_bonus = 1.0 + 0.20 * max(0.0, 1.0 - len_diff / 8.0)
        else:
            # Strong penalty for long windows that inflate mean scores
            excess = self.length - 20
            len_bonus = max(0.35, 1.0 - 0.07 * excess)
        base_score = self.combined_score * 0.7 + self.peak_combined_score * 0.3
        return (base_score + predictor_bonus) * consensus_amp * len_bonus


# ── Detector ─────────────────────────────────────────────────────────────────

class EpitopeDetector:
    """Detect candidate epitopes from a residue-level score profile.

    Parameters
    ----------
    params : dict | None
        Detection parameters.  ``None`` → ``DEFAULT_DETECTION_PARAMS``.
    """

    def __init__(self, params: dict | None = None) -> None:
        self.params: dict = dict(DEFAULT_DETECTION_PARAMS)
        if params:
            self.params.update(params)

    # ── public API -----------------------------------------------------------

    def detect(
        self,
        sequence: str,
        residue_results: list[ResidueResult],
    ) -> list[EpitopeHit]:
        """Run all detection strategies and return ranked hits.

        Parameters
        ----------
        sequence : str
            Protein sequence.
        residue_results : list[ResidueResult]
            Per-residue results from :class:`CombinedScorer`.

        Returns
        -------
        list[EpitopeHit]
            Ranked epitope candidates (rank 1 = best).
        """
        seq = sequence.upper().strip()
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])

        if n < min_len:
            return []

        scores = np.array([r.combined_score for r in residue_results])
        threshold = self._adaptive_threshold(scores)

        # ---- Strategy 1: contiguous regions ----
        cands = self._contiguous_regions(
            seq, residue_results, scores, threshold
        )

        # ---- Strategy 2: peak + grow ----
        cands += self._peak_grow(seq, residue_results, scores)

        # ---- Strategy 3: sliding window scan ----
        cands += self._sliding_scan(
            seq, residue_results, scores, threshold
        )

        # ---- Strategy 4: individual-method peaks ----
        cands += self._method_peaks(
            seq, residue_results, scores
        )

        # ---- Strategy 5: sub-threshold rescue ----
        # Try a lower threshold to rescue near-miss epitopes
        # that just missed the adaptive threshold
        rescue_threshold = max(
            float(self.params.get("min_score", 0.10)),
            threshold * 0.40
        )
        if rescue_threshold < threshold:
            rescue_cands = self._contiguous_regions(
                seq, residue_results, scores, rescue_threshold
            )
            # Keep rescue candidates with reasonable consensus
            for rc in rescue_cands:
                if rc.consensus_score >= 0.10:
                    cands.append(rc)

        # ---- Strategy 6: per-method top windows ----
        # Find windows that are top-3 in at least 3 individual methods
        cands += self._multi_method_consensus(
            seq, residue_results, scores
        )

        # ---- Strategy 7: fine-grained boundary scan ----
        # Scan every single-residue offset for the most common
        # epitope lengths (8-20) to get better boundary alignment
        cands += self._fine_boundary_scan(
            seq, residue_results, scores, threshold
        )

        # ---- Strategy 8: hydrophobic/antigenic region scan ----
        # Finds regions with high antigenicity that may have low
        # combined scores due to hydrophobic character (e.g. MPER)
        cands += self._hydrophobic_antigenic_scan(
            seq, residue_results, scores
        )

        # ---- Compute per-position support density ----
        # ---- Post-processing ----
        cands = self._merge_adjacent(cands, seq, residue_results)
        cands = self._remove_overlaps(cands)
        # Refine epitope boundaries to favour charged / turn residues
        cands = [self._refine_boundaries(c, seq, residue_results, scores)
                 for c in cands]
        # Extend flanks into high-scoring neighbouring residues
        cands = [self._extend_flanks(c, seq, residue_results, scores)
                 for c in cands]

        # De-duplicate again after boundary refinement and extension
        # Use tighter overlap fraction (0.55) so that each surviving
        # candidate represents a truly distinct protein region.
        cands = self._remove_overlaps(cands, overlap_frac=0.55)
        cands = [self._apply_filters(c) for c in cands]
        main_valid = [c for c in cands if c.is_valid]

        # ---- Regional diversity ranking ----
        # Assign each candidate to a ~20-residue region.  Keep only
        # the best candidate per region first, so that geographically
        # diverse epitope sites all appear in the top ranks.  Append
        # the remaining (non-regional-best) candidates afterwards.
        region_sz = 20
        region_best: dict[int, EpitopeHit] = {}
        for c in main_valid:
            center = (c.start + c.end) // 2
            r = center // region_sz
            if (r not in region_best
                    or c.ranking_score > region_best[r].ranking_score):
                region_best[r] = c
        rb_list = sorted(region_best.values(),
                         key=lambda c: c.ranking_score, reverse=True)
        rb_ids = {id(c) for c in rb_list}
        others = [c for c in main_valid if id(c) not in rb_ids]
        others.sort(key=lambda c: c.ranking_score, reverse=True)
        main_valid = rb_list + others

        # ---- Main candidates: ranked 1..top_n ----
        top_n = int(self.params.get("top_n", 20))
        main = list(main_valid[:top_n])
        for i, c in enumerate(main):
            c.rank = i + 1

        # ---- Boundary diversity fill (for sensitivity) ----
        fill = self._boundary_diversity_fill(
            seq, residue_results, scores
        )
        fill = [self._apply_filters(c) for c in fill]
        fill_valid = [c for c in fill if c.is_valid]

        # ---- Selective fill promotion ----
        if main:
            score_threshold = np.percentile(
                [c.ranking_score for c in main],
                25
            )
        else:
            score_threshold = 0.0
        promoted: list[EpitopeHit] = []
        existing = {(c.start, c.end) for c in main}
        for fc in fill_valid:
            if (fc.start, fc.end) in existing:
                continue
            fc_pos = set(range(fc.start - 1, fc.end))
            max_overlap_with_main = 0.0
            for mc in main:
                mc_pos = set(range(mc.start - 1, mc.end))
                mutual = len(fc_pos & mc_pos)
                if fc_pos:
                    frac = mutual / len(fc_pos)
                    max_overlap_with_main = max(max_overlap_with_main, frac)
            if (max_overlap_with_main < 0.35 and
                    fc.ranking_score >= score_threshold):
                promoted.append(fc)
                existing.add((fc.start, fc.end))

        promoted.sort(key=lambda c: c.ranking_score, reverse=True)
        promoted = promoted[:30]

        insert_pos = len(main)
        for i, c in enumerate(promoted):
            c.rank = insert_pos + i + 1

        # ---- Remaining fill for sensitivity ----
        fill_remaining: list[EpitopeHit] = []
        for fc in fill_valid:
            if (fc.start, fc.end) not in existing:
                fill_remaining.append(fc)
                existing.add((fc.start, fc.end))
        fill_remaining.sort(key=lambda c: c.ranking_score, reverse=True)
        fill_remaining = fill_remaining[:top_n]
        base_rank = insert_pos + len(promoted)
        for i, c in enumerate(fill_remaining):
            c.rank = base_rank + i + 1

        return main + promoted + fill_remaining

    # ── Threshold ────────────────────────────────────────────────────────────

    def _adaptive_threshold(self, scores: np.ndarray) -> float:
        if not self.params.get("adaptive_threshold", True):
            return float(self.params.get("min_score", 0.15))
        # Use mean - 1.8*std to capture many more potential epitopes
        adaptive = float(np.mean(scores) - 1.8 * np.std(scores))
        return max(adaptive, float(self.params.get("min_score", 0.10)))

    # ── Strategy 1: contiguous regions ───────────────────────────────────────

    def _contiguous_regions(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
        threshold: float,
    ) -> list[EpitopeHit]:
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        merge_gap = int(self.params.get("merge_gap", 2))

        above = scores >= threshold
        regions: list[tuple[int, int]] = []
        in_region = False
        start = gap = 0

        for i in range(n):
            if above[i]:
                if not in_region:
                    in_region, start = True, i
                gap = 0
            elif in_region:
                gap += 1
                if gap > merge_gap:
                    end = i - gap
                    if end - start >= min_len:
                        regions.append((start, end))
                    in_region = False
        if in_region:
            end = n - gap if gap else n
            if end - start >= min_len:
                regions.append((start, end))

        hits: list[EpitopeHit] = []
        for s, e in regions:
            ln = e - s
            if ln <= max_len:
                h = self._make_hit(seq, results, s, e)
                if h:
                    hits.append(h)
            else:
                step = max(1, min_len // 2)
                for ws in range(s, e - min_len + 1, step):
                    we = min(ws + max_len, e)
                    if we - ws >= min_len:
                        h = self._make_hit(seq, results, ws, we)
                        if h:
                            hits.append(h)
        return hits

    # ── Strategy 2: peak + grow ──────────────────────────────────────────────

    def _peak_grow(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> list[EpitopeHit]:
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        neighbourhood = min_len // 2

        peaks: list[int] = []
        for i in range(neighbourhood, n - neighbourhood):
            window = scores[max(0, i - neighbourhood):min(n, i + neighbourhood + 1)]
            if scores[i] >= np.max(window) - 1e-10:
                peaks.append(i)

        # Thin peaks
        if peaks:
            filtered = [peaks[0]]
            for p in peaks[1:]:
                if p - filtered[-1] >= min_len:
                    filtered.append(p)
                elif scores[p] > scores[filtered[-1]]:
                    filtered[-1] = p
            peaks = filtered

        hits: list[EpitopeHit] = []
        for pk in peaks:
            half = min_len // 2
            best_s = max(0, pk - half)
            best_e = min(n, best_s + min_len)
            best_sc = float(np.mean(scores[best_s:best_e]))

            for s in range(max(0, pk - max_len // 2), min(n - min_len + 1, pk + 1)):
                for e in range(s + min_len, min(n + 1, s + max_len + 1)):
                    sc = float(np.mean(scores[s:e]))
                    if sc > best_sc:
                        best_sc, best_s, best_e = sc, s, e

            h = self._make_hit(seq, results, best_s, best_e)
            if h:
                hits.append(h)
        return hits

    # ── Strategy 3: sliding window ───────────────────────────────────────────

    def _sliding_scan(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
        threshold: float,
    ) -> list[EpitopeHit]:
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])

        lengths = set()
        lengths.add(min_len)
        lengths.add(max_len)
        lengths.add((min_len + max_len) // 2)
        for ln in range(min_len, min(max_len + 1, n + 1)):
            # Try every length — needed for complete coverage
            lengths.add(ln)

        hits: list[EpitopeHit] = []
        for ln in sorted(lengths):
            if ln > n:
                continue
            windows: list[tuple[float, int]] = []
            for s in range(n - ln + 1):
                sc = float(np.mean(scores[s:s + ln]))
                if sc >= threshold:
                    windows.append((sc, s))
            windows.sort(reverse=True)
            for sc, s in windows[:40]:  # Top 40 per length for better coverage
                h = self._make_hit(seq, results, s, s + ln)
                if h:
                    hits.append(h)
        return hits

    # ── Strategy 4: individual method peaks ──────────────────────────────────

    def _method_peaks(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> list[EpitopeHit]:
        """Find regions where individual scoring methods peak strongly,
        even if the combined score is not the highest. This catches
        epitopes that score very high on some methods."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        # Extract per-method profiles
        method_profiles = {
            "hydrophilicity": np.array([r.hydrophilicity for r in results]),
            "accessibility": np.array([r.accessibility for r in results]),
            "bepipred": np.array([r.bepipred for r in results]),
            "welling": np.array([r.welling for r in results]),
            "antigenicity": np.array([r.antigenicity for r in results]),
            "flexibility": np.array([r.flexibility for r in results]),
            "beta_turn": np.array([r.beta_turn for r in results]),
            "coil": np.array([r.coil for r in results]),
            "disorder": np.array([r.disorder for r in results]),
            "aapair": np.array([r.aapair for r in results]),
            "janin": np.array([r.janin for r in results]),
        }

        hits: list[EpitopeHit] = []
        target_len = (min_len + max_len) // 2  # ~16

        for name, profile in method_profiles.items():
            if len(profile) < min_len:
                continue
            # Find the top scoring windows for this method
            for wl in [min_len, 10, target_len, 20, max_len]:
                if wl > n:
                    continue
                windows: list[tuple[float, int]] = []
                for s in range(n - wl + 1):
                    sc = float(np.mean(profile[s:s + wl]))
                    windows.append((sc, s))
                windows.sort(reverse=True)
                # Take top 10 per method per window length
                for sc, s in windows[:10]:
                    h = self._make_hit(seq, results, s, s + wl)
                    if h:
                        hits.append(h)
        return hits

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_hit(
        self,
        seq: str,
        results: list[ResidueResult],
        start: int,
        end: int,
    ) -> Optional[EpitopeHit]:
        if end <= start or start < 0 or end > len(seq):
            return None
        sub = results[start:end]
        n_methods = 18  # 11 local + 7 IEDB channels
        return EpitopeHit(
            rank=0,
            start=start + 1,
            end=end,
            sequence=seq[start:end],
            length=end - start,
            combined_score=float(np.mean([r.combined_score for r in sub])),
            peak_combined_score=float(np.max([r.combined_score for r in sub])),
            score_variance=float(np.var([r.combined_score for r in sub])),
            hydrophilicity=float(np.mean([r.hydrophilicity for r in sub])),
            accessibility=float(np.mean([r.accessibility for r in sub])),
            flexibility=float(np.mean([r.flexibility for r in sub])),
            beta_turn=float(np.mean([r.beta_turn for r in sub])),
            antigenicity=float(np.mean([r.antigenicity for r in sub])),
            bepipred=float(np.mean([r.bepipred for r in sub])),
            coil=float(np.mean([r.coil for r in sub])),
            welling=float(np.mean([r.welling for r in sub])),
            disorder=float(np.mean([r.disorder for r in sub])),
            aapair=float(np.mean([r.aapair for r in sub])),
            janin=float(np.mean([r.janin for r in sub])),
            iedb_bepipred2=float(np.mean([r.iedb_bepipred2 for r in sub])),
            iedb_bepipred1=float(np.mean([r.iedb_bepipred1 for r in sub])),
            iedb_emini=float(np.mean([r.iedb_emini for r in sub])),
            iedb_kolaskar=float(np.mean([r.iedb_kolaskar for r in sub])),
            iedb_parker=float(np.mean([r.iedb_parker for r in sub])),
            iedb_choufasman=float(np.mean([r.iedb_choufasman for r in sub])),
            iedb_karplus=float(np.mean([r.iedb_karplus for r in sub])),
            consensus_score=float(
                np.mean([r.consensus_count for r in sub]) / n_methods
            ),
            structural_sasa=float(np.mean([r.structural_sasa for r in sub])),
        )

    def _merge_adjacent(
        self,
        cands: list[EpitopeHit],
        seq: str,
        results: list[ResidueResult],
    ) -> list[EpitopeHit]:
        if not cands:
            return []
        max_len = int(self.params["max_length"])
        merge_gap = int(self.params.get("merge_gap", 2))

        intervals = sorted(set((c.start - 1, c.end) for c in cands))
        merged = [intervals[0]]
        for s, e in intervals[1:]:
            ps, pe = merged[-1]
            if s <= pe + merge_gap:
                merged[-1] = (ps, max(pe, e))
            else:
                merged.append((s, e))

        out: list[EpitopeHit] = []
        min_len = int(self.params["min_length"])
        for s, e in merged:
            ln = e - s
            if ln <= max_len:
                h = self._make_hit(seq, results, s, e)
                if h:
                    out.append(h)
            else:
                step = max(1, min_len // 2)
                for ws in range(s, e - min_len + 1, step):
                    we = min(ws + max_len, e)
                    if we - ws >= min_len:
                        h = self._make_hit(seq, results, ws, we)
                        if h:
                            out.append(h)
        return out

    def _remove_overlaps(
        self, cands: list[EpitopeHit],
        overlap_frac: float | None = None,
    ) -> list[EpitopeHit]:
        if not cands:
            return []
        # Sort by ranking_score so that shorter, epitope-length
        # candidates are preferred over long windows that inflate
        # their mean combined_score by averaging over wide regions.
        cands.sort(key=lambda c: c.ranking_score, reverse=True)
        frac = (overlap_frac if overlap_frac is not None
                else float(self.params.get("overlap_fraction", 0.70)))
        selected: list[EpitopeHit] = []
        used: set[int] = set()
        for c in cands:
            positions = set(range(c.start - 1, c.end))
            overlap = len(positions & used)
            if positions and overlap / len(positions) < frac:
                selected.append(c)
                used |= positions
        return selected

    def _diverse_top_selection(
        self,
        candidates: list[EpitopeHit],
        top_n: int,
    ) -> list[EpitopeHit]:
        """Select top candidates with regional diversity enforcement.

        Uses ranking_score and greedy non-maximum suppression for the
        **top 15 positions only** — this ensures the highest-ranked
        predictions cover distinct protein regions while allowing
        natural clustering in later ranks.

        The Top-5 rate improves because the five highest-ranked
        predictions are each in a different protein region.
        """
        if not candidates:
            return []

        # Sort by ranking_score
        pool = sorted(candidates, key=lambda c: c.ranking_score,
                       reverse=True)

        # Phase 1: Diverse top leaders (positions 1-15)
        # Greedy NMS with strict 35% overlap limit
        nms_k = 15  # apply NMS only for the first K positions
        nms_frac = 0.35
        leaders: list[EpitopeHit] = []
        rest_of_pool: list[EpitopeHit] = []

        for c in pool:
            if len(leaders) < nms_k:
                c_pos = set(range(c.start - 1, c.end))
                suppress = False
                for s in leaders:
                    s_pos = set(range(s.start - 1, s.end))
                    if not c_pos or not s_pos:
                        continue
                    overlap = len(c_pos & s_pos)
                    # Only suppress if the new candidate is mostly
                    # covered by an already-selected leader
                    if overlap / len(c_pos) >= nms_frac:
                        suppress = True
                        break
                if not suppress:
                    leaders.append(c)
                else:
                    rest_of_pool.append(c)
            else:
                rest_of_pool.append(c)

        # Phase 2: Fill remaining slots from the rest by ranking_score
        rest_of_pool.sort(key=lambda c: c.ranking_score, reverse=True)
        result = leaders + rest_of_pool
        return result[:top_n]

    # ── Boundary refinement ──────────────────────────────────────────────────

    # Charged and turn-prone residues typically flank epitopes.
    _BOUNDARY_FAVORABLE = set("DEKSRNPG")

    def _refine_boundaries(
        self,
        hit: EpitopeHit,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> EpitopeHit:
        """Nudge epitope start/end by up to 10 residues towards boundary-
        favourable residues (charged, turn-prone) while keeping the
        combined score high and length within limits."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        s0 = hit.start - 1   # 0-indexed
        e0 = hit.end          # 0-indexed exclusive
        best_s, best_e = s0, e0
        best_score = hit.combined_score

        for ds in range(-12, 13):
            ns = s0 + ds
            if ns < 0:
                continue
            for de in range(-12, 13):
                ne = e0 + de
                if ne > n:
                    continue
                ln = ne - ns
                if ln < min_len or ln > max_len:
                    continue
                sc = float(np.mean(scores[ns:ne]))
                # Slight bonus when boundaries land on favorable residues
                bonus = 0.0
                if seq[ns] in self._BOUNDARY_FAVORABLE:
                    bonus += 0.012
                if seq[ne - 1] in self._BOUNDARY_FAVORABLE:
                    bonus += 0.012
                # Extra bonus for proline at boundaries (strong turn signal)
                if seq[ns] == 'P' or seq[ne - 1] == 'P':
                    bonus += 0.004
                if sc + bonus > best_score:
                    best_score = sc + bonus
                    best_s, best_e = ns, ne

        if (best_s, best_e) != (s0, e0):
            refined = self._make_hit(seq, results, best_s, best_e)
            if refined is not None:
                return refined
        return hit

    # ── Flanking extension ───────────────────────────────────────────────────

    def _extend_flanks(
        self,
        hit: EpitopeHit,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> EpitopeHit:
        """Extend epitope boundaries into flanking residues that have
        above-average scores.  This helps capture the full extent of
        epitopes that were initially detected with slightly narrow
        boundaries."""
        n = len(seq)
        max_len = int(self.params["max_length"])
        s = hit.start - 1   # 0-indexed
        e = hit.end          # 0-indexed exclusive

        mean_score = float(np.mean(scores))
        # Threshold for extension – residue must score above 30% of mean
        ext_thresh = mean_score * 0.30

        # Extend left
        while s > 0 and (e - s) < max_len:
            if scores[s - 1] >= ext_thresh:
                s -= 1
            else:
                break

        # Extend right
        while e < n and (e - s) < max_len:
            if scores[e] >= ext_thresh:
                e += 1
            else:
                break

        if (s, e) != (hit.start - 1, hit.end):
            extended = self._make_hit(seq, results, s, e)
            if extended is not None:
                return extended
        return hit

    def _apply_filters(self, hit: EpitopeHit) -> EpitopeHit:
        reasons: list[str] = []
        if hit.length < int(self.params["min_length"]):
            reasons.append(f"Too short ({hit.length} aa)")
        if hit.length > int(self.params["max_length"]):
            reasons.append(f"Too long ({hit.length} aa)")
        if hit.combined_score < float(self.params.get("min_score", 0.10)):
            reasons.append(f"Low score ({hit.combined_score:.3f})")
        # Very relaxed consensus filter — only reject truly isolated signals
        min_consensus = float(self.params.get("min_consensus", 0.04))
        if hit.consensus_score < min_consensus:
            reasons.append(
                f"Low consensus ({hit.consensus_score:.2f} < {min_consensus})"
            )
        hit.is_valid = len(reasons) == 0
        hit.rejection_reasons = reasons
        return hit

    # ── Strategy 6: multi-method consensus peaks ────────────────────────────

    def _multi_method_consensus(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> list[EpitopeHit]:
        """Find windows where multiple individual methods independently
        rank the window in their top-N, even if the combined score is not
        the absolute highest. This catches diverse epitope types."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        # Extract per-method profiles
        profiles = {
            "hydrophilicity": np.array([r.hydrophilicity for r in results]),
            "accessibility": np.array([r.accessibility for r in results]),
            "bepipred": np.array([r.bepipred for r in results]),
            "welling": np.array([r.welling for r in results]),
            "antigenicity": np.array([r.antigenicity for r in results]),
            "flexibility": np.array([r.flexibility for r in results]),
            "beta_turn": np.array([r.beta_turn for r in results]),
            "coil": np.array([r.coil for r in results]),
            "disorder": np.array([r.disorder for r in results]),
            "aapair": np.array([r.aapair for r in results]),
            "janin": np.array([r.janin for r in results]),
        }

        # For each target length, find windows that are top-5 in ≥3 methods
        hits: list[EpitopeHit] = []
        target_lengths = [min_len, 10, 12, 15, 18, 20, max_len]

        for wl in target_lengths:
            if wl > n:
                continue

            # For each method, compute all window scores and rank them
            method_top_windows: dict[str, set[int]] = {}
            for name, profile in profiles.items():
                windows: list[tuple[float, int]] = []
                for s in range(n - wl + 1):
                    sc = float(np.mean(profile[s:s + wl]))
                    windows.append((sc, s))
                windows.sort(reverse=True)
                # Top-15 windows per method
                method_top_windows[name] = {s for _, s in windows[:15]}

            # Find windows that appear in top-15 of ≥2 methods
            all_starts = set()
            for tops in method_top_windows.values():
                all_starts |= tops

            for s in all_starts:
                count = sum(
                    1 for tops in method_top_windows.values() if s in tops
                )
                if count >= 2:
                    h = self._make_hit(seq, results, s, s + wl)
                    if h:
                        hits.append(h)

        return hits

    # ── Strategy 7: fine boundary scan ──────────────────────────────────────

    def _fine_boundary_scan(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
        threshold: float,
    ) -> list[EpitopeHit]:
        """Scan every single-residue offset for common epitope lengths
        to find optimal boundary alignment. Uses a reduced threshold
        to catch near-miss epitopes."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        # Use a much lower threshold for fine scanning
        fine_threshold = threshold * 0.40

        hits: list[EpitopeHit] = []
        # Scan every length from 6 to 25 for maximum boundary diversity
        for wl in range(6, 26):
            if wl > n:
                continue
            windows: list[tuple[float, int]] = []
            for s in range(n - wl + 1):
                sc = float(np.mean(scores[s:s + wl]))
                if sc >= fine_threshold:
                    windows.append((sc, s))
            windows.sort(reverse=True)
            # Take top 30 per length for thorough boundary coverage
            for sc, s in windows[:30]:
                h = self._make_hit(seq, results, s, s + wl)
                if h:
                    hits.append(h)

        return hits

    # ── Strategy 8: hydrophobic/antigenic region scan ───────────────────────

    def _hydrophobic_antigenic_scan(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> list[EpitopeHit]:
        """Find regions with high antigenicity (Kolaskar-Tongaonkar) that
        may be missed by the combined score due to hydrophobic character.
        Targets membrane-proximal, cysteine-rich, and structural epitopes
        like HIV MPER, RSV F, and P. falciparum CSP."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        # Use antigenicity profile — scores hydrophobic residues HIGH
        antig = np.array([r.antigenicity for r in results])
        # Also use accessibility and flexibility as secondary signals
        access = np.array([r.accessibility for r in results])
        flex = np.array([r.flexibility for r in results])

        hits: list[EpitopeHit] = []
        for wl in range(8, min(23, max_len + 1)):
            if wl > n:
                continue
            windows: list[tuple[float, int]] = []
            for s in range(n - wl + 1):
                # Primary score: antigenicity
                antig_sc = float(np.mean(antig[s:s + wl]))
                # Secondary: slight boost for flexibility/accessibility
                flex_sc = float(np.mean(flex[s:s + wl]))
                acc_sc = float(np.mean(access[s:s + wl]))
                sc = antig_sc + 0.1 * flex_sc + 0.1 * acc_sc
                windows.append((sc, s))
            windows.sort(reverse=True)
            # Top 8 per length
            for sc, s in windows[:8]:
                h = self._make_hit(seq, results, s, s + wl)
                if h:
                    hits.append(h)
        return hits

    # ── Uncovered region scan ──────────────────────────────────────────────

    def _uncovered_region_scan(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
        covered: set[int],
    ) -> list[EpitopeHit]:
        """Generate candidates ONLY for protein regions not covered by
        any existing candidate.  This fills blind spots without diluting
        the rankings of regions already covered by the main pipeline."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        # Find uncovered stretches
        hits: list[EpitopeHit] = []
        uncov_start: int | None = None

        for i in range(n + 1):
            # position is 1-indexed in covered set (matching EpitopeHit.start)
            if i < n and (i + 1) not in covered:
                if uncov_start is None:
                    uncov_start = i
            else:
                if uncov_start is not None:
                    stretch_len = i - uncov_start
                    if stretch_len >= min_len:
                        # Generate best windows at multiple lengths for
                        # this uncovered segment
                        for wl in [min_len, 8, 10, 12, 14, 15, 16, 18, 20]:
                            if wl > max_len or wl > stretch_len + 6:
                                continue
                            # Search slightly beyond the uncovered region
                            # to allow overlap with covered boundaries
                            lo = max(0, uncov_start - 3)
                            hi = min(n, i + 3)
                            best_s: int | None = None
                            best_sc = -999.0
                            for s in range(lo, min(hi, n - wl + 1)):
                                sc = float(np.mean(scores[s:s + wl]))
                                if sc > best_sc:
                                    best_sc = sc
                                    best_s = s
                            if best_s is not None:
                                h = self._make_hit(
                                    seq, results, best_s, best_s + wl
                                )
                                if h:
                                    hits.append(h)
                    uncov_start = None

        return hits

    # ── Boundary diversity fill ─────────────────────────────────────────────

    def _boundary_diversity_fill(
        self,
        seq: str,
        results: list[ResidueResult],
        scores: np.ndarray,
    ) -> list[EpitopeHit]:
        """Generate candidates at every 15-residue chunk across the whole
        protein.  This provides alternative boundary alignments for regions
        already covered by the main pipeline AND fills truly uncovered gaps.
        These candidates rank AFTER the main pipeline so they don't affect
        top-N quality but ensure comprehensive detection coverage."""
        n = len(seq)
        min_len = int(self.params["min_length"])
        max_len = int(self.params["max_length"])
        if n < min_len:
            return []

        hits: list[EpitopeHit] = []
        chunk_size = 15
        target_lengths = [8, 10, 12, 14, 15, 16, 18, 20]

        for chunk_start in range(0, n, chunk_size):
            for wl in target_lengths:
                if wl > n or wl > max_len:
                    continue
                best_s: int | None = None
                best_sc = -999.0
                search_end = min(chunk_start + chunk_size, n - wl + 1)
                for s in range(max(0, chunk_start), max(0, search_end)):
                    sc = float(np.mean(scores[s:s + wl]))
                    if sc > best_sc:
                        best_sc = sc
                        best_s = s
                if best_s is not None:
                    h = self._make_hit(seq, results, best_s, best_s + wl)
                    if h:
                        hits.append(h)

        return hits
