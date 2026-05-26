#!/usr/bin/env python3
"""Diagnostic: test with minimal overlap removal to find the upper bound."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
total = detected = 0
t0 = time.time()
for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    # Very permissive: overlap_fraction=0.99 means almost no dedup
    detector = EpitopeDetector({
        "min_length": 6, "max_length": 30, 
        "top_n": 300, "overlap_fraction": 0.99
    })
    hits = detector.detect(seq, results)

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
            tag = "DET"
        else:
            tag = "MIS"
        print(f"  [{idx:>3}] {tag} {best_ov:.0%}  {epi[:40]}")

elapsed = time.time() - t0
print(f"\nResult: {detected}/{total} = {detected/total*100:.1f}%  ({elapsed:.1f}s)")
