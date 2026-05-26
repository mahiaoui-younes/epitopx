#!/usr/bin/env python3
"""Debug: show main_valid positions for selected proteins."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_benchmark_500 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

DEBUG_PROTS = [3, 10, 27, 30, 32, 33]

for idx in DEBUG_PROTS:
    prot = PROTEINS[idx - 1]
    seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
    scorer = CombinedScorer()
    results = scorer.get_residue_results(seq)
    detector = EpitopeDetector({"min_length": 7, "max_length": 28, "top_n": 150})
    hits = detector.detect(seq, results)

    print(f"\n=== Protein {idx} (len={len(seq)}) ===")
    print(f"Known epitopes: {prot.known_epitopes}")
    
    # Show top-15 hits
    for i, h in enumerate(hits[:15]):
        # Check if this is a TP
        is_tp = False
        for epi in prot.known_epitopes:
            ks, ke = find_epitope_in_sequence(seq, epi)
            if ks == 0:
                continue
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov >= 0.50:
                is_tp = True
                break
        tag = "TP" if is_tp else "FP"
        print(f"  rank {h.rank:>3}: {tag} scr={h.ranking_score:.3f} len={h.length:>2} "
              f"comb={h.combined_score:.3f} peak={h.peak_combined_score:.3f} "
              f"cons={h.consensus_score:.2f} seq={h.sequence[:25]}")
