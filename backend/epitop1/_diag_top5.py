#!/usr/bin/env python3
"""Diagnostic: show top-10 predictions vs known epitopes for first 10 proteins."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

N = 15
for idx, prot in enumerate(PROTEINS[:N], 1):
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    print(f"\n{'='*80}")
    print(f"[{idx}] {prot.name} ({len(seq)} aa)")
    
    # Known epitopes
    known = []
    for epi in prot.known_epitopes:
        ks, ke = find_epitope_in_sequence(seq, epi)
        known.append((ks, ke, epi))
    
    print(f"  Known epitopes:")
    for ks, ke, epi in known:
        print(f"    pos {ks:>3}-{ke:>3}  {epi[:30]}")
    
    print(f"\n  Top-10 predictions:")
    for h in hits[:10]:
        # Check overlap with known
        best_ov = 0.0
        matched = ""
        for ks, ke, epi in known:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                matched = epi[:20]
        ov_tag = f"  <- {matched} ({best_ov:.0%})" if best_ov >= 0.30 else ""
        print(f"    r{h.rank:>3} pos {h.start:>3}-{h.end:>3} len={h.length:>2}"
              f"  cs={h.combined_score:.3f}"
              f"  rs={h.ranking_score:.3f}"
              f"  cons={h.consensus_score:.2f}"
              f"  {h.sequence[:25]}{ov_tag}")
    
    # Check which known epitopes are NOT in top 5
    print(f"\n  Epitope rank analysis:")
    for ks, ke, epi in known:
        best_ov = 0.0
        best_rk = 999
        for h in hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > best_ov:
                best_ov = ov
                best_rk = h.rank
        status = "OK" if best_ov >= 0.50 and best_rk <= 5 else "MISS-T5" if best_ov >= 0.50 else "MISS"
        print(f"    {status:8s} rank {best_rk:>4} ov={best_ov:.0%}  {epi[:30]}")
