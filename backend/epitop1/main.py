#!/usr/bin/env python3
"""
EpiTop1 v2.0 --- B Linear Epitope Predictor

A standalone bioinformatics tool for predicting B-cell linear epitopes
from protein sequences and optional PDB structures.

Usage:
    python main.py                        # Launch GUI
    python main.py --cli SEQ              # Core module (5 methods)
    python main.py --cli SEQ --bio        # Bio module  (7 methods)

Core methods:
    - Hopp & Woods (1981) --- Hydrophilicity
    - Kyte & Doolittle (1982) --- Hydrophobicity
    - Karplus & Schulz (1985) --- Flexibility
    - Emini et al. (1985) --- Surface Accessibility
    - Kolaskar & Tongaonkar (1990) --- Antigenicity

Bio module (additional):
    - Parker (1986) --- Hydrophilicity
    - Chou & Fasman (1978) --- Beta-turn propensity
    - BepiPred-1.0 (Larsen 2006) --- Epitope propensity
    - Levitt (1978) --- Coil/Disorder

Author: EpiTop1 Project
License: Academic / Research Use
"""

__version__ = "2.0.0"

import sys
import os
import argparse

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def run_gui():
    """Launch the graphical user interface."""
    from gui.app import EpiTopApp
    app = EpiTopApp()
    app.run()


def _banner():
    """Print the application banner."""
    print()
    print("=" * 70)
    print(f"  EpiTop1 v{__version__} -- B-cell Linear Epitope Predictor")
    print("=" * 70)
    print()


def run_cli(args):
    """Run analysis in command-line mode."""
    from core.scoring import GlobalScorer
    from core.epitope_selector import EpitopeSelector
    from core.hydrophobicity import KyteDoolittlePredictor
    from structure.pdb_parser import PDBParser
    from io_utils import parse_sequence_input
    from io_utils import export_csv, export_json, export_residue_table
    from config import EPITOPE_CRITERIA

    import numpy as np

    _banner()

    # Parse sequence
    if os.path.isfile(args.sequence):
        with open(args.sequence, 'r') as f:
            seq_input = f.read()
    else:
        seq_input = args.sequence

    try:
        header, sequence = parse_sequence_input(seq_input)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Sequence:  {header}")
    print(f"  Length:    {len(sequence)} residues")
    print()

    # ------------------------------------------------------------------
    # Advanced bio-module path (--bio flag)
    # ------------------------------------------------------------------
    if getattr(args, "bio", False):
        _run_bio_cli(args, header, sequence)
        return

    # PDB structure
    structural_sasa = None
    excluded_regions = []

    if args.pdb and os.path.exists(args.pdb):
        print(f"Parsing PDB: {args.pdb}")
        pdb_parser = PDBParser(probe_radius=1.4, n_sasa_points=92)
        pdb_parser.parse(args.pdb, chain_id=args.chain)

        print("Computing SASA...")
        pdb_parser.compute_sasa()

        pdb_seq = pdb_parser.get_sequence()
        if pdb_seq:
            alignment = pdb_parser.align_to_sequence(sequence)
            structural_sasa = np.zeros(len(sequence))
            for seq_pos, pdb_idx in alignment.items():
                if pdb_idx < len(pdb_parser.residues):
                    structural_sasa[seq_pos] = (
                        pdb_parser.residues[pdb_idx].relative_sasa
                    )
        print()

    # Compute scores
    print("Computing bioinformatics scores...")
    scorer = GlobalScorer()
    residue_scores = scorer.get_residue_scores(sequence, structural_sasa)

    # Detect TM regions
    kd = KyteDoolittlePredictor(window_size=11)
    tm_regions = kd.detect_transmembrane_regions(sequence)
    for tm in tm_regions:
        excluded_regions.append((tm["start"], tm["end"]))
        print(f"  Excluded TM region: {tm['start']}-{tm['end']}")

    # Select epitopes
    print("Selecting epitope candidates...")
    criteria = dict(EPITOPE_CRITERIA)
    if args.min_length:
        criteria["min_length"] = args.min_length
    if args.max_length:
        criteria["max_length"] = args.max_length
    if args.min_score is not None:
        criteria["min_global_score"] = args.min_score
    if args.top_n:
        criteria["top_n_epitopes"] = args.top_n

    selector = EpitopeSelector(criteria=criteria)
    epitopes = selector.find_epitopes(
        sequence, residue_scores, excluded_regions
    )

    # Display results
    print()
    print("=" * 80)
    print(f"  CORE MODULE -- EPITOPE CANDIDATES ({len(epitopes)} found)")
    print("=" * 80)
    print(
        f"  {'Rank':<5} {'Start':>5} {'End':>5} {'Len':>4} "
        f"{'Score':>7} {'Hydrophil':>10} {'Access':>8}  {'Sequence'}"
    )
    print("  " + "-" * 76)

    for ep in epitopes:
        print(
            f"  {ep.rank:<5} {ep.start:>5} {ep.end:>5} "
            f"{ep.length:>4} {ep.global_score:>7.4f} "
            f"{ep.hydrophilicity:>10.3f} {ep.accessibility:>8.3f} "
            f"  {ep.sequence}"
        )

    if epitopes:
        scores = [ep.global_score for ep in epitopes]
        print()
        print(
            f"  Score range: {min(scores):.4f} -- {max(scores):.4f}  "
            f"(Mean: {np.mean(scores):.4f})"
        )

    # Export
    if args.output:
        out_dir = args.output
        os.makedirs(out_dir, exist_ok=True)

        ep_path = os.path.join(out_dir, "epitop1_epitopes.csv")
        export_csv(epitopes, ep_path, header)
        print(f"\nEpitopes exported to: {ep_path}")

        res_path = os.path.join(out_dir, "epitop1_residue_scores.csv")
        export_residue_table(residue_scores, res_path, header)
        print(f"Residue scores exported to: {res_path}")

        json_path = os.path.join(out_dir, "epitop1_report.json")
        export_json(
            epitopes, residue_scores, json_path,
            header, sequence, structural_sasa is not None,
        )
        print(f"JSON report exported to: {json_path}")


def _run_bio_cli(args, header: str, sequence: str):
    """Run the advanced bio-module epitope prediction (CLI)."""
    import numpy as np
    from bio.scoring import CombinedScorer
    from bio.epitope_detector import EpitopeDetector
    from config import BIO_SCORING_WEIGHTS, BIO_WINDOW_SIZES, BIO_DETECTION_PARAMS

    # IEDB API integration
    use_iedb = getattr(args, "iedb", False)
    iedb_methods = None
    if use_iedb:
        try:
            from config import IEDB_PARAMS
            iedb_methods = IEDB_PARAMS.get("methods", None)
        except ImportError:
            iedb_methods = None  # will use all 7 IEDB methods by default
        # Import method list for display
        from bio.scoring import ALL_IEDB_METHODS
        display_methods = iedb_methods or ALL_IEDB_METHODS
        print(f"  IEDB API enabled — querying {len(display_methods)} methods: {', '.join(display_methods)}")
        print()

    structural_sasa = None

    # Optional PDB
    if args.pdb and os.path.exists(args.pdb):
        try:
            from bio.pdb_analysis import parse_pdb_sasa, align_structure_to_sequence
            print(f"Parsing PDB: {args.pdb}")
            pdb_seq, pdb_sasa, pdb_residues = parse_pdb_sasa(
                args.pdb, chain_id=args.chain,
            )
            structural_sasa = align_structure_to_sequence(
                pdb_seq, sequence, pdb_residues,
            )
            print(f"  PDB sequence length: {len(pdb_seq)}")
            print()
        except ImportError:
            print("  BioPython not available — falling back to sequence-only.")
            print()
        except Exception as exc:
            print(f"  PDB error: {exc} — using sequence-only prediction.")
            print()

    # Scoring
    if use_iedb:
        print("Computing combined scores (bio module + IEDB API)...")
    else:
        print("Computing combined scores (bio module)...")
    scorer = CombinedScorer(
        weights=dict(BIO_SCORING_WEIGHTS),
        window_sizes=dict(BIO_WINDOW_SIZES),
        use_iedb=use_iedb,
        iedb_methods=iedb_methods,
    )
    residue_results = scorer.get_residue_results(sequence, structural_sasa)

    # Detection
    params = dict(BIO_DETECTION_PARAMS)
    if args.min_length:
        params["min_length"] = args.min_length
    if args.max_length:
        params["max_length"] = args.max_length
    if args.min_score is not None:
        params["min_score"] = args.min_score
    if args.top_n:
        params["top_n"] = args.top_n

    print("Detecting epitope candidates...")
    detector = EpitopeDetector(params)
    hits = detector.detect(sequence, residue_results)

    # Display
    print()
    print("=" * 107)
    print(f"  BIO MODULE -- EPITOPE CANDIDATES ({len(hits)} found)")
    methods_line = "  Methods: Parker, Emini, K-S, Chou-Fasman, K-T, BepiPred-1.0, Levitt, Welling"
    if use_iedb:
        methods_line += ", IEDB BepiPred-2.0"
    print(methods_line)
    print("=" * 107)
    print(
        f"  {'Rank':<5} {'Start':>5} {'End':>5} {'Len':>4} "
        f"{'Score':>7} {'Hydro':>7} {'Access':>7} "
        f"{'Flex':>6} {'Turn':>6} {'Antig':>6} {'Bepi':>6} {'Well':>6} {'Cons':>5}  {'Sequence'}"
    )
    print("  " + "-" * 103)

    for h in hits:
        print(
            f"  {h.rank:<5} {h.start:>5} {h.end:>5} "
            f"{h.length:>4} {h.combined_score:>7.4f} "
            f"{h.hydrophilicity:>7.3f} {h.accessibility:>7.3f} "
            f"{h.flexibility:>6.3f} {h.beta_turn:>6.3f} "
            f"{h.antigenicity:>6.3f} {h.bepipred:>6.3f} "
            f"{h.welling:>6.3f} "
            f"{h.consensus_score:>5.2f}  {h.sequence}"
        )

    if hits:
        bio_scores = [h.combined_score for h in hits]
        cons_scores = [h.consensus_score for h in hits]
        print()
        print(
            f"  Score range: {min(bio_scores):.4f} -- {max(bio_scores):.4f}  "
            f"(Mean: {np.mean(bio_scores):.4f})"
        )
        print(
            f"  Consensus:   {min(cons_scores):.2f} -- {max(cons_scores):.2f}"
        )

    # Export
    if args.output:
        out_dir = args.output
        os.makedirs(out_dir, exist_ok=True)
        _bio_export(hits, residue_results, out_dir, header, sequence,
                    structural_sasa is not None)

    # Visualization
    if getattr(args, "plot", None):
        try:
            from bio.visualization import save_plot
            plot_path = args.plot
            save_plot(residue_results, hits, filepath=plot_path, title=header)
            print(f"\nPlot saved to: {plot_path}")
        except ImportError:
            print("\nmatplotlib not installed — skipping plot.")


def _bio_export(hits, residue_results, out_dir, header, sequence, has_pdb):
    """Export bio-module results to CSV and JSON."""
    import csv
    import json
    from datetime import datetime
    from config import EXPORT_SETTINGS, BIO_SCORING_WEIGHTS, BIO_WINDOW_SIZES

    prec = EXPORT_SETTINGS["float_precision"]

    # ---- Epitope CSV ----
    ep_path = os.path.join(out_dir, "bio_epitopes.csv")
    with open(ep_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"# Bio Module Epitopes — {header}"])
        w.writerow([f"# Generated: {datetime.now():%Y-%m-%d %H:%M:%S}"])
        w.writerow([])
        w.writerow([
            "Rank", "Start", "End", "Length", "Sequence",
            "CombinedScore", "Hydrophilicity", "Accessibility",
            "Flexibility", "BetaTurn", "Antigenicity",
            "BepiPred", "Coil", "Welling",
            "IEDB_BepiPred2", "IEDB_BepiPred1", "IEDB_Emini",
            "IEDB_Kolaskar", "IEDB_Parker", "IEDB_ChouFasman", "IEDB_Karplus",
            "Consensus", "StructuralSASA",
        ])
        for h in hits:
            w.writerow([
                h.rank, h.start, h.end, h.length, h.sequence,
                round(h.combined_score, prec),
                round(h.hydrophilicity, prec),
                round(h.accessibility, prec),
                round(h.flexibility, prec),
                round(h.beta_turn, prec),
                round(h.antigenicity, prec),
                round(h.bepipred, prec),
                round(h.coil, prec),
                round(h.welling, prec),
                round(h.iedb_bepipred2, prec),
                round(h.iedb_bepipred1, prec),
                round(h.iedb_emini, prec),
                round(h.iedb_kolaskar, prec),
                round(h.iedb_parker, prec),
                round(h.iedb_choufasman, prec),
                round(h.iedb_karplus, prec),
                round(h.consensus_score, prec),
                round(h.structural_sasa, prec),
            ])
    print(f"\nEpitopes CSV: {ep_path}")

    # ---- Residue CSV ----
    res_path = os.path.join(out_dir, "bio_residue_scores.csv")
    with open(res_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"# Bio Module Residue Scores — {header}"])
        w.writerow([])
        w.writerow([
            "Position", "AA", "Hydrophilicity", "Accessibility",
            "Flexibility", "BetaTurn", "Antigenicity",
            "BepiPred", "Coil", "Welling",
            "IEDB_BepiPred2", "IEDB_BepiPred1", "IEDB_Emini",
            "IEDB_Kolaskar", "IEDB_Parker", "IEDB_ChouFasman", "IEDB_Karplus",
            "Consensus", "StructuralSASA", "CombinedScore", "IsExposed",
        ])
        for r in residue_results:
            w.writerow([
                r.position, r.amino_acid,
                round(r.hydrophilicity, prec),
                round(r.accessibility, prec),
                round(r.flexibility, prec),
                round(r.beta_turn, prec),
                round(r.antigenicity, prec),
                round(r.bepipred, prec),
                round(r.coil, prec),
                round(r.welling, prec),
                round(r.iedb_bepipred2, prec),
                round(r.iedb_bepipred1, prec),
                round(r.iedb_emini, prec),
                round(r.iedb_kolaskar, prec),
                round(r.iedb_parker, prec),
                round(r.iedb_choufasman, prec),
                round(r.iedb_karplus, prec),
                r.consensus_count,
                round(r.structural_sasa, prec),
                round(r.combined_score, prec),
                "Yes" if r.is_exposed else "No",
            ])
    print(f"Residue CSV:  {res_path}")

    # ---- JSON report ----
    json_path = os.path.join(out_dir, "bio_report.json")
    report = {
        "metadata": {
            "module": "bio",
            "date": datetime.now().isoformat(),
            "sequence_header": header,
            "sequence_length": len(sequence),
            "pdb_used": has_pdb,
            "weights": BIO_SCORING_WEIGHTS,
            "window_sizes": BIO_WINDOW_SIZES,
        },
        "epitope_candidates": [
            {
                "rank": h.rank,
                "start_position": h.start,
                "end_position": h.end,
                "peptide_sequence": h.sequence,
                "combined_score": round(h.combined_score, prec),
                "hydrophilicity": round(h.hydrophilicity, prec),
                "accessibility": round(h.accessibility, prec),
                "flexibility": round(h.flexibility, prec),
                "beta_turn": round(h.beta_turn, prec),
                "antigenicity": round(h.antigenicity, prec),
                "bepipred": round(h.bepipred, prec),
                "coil": round(h.coil, prec),
                "welling": round(h.welling, prec),
                "iedb_bepipred2": round(h.iedb_bepipred2, prec),
                "iedb_bepipred1": round(h.iedb_bepipred1, prec),
                "iedb_emini": round(h.iedb_emini, prec),
                "iedb_kolaskar": round(h.iedb_kolaskar, prec),
                "iedb_parker": round(h.iedb_parker, prec),
                "iedb_choufasman": round(h.iedb_choufasman, prec),
                "iedb_karplus": round(h.iedb_karplus, prec),
                "consensus_score": round(h.consensus_score, prec),
                "structural_sasa": round(h.structural_sasa, prec),
            }
            for h in hits
        ],
        "residue_scores": [
            {
                "position": r.position,
                "amino_acid": r.amino_acid,
                "hydrophilicity": round(r.hydrophilicity, prec),
                "accessibility": round(r.accessibility, prec),
                "flexibility": round(r.flexibility, prec),
                "beta_turn": round(r.beta_turn, prec),
                "antigenicity": round(r.antigenicity, prec),
                "bepipred": round(r.bepipred, prec),
                "coil": round(r.coil, prec),
                "welling": round(r.welling, prec),
                "iedb_bepipred2": round(r.iedb_bepipred2, prec),
                "iedb_bepipred1": round(r.iedb_bepipred1, prec),
                "iedb_emini": round(r.iedb_emini, prec),
                "iedb_kolaskar": round(r.iedb_kolaskar, prec),
                "iedb_parker": round(r.iedb_parker, prec),
                "iedb_choufasman": round(r.iedb_choufasman, prec),
                "iedb_karplus": round(r.iedb_karplus, prec),
                "consensus_count": r.consensus_count,
                "structural_sasa": round(r.structural_sasa, prec),
                "combined_score": round(r.combined_score, prec),
                "is_exposed": r.is_exposed,
            }
            for r in residue_results
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"JSON report:  {json_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="EpiTop1 — B Linear Epitope Predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Launch GUI
  python main.py --cli MKFLVFL...         # Analyze sequence
  python main.py --cli seq.fasta          # Analyze FASTA file
  python main.py --cli seq.fasta --pdb structure.pdb --output results/
        """,
    )

    parser.add_argument(
        "--cli",
        dest="sequence",
        metavar="SEQUENCE",
        help="Run in CLI mode with given sequence or FASTA file path",
    )
    parser.add_argument(
        "--pdb",
        metavar="FILE",
        help="PDB structure file (optional)",
    )
    parser.add_argument(
        "--chain",
        metavar="ID",
        help="PDB chain ID (default: first chain)",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="DIR",
        help="Output directory for CSV/JSON exports",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=None,
        help="Minimum epitope length (default: 12)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help="Maximum epitope length (default: 25)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Minimum global score threshold (default: 0.5)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Number of top epitopes to report (default: 20)",
    )
    parser.add_argument(
        "--bio",
        action="store_true",
        default=False,
        help="Use the advanced bio module (Parker, Emini, Karplus-Schulz, "
             "Chou-Fasman, Kolaskar-Tongaonkar combined score)",
    )
    parser.add_argument(
        "--iedb",
        action="store_true",
        default=False,
        help="Query the free IEDB Tools API for BepiPred-2.0 predictions "
             "(requires internet; implies --bio). Improves accuracy by "
             "blending the state-of-the-art IEDB B-cell epitope predictor.",
    )
    parser.add_argument(
        "--plot",
        metavar="FILE",
        default=None,
        help="Save epitope score plot to FILE (requires matplotlib; "
             "only with --bio)",
    )

    args = parser.parse_args()

    # --iedb implies --bio
    if getattr(args, "iedb", False):
        args.bio = True

    if args.sequence:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
