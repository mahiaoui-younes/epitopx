"""
Pairwise sequence alignment using Needleman-Wunsch algorithm.
Classic dynamic programming approach for optimal global alignment.
"""

from typing import Tuple, List, Dict
from .scoring import ScoringMatrix, gap_penalty


class NeedlemanWunsch:
    """
    Needleman-Wunsch algorithm implementation for global pairwise alignment.
    
    This is the classic bioinformatics algorithm for optimal global sequence alignment
    using dynamic programming. Works on DNA sequences using a scoring matrix.
    """
    
    def __init__(self, match: int = 1, mismatch: int = -1, gap_cost: int = -2):
        """
        Initialize Needleman-Wunsch aligner with scoring parameters.
        
        Args:
            match: Score for matching bases (typically 1)
            mismatch: Score for mismatched bases (typically -1)
            gap_cost: Cost per gap position (typically -2)
        """
        self.scoring_matrix = ScoringMatrix(match, mismatch)
        self.gap_cost = gap_cost
        self.match = match
        self.mismatch = mismatch
    
    def align(self, seq1: str, seq2: str) -> Tuple[str, str, float]:
        """
        Perform Needleman-Wunsch global alignment.
        
        Algorithm steps:
        1. Initialize DP matrix with gap penalties
        2. Fill matrix with recurrence relation: 
           F(i,j) = max(
               F(i-1,j-1) + match/mismatch,
               F(i-1,j) + gap_cost,
               F(i,j-1) + gap_cost
           )
        3. Backtrack to reconstruct optimal alignment
        
        Args:
            seq1: First DNA sequence
            seq2: Second DNA sequence
            
        Returns:
            Tuple of (aligned_seq1, aligned_seq2, score)
        """
        seq1 = seq1.upper()
        seq2 = seq2.upper()
        
        # Validate sequences
        if not self.scoring_matrix.validate_sequence(seq1):
            raise ValueError(f"Invalid DNA sequence: {seq1}. Use only A, T, C, G.")
        if not self.scoring_matrix.validate_sequence(seq2):
            raise ValueError(f"Invalid DNA sequence: {seq2}. Use only A, T, C, G.")
        
        # Initialize DP matrix
        rows = len(seq1) + 1
        cols = len(seq2) + 1
        
        # DP table for scores
        dp = [[0] * cols for _ in range(rows)]
        
        # Initialize first row and column with gap penalties
        for i in range(rows):
            dp[i][0] = i * self.gap_cost
        for j in range(cols):
            dp[0][j] = j * self.gap_cost
        
        # Fill DP matrix using recurrence relation
        for i in range(1, rows):
            for j in range(1, cols):
                # Score from diagonal (match or mismatch)
                diag_score = dp[i-1][j-1] + self.scoring_matrix.score(
                    seq1[i-1], seq2[j-1]
                )
                # Score from above (gap in seq2)
                up_score = dp[i-1][j] + self.gap_cost
                # Score from left (gap in seq1)
                left_score = dp[i][j-1] + self.gap_cost
                
                # Take maximum score
                dp[i][j] = max(diag_score, up_score, left_score)
        
        # Backtrack to get alignment
        aligned_seq1, aligned_seq2 = self._backtrack(
            seq1, seq2, dp
        )
        
        score = dp[rows-1][cols-1]
        
        return aligned_seq1, aligned_seq2, score
    
    def _backtrack(self, seq1: str, seq2: str, dp: List[List[float]]) -> Tuple[str, str]:
        """
        Backtrack through DP matrix to reconstruct optimal alignment.
        
        Starts from bottom-right corner and traces back to top-left,
        following the path that was used to compute the optimal score.
        
        Args:
            seq1: First sequence
            seq2: Second sequence
            dp: DP score matrix
            
        Returns:
            Tuple of (aligned_seq1, aligned_seq2)
        """
        i = len(seq1)
        j = len(seq2)
        
        aligned_seq1 = []
        aligned_seq2 = []
        
        # Backtrack from bottom-right to top-left
        while i > 0 or j > 0:
            if i == 0:
                # Reached top edge, must insert from seq2
                aligned_seq1.append('-')
                aligned_seq2.append(seq2[j-1])
                j -= 1
            elif j == 0:
                # Reached left edge, must insert from seq1
                aligned_seq1.append(seq1[i-1])
                aligned_seq2.append('-')
                i -= 1
            else:
                # Check which direction we came from
                current_score = dp[i][j]
                diag_score = dp[i-1][j-1] + self.scoring_matrix.score(
                    seq1[i-1], seq2[j-1]
                )
                up_score = dp[i-1][j] + self.gap_cost
                left_score = dp[i][j-1] + self.gap_cost
                
                # Prefer diagonal (match/mismatch) in case of ties
                if current_score == diag_score:
                    aligned_seq1.append(seq1[i-1])
                    aligned_seq2.append(seq2[j-1])
                    i -= 1
                    j -= 1
                elif current_score == up_score:
                    aligned_seq1.append(seq1[i-1])
                    aligned_seq2.append('-')
                    i -= 1
                else:  # left_score
                    aligned_seq1.append('-')
                    aligned_seq2.append(seq2[j-1])
                    j -= 1
        
        # Reverse since we backtracked
        aligned_seq1 = ''.join(reversed(aligned_seq1))
        aligned_seq2 = ''.join(reversed(aligned_seq2))
        
        return aligned_seq1, aligned_seq2
    
    def similarity_score(self, seq1: str, seq2: str) -> float:
        """
        Compute normalized similarity score between two sequences.
        Score is in range [0, 100] representing percentage similarity.
        
        Args:
            seq1: First DNA sequence
            seq2: Second DNA sequence
            
        Returns:
            Similarity score as percentage
        """
        try:
            _, _, raw_score = self.align(seq1, seq2)
        except ValueError:
            return 0.0
        
        # Normalize by maximum possible score
        max_length = max(len(seq1), len(seq2))
        if max_length == 0:
            return 100.0
        
        # Maximum possible score (all matches)
        max_score = max_length * self.match
        
        # Normalize to percentage
        if max_score > 0:
            similarity = ((raw_score + (max_length * abs(self.gap_cost))) / 
                         (max_score + (max_length * abs(self.gap_cost)))) * 100
            return max(0, min(100, similarity))  # Clamp to 0-100
        
        return 0.0


def pairwise_align(seq1: str, seq2: str, match: int = 1, 
                   mismatch: int = -1, gap_cost: int = -2) -> Dict:
    """
    Convenience function for pairwise alignment.
    
    Args:
        seq1: First sequence
        seq2: Second sequence
        match: Match score
        mismatch: Mismatch score
        gap_cost: Gap cost
        
    Returns:
        Dictionary with 'aligned_seq1', 'aligned_seq2', and 'score'
    """
    aligner = NeedlemanWunsch(match, mismatch, gap_cost)
    aligned_seq1, aligned_seq2, score = aligner.align(seq1, seq2)
    
    return {
        'aligned_seq1': aligned_seq1,
        'aligned_seq2': aligned_seq2,
        'score': score
    }
