"""
Validation test: Check if the known epitope SEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHA
from Theileria annulata surface protein (CAC87893.1) is detected.
"""

from core.scoring import GlobalScorer
from core.epitope_selector import EpitopeSelector

# Theileria annulata TaSP protein (CAC87893.1)
sequence = (
    "MANKVISFLLAFIFSQSAADNCSEENQDSQESLVTSVENNHSEEMQEESRVVSETEHNKTP"
    "TSVHQEEDHNEESIHQPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPV"
    "DEPAVHAQEDEGEDDEVTPEFEDDMKPADLLKKTNDQTESQPVSEENHTKEEKPEKGPKDE"
    "NKASHTATKVEEEENVEETEKPVQGDDDENKDEETKEEIDQADTSIHGETKPEDQGDNEKPV"
    "KAEEETPEEFQGSVIAILLAFTIGFLITKKRKVFVK"
)

KNOWN_EPITOPE = "SEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHA"
known_start = sequence.find(KNOWN_EPITOPE) + 1  # 1-indexed
known_end = known_start + len(KNOWN_EPITOPE) - 1
print(f"Known epitope: {KNOWN_EPITOPE}")
print(f"Known position: {known_start}-{known_end} ({len(KNOWN_EPITOPE)} aa)")
print()

# Run scoring
scorer = GlobalScorer()
residue_scores = scorer.get_residue_scores(sequence)

# Run epitope selection
selector = EpitopeSelector()
epitopes = selector.find_epitopes(sequence, residue_scores)

print(f"Found {len(epitopes)} valid epitopes:")
print("-" * 80)

found_overlap = False
for ep in epitopes:
    # Check overlap with known epitope
    ep_set = set(range(ep.start, ep.end + 1))
    known_set = set(range(known_start, known_end + 1))
    overlap = len(ep_set & known_set)
    overlap_pct = overlap / len(known_set) * 100 if known_set else 0

    marker = ""
    if overlap_pct >= 50:
        marker = " *** MATCH ***"
        found_overlap = True
    elif overlap > 0:
        marker = f" (partial: {overlap_pct:.0f}%)"

    print(f"  #{ep.rank}: pos {ep.start}-{ep.end} ({ep.length} aa) "
          f"score={ep.global_score:.3f} seq={ep.sequence[:40]}...{marker}")

print()
if found_overlap:
    print("SUCCESS: Known epitope region DETECTED!")
else:
    print("FAILURE: Known epitope region NOT detected.")
    print("\nDiagnostic: Score profile over known epitope region:")
    import numpy as np
    for i in range(known_start - 1, known_end):
        rs = residue_scores[i]
        print(f"  pos {i+1} ({sequence[i]}): global={rs.global_score:.3f} "
              f"hydro={rs.hydrophilicity:.3f} acc={rs.accessibility:.3f} "
              f"flex={rs.flexibility:.3f} antig={rs.antigenicity:.3f}")
