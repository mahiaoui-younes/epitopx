#!/usr/bin/env python3
"""Detailed analysis of the 52 detected-but-not-top-5 epitopes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
rank_histogram = {}
proteins_with_misses = {}  # protein index -> list of missed ranks

total = detected = t5 = 0
for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)
    
    n_known = len(prot.known_epitopes)
    n_in_top5 = 0
    n_detected = 0
    
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
            n_detected += 1
            if best_rk <= 5:
                t5 += 1
                n_in_top5 += 1
            else:
                rank_histogram[best_rk] = rank_histogram.get(best_rk, 0) + 1
                if idx not in proteins_with_misses:
                    proteins_with_misses[idx] = []
                proteins_with_misses[idx].append(best_rk)
    
    # Print per-protein summary
    if n_detected > 0 and n_in_top5 < n_detected:
        missed = n_detected - n_in_top5
        print(f"P{idx:>3}: {n_known} known, {n_detected} det, {n_in_top5}/5 hit, {missed} miss  seqlen={len(seq)}")

print(f"\n=== Summary ===")
print(f"Total: {total}, Detected: {detected}, Top-5: {t5}")
print(f"Detected but not top-5: {detected - t5}")
print()

# Rank distribution of misses
print("Rank distribution of detected-but-not-top-5:")
for rank in sorted(rank_histogram.keys()):
    print(f"  rank {rank:>3}: {rank_histogram[rank]}")

# How many proteins have >5 known epitopes?
print("\n--- Proteins with >5 known epitopes: ---")
for idx, prot in enumerate(PROTEINS[:N], 1):
    n_known = len(prot.known_epitopes)
    if n_known > 5:
        print(f"  P{idx}: {n_known} known epitopes")

# How many proteins contribute most to the misses?
print("\n--- Proteins contributing most misses: ---")
by_miss_count = sorted(proteins_with_misses.items(), 
                        key=lambda x: len(x[1]), reverse=True)
for idx, ranks in by_miss_count[:15]:
    print(f"  P{idx}: {len(ranks)} misses at ranks {sorted(ranks)}")
