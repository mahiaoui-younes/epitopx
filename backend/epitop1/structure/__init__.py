"""
Structure package for EpiTop1 - PDB parsing and SASA calculation.

Contains:
- PDB file parser (BioPython-based)
- SASA calculator (Shrake & Rupley algorithm)
"""

from .pdb_parser import PDBParser
from .sasa import SASACalculator

__all__ = ["PDBParser", "SASACalculator"]
