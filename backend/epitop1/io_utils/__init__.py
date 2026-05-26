"""
IO utilities package for EpiTop1 - File parsing and export.

Contains:
- FASTA sequence parser
- CSV/JSON exporter
"""

from .fasta_parser import parse_fasta, parse_sequence_input
from .exporter import export_csv, export_json, export_residue_table

__all__ = [
    "parse_fasta",
    "parse_sequence_input",
    "export_csv",
    "export_json",
    "export_residue_table",
]
