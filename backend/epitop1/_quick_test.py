#!/usr/bin/env python3
"""Quick test of first 50 proteins to check improvement."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

total = 0
detected = 0

for idx, prot in enumerate(PROTEINS[:50], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    res = scorer.get_residue_results(seq)
    det = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 60})
    hits = det.detect(seq, res)

    for epi in prot.known_epitopes:
        total += 1
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        best_ov = 0.0
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
        if best_ov >= 0.50:
            detected += 1
            status = "DET"
        else:
            status = "MIS"
        print(f"  [{idx:>3}] {status} {best_ov:.0%} {prot.name[:30]:30s} {epi[:25]}")

print(f"\nFirst 50 proteins: {detected}/{total} = {detected/total*100:.1f}%")
