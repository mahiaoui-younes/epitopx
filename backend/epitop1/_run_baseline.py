"""Quick baseline benchmark runner."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_benchmark_100 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from core.scoring import GlobalScorer
from core.epitope_selector import EpitopeSelector
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

total_known = 0
core_det = bio_det = 0

for idx, prot in enumerate(PROTEINS, 1):
    seq = prot.sequence.upper().replace(" ", "").replace("\n", "")
    
    core_scorer = GlobalScorer()
    core_res = core_scorer.get_residue_scores(seq)
    core_sel = EpitopeSelector()
    core_epi = core_sel.find_epitopes(seq, core_res)

    bio_scorer = CombinedScorer()
    bio_res = bio_scorer.get_residue_results(seq)
    bio_det_obj = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 40, "min_consensus": 0.20, "min_score": 0.30})
    bio_hits = bio_det_obj.detect(seq, bio_res)

    for epi_seq in prot.known_epitopes:
        total_known += 1
        ks, ke = find_epitope_in_sequence(seq, epi_seq)
        if ks == 0:
            continue
        bc_ov = 0.0
        for ep in core_epi:
            ov = overlap_fraction(ep.start, ep.end, ks, ke)
            if ov > bc_ov:
                bc_ov = ov
        if bc_ov >= 0.50:
            core_det += 1
        bb_ov = 0.0
        for h in bio_hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > bb_ov:
                bb_ov = ov
        if bb_ov >= 0.50:
            bio_det += 1

    if idx % 25 == 0:
        print(f"  Processed {idx}/100...", flush=True)

print()
print(f"=== BASELINE (100 proteins, {total_known} epitopes) ===")
print(f"Core: {core_det}/{total_known} ({core_det/total_known*100:.1f}%)")
print(f"Bio:  {bio_det}/{total_known} ({bio_det/total_known*100:.1f}%)")
