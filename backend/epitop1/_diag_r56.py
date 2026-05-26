#!/usr/bin/env python3
"""Diagnostic: show positions 1-10 for proteins where TPs are at rank 6-7."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
lines = []
P = lines.append

for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # Check if any known epitope has best rank = 6 or 7
    has_r6_tp = False
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        best_ov = 0.0
        best_rk = 999
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                best_rk = h.rank
        if best_ov >= 0.50 and best_rk in (6, 7):
            has_r6_tp = True

    if not has_r6_tp:
        continue

    P("")
    P("=" * 80)
    P(f"PROTEIN {idx}: len={len(seq)}")
    P("Known epitopes:")
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks > 0:
            P(f"  [{ks}-{ke}] {epi[:30]}")

    P("")
    P("  Rank | Len | RankScr | CombScr | Peak    | Cons  | Well  | Bep   | Contr | TP?    | Sequence")
    P("  " + "-" * 110)
    for h in sorted(hits, key=lambda x: x.rank):
        if h.rank > 10:
            break
        is_tp = False
        best_ov_h = 0.0
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0:
                continue
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov >= 0.50:
                is_tp = True
                best_ov_h = max(best_ov_h, ov)

        tp_flag = f"TP {best_ov_h:.0%}" if is_tp else "FP"
        marker = " <<<" if h.rank in (5, 6) else ""
        P(f"  r{h.rank:>3} | {h.length:>3} | {h.ranking_score:.4f} | {h.combined_score:.4f} | "
          f"{h.peak_combined_score:.4f} | {h.consensus_score:.3f} | "
          f"{h.welling:.4f} | {h.bepipred:.4f} | {h.score_contrast:.4f} | "
          f"{tp_flag:>6s} | [{h.start}-{h.end}] {h.sequence[:20]}{marker}")

    r5 = [h for h in hits if h.rank == 5]
    r6 = [h for h in hits if h.rank == 6]
    if r5 and r6:
        P(f"\n  RankScore: r5={r5[0].ranking_score:.4f}  r6={r6[0].ranking_score:.4f}  "
          f"gap={r5[0].ranking_score - r6[0].ranking_score:.4f}  "
          f"ratio={r5[0].ranking_score / r6[0].ranking_score:.3f}")

with open("_diag_r56_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Done. See _diag_r56_result.txt")
