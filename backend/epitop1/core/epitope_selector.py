"""
Epitope selection algorithm for B linear epitope prediction.

Identifies the best candidate epitopes from the global score profile
by applying scientifically validated selection criteria:

1. Length: 12-25 amino acids (optimal for B cell recognition)
2. Hydrophilicity: positive Hopp & Woods score
3. Surface exposure: Emini score > 1.0 and/or SASA > 0.25
4. Flexibility: Karplus & Schulz score > 1.0
5. Antigenicity: Kolaskar & Tongaonkar score above threshold
6. Exclusion: transmembrane, signal peptides, buried regions

Additional filters based on:
    Pellequer & Westhof (1993) — Empirical comparison of methods
    Saha & Raghava (2006) — Improved B-cell epitope prediction
    Jespersen et al. (2017) — BepiPred-2.0 methodology

References:
    Pellequer JL & Westhof E (1993) Methods Enzymol 237:1-11.
    Saha S & Raghava GPS (2006) Proteins 65:40-48.
    Jespersen MC et al. (2017) Nucleic Acids Res 45:W265-W270.
"""

import numpy as np
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass

from config import (
    EPITOPE_CRITERIA,
    EXCLUSION_PARAMS,
    HYDROPHILIC_RESIDUES,
    HYDROPHOBIC_RESIDUES,
)
from core.scoring import GlobalScorer, ResidueScore


@dataclass
class EpitopeCandidate:
    """Represents a candidate B linear epitope."""
    rank: int               # Rank (1 = best)
    start: int              # Start position (1-indexed)
    end: int                # End position (1-indexed)
    sequence: str           # Peptide sequence
    length: int             # Peptide length
    global_score: float     # Average global score
    hydrophilicity: float   # Average hydrophilicity
    hydrophobicity: float   # Average hydrophobicity
    flexibility: float      # Average flexibility
    accessibility: float    # Average Emini accessibility
    antigenicity: float     # Average antigenicity
    structural_sasa: float  # Average structural SASA (0 if no PDB)
    hydrophilic_fraction: float  # Fraction of hydrophilic residues
    is_valid: bool          # Passed all filters
    exclusion_reasons: List[str]  # Why it was rejected (if any)


class EpitopeSelector:
    """
    Selects the best B linear epitope candidates from residue scores.
    """

    def __init__(
        self,
        criteria: Dict = None,
        exclusion_params: Dict = None,
    ):
        """
        Initialize epitope selector.

        Args:
            criteria: Epitope selection criteria (defaults from config).
            exclusion_params: Exclusion parameters (defaults from config).
        """
        self.criteria = criteria or EPITOPE_CRITERIA
        self.exclusion = exclusion_params or EXCLUSION_PARAMS

    def find_epitopes(
        self,
        sequence: str,
        residue_scores: List[ResidueScore],
        excluded_regions: List[Tuple[int, int]] = None,
    ) -> List[EpitopeCandidate]:
        """
        Identify candidate epitopes using multiple complementary strategies:

        1. Contiguous region detection (above-threshold regions)
        2. Peak detection + region growing
        3. Systematic sliding window scan (multiple candidates per length)
        4. Merge adjacent/overlapping high-scoring regions
        5. Apply selection filters
        6. Rank by global score

        Args:
            sequence: Protein sequence.
            residue_scores: List of ResidueScore objects.
            excluded_regions: List of (start, end) tuples to exclude
                             (transmembrane, signal peptides, etc.).

        Returns:
            List of EpitopeCandidate objects, ranked by score.
        """
        sequence = sequence.upper().strip()
        n = len(sequence)

        if n < self.criteria["min_length"]:
            return []

        # Extract score arrays
        global_scores = np.array([r.global_score for r in residue_scores])

        # Build exclusion set
        excluded = set()
        if excluded_regions:
            for start, end in excluded_regions:
                for i in range(start - 1, min(end, n)):
                    excluded.add(i)

        # Signal peptide exclusion (only if enabled)
        sp_max = self.exclusion.get("signal_peptide_max_pos", 0)
        if sp_max > 0 and n > sp_max * 3:
            for i in range(min(sp_max, n)):
                excluded.add(i)

        # Compute adaptive threshold
        threshold = self._compute_adaptive_threshold(global_scores, excluded)

        # Strategy 1: Contiguous region detection
        contiguous = self._find_contiguous_regions(
            sequence, residue_scores, global_scores, excluded, threshold
        )

        # Strategy 2: Peak detection + region growing
        peaks = self._find_peaks(global_scores, excluded)
        peak_candidates = []
        for peak_pos in peaks:
            epitope = self._grow_region(
                sequence, residue_scores, global_scores, peak_pos, excluded
            )
            if epitope is not None:
                peak_candidates.append(epitope)

        # Strategy 3: Systematic sliding window (multiple candidates)
        systematic = self._systematic_scan(
            sequence, residue_scores, global_scores, excluded, threshold
        )

        # Combine all candidates
        all_candidates = contiguous + peak_candidates + systematic

        # Merge overlapping/adjacent candidates
        all_candidates = self._merge_adjacent(
            all_candidates, sequence, residue_scores
        )

        # Remove duplicates and heavy overlaps
        all_candidates = self._remove_overlaps(all_candidates)

        # Apply filters
        filtered = []
        for cand in all_candidates:
            cand = self._apply_filters(cand, residue_scores)
            filtered.append(cand)

        # Sort by global score (descending)
        filtered.sort(key=lambda c: c.global_score, reverse=True)

        # Assign ranks to valid epitopes
        valid = [c for c in filtered if c.is_valid]

        for i, c in enumerate(valid):
            c.rank = i + 1

        # Return top N valid
        top_n = self.criteria.get("top_n_epitopes", 20)
        result = valid[:top_n]

        return result

    def _compute_adaptive_threshold(
        self, scores: np.ndarray, excluded: Set[int]
    ) -> float:
        """
        Compute an adaptive score threshold based on the score distribution
        of non-excluded residues.

        Uses: mean - 0.5 * std of non-excluded scores, but no lower than
        the configured min_global_score.

        Args:
            scores: Global score array.
            excluded: Excluded positions.

        Returns:
            Adaptive threshold value.
        """
        if not self.criteria.get("adaptive_threshold", True):
            return self.criteria.get("min_global_score", 0.35)

        # Use only non-excluded positions
        mask = np.ones(len(scores), dtype=bool)
        for i in excluded:
            if 0 <= i < len(scores):
                mask[i] = False

        valid_scores = scores[mask]
        if len(valid_scores) == 0:
            return self.criteria.get("min_global_score", 0.35)

        # Adaptive: mean - 0.7*std (captures more above-average regions)
        adaptive = float(np.mean(valid_scores) - 0.7 * np.std(valid_scores))

        # Don't go below configured minimum
        floor = self.criteria.get("min_global_score", 0.25)
        return max(adaptive, floor)

    def _find_contiguous_regions(
        self,
        sequence: str,
        residue_scores: List[ResidueScore],
        global_scores: np.ndarray,
        excluded: Set[int],
        threshold: float,
    ) -> List[EpitopeCandidate]:
        """
        Find contiguous regions where the global score stays above threshold.
        Allows small gaps (merge_gap) of below-threshold residues.

        This is the primary detection method — it naturally identifies
        long epitopes spanning regions of sustained high scores.

        Args:
            sequence: Protein sequence.
            residue_scores: Residue scores.
            global_scores: Global score array.
            excluded: Excluded positions.
            threshold: Score threshold.

        Returns:
            List of EpitopeCandidate objects.
        """
        n = len(sequence)
        min_len = self.criteria["min_length"]
        max_len = self.criteria["max_length"]
        merge_gap = self.criteria.get("merge_gap", 3)

        # Mark positions above threshold and not excluded
        above = np.zeros(n, dtype=bool)
        for i in range(n):
            if i not in excluded and global_scores[i] >= threshold:
                above[i] = True

        # Find contiguous regions, bridging small gaps
        regions = []
        in_region = False
        start = 0
        gap_count = 0

        for i in range(n):
            if above[i]:
                if not in_region:
                    in_region = True
                    start = i
                gap_count = 0
            else:
                if in_region:
                    gap_count += 1
                    if gap_count > merge_gap or i in excluded:
                        # End of region
                        end = i - gap_count
                        if end - start >= min_len:
                            regions.append((start, end))
                        in_region = False
                        gap_count = 0

        # Close last region
        if in_region:
            end = n - gap_count if gap_count > 0 else n
            if end - start >= min_len:
                regions.append((start, end))

        # Convert to candidates, splitting if too long
        candidates = []
        for start, end in regions:
            length = end - start
            if length <= max_len:
                cand = self._create_candidate(
                    sequence, residue_scores, start, end
                )
                if cand is not None:
                    candidates.append(cand)
            else:
                # Split into overlapping windows of max_len
                # and also keep the full region as a candidate
                # if it's not excessively long
                if length <= max_len + 10:
                    cand = self._create_candidate(
                        sequence, residue_scores, start, end
                    )
                    if cand is not None:
                        candidates.append(cand)

                # Also produce sub-windows
                step = max(1, min_len // 2)
                for s in range(start, end - min_len + 1, step):
                    e = min(s + max_len, end)
                    if e - s >= min_len:
                        cand = self._create_candidate(
                            sequence, residue_scores, s, e
                        )
                        if cand is not None:
                            candidates.append(cand)

        return candidates

    def _find_peaks(
        self, scores: np.ndarray, excluded: Set[int]
    ) -> List[int]:
        """
        Find local peaks in the score profile.

        A peak is a position where the score is higher than both
        neighbors within a neighborhood window.

        Args:
            scores: Global score array.
            excluded: Set of excluded positions.

        Returns:
            List of peak positions (0-indexed).
        """
        n = len(scores)
        peaks = []
        min_len = self.criteria["min_length"]
        neighborhood = min_len // 2

        for i in range(neighborhood, n - neighborhood):
            if i in excluded:
                continue

            # Check if this is a local maximum
            window = scores[max(0, i - neighborhood):min(n, i + neighborhood + 1)]
            if scores[i] >= np.max(window) - 1e-10:
                peaks.append(i)

        # Remove peaks too close together
        if peaks:
            filtered = [peaks[0]]
            for p in peaks[1:]:
                if p - filtered[-1] >= min_len:
                    filtered.append(p)
                elif scores[p] > scores[filtered[-1]]:
                    filtered[-1] = p
            peaks = filtered

        return peaks

    def _grow_region(
        self,
        sequence: str,
        residue_scores: List[ResidueScore],
        global_scores: np.ndarray,
        peak_pos: int,
        excluded: Set[int],
    ) -> Optional[EpitopeCandidate]:
        """
        Grow an epitope region around a peak position.

        Extends the region in both directions while maintaining
        high scores, targeting 12-25 amino acids.

        Args:
            sequence: Protein sequence.
            residue_scores: Residue scores.
            global_scores: Global score array.
            peak_pos: Peak position (0-indexed).
            excluded: Excluded positions.

        Returns:
            EpitopeCandidate or None.
        """
        n = len(sequence)
        min_len = self.criteria["min_length"]
        max_len = self.criteria["max_length"]

        # Start with a minimal region centered at peak
        half = min_len // 2
        start = max(0, peak_pos - half)
        end = min(n, start + min_len)

        if end - start < min_len:
            start = max(0, end - min_len)

        # Check for excluded positions
        for i in range(start, end):
            if i in excluded:
                return None

        # Try to extend to maximize score (up to max_len)
        best_score = np.mean(global_scores[start:end])
        best_start, best_end = start, end

        for s in range(max(0, peak_pos - max_len // 2),
                       min(n - min_len + 1, peak_pos + 1)):
            for e in range(s + min_len, min(n + 1, s + max_len + 1)):
                # Check no excluded positions
                has_excluded = any(i in excluded for i in range(s, e))
                if has_excluded:
                    continue

                score = np.mean(global_scores[s:e])
                if score > best_score:
                    best_score = score
                    best_start = s
                    best_end = e

        return self._create_candidate(
            sequence, residue_scores, best_start, best_end
        )

    def _systematic_scan(
        self,
        sequence: str,
        residue_scores: List[ResidueScore],
        global_scores: np.ndarray,
        excluded: Set[int],
        threshold: float,
    ) -> List[EpitopeCandidate]:
        """
        Systematically scan for high-scoring regions using sliding windows
        of various lengths. Finds ALL above-threshold windows (not just one
        per length).

        Args:
            sequence: Protein sequence.
            residue_scores: Residue scores.
            global_scores: Global score array.
            excluded: Excluded positions.
            threshold: Minimum score threshold.

        Returns:
            List of candidate epitopes.
        """
        n = len(sequence)
        min_len = self.criteria["min_length"]
        max_len = self.criteria["max_length"]
        candidates = []

        # Try a few representative lengths
        lengths_to_try = set()
        for l in range(min_len, min(max_len + 1, n + 1)):
            if l <= 15 or l >= max_len - 2 or l % 3 == 0:
                lengths_to_try.add(l)
        # Always include min, max, and some intermediates
        lengths_to_try.add(min_len)
        lengths_to_try.add(max_len)
        lengths_to_try.add((min_len + max_len) // 2)

        for length in sorted(lengths_to_try):
            if length > n:
                continue

            # Collect ALL windows above threshold for this length
            window_scores = []
            for start in range(n - length + 1):
                end = start + length
                has_excluded = any(i in excluded for i in range(start, end))
                if has_excluded:
                    continue
                score = np.mean(global_scores[start:end])
                if score >= threshold:
                    window_scores.append((score, start))

            # Sort by score descending, take top candidates
            window_scores.sort(reverse=True)
            for score, start in window_scores[:8]:  # Top 8 per length
                cand = self._create_candidate(
                    sequence, residue_scores, start, start + length
                )
                if cand is not None:
                    candidates.append(cand)

        return candidates

    def _merge_adjacent(
        self,
        candidates: List[EpitopeCandidate],
        sequence: str,
        residue_scores: List[ResidueScore],
    ) -> List[EpitopeCandidate]:
        """
        Merge overlapping or adjacent candidate epitopes into longer ones.

        Two candidates are merged if they overlap or are within merge_gap
        residues of each other. The merged candidate spans the full range
        of the originals.

        Args:
            candidates: List of candidates to merge.
            sequence: Protein sequence.
            residue_scores: Residue scores.

        Returns:
            Merged list of candidates (may be shorter).
        """
        if not candidates:
            return []

        merge_gap = self.criteria.get("merge_gap", 3)
        max_len = self.criteria.get("max_length", 35)

        # Convert to 0-indexed intervals: (start, end_exclusive)
        intervals = []
        for c in candidates:
            s = c.start - 1  # Convert from 1-indexed
            e = c.end        # Already exclusive in 0-indexed
            intervals.append((s, e))

        # Sort by start position
        intervals.sort()

        # Merge overlapping/adjacent intervals
        merged = [intervals[0]]
        for s, e in intervals[1:]:
            prev_s, prev_e = merged[-1]
            if s <= prev_e + merge_gap:
                # Merge: extend end if needed
                merged[-1] = (prev_s, max(prev_e, e))
            else:
                merged.append((s, e))

        # Create candidates from merged intervals
        result = []
        for s, e in merged:
            length = e - s
            if length <= max_len:
                cand = self._create_candidate(sequence, residue_scores, s, e)
                if cand is not None:
                    result.append(cand)
            else:
                # Region too long — keep full region if within tolerance
                if length <= max_len + 10:
                    cand = self._create_candidate(
                        sequence, residue_scores, s, e
                    )
                    if cand is not None:
                        result.append(cand)

                # Also split into overlapping sub-windows
                min_len = self.criteria["min_length"]
                step = max(1, min_len // 2)
                for ws in range(s, e - min_len + 1, step):
                    we = min(ws + max_len, e)
                    if we - ws >= min_len:
                        cand = self._create_candidate(
                            sequence, residue_scores, ws, we
                        )
                        if cand is not None:
                            result.append(cand)

        return result

    def _create_candidate(
        self,
        sequence: str,
        residue_scores: List[ResidueScore],
        start: int,
        end: int,
    ) -> Optional[EpitopeCandidate]:
        """
        Create an EpitopeCandidate from a region.

        Args:
            sequence: Protein sequence.
            residue_scores: Residue scores.
            start: Start position (0-indexed).
            end: End position (0-indexed, exclusive).

        Returns:
            EpitopeCandidate or None if invalid range.
        """
        if end <= start or start < 0 or end > len(sequence):
            return None

        subseq = sequence[start:end]
        sub_scores = residue_scores[start:end]

        # Calculate averages
        avg_global = np.mean([s.global_score for s in sub_scores])
        avg_hydrophilicity = np.mean([s.hydrophilicity for s in sub_scores])
        avg_hydrophobicity = np.mean([s.hydrophobicity for s in sub_scores])
        avg_flexibility = np.mean([s.flexibility for s in sub_scores])
        avg_accessibility = np.mean([s.accessibility for s in sub_scores])
        avg_antigenicity = np.mean([s.antigenicity for s in sub_scores])
        avg_sasa = np.mean([s.structural_sasa for s in sub_scores])

        # Calculate hydrophilic residue fraction
        n_hydrophilic = sum(1 for aa in subseq if aa in HYDROPHILIC_RESIDUES)
        hydrophilic_fraction = n_hydrophilic / len(subseq) if subseq else 0

        return EpitopeCandidate(
            rank=0,
            start=start + 1,      # 1-indexed
            end=end,               # 1-indexed inclusive
            sequence=subseq,
            length=len(subseq),
            global_score=float(avg_global),
            hydrophilicity=float(avg_hydrophilicity),
            hydrophobicity=float(avg_hydrophobicity),
            flexibility=float(avg_flexibility),
            accessibility=float(avg_accessibility),
            antigenicity=float(avg_antigenicity),
            structural_sasa=float(avg_sasa),
            hydrophilic_fraction=float(hydrophilic_fraction),
            is_valid=True,
            exclusion_reasons=[],
        )

    def _apply_filters(
        self,
        candidate: EpitopeCandidate,
        residue_scores: List[ResidueScore],
    ) -> EpitopeCandidate:
        """
        Apply all selection filters to a candidate.

        Filters based on:
        1. Hydrophilicity (Hopp & Woods > 0)
        2. Surface accessibility (Emini > 1.0)
        3. Hydrophobic residue content
        4. Antigenicity threshold
        5. Pellequer & Westhof (1993) empirical rules
        6. Saha & Raghava (2006) composition rules

        Args:
            candidate: Epitope candidate to filter.
            residue_scores: All residue scores.

        Returns:
            Updated EpitopeCandidate with validation status.
        """
        reasons = []

        # 1. Hydrophilicity check
        if candidate.hydrophilicity < self.criteria.get(
            "min_hydrophilicity", 0.0
        ):
            reasons.append(
                f"Low hydrophilicity ({candidate.hydrophilicity:.2f})"
            )

        # 2. Surface accessibility check
        if candidate.accessibility < self.criteria.get(
            "min_accessibility", 1.0
        ):
            reasons.append(
                f"Low surface accessibility ({candidate.accessibility:.2f})"
            )

        # 3. Hydrophobic residue check (Pellequer & Westhof 1993)
        n_hydrophobic = sum(
            1 for aa in candidate.sequence if aa in HYDROPHOBIC_RESIDUES
        )
        hydrophobic_fraction = n_hydrophobic / candidate.length
        if hydrophobic_fraction > 0.65:
            reasons.append(
                f"Too many hydrophobic residues ({hydrophobic_fraction:.0%})"
            )

        # 4. Minimum hydrophilic residue content (Saha & Raghava 2006)
        if candidate.hydrophilic_fraction < 0.15:
            reasons.append(
                f"Low hydrophilic content ({candidate.hydrophilic_fraction:.0%})"
            )

        # 5. Too high hydrophobicity (potential TM region)
        if candidate.hydrophobicity > self.criteria.get(
            "max_hydrophobicity", 0.5
        ):
            reasons.append(
                f"High hydrophobicity ({candidate.hydrophobicity:.2f})"
            )

        # 6. Length validation
        if candidate.length < self.criteria["min_length"]:
            reasons.append(f"Too short ({candidate.length} aa)")
        if candidate.length > self.criteria["max_length"]:
            reasons.append(f"Too long ({candidate.length} aa)")

        # 7. Global score threshold
        if candidate.global_score < self.criteria.get(
            "min_global_score", 0.5
        ):
            reasons.append(
                f"Low global score ({candidate.global_score:.3f})"
            )

        # Update candidate
        candidate.is_valid = len(reasons) == 0
        candidate.exclusion_reasons = reasons

        return candidate

    def _remove_overlaps(
        self, candidates: List[EpitopeCandidate]
    ) -> List[EpitopeCandidate]:
        """
        Remove overlapping candidates, keeping the highest scoring ones.

        Two candidates overlap if they share more than 50% of their
        positions.

        Args:
            candidates: List of EpitopeCandidate objects.

        Returns:
            Non-overlapping candidates.
        """
        if not candidates:
            return []

        # Sort by score descending
        candidates.sort(key=lambda c: c.global_score, reverse=True)

        selected = []
        used_positions = set()

        for cand in candidates:
            cand_positions = set(range(cand.start - 1, cand.end))
            overlap = len(cand_positions & used_positions)
            overlap_fraction = overlap / len(cand_positions) if cand_positions else 0

            if overlap_fraction < 0.60:
                selected.append(cand)
                used_positions |= cand_positions

        return selected
