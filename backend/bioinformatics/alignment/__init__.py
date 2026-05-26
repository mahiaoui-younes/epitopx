"""
Alignment module for bioinformatics.
Provides pairwise alignment, guide tree construction, and progressive MSA.
"""

from .scoring import ScoringMatrix, gap_penalty
from .pairwise import NeedlemanWunsch, pairwise_align
from .tree import UPGMATree, TreeNode, build_distance_matrix
from .progressive import ProgressiveAligner

__all__ = [
    'ScoringMatrix',
    'gap_penalty',
    'NeedlemanWunsch',
    'pairwise_align',
    'UPGMATree',
    'TreeNode',
    'build_distance_matrix',
    'ProgressiveAligner',
]
