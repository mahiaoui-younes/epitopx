#!/usr/bin/env python3
"""Deep analysis of ranking failures: where do epitope candidates rank
relative to non-epitope candidates, and WHY?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
missed_analyses = []

for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # For each known epitope
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        best_ov = 0.0
        best_hit = None
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                best_hit = h
        if best_ov >= 0.50 and best_hit and best_hit.rank > 5:
            # This epitope IS detected but NOT in top 5 — analyze why
            # Find what's in positions 1-5 instead
            top5 = [h for h in hits if h.rank <= 5]
            # Check overlap of top5 with any known epitope
            top5_is_epitope = []
            for h in top5:
                is_epi = False
                for e2 in prot.known_epitopes:
                    ks2, ke2 = find_epitope_in_sequence(seq, e2)
                    if ks2 == 0: continue
                    if overlap_fraction(h.start, h.end, ks2, ke2) >= 0.50:
                        is_epi = True
                        break
                top5_is_epitope.append(is_epi)
            
            n_true_in_top5 = sum(top5_is_epitope)
            n_false_in_top5 = 5 - n_true_in_top5
            
            missed_analyses.append({
                'protein': idx,
                'epitope': epi[:30],
                'rank': best_hit.rank,
                'length': best_hit.length,
                'combined': best_hit.combined_score,
                'ranking_score': best_hit.ranking_score,
                'consensus': best_hit.consensus_score,
                'antigenicity': best_hit.antigenicity,
                'bepipred': best_hit.bepipred,
                'true_in_top5': n_true_in_top5,
                'false_in_top5': n_false_in_top5,
            })

# Summary statistics
print(f"Total epitopes detected but NOT in top 5: {len(missed_analyses)}")
print()

# Group by rank range
from collections import Counter
rank_ranges = Counter()
for m in missed_analyses:
    if m['rank'] <= 10: rank_ranges['6-10'] += 1
    elif m['rank'] <= 20: rank_ranges['11-20'] += 1
    elif m['rank'] <= 50: rank_ranges['21-50'] += 1
    elif m['rank'] <= 150: rank_ranges['51-150'] += 1
    else: rank_ranges['150+'] += 1

print("Rank distribution of detected-but-not-top-5 epitopes:")
for rr in ['6-10','11-20','21-50','51-150','150+']:
    print(f"  {rr:>6}: {rank_ranges.get(rr, 0)}")

print()

# How many false positives are in top 5?
total_false = sum(m['false_in_top5'] for m in missed_analyses)
total_slots = len(missed_analyses) * 5
print(f"Average false positives in top 5 (for these proteins): {total_false/len(missed_analyses):.1f}/5")
print()

# Detailed per-protein analysis for first few
print("\n--- Detailed examples (first 15 ranked 6-20): ---")
count = 0
for m in missed_analyses:
    if m['rank'] <= 20 and count < 15:
        print(f"P{m['protein']:>3} rank={m['rank']:>3} len={m['length']:>2} "
              f"cs={m['combined']:.3f} rs={m['ranking_score']:.3f} "
              f"cons={m['consensus']:.2f} true_top5={m['true_in_top5']}/5 "
              f"false_top5={m['false_in_top5']}/5  {m['epitope']}")
        count += 1

# Key question: for proteins where epitopes rank 6-20,
# what would happen if we had more top-K slots?
print("\n--- What if we use top-K instead of top-5? ---")
for K in [3, 5, 7, 10, 15, 20]:
    count = sum(1 for m in missed_analyses if m['rank'] <= K) + sum(
        1 for prot_idx, prot in enumerate(PROTEINS[:N], 1) 
        for epi in prot.known_epitopes
        if any(True for h in [] if True)  # placeholder
    )
    # Actually let me compute properly
    pass

# Simpler: what fraction of detections are at each rank level
print("\n--- Cumulative detection by rank threshold: ---")
for K in [1, 2, 3, 4, 5, 6, 7, 8, 10, 15, 20, 30, 50]:
    in_k = sum(1 for m in missed_analyses if m['rank'] <= K)
    # Add the ones already in top 5 back
    print(f"  Top-{K:>3}: {in_k} would move in (of {len(missed_analyses)} misses)")

# Length distribution
print("\n--- Length distribution of misses vs hits: ---")
len_miss = Counter()
for m in missed_analyses:
    len_miss[m['length']] += 1
print("Missed epitope candidate lengths:")
for l in sorted(len_miss):
    print(f"  {l:>2} aa: {len_miss[l]}")
