#!/usr/bin/env python3
"""Quick test on first 50 proteins to measure sensitivity."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50  # first 50 proteins
total = detected = 0
near_misses = []
zero_misses = []

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
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
        if best_ov >= 0.50:
            detected += 1
            tag = "DET"
        else:
            tag = "MIS"
            if best_ov > 0.25:
                near_misses.append((prot.name, epi, best_ov))
            elif best_ov == 0.0:
                zero_misses.append((prot.name, epi))
        print(f"  [{idx:>3}] {tag} {best_ov:.0%}  {epi[:40]}")

elapsed = time.time() - t0
print(f"\n{'='*60}")
print(f"  Result: {detected}/{total} = {detected/total*100:.1f}%")
print(f"  Time: {elapsed:.1f}s")
print(f"  Near misses (25-49%): {len(near_misses)}")
for name, epi, ov in near_misses:
    print(f"    {name:30s} {epi:30s} {ov:.0%}")
print(f"  Zero misses (0%): {len(zero_misses)}")
for name, epi in zero_misses:
    print(f"    {name:30s} {epi}")
print(f"{'='*60}")
