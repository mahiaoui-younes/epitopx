"""
Export module for EpiTop1 results.

Exports analysis results in CSV and JSON formats:
- Per-residue score table
- Epitope candidate list
- Full analysis report

All exports include metadata (date, parameters, sequence info).
"""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import (
    EXPORT_SETTINGS,
    SCORING_WEIGHTS,
    WINDOW_SIZES,
    EPITOPE_CRITERIA,
)
from core.scoring import ResidueScore
from core.epitope_selector import EpitopeCandidate


def _get_metadata(
    sequence_header: str,
    sequence_length: int,
    has_pdb: bool = False,
) -> Dict[str, Any]:
    """Generate analysis metadata."""
    return {
        "software": "EpiTop1 — B Linear Epitope Predictor",
        "version": "1.0.0",
        "date": datetime.now().isoformat(),
        "sequence_header": sequence_header,
        "sequence_length": sequence_length,
        "pdb_structure_used": bool(has_pdb),
        "parameters": {
            "scoring_weights": SCORING_WEIGHTS,
            "window_sizes": WINDOW_SIZES,
            "epitope_criteria": EPITOPE_CRITERIA,
        },
    }


def export_residue_table(
    residue_scores: List[ResidueScore],
    filepath: str,
    sequence_header: str = "Unknown",
) -> str:
    """
    Export per-residue score table to CSV.

    Columns: Position, AA, Hydrophilicity, Hydrophobicity,
    Flexibility, Accessibility, Antigenicity, SASA, GlobalScore, Exposed

    Args:
        residue_scores: List of ResidueScore objects.
        filepath: Output CSV file path.
        sequence_header: Sequence header for metadata.

    Returns:
        Path to created file.
    """
    precision = EXPORT_SETTINGS["float_precision"]
    delimiter = EXPORT_SETTINGS["csv_delimiter"]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=delimiter)

        # Header with metadata
        writer.writerow([
            f"# EpiTop1 Residue Scores — {sequence_header}"
        ])
        writer.writerow([
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        writer.writerow([])

        # Column headers
        writer.writerow([
            "Position", "AA",
            "Hydrophilicity_HW", "Hydrophobicity_KD",
            "Flexibility_KS", "Accessibility_Emini",
            "Antigenicity_KT", "Structural_SASA",
            "Global_Score", "Is_Exposed",
        ])

        # Data rows
        for score in residue_scores:
            writer.writerow([
                score.position,
                score.amino_acid,
                round(score.hydrophilicity, precision),
                round(score.hydrophobicity, precision),
                round(score.flexibility, precision),
                round(score.accessibility, precision),
                round(score.antigenicity, precision),
                round(score.structural_sasa, precision),
                round(score.global_score, precision),
                "Yes" if score.is_exposed else "No",
            ])

    return filepath


def export_csv(
    epitopes: List[EpitopeCandidate],
    filepath: str,
    sequence_header: str = "Unknown",
) -> str:
    """
    Export epitope candidates to CSV.

    Args:
        epitopes: List of EpitopeCandidate objects.
        filepath: Output CSV file path.
        sequence_header: Sequence header for metadata.

    Returns:
        Path to created file.
    """
    precision = EXPORT_SETTINGS["float_precision"]
    delimiter = EXPORT_SETTINGS["csv_delimiter"]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=delimiter)

        # Header
        writer.writerow([
            f"# EpiTop1 Epitope Candidates — {sequence_header}"
        ])
        writer.writerow([
            f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        writer.writerow([])

        # Column headers
        writer.writerow([
            "Rank", "Start", "End", "Length",
            "Sequence", "Global_Score",
            "Hydrophilicity", "Hydrophobicity",
            "Flexibility", "Accessibility",
            "Antigenicity", "Structural_SASA",
            "Hydrophilic_Fraction", "Valid",
            "Exclusion_Reasons",
        ])

        # Data rows
        for ep in epitopes:
            writer.writerow([
                ep.rank,
                ep.start,
                ep.end,
                ep.length,
                ep.sequence,
                round(ep.global_score, precision),
                round(ep.hydrophilicity, precision),
                round(ep.hydrophobicity, precision),
                round(ep.flexibility, precision),
                round(ep.accessibility, precision),
                round(ep.antigenicity, precision),
                round(ep.structural_sasa, precision),
                round(ep.hydrophilic_fraction, precision),
                "Yes" if ep.is_valid else "No",
                "; ".join(ep.exclusion_reasons) if ep.exclusion_reasons else "",
            ])

    return filepath


def export_json(
    epitopes: List[EpitopeCandidate],
    residue_scores: List[ResidueScore],
    filepath: str,
    sequence_header: str = "Unknown",
    sequence: str = "",
    has_pdb: bool = False,
) -> str:
    """
    Export complete analysis report to JSON.

    Args:
        epitopes: List of EpitopeCandidate objects.
        residue_scores: List of ResidueScore objects.
        filepath: Output JSON file path.
        sequence_header: Sequence header.
        sequence: Full protein sequence.
        has_pdb: Whether PDB structure was used.

    Returns:
        Path to created file.
    """
    indent = EXPORT_SETTINGS["json_indent"]
    precision = EXPORT_SETTINGS["float_precision"]

    report = {
        "metadata": _get_metadata(
            sequence_header, len(sequence), has_pdb
        ),
        "sequence": {
            "header": sequence_header,
            "sequence": sequence,
            "length": len(sequence),
        },
        "epitope_candidates": [
            {
                "rank": ep.rank,
                "start": ep.start,
                "end": ep.end,
                "length": ep.length,
                "sequence": ep.sequence,
                "scores": {
                    "global_score": round(ep.global_score, precision),
                    "hydrophilicity": round(ep.hydrophilicity, precision),
                    "hydrophobicity": round(ep.hydrophobicity, precision),
                    "flexibility": round(ep.flexibility, precision),
                    "accessibility": round(ep.accessibility, precision),
                    "antigenicity": round(ep.antigenicity, precision),
                    "structural_sasa": round(ep.structural_sasa, precision),
                    "hydrophilic_fraction": round(
                        ep.hydrophilic_fraction, precision
                    ),
                },
                "is_valid": bool(ep.is_valid),
                "exclusion_reasons": ep.exclusion_reasons,
            }
            for ep in epitopes
        ],
        "residue_scores": [
            {
                "position": s.position,
                "amino_acid": s.amino_acid,
                "hydrophilicity": round(s.hydrophilicity, precision),
                "hydrophobicity": round(s.hydrophobicity, precision),
                "flexibility": round(s.flexibility, precision),
                "accessibility": round(s.accessibility, precision),
                "antigenicity": round(s.antigenicity, precision),
                "structural_sasa": round(s.structural_sasa, precision),
                "global_score": round(s.global_score, precision),
                "is_exposed": bool(s.is_exposed),
            }
            for s in residue_scores
        ],
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=indent, ensure_ascii=False)

    return filepath
