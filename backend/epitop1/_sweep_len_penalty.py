#!/usr/bin/env python3
"""Sweep length penalty parameters to find optimal combination."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector, EpitopeHit

N = 50

# Save original
_ORIG_RS = EpitopeHit.ranking_score

# Pre-compute residue results
precomputed = []
for prot in PROTEINS[:N]:
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    precomputed.append((prot, seq, results))
print("Precomputed done")

def make_ranking_score(slope, floor):
    @property
    def patched(self):
        consensus_amp = 1.0 + 1.0 * (self.consensus_score ** 1.3)
        predictor_bonus = 0.10 * self.antigenicity + 0.08 * self.bepipred
        optimal_len = 14.0
        if self.length <= 20:
            len_diff = abs(self.length - optimal_len)
            len_bonus = 1.0 + 0.10 * max(0.0, 1.0 - len_diff / 8.0)
        else:
            excess = self.length - 20
            len_bonus = max(floor, 1.0 - slope * excess)
        return (self.combined_score + predictor_bonus) * consensus_amp * len_bonus
    return patched

def test_params(slope, floor):
    EpitopeHit.ranking_score = make_ranking_score(slope, floor)
    total = detected = t5 = t10 = 0
    for prot, seq, results in precomputed:
        detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
        hits = detector.detect(seq, results)
        for epi in prot.known_epitopes:
            total += 1
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0: continue
            bo = 0.0; br = 999
            for h in hits:
                ov = overlap_fraction(h.start, h.end, ks, ke)
                if ov > bo: bo = ov; br = h.rank
            if bo >= 0.50:
                detected += 1
                if br <= 5: t5 += 1
                if br <= 10: t10 += 1
    return total, detected, t5, t10

print("slope  floor   Sens   Top5   Top10")
print("-" * 50)
best_t5 = 0
best_params = None

for slope in [0.06, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]:
    for floor in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]:
        total, detected, t5, t10 = test_params(slope, floor)
        sens = detected / total * 100
        t5p = t5 / total * 100
        t10p = t10 / total * 100
        marker = " ***" if t5 > best_t5 else ""
        print(f"{slope:.2f}   {floor:.2f}   {sens:.1f}%  {t5p:.1f}%  {t10p:.1f}%{marker}", flush=True)
        if t5 > best_t5:
            best_t5 = t5
            best_params = (slope, floor)

# Restore
EpitopeHit.ranking_score = _ORIG_RS
print(f"\nBest: slope={best_params[0]}, floor={best_params[1]}, t5={best_t5}/{total}={best_t5/total*100:.1f}%")
