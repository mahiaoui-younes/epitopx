#!/usr/bin/env python3
"""Quick test on first 50 proteins — measures sensitivity AND ranking."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
total = detected = t5 = t10 = 0

t0 = time.time()
for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    for epi in prot.known_epitopes:
        total += 1
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
        if best_ov >= 0.50:
            detected += 1
            if best_rk <= 5: t5 += 1
            if best_rk <= 10: t10 += 1
            tag = f"DET r{best_rk}"
        else:
            tag = "MIS"
        print(f"  [{idx:>3}] {tag:10s} {best_ov:.0%}  {epi[:40]}")

elapsed = time.time() - t0
print(f"\n{'='*60}")
print(f"  Sensitivity: {detected}/{total} = {detected/total*100:.1f}%")
print(f"  Top-5 rate:  {t5}/{total} = {t5/total*100:.1f}%")
print(f"  Top-10 rate: {t10}/{total} = {t10/total*100:.1f}%")
print(f"  Time: {elapsed:.1f}s")
print(f"{'='*60}")
