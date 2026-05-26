"""
Evaluation module for B-cell linear epitope prediction.

Compares predicted epitope candidates against experimentally validated
epitopes and computes overlap, coverage, and detection metrics.

Metrics computed:
    - Amino acid overlap percentage (Jaccard and positional)
    - Top-N hit rate (is the known epitope in the top N predictions?)
    - Per-protein summary table
    - Sensitivity and false-positive indicators

References:
    Vita R et al. (2019) The Immune Epitope Database (IEDB).
    Nucleic Acids Res 47:D339-D343.

    Jespersen MC et al. (2017) BepiPred-2.0: improving sequence-based
    B-cell epitope prediction using conformational epitopes.
    Nucleic Acids Res 45:W24-W29.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

from core.epitope_selector import EpitopeCandidate


@dataclass
class EpitopeOverlap:
    """Overlap result between a predicted and a known epitope."""
    predicted_rank: int          # Rank of the predicted epitope
    predicted_start: int         # Predicted start (1-indexed)
    predicted_end: int           # Predicted end (1-indexed)
    predicted_sequence: str      # Predicted sequence
    predicted_score: float       # Composite score of predicted epitope
    known_start: int             # Known epitope start (1-indexed)
    known_end: int               # Known epitope end (1-indexed)
    known_sequence: str          # Known epitope sequence
    overlap_residues: int        # Number of overlapping residue positions
    overlap_pct_of_known: float  # % of known epitope covered
    overlap_pct_of_predicted: float  # % of predicted that overlaps
    jaccard_similarity: float    # |intersection| / |union|
    is_hit: bool                 # Treated as a successful detection


@dataclass
class ProteinEvaluation:
    """Complete evaluation result for one protein."""
    protein_name: str
    sequence_length: int
    num_known_epitopes: int
    num_predicted: int
    overlaps: List[EpitopeOverlap]
    detected_known: List[str]       # Known epitope sequences detected
    missed_known: List[str]         # Known epitope sequences missed
    true_positive_count: int        # How many known epitopes were found
    false_positive_count: int       # Predictions not matching any known
    sensitivity: float              # TP / total_known
    detection_in_top5: bool         # Any known epitope in top-5?
    detection_in_top10: bool        # Any known epitope in top-10?
    best_overlap_pct: float         # Best overlap % achieved for any known


def parse_known_epitopes(
    text: str,
    protein_sequence: str = "",
) -> List[Dict]:
    """
    Parse known epitope sequences from user input.

    Accepts formats:
    - One epitope per line (sequence only)
    - start-end:SEQUENCE
    - FASTA-like (>header\\nSEQUENCE)

    If protein_sequence is provided, positions are auto-detected
    by searching for the epitope within the protein.

    Args:
        text: Multi-line text with known epitopes.
        protein_sequence: Full protein sequence for position lookup.

    Returns:
        List of dicts with keys: sequence, start, end.
    """
    epitopes = []
    protein_sequence = protein_sequence.upper().strip()
    lines = text.strip().splitlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line or line.startswith('#'):
            continue

        # FASTA-like header
        if line.startswith('>'):
            # Next line is the epitope sequence
            if i < len(lines):
                seq = lines[i].strip().upper()
                seq = ''.join(c for c in seq if c.isalpha())
                i += 1
            else:
                continue
        elif ':' in line:
            # Format: start-end:SEQUENCE or label:SEQUENCE
            parts = line.split(':', 1)
            seq = parts[1].strip().upper()
            seq = ''.join(c for c in seq if c.isalpha())
        else:
            # Plain sequence
            seq = line.upper()
            seq = ''.join(c for c in seq if c.isalpha())

        if len(seq) < 4:
            continue

        # Find position in protein
        start, end = 0, 0
        if protein_sequence and seq in protein_sequence:
            pos = protein_sequence.find(seq)
            start = pos + 1  # 1-indexed
            end = pos + len(seq)

        epitopes.append({
            "sequence": seq,
            "start": start,
            "end": end,
            "length": len(seq),
        })

    return epitopes


def compute_overlap(
    predicted: EpitopeCandidate,
    known: Dict,
) -> EpitopeOverlap:
    """
    Compute overlap metrics between a predicted and a known epitope.

    Uses positional overlap when both have valid positions,
    otherwise falls back to sequence-based matching.

    Args:
        predicted: Predicted EpitopeCandidate.
        known: Known epitope dict with sequence, start, end.

    Returns:
        EpitopeOverlap result.
    """
    pred_start = predicted.start
    pred_end = predicted.end
    known_start = known["start"]
    known_end = known["end"]

    # Positional overlap
    if known_start > 0 and known_end > 0:
        pred_set = set(range(pred_start, pred_end + 1))
        known_set = set(range(known_start, known_end + 1))
        intersection = pred_set & known_set
        union = pred_set | known_set
        overlap_count = len(intersection)
        jaccard = len(intersection) / len(union) if union else 0.0
        overlap_of_known = overlap_count / len(known_set) if known_set else 0.0
        overlap_of_pred = overlap_count / len(pred_set) if pred_set else 0.0
    else:
        # Fall back to sequence match
        known_seq = known["sequence"]
        pred_seq = predicted.sequence
        # Count matching chars via LCS-like approach
        overlap_count = _count_common_substring_overlap(pred_seq, known_seq)
        jaccard = overlap_count / (len(pred_seq) + len(known_seq) - overlap_count) if (len(pred_seq) + len(known_seq) - overlap_count) > 0 else 0
        overlap_of_known = overlap_count / len(known_seq) if known_seq else 0.0
        overlap_of_pred = overlap_count / len(pred_seq) if pred_seq else 0.0

    # A hit requires >=50% of the known epitope to be covered
    is_hit = overlap_of_known >= 0.50

    return EpitopeOverlap(
        predicted_rank=predicted.rank,
        predicted_start=pred_start,
        predicted_end=pred_end,
        predicted_sequence=predicted.sequence,
        predicted_score=predicted.global_score,
        known_start=known_start,
        known_end=known_end,
        known_sequence=known["sequence"],
        overlap_residues=overlap_count,
        overlap_pct_of_known=round(overlap_of_known * 100, 1),
        overlap_pct_of_predicted=round(overlap_of_pred * 100, 1),
        jaccard_similarity=round(jaccard, 4),
        is_hit=is_hit,
    )


def _count_common_substring_overlap(s1: str, s2: str) -> int:
    """Count overlapping characters via longest common substring."""
    if not s1 or not s2:
        return 0
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    max_len = 0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
                max_len = max(max_len, dp[i][j])
    return max_len


def evaluate_predictions(
    epitopes: List[EpitopeCandidate],
    known_epitopes: List[Dict],
    protein_name: str = "Unknown",
    sequence_length: int = 0,
    hit_threshold: float = 0.50,
) -> ProteinEvaluation:
    """
    Evaluate predicted epitopes against known/validated epitopes.

    For each known epitope, finds the best-matching prediction
    and computes overlap metrics. Then classifies predictions
    as true positives or false positives.

    Args:
        epitopes: List of predicted EpitopeCandidate objects.
        known_epitopes: List of known epitope dicts.
        protein_name: Protein identifier.
        sequence_length: Total protein length.
        hit_threshold: Minimum overlap fraction to count as a hit.

    Returns:
        ProteinEvaluation summary.
    """
    all_overlaps = []
    detected = []
    missed = []

    # For each known epitope, find best matching prediction
    for known in known_epitopes:
        best_overlap = None
        best_jaccard = -1.0

        for pred in epitopes:
            ov = compute_overlap(pred, known)
            all_overlaps.append(ov)

            if ov.jaccard_similarity > best_jaccard:
                best_jaccard = ov.jaccard_similarity
                best_overlap = ov

        if best_overlap and best_overlap.overlap_pct_of_known >= hit_threshold * 100:
            detected.append(known["sequence"])
        else:
            missed.append(known["sequence"])

    # Count false positives: predictions that don't overlap any known
    matched_pred_ranks = set()
    for ov in all_overlaps:
        if ov.is_hit:
            matched_pred_ranks.add(ov.predicted_rank)

    fp_count = sum(1 for ep in epitopes if ep.rank not in matched_pred_ranks)

    # Top-N detection
    top5_hit = False
    top10_hit = False
    for ov in all_overlaps:
        if ov.is_hit:
            if ov.predicted_rank <= 5:
                top5_hit = True
            if ov.predicted_rank <= 10:
                top10_hit = True

    # Best overlap achieved
    best_pct = max(
        (ov.overlap_pct_of_known for ov in all_overlaps), default=0.0
    )

    num_known = len(known_epitopes)
    sensitivity = len(detected) / num_known if num_known > 0 else 0.0

    return ProteinEvaluation(
        protein_name=protein_name,
        sequence_length=sequence_length,
        num_known_epitopes=num_known,
        num_predicted=len(epitopes),
        overlaps=all_overlaps,
        detected_known=detected,
        missed_known=missed,
        true_positive_count=len(detected),
        false_positive_count=fp_count,
        sensitivity=round(sensitivity, 4),
        detection_in_top5=top5_hit,
        detection_in_top10=top10_hit,
        best_overlap_pct=round(best_pct, 1),
    )


def format_evaluation_report(evaluation: ProteinEvaluation) -> str:
    """
    Format a human-readable evaluation report.

    Args:
        evaluation: ProteinEvaluation result.

    Returns:
        Formatted string report.
    """
    lines = []
    lines.append("=" * 80)
    lines.append("  EVALUATION REPORT: PREDICTED vs. KNOWN EPITOPES")
    lines.append("=" * 80)
    lines.append(f"  Protein: {evaluation.protein_name}")
    lines.append(f"  Sequence length: {evaluation.sequence_length} aa")
    lines.append(f"  Known epitopes: {evaluation.num_known_epitopes}")
    lines.append(f"  Predicted epitopes: {evaluation.num_predicted}")
    lines.append("")

    # Detection summary
    lines.append("  DETECTION SUMMARY")
    lines.append("  " + "-" * 60)
    lines.append(
        f"  True positives (detected):  {evaluation.true_positive_count}"
        f" / {evaluation.num_known_epitopes}"
    )
    lines.append(
        f"  False positives:            {evaluation.false_positive_count}"
        f" / {evaluation.num_predicted}"
    )
    lines.append(
        f"  Sensitivity:                {evaluation.sensitivity:.1%}"
    )
    lines.append(
        f"  Best overlap:               {evaluation.best_overlap_pct:.1f}%"
    )
    lines.append(
        f"  Detected in Top-5:          "
        f"{'YES' if evaluation.detection_in_top5 else 'NO'}"
    )
    lines.append(
        f"  Detected in Top-10:         "
        f"{'YES' if evaluation.detection_in_top10 else 'NO'}"
    )
    lines.append("")

    # Known epitopes detected
    if evaluation.detected_known:
        lines.append("  DETECTED KNOWN EPITOPES:")
        for seq in evaluation.detected_known:
            lines.append(f"    [+] {seq}")
    if evaluation.missed_known:
        lines.append("  MISSED KNOWN EPITOPES:")
        for seq in evaluation.missed_known:
            lines.append(f"    [-] {seq}")
    lines.append("")

    # Detailed overlaps: group by known epitope, show best match
    seen_known = set()
    lines.append("  DETAILED OVERLAP TABLE")
    lines.append("  " + "-" * 76)
    lines.append(
        f"  {'Pred#':<6} {'Pred_Pos':<12} {'Score':<7} "
        f"{'Known_Pos':<12} {'Ovlp_aa':<8} {'Ovlp%_K':<8} "
        f"{'Jaccard':<8} {'Hit?'}"
    )
    lines.append("  " + "-" * 76)

    # Show only best match per known + per predicted
    best_per_known = {}
    for ov in evaluation.overlaps:
        key = ov.known_sequence
        if key not in best_per_known or ov.jaccard_similarity > best_per_known[key].jaccard_similarity:
            best_per_known[key] = ov

    for known_seq, ov in best_per_known.items():
        lines.append(
            f"  {ov.predicted_rank:<6} "
            f"{ov.predicted_start}-{ov.predicted_end:<7} "
            f"{ov.predicted_score:<7.4f} "
            f"{ov.known_start}-{ov.known_end:<7} "
            f"{ov.overlap_residues:<8} "
            f"{ov.overlap_pct_of_known:<7.1f}% "
            f"{ov.jaccard_similarity:<8.4f} "
            f"{'YES' if ov.is_hit else 'NO'}"
        )

    lines.append("")
    return "\n".join(lines)


def evaluation_to_dict(evaluation: ProteinEvaluation) -> Dict:
    """Convert evaluation to JSON-serializable dict."""
    return {
        "protein_name": evaluation.protein_name,
        "sequence_length": evaluation.sequence_length,
        "num_known_epitopes": evaluation.num_known_epitopes,
        "num_predicted": evaluation.num_predicted,
        "true_positive_count": evaluation.true_positive_count,
        "false_positive_count": evaluation.false_positive_count,
        "sensitivity": evaluation.sensitivity,
        "detection_in_top5": bool(evaluation.detection_in_top5),
        "detection_in_top10": bool(evaluation.detection_in_top10),
        "best_overlap_pct": evaluation.best_overlap_pct,
        "detected_known": evaluation.detected_known,
        "missed_known": evaluation.missed_known,
        "overlaps": [
            {
                "predicted_rank": ov.predicted_rank,
                "predicted_pos": f"{ov.predicted_start}-{ov.predicted_end}",
                "predicted_sequence": ov.predicted_sequence,
                "predicted_score": ov.predicted_score,
                "known_pos": f"{ov.known_start}-{ov.known_end}",
                "known_sequence": ov.known_sequence,
                "overlap_residues": ov.overlap_residues,
                "overlap_pct_of_known": ov.overlap_pct_of_known,
                "overlap_pct_of_predicted": ov.overlap_pct_of_predicted,
                "jaccard_similarity": ov.jaccard_similarity,
                "is_hit": bool(ov.is_hit),
            }
            for ov in evaluation.overlaps
            if ov.overlap_residues > 0  # Only include actual overlaps
        ],
    }
