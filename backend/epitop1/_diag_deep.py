#!/usr/bin/env python3
"""Deep diagnostic: compare features of R1-5 TPs, R1-5 FPs, R6-10 TPs, R6-10 FPs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
# Collect per-candidate feature vectors
tp5 = []   # TPs in rank 1-5
fp5 = []   # FPs in rank 1-5
tp610 = [] # TPs in rank 6-10
fp610 = [] # FPs in rank 6-10

for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    # Label each hit as TP or FP
    for h in hits:
        if h.rank > 10:
            continue
        is_tp = False
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0:
                continue
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov >= 0.50:
                is_tp = True
                break

        features = {
            'protein': idx,
            'rank': h.rank,
            'length': h.length,
            'combined_score': h.combined_score,
            'peak_combined_score': h.peak_combined_score,
            'score_variance': h.score_variance,
            'ranking_score': h.ranking_score,
            'consensus_score': h.consensus_score,
            'antigenicity': h.antigenicity,
            'bepipred': h.bepipred,
            'accessibility': h.accessibility,
            'flexibility': h.flexibility,
            'beta_turn': h.beta_turn,
            'hydrophilicity': h.hydrophilicity,
            'welling': h.welling,
            'coil': h.coil,
            'disorder': h.disorder,
            'aapair': h.aapair,
            'janin': h.janin,
            'sequence': h.sequence,
            # Derived features
            'charged_frac': sum(1 for aa in h.sequence if aa in 'KRDE') / h.length,
            'polar_frac': sum(1 for aa in h.sequence if aa in 'STNQKRDEH') / h.length,
            'peak_to_mean': h.peak_combined_score / max(h.combined_score, 0.001),
        }

        if h.rank <= 5:
            if is_tp:
                tp5.append(features)
            else:
                fp5.append(features)
        else:  # rank 6-10
            if is_tp:
                tp610.append(features)
            else:
                fp610.append(features)

def avg(lst, key):
    vals = [d[key] for d in lst]
    return sum(vals) / len(vals) if vals else 0.0

def med(lst, key):
    vals = sorted([d[key] for d in lst])
    if not vals: return 0.0
    n = len(vals)
    if n % 2 == 0:
        return (vals[n//2-1] + vals[n//2]) / 2
    return vals[n//2]

print(f"\n{'='*80}")
print(f"  COUNTS:  TP@1-5={len(tp5)}  FP@1-5={len(fp5)}  TP@6-10={len(tp610)}  FP@6-10={len(fp610)}")
print(f"{'='*80}")

features_to_compare = [
    'length', 'combined_score', 'peak_combined_score', 'score_variance',
    'ranking_score', 'consensus_score', 'antigenicity', 'bepipred',
    'accessibility', 'flexibility', 'beta_turn', 'hydrophilicity',
    'welling', 'coil', 'disorder', 'aapair', 'janin',
    'charged_frac', 'polar_frac', 'peak_to_mean',
]

print(f"\n{'Feature':<24s} {'TP@1-5':>10s} {'FP@1-5':>10s} {'TP@6-10':>10s} {'FP@6-10':>10s}   {'TP5-FP5':>10s}")
print("-" * 80)
for feat in features_to_compare:
    a = avg(tp5, feat)
    b = avg(fp5, feat)
    c = avg(tp610, feat)
    d = avg(fp610, feat)
    diff = a - b
    print(f"  {feat:<22s} {a:>10.4f} {b:>10.4f} {c:>10.4f} {d:>10.4f}   {diff:>+10.4f}")

# Show what the best feature for separating FP@1-5 from TP@6-10 is
print(f"\n{'='*80}")
print("  KEY COMPARISON: FP@1-5 vs TP@6-10 (what distinguishes salvageable TPs from blocking FPs)")
print(f"{'='*80}")
print(f"\n{'Feature':<24s} {'FP@1-5 avg':>12s} {'TP@6-10 avg':>12s} {'Ratio':>8s}   {'Direction':>10s}")
print("-" * 80)
for feat in features_to_compare:
    fp5_avg = avg(fp5, feat)
    tp610_avg = avg(tp610, feat)
    if fp5_avg > 0.001:
        ratio = tp610_avg / fp5_avg
    else:
        ratio = 0.0
    direction = "TP610 HIGH" if tp610_avg > fp5_avg else "FP5 HIGH"
    print(f"  {feat:<22s} {fp5_avg:>12.4f} {tp610_avg:>12.4f} {ratio:>8.2f}   {direction:>10s}")

# Per-protein detail for salvageable cases
print(f"\n{'='*80}")
print("  SALVAGEABLE proteins (have TP@6-10):")
print(f"{'='*80}")
salvageable_prots = sorted(set(d['protein'] for d in tp610))
for pidx in salvageable_prots:
    tp_hits = [d for d in tp610 if d['protein'] == pidx]
    fp5_hits = [d for d in fp5 if d['protein'] == pidx]
    tp5_hits = [d for d in tp5 if d['protein'] == pidx]
    print(f"\n  P{pidx}: {len(tp5_hits)} TP@top5, {len(fp5_hits)} FP@top5, {len(tp_hits)} TP@6-10")
    for h in tp_hits:
        print(f"    TP r{h['rank']:>2d}: len={h['length']:>2d} comb={h['combined_score']:.3f} peak={h['peak_combined_score']:.3f}"
              f" var={h['score_variance']:.4f} rscore={h['ranking_score']:.3f} cons={h['consensus_score']:.2f}"
              f" chg={h['charged_frac']:.2f} seq={h['sequence'][:20]}")
    for h in sorted(fp5_hits, key=lambda x: x['rank']):
        print(f"    FP r{h['rank']:>2d}: len={h['length']:>2d} comb={h['combined_score']:.3f} peak={h['peak_combined_score']:.3f}"
              f" var={h['score_variance']:.4f} rscore={h['ranking_score']:.3f} cons={h['consensus_score']:.2f}"
              f" chg={h['charged_frac']:.2f} seq={h['sequence'][:20]}")
