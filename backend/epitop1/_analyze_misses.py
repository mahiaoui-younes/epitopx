"""Analyze which epitopes the Bio module is missing and why."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_benchmark_100 import PROTEINS, find_epitope_in_sequence, overlap_fraction
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector
import numpy as np

missed = []
detected = []
total = 0

for idx, prot in enumerate(PROTEINS, 1):
    seq = prot.sequence.upper().replace(" ", "").replace("\n", "")
    bio_scorer = CombinedScorer()
    bio_res = bio_scorer.get_residue_results(seq)
    bio_det_obj = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 30, "min_consensus": 0.20, "min_score": 0.30})
    bio_hits = bio_det_obj.detect(seq, bio_res)
    
    scores = np.array([r.combined_score for r in bio_res])
    
    for epi_seq in prot.known_epitopes:
        total += 1
        ks, ke = find_epitope_in_sequence(seq, epi_seq)
        if ks == 0:
            continue
        
        # Get scores in epitope region
        epi_scores = scores[ks-1:ke]
        epi_mean = float(np.mean(epi_scores))
        epi_max = float(np.max(epi_scores))
        
        bb_ov = 0.0
        best_hit = None
        for h in bio_hits:
            ov = overlap_fraction(h.start, h.end, ks, ke)
            if ov > bb_ov:
                bb_ov = ov
                best_hit = h
        
        info = {
            'prot': idx, 'name': prot.name,
            'epi': epi_seq[:20], 'pos': f"{ks}-{ke}", 'len': ke-ks+1,
            'mean_score': epi_mean, 'max_score': epi_max,
            'best_overlap': bb_ov,
            'best_hit_score': best_hit.combined_score if best_hit else 0,
            'best_hit_pos': f"{best_hit.start}-{best_hit.end}" if best_hit else "none",
        }
        
        if bb_ov >= 0.50:
            detected.append(info)
        else:
            missed.append(info)

print(f"Total: {total}, Detected: {len(detected)}, Missed: {len(missed)}")
print()

# Categorize misses
low_score = [m for m in missed if m['mean_score'] < 0.40]
mid_score = [m for m in missed if 0.40 <= m['mean_score'] < 0.55]
high_score = [m for m in missed if m['mean_score'] >= 0.55]

print(f"MISSED by score category:")
print(f"  Low score (<0.40): {len(low_score)}")
print(f"  Mid score (0.40-0.55): {len(mid_score)}")
print(f"  High score (>=0.55): {len(high_score)}")
print()

# Show misses with high scores (these should be detectable)
print("HIGH-SCORE MISSES (scoring well but not detected):")
for m in sorted(high_score, key=lambda x: -x['mean_score'])[:20]:
    print(f"  Prot {m['prot']:3d} | {m['name'][:18]:18s} | pos {m['pos']:10s} | len {m['len']:2d} | mean {m['mean_score']:.3f} | max {m['max_score']:.3f} | best_ov {m['best_overlap']:.2f} | hit_pos {m['best_hit_pos']}")
print()

print("MID-SCORE MISSES:")
for m in sorted(mid_score, key=lambda x: -x['mean_score'])[:15]:
    print(f"  Prot {m['prot']:3d} | {m['name'][:18]:18s} | pos {m['pos']:10s} | len {m['len']:2d} | mean {m['mean_score']:.3f} | max {m['max_score']:.3f} | best_ov {m['best_overlap']:.2f}")
print()

# Statistics on detected
det_scores = [d['mean_score'] for d in detected]
miss_scores = [m['mean_score'] for m in missed]
print(f"Detected mean score: {np.mean(det_scores):.3f}")
print(f"Missed mean score:   {np.mean(miss_scores):.3f}")

# Length distribution of misses
miss_lens = [m['len'] for m in missed]
print(f"\nMissed epitope lengths: min={min(miss_lens)}, max={max(miss_lens)}, mean={np.mean(miss_lens):.1f}")
short = [m for m in missed if m['len'] < 8]
long = [m for m in missed if m['len'] > 25]
print(f"  Too short (<8): {len(short)}")
print(f"  Too long (>25): {len(long)}")

# Near-misses (overlap 0.30-0.49)
near_misses = [m for m in missed if m['best_overlap'] >= 0.30]
print(f"\nNear-misses (overlap 0.30-0.49): {len(near_misses)}")
for m in near_misses[:10]:
    print(f"  Prot {m['prot']:3d} | pos {m['pos']:10s} | ov {m['best_overlap']:.2f} | hit_pos {m['best_hit_pos']}")
