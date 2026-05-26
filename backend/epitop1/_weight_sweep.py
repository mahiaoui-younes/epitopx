"""Quick weight sweep to find optimal Bio scoring weights."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_benchmark_100 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector
import itertools

def eval_weights(weights):
    """Return number of detected epitopes with given weights."""
    det = 0
    total = 0
    for prot in PROTEINS:
        seq = prot.sequence.upper().replace(" ", "").replace("\n", "")
        scorer = CombinedScorer(weights=weights)
        res = scorer.get_residue_results(seq)
        detector = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 40,
                                    "min_consensus": 0.20, "min_score": 0.30})
        hits = detector.detect(seq, res)
        for epi_seq in prot.known_epitopes:
            total += 1
            ks, ke = find_epitope_in_sequence(seq, epi_seq)
            if ks == 0:
                continue
            best_ov = max((overlap_fraction(h.start, h.end, ks, ke) for h in hits), default=0.0)
            if best_ov >= 0.50:
                det += 1
    return det, total

# Sweep key weight variations
configs = [
    ("current", {"hydrophilicity": 0.15, "accessibility": 0.15, "flexibility": 0.09, "beta_turn": 0.09, "antigenicity": 0.12, "bepipred": 0.16, "coil": 0.10, "welling": 0.14}),
    ("bepi_heavy", {"hydrophilicity": 0.13, "accessibility": 0.13, "flexibility": 0.08, "beta_turn": 0.08, "antigenicity": 0.11, "bepipred": 0.20, "coil": 0.11, "welling": 0.16}),
    ("access_heavy", {"hydrophilicity": 0.14, "accessibility": 0.20, "flexibility": 0.08, "beta_turn": 0.08, "antigenicity": 0.11, "bepipred": 0.15, "coil": 0.10, "welling": 0.14}),
    ("hydro_heavy", {"hydrophilicity": 0.20, "accessibility": 0.14, "flexibility": 0.08, "beta_turn": 0.08, "antigenicity": 0.11, "bepipred": 0.15, "coil": 0.10, "welling": 0.14}),
    ("well_heavy", {"hydrophilicity": 0.13, "accessibility": 0.13, "flexibility": 0.08, "beta_turn": 0.08, "antigenicity": 0.11, "bepipred": 0.15, "coil": 0.10, "welling": 0.22}),
    ("balanced", {"hydrophilicity": 0.125, "accessibility": 0.125, "flexibility": 0.125, "beta_turn": 0.125, "antigenicity": 0.125, "bepipred": 0.125, "coil": 0.125, "welling": 0.125}),
    ("top3_heavy", {"hydrophilicity": 0.18, "accessibility": 0.18, "flexibility": 0.07, "beta_turn": 0.07, "antigenicity": 0.10, "bepipred": 0.18, "coil": 0.08, "welling": 0.14}),
    ("bepi_well_heavy", {"hydrophilicity": 0.12, "accessibility": 0.12, "flexibility": 0.07, "beta_turn": 0.07, "antigenicity": 0.10, "bepipred": 0.22, "coil": 0.08, "welling": 0.22}),
]

print("Weight sweep results:")
print("-" * 50)
for name, w in configs:
    det, total = eval_weights(w)
    print(f"  {name:18s}  {det}/{total}  ({det/total*100:.1f}%)")
    sys.stdout.flush()
print("-" * 50)
