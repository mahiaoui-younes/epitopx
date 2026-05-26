#!/usr/bin/env python3
"""Detailed diagnostic for v47: analyze why TPs miss top-5.

For each protein, compare the TP at rank 6-10 (or rank>10) with
the FP(s) at rank 1-5 that displaced it.  Output per-protein details
and aggregate statistics.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector
import numpy as np

N = 50

# Collect all data
data = []
tp5_features = []
fp5_features = []
tp610_features = []

for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # Classify each hit as TP or FP
    hit_tp = {}  # hit_idx -> (epi, overlap)
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        for hi, h in enumerate(hits):
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov >= 0.50:
                if hi not in hit_tp or ov > hit_tp[hi][1]:
                    hit_tp[hi] = (epi, ov)

    # For each known epitope, find best match
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        best_ov = 0.0
        best_rk = 999
        best_hit = None
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                best_rk = h.rank
                best_hit = h

        if best_ov < 0.50:
            continue  # miss

        feat = {
            'len': best_hit.length,
            'rank': best_rk,
            'ranking_score': best_hit.ranking_score,
            'combined': best_hit.combined_score,
            'peak': best_hit.peak_combined_score,
            'consensus': best_hit.consensus_score,
            'antigenicity': best_hit.antigenicity,
            'bepipred': best_hit.bepipred,
            'welling': best_hit.welling,
            'disorder': best_hit.disorder,
        }

        if best_rk <= 5:
            tp5_features.append(feat)
        elif best_rk <= 10:
            tp610_features.append(feat)

    # Classify rank 1-5 hits as TP or FP
    for hi, h in enumerate(hits[:5]):
        feat = {
            'len': h.length,
            'rank': h.rank,
            'ranking_score': h.ranking_score,
            'combined': h.combined_score,
            'peak': h.peak_combined_score,
            'consensus': h.consensus_score,
            'antigenicity': h.antigenicity,
            'bepipred': h.bepipred,
            'welling': h.welling,
            'disorder': h.disorder,
        }
        if hi not in hit_tp:
            fp5_features.append(feat)
            fp5_features[-1]['protein'] = idx

    # For misses at rank 6-10, print details
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        if ks == 0:
            continue
        best_ov = 0.0
        best_rk = 999
        best_hit = None
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                best_rk = h.rank
                best_hit = h
        if best_ov >= 0.50 and 6 <= best_rk <= 10:
            # Find what's at rank 5 (the FP that displaced this TP)
            r5_hit = hits[4] if len(hits) >= 5 else None
            is_r5_fp = r5_hit and (4 not in hit_tp)
            data.append({
                'prot': idx,
                'epi': epi[:30],
                'tp_rank': best_rk,
                'tp_score': best_hit.ranking_score,
                'tp_len': best_hit.length,
                'tp_combined': best_hit.combined_score,
                'tp_peak': best_hit.peak_combined_score,
                'tp_consensus': best_hit.consensus_score,
                'r5_is_fp': is_r5_fp,
                'r5_score': r5_hit.ranking_score if r5_hit else 0,
                'r5_len': r5_hit.length if r5_hit else 0,
                'r5_combined': r5_hit.combined_score if r5_hit else 0,
                'r5_peak': r5_hit.peak_combined_score if r5_hit else 0,
                'r5_consensus': r5_hit.consensus_score if r5_hit else 0,
            })

print("=" * 80)
print(f"Top-5 TPs: {len(tp5_features)}, Top-5 FPs: {len(fp5_features)}, Rank 6-10 TPs: {len(tp610_features)}")
print("=" * 80)

def mean_feat(feat_list, key):
    vals = [f[key] for f in feat_list]
    return np.mean(vals) if vals else 0

print(f"\n{'Feature':<20} {'Top5-TP':>10} {'Top5-FP':>10} {'R6-10 TP':>10}")
print("-" * 55)
for key in ['len', 'ranking_score', 'combined', 'peak', 'consensus', 'antigenicity', 'bepipred', 'welling', 'disorder']:
    v_tp = mean_feat(tp5_features, key)
    v_fp = mean_feat(fp5_features, key)
    v_610 = mean_feat(tp610_features, key)
    print(f"{key:<20} {v_tp:>10.3f} {v_fp:>10.3f} {v_610:>10.3f}")

print(f"\nLength distribution of Top-5 FPs:")
fp_lens = [f['len'] for f in fp5_features]
for l in sorted(set(fp_lens)):
    cnt = fp_lens.count(l)
    print(f"  len={l}: {cnt} ({cnt/len(fp_lens)*100:.0f}%)")

print(f"\nRank 6-10 TPs that could be salvaged ({len(data)} near-misses):")
for d in data:
    gap = d['tp_score'] - d['r5_score']
    print(f"  P{d['prot']:>2} epi={d['epi'][:25]:<25s} "
          f"tp_rk={d['tp_rank']} tp_scr={d['tp_score']:.3f} tp_len={d['tp_len']:>2} "
          f"| r5_scr={d['r5_score']:.3f} r5_len={d['r5_len']:>2} "
          f"gap={gap:+.3f} r5_fp={d['r5_is_fp']}")

# Check how many rank 6-10 TPs have higher ranking_score than rank 5
salvage_count = sum(1 for d in data if d['tp_score'] > d['r5_score'])
print(f"\nRank 6-10 TPs with score > Rank 5: {salvage_count}/{len(data)}")

# Check if rank 5 is FP
r5_fp_count = sum(1 for d in data if d['r5_is_fp'])
print(f"Rank 5 is FP: {r5_fp_count}/{len(data)}")

# Analyze what features FPs at rank 1-5 exploit
print(f"\n--- Key discriminators (R6-10 TP vs Top5 FP) ---")
for key in ['len', 'ranking_score', 'combined', 'peak', 'consensus', 'antigenicity', 'bepipred', 'welling', 'disorder']:
    v_fp = mean_feat(fp5_features, key)
    v_610 = mean_feat(tp610_features, key)
    if v_fp != 0:
        ratio = (v_610 - v_fp) / abs(v_fp) * 100
        print(f"  {key:<20}: R6-10 TP={v_610:.3f}, Top5 FP={v_fp:.3f}, diff={ratio:+.0f}%")
