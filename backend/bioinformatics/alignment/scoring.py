"""
Scoring functions for sequence alignment.
Implements scoring matrices and gap penalty calculations.
"""

from typing import Tuple, Dict


class ScoringMatrix:
    """
    Represents a substitution scoring matrix for biological sequences.
    Used in Needleman-Wunsch algorithm.
    """
    
    def __init__(self, match: int = 1, mismatch: int = -1):
        """
        Initialize scoring matrix with match and mismatch penalties.
        
        Args:
            match: Score for matching characters (typically positive)
            mismatch: Score for mismatched characters (typically negative)
        """
        self.match = match
        self.mismatch = mismatch
        # Valid DNA alphabet: A, T, C, G, and gap (-/*)
        self.alphabet = set(['A', 'T', 'C', 'G'])
    
    def validate_sequence(self, sequence: str) -> bool:
        """
        Validate that sequence contains only valid DNA characters.
        
        Args:
            sequence: DNA sequence to validate
            
        Returns:
            True if valid, False otherwise
        """
        sequence = sequence.upper()
        return all(c in self.alphabet for c in sequence)
    
    def score(self, char1: str, char2: str) -> int:
        """
        Get alignment score between two characters.
        
        Args:
            char1: First character
            char2: Second character
            
        Returns:
            Match score or mismatch score
        """
        if char1.upper() == char2.upper():
            return self.match
        else:
            return self.mismatch
    
    def get_matrix(self) -> Dict[Tuple[str, str], int]:
        """
        Get full substitution matrix for all character pairs.
        
        Returns:
            Dictionary mapping (char1, char2) to score
        """
        matrix = {}
        chars = list(self.alphabet)
        for c1 in chars:
            for c2 in chars:
                matrix[(c1, c2)] = self.score(c1, c2)
        return matrix


def gap_penalty(gap_length: int, gap_cost: int = -2) -> int:
    """
    Calculate gap penalty based on gap length.
    Uses linear gap penalty model for simplicity and efficiency.
    
    Args:
        gap_length: Length of the gap
        gap_cost: Cost per gap position (typically -2)
        
    Returns:
        Total gap penalty
    """
    return gap_length * gap_cost
