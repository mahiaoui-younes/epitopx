#!/usr/bin/env python3
"""Test regional diversity at different region sizes and with length caps."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector, EpitopeHit

N = 50

def run_test(region_sz, max_length=28, label=""):
    total = detected = t5 = t10 = 0
    t0 = time.time()
    for idx, prot in enumerate(PROTEINS[:N], 1):
        seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
        scorer = CombinedScorer()
        results = scorer.get_residue_results(seq)
        det = EpitopeDetector({"min_length": 7, "max_length": max_length, "top_n": 150})
        hits = det.detect(seq, results)
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
    elapsed = time.time() - t0
    print(f"  {label:30s} sens={detected}/{total} ({detected/total*100:.1f}%)  "
          f"top5={t5}/{total} ({t5/total*100:.1f}%)  "
          f"top10={t10}/{total} ({t10/total*100:.1f}%)  "
          f"{elapsed:.0f}s")

# Test current setup (region_sz=20 is in the source)
print("Testing with region_sz=20 (current code):")
run_test(20, label="region_sz=20, max_len=28")

# Test with max_length=22
print("\nTesting with max_length=22:")
run_test(20, max_length=22, label="region_sz=20, max_len=22")

# Test with max_length=20
print("\nTesting with max_length=20:")
run_test(20, max_length=20, label="region_sz=20, max_len=20")
