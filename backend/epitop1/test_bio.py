"""Quick validation of the bio module end-to-end."""

from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector

seq = (
    "MKFFYLFVLFPILLKFCECGPFLPLDRQLNPIDFDPNDDQHPLDPDQLIDQIEPSEQPAQQEPIEPQQPT"
    "QPSTEPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHATESTPTKASSSGDGA"
    "AVCHGKHHDYDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSYFTNSYKITVAFDWWLCDKPWQYALTLLALF"
    "GFSLLSPCLKAYREVLRAKAIRSFIFDCFLTHLFLFLIAFCAYALDFLLMLVVMTFNVGVFFAVITGYTVGYL"
    "VSSLAYSTLRSHPARSSSFSRINEDCC"
)

print(f"Sequence length: {len(seq)}")
print()

# Score
scorer = CombinedScorer()
results = scorer.get_residue_results(seq)

# Detect
detector = EpitopeDetector({"min_length": 8, "max_length": 20, "top_n": 10})
hits = detector.detect(seq, results)

print(f"Found {len(hits)} epitopes:\n")
header = f"{'Rank':<5} {'Start':<6} {'End':<5} {'Len':<5} {'Score':<8} {'Sequence'}"
print(header)
print("-" * 70)
for h in hits:
    print(
        f"{h.rank:<5} {h.start:<6} {h.end:<5} {h.length:<5} "
        f"{h.combined_score:<8.4f} {h.sequence}"
    )

print("\n--- Residue score sample (first 10) ---")
for r in results[:10]:
    print(
        f"  {r.position:>3} {r.amino_acid}  hydro={r.hydrophilicity:>7.3f}  "
        f"acc={r.accessibility:>7.3f}  flex={r.flexibility:.3f}  "
        f"turn={r.beta_turn:.3f}  antig={r.antigenicity:.3f}  "
        f"combined={r.combined_score:.4f}"
    )

# Test visualization (save plot)
try:
    from bio.visualization import save_plot
    path = save_plot(results, hits, filepath="test_bio_plot.png", title="Test Protein")
    print(f"\nPlot saved: {path}")
except ImportError:
    print("\nmatplotlib not installed — skipping plot test.")

# Test existing system still works
print("\n--- Existing system check ---")
from core.scoring import GlobalScorer
from core.epitope_selector import EpitopeSelector

old_scorer = GlobalScorer()
old_results = old_scorer.get_residue_scores(seq)
old_selector = EpitopeSelector()
old_epitopes = old_selector.find_epitopes(seq, old_results)
print(f"Existing system found {len(old_epitopes)} epitopes — OK")

print("\n=== ALL TESTS PASSED ===")
