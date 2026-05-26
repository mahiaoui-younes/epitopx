#!/usr/bin/env python3
"""Compare features of true positive vs false positive top-5 candidates."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 50
true_positives = []
false_positives = []

for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)
    
    top5 = [h for h in hits if h.rank <= 5]
    
    for h in top5:
        is_true = False
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0:
                continue
            if overlap_fraction(h.start, h.end, ks, ke) >= 0.50:
                is_true = True
                break
        
        entry = {
            'prot': idx,
            'length': h.length,
            'combined': h.combined_score,
            'ranking': h.ranking_score,
            'consensus': h.consensus_score,
            'antigenicity': h.antigenicity,
            'bepipred': h.bepipred,
            'accessibility': h.accessibility,
            'flexibility': h.flexibility,
            'beta_turn': h.beta_turn,
            'hydrophilicity': h.hydrophilicity,
            'coil': h.coil,
            'welling': h.welling,
            'disorder': h.disorder,
            'aapair': h.aapair,
            'janin': h.janin,
        }
        if is_true:
            true_positives.append(entry)
        else:
            false_positives.append(entry)

import numpy as np

print(f"True positives in top-5: {len(true_positives)}")
print(f"False positives in top-5: {len(false_positives)}")
print()

props = ['length', 'combined', 'ranking', 'consensus', 'antigenicity', 
         'bepipred', 'accessibility', 'flexibility', 'beta_turn',
         'hydrophilicity', 'coil', 'welling', 'disorder', 'aapair', 'janin']

print(f"{'Property':18s} {'TP mean':>8s} {'FP mean':>8s} {'TP med':>8s} {'FP med':>8s} {'Diff%':>8s}")
print("-" * 60)
for prop in props:
    tp_vals = [e[prop] for e in true_positives]
    fp_vals = [e[prop] for e in false_positives]
    tp_mean = np.mean(tp_vals) if tp_vals else 0
    fp_mean = np.mean(fp_vals) if fp_vals else 0
    tp_med = np.median(tp_vals) if tp_vals else 0
    fp_med = np.median(fp_vals) if fp_vals else 0
    diff_pct = ((tp_mean - fp_mean) / fp_mean * 100) if fp_mean > 0.001 else 0
    print(f"{prop:18s} {tp_mean:>8.3f} {fp_mean:>8.3f} {tp_med:>8.3f} {fp_med:>8.3f} {diff_pct:>+7.1f}%")

# Derived features
print("\n--- Derived features ---")
for entry_list, label in [(true_positives, "TP"), (false_positives, "FP")]:
    bepi_antig = [e['bepipred'] * e['antigenicity'] for e in entry_list]
    consensus_x_bepi = [e['consensus'] * e['bepipred'] for e in entry_list]
    flex_acc = [e['flexibility'] * e['accessibility'] for e in entry_list]
    print(f"  {label}: bepi*antig={np.mean(bepi_antig):.4f}  cons*bepi={np.mean(consensus_x_bepi):.4f}  flex*acc={np.mean(flex_acc):.4f}")
