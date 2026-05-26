#!/usr/bin/env python3
"""Diagnose: compare top-5 FPs vs rank 6-10 TPs to find discriminative features."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
fp_in_top5 = []    # FP candidates ranked 1-5
tp_rank6_10 = []   # TP candidates ranked 6-10
tp_in_top5 = []    # TP candidates ranked 1-5

for prot in PROTEINS[:N]:
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # Classify each hit as TP or FP
    for h in hits:
        is_tp = False
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0:
                continue
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov >= 0.50:
                is_tp = True
                break

        if h.rank <= 5:
            if is_tp:
                tp_in_top5.append(h)
            else:
                fp_in_top5.append(h)
        elif h.rank <= 10:
            if is_tp:
                tp_rank6_10.append(h)

print(f"=== Top-5 TPs: {len(tp_in_top5)}, Top-5 FPs: {len(fp_in_top5)}, Rank 6-10 TPs: {len(tp_rank6_10)} ===\n")

def stats(group, label):
    if not group:
        print(f"{label}: empty")
        return
    import numpy as np
    fields = ['ranking_score', 'combined_score', 'consensus_score', 'length',
              'hydrophilicity', 'accessibility', 'flexibility', 'beta_turn',
              'antigenicity', 'bepipred', 'welling', 'disorder', 'coil',
              'aapair', 'janin']
    print(f"\n{label} (n={len(group)}):")
    for f in fields:
        vals = [getattr(h, f) for h in group]
        print(f"  {f:20s}  mean={np.mean(vals):.4f}  med={np.median(vals):.4f}  std={np.std(vals):.4f}")

stats(tp_in_top5, "Top-5 TPs")
stats(fp_in_top5, "Top-5 FPs")
stats(tp_rank6_10, "Rank 6-10 TPs")

# Feature differences: rank6-10 TP vs top-5 FP
print("\n=== Feature delta: (Rank6-10 TP) - (Top-5 FP) ===")
print("  Positive = TP higher (good signal to boost)")
import numpy as np
fields = ['ranking_score', 'combined_score', 'consensus_score', 'length',
          'hydrophilicity', 'accessibility', 'flexibility', 'beta_turn',
          'antigenicity', 'bepipred', 'welling', 'disorder', 'coil',
          'aapair', 'janin']
for f in fields:
    tp_mean = np.mean([getattr(h, f) for h in tp_rank6_10]) if tp_rank6_10 else 0
    fp_mean = np.mean([getattr(h, f) for h in fp_in_top5]) if fp_in_top5 else 0
    delta = tp_mean - fp_mean
    pct = (delta / fp_mean * 100) if fp_mean else 0
    marker = ">>>" if delta > 0 else "   "
    print(f"  {marker} {f:20s}  TP6-10={tp_mean:.4f}  FP1-5={fp_mean:.4f}  delta={delta:+.4f} ({pct:+.1f}%)")

# Check distribution of ranking_scores
print(f"\n=== Ranking score distributions ===")
tp5_rs = sorted([h.ranking_score for h in tp_in_top5])
fp5_rs = sorted([h.ranking_score for h in fp_in_top5])
tp610_rs = sorted([h.ranking_score for h in tp_rank6_10])
print(f"  Top-5 TP ranking_scores: min={min(tp5_rs):.4f} med={np.median(tp5_rs):.4f} max={max(tp5_rs):.4f}")
print(f"  Top-5 FP ranking_scores: min={min(fp5_rs):.4f} med={np.median(fp5_rs):.4f} max={max(fp5_rs):.4f}")
print(f"  Rank6-10 TP ranking_scores: min={min(tp610_rs):.4f} med={np.median(tp610_rs):.4f} max={max(tp610_rs):.4f}")

# For each rank6-10 TP, find the FP it needs to beat
print(f"\n=== Per-protein: which FPs block rank6-10 TPs ===")
for prot in PROTEINS[:N]:
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # Find TPs at rank 6-10
    tp_hits = []
    fp_top5 = []
    for h in hits:
        is_tp = False
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0: continue
            if overlap_fraction(h.start, h.end, ks, ke) >= 0.50:
                is_tp = True; break
        if 6 <= h.rank <= 10 and is_tp:
            tp_hits.append(h)
        if h.rank <= 5 and not is_tp:
            fp_top5.append(h)

    if tp_hits and fp_top5:
        for tp in tp_hits:
            # Find the weakest FP in top-5 (the one to displace)
            weakest_fp = min(fp_top5, key=lambda x: x.ranking_score)
            gap = tp.ranking_score - weakest_fp.ranking_score
            print(f"  TP r{tp.rank} ({tp.start}-{tp.end}, len={tp.length}) rs={tp.ranking_score:.4f} "
                  f"vs weakest FP r{weakest_fp.rank} ({weakest_fp.start}-{weakest_fp.end}, len={weakest_fp.length}) rs={weakest_fp.ranking_score:.4f} "
                  f"gap={gap:+.4f} "
                  f"tp_well={tp.welling:.3f} fp_well={weakest_fp.welling:.3f} "
                  f"tp_cons={tp.consensus_score:.3f} fp_cons={weakest_fp.consensus_score:.3f}")
