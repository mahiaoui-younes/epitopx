"""
Multiple Sequence Alignment (MSA) service.
High-level orchestration of the MSA pipeline using algorithms from alignment module.
"""

from typing import List, Dict, Tuple
import statistics
from ..alignment import (
    NeedlemanWunsch,
    UPGMATree,
    build_distance_matrix,
    ProgressiveAligner,
)


class MSAService:
    """
    Multiple Sequence Alignment service.
    
    Orchestrates the complete MSA workflow:
    1. Validate input sequences
    2. Compute pairwise alignments and distance matrix
    3. Build UPGMA guide tree
    4. Perform progressive alignment
    5. Compute consensus and identity scores
    """
    
    def __init__(self, match: int = 1, mismatch: int = -1, gap_cost: int = -2):
        """
        Initialize MSA service with scoring parameters.
        
        Args:
            match: Score for matching bases
            mismatch: Score for mismatched bases
            gap_cost: Cost per gap position
        """
        self.match = match
        self.mismatch = mismatch
        self.gap_cost = gap_cost
        self.pairwise_aligner = NeedlemanWunsch(match, mismatch, gap_cost)
        self.progressive_aligner = ProgressiveAligner(match, mismatch, gap_cost)
    
    def validate_sequences(self, sequences: List[str]) -> Tuple[bool, str]:
        """
        Validate input sequences for DNA content and basic requirements.
        
        Args:
            sequences: List of DNA sequences
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not sequences:
            return False, "No sequences provided"
        
        if len(sequences) < 2:
            return False, "At least 2 sequences required for MSA"
        
        if len(sequences) > 50:
            return False, "Maximum 50 sequences allowed"
        
        for i, seq in enumerate(sequences):
            if not isinstance(seq, str):
                return False, f"Sequence {i} is not a string"
            
            if len(seq) == 0:
                return False, f"Sequence {i} is empty"
            
            if len(seq) > 10000:
                return False, f"Sequence {i} exceeds maximum length of 10000 bp"
            
            if not self.pairwise_aligner.scoring_matrix.validate_sequence(seq):
                return False, f"Sequence {i} contains invalid DNA characters. Use only A, T, C, G"
        
        return True, ""
    
    def align(self, sequences: List[str]) -> Dict:
        """
        Perform multiple sequence alignment.
        
        Pipeline:
        1. Validate sequences
        2. Compute pairwise similarity scores
        3. Build distance matrix
        4. Construct UPGMA guide tree
        5. Perform progressive alignment
        6. Compute consensus and identity scores
        
        Args:
            sequences: List of DNA sequences to align
            
        Returns:
            Dictionary with alignment results
        """
        # Validate sequences
        is_valid, error_msg = self.validate_sequences(sequences)
        if not is_valid:
            return {
                'success': False,
                'error': error_msg,
                'alignment': [],
                'consensus': '',
                'identity_scores': [],
                'method': 'progressive_msa'
            }
        
        try:
            # Normalize sequences to uppercase
            sequences_upper = [seq.upper() for seq in sequences]
            
            # Compute pairwise distances
            distance_matrix = build_distance_matrix(
                sequences_upper,
                self.pairwise_aligner.similarity_score
            )
            
            # Build UPGMA guide tree
            sequence_names = [f"seq_{i}" for i in range(len(sequences_upper))]
            tree_builder = UPGMATree(distance_matrix, sequence_names)
            guide_tree = tree_builder.build()
            
            # Perform progressive alignment
            alignment = self.progressive_aligner.align_with_tree(
                sequences_upper, guide_tree
            )
            
            # Ensure alignment has correct number of sequences
            if len(alignment) != len(sequences_upper):
                # Pad alignment if necessary
                alignment_length = len(alignment[0]) if alignment else 0
                alignment = alignment + ['-' * alignment_length] * (len(sequences_upper) - len(alignment))
            
            # Compute consensus sequence
            consensus = self._compute_consensus(alignment)
            
            # Compute identity scores for each sequence
            identity_scores = self._compute_identity_scores(alignment)
            
            return {
                'success': True,
                'alignment': alignment,
                'consensus': consensus,
                'identity_scores': identity_scores,
                'method': 'progressive_msa',
                'num_sequences': len(sequences),
                'alignment_length': len(alignment[0]) if alignment else 0
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f"Alignment failed: {str(e)}",
                'alignment': [],
                'consensus': '',
                'identity_scores': [],
                'method': 'progressive_msa'
            }
    
    def _compute_consensus(self, alignment: List[str]) -> str:
        """
        Compute consensus sequence from alignment using majority rule.
        
        At each column:
        - Count frequency of each base
        - Select most frequent base
        - If most frequent is gap and other bases exist, select most common base
        
        Args:
            alignment: Aligned sequences
            
        Returns:
            Consensus sequence
        """
        if not alignment or len(alignment[0]) == 0:
            return ""
        
        consensus = []
        alignment_length = len(alignment[0])
        
        for pos in range(alignment_length):
            char_counts = {}
            
            for seq in alignment:
                if pos < len(seq):
                    char = seq[pos]
                    char_counts[char] = char_counts.get(char, 0) + 1
            
            if char_counts:
                # Find most frequent character
                most_frequent = max(char_counts.items(), key=lambda x: x[1])[0]
                
                # Prefer non-gap if it's reasonably frequent
                if most_frequent == '-':
                    # Try to find a non-gap character
                    non_gap_chars = {c: cnt for c, cnt in char_counts.items() if c != '-'}
                    if non_gap_chars:
                        most_frequent = max(non_gap_chars.items(), key=lambda x: x[1])[0]
                
                consensus.append(most_frequent)
            else:
                consensus.append('-')
        
        return ''.join(consensus)
    
    def _compute_identity_scores(self, alignment: List[str]) -> List[float]:
        """
        Compute identity percentage for each sequence.
        
        Identity = (number of positions matching consensus) / (alignment length) * 100
        Gaps are treated as non-matching positions.
        
        Args:
            alignment: Aligned sequences
            
        Returns:
            List of identity percentages
        """
        if not alignment or len(alignment[0]) == 0:
            return []
        
        consensus = self._compute_consensus(alignment)
        scores = []
        
        for seq in alignment:
            matches = 0
            for i, char in enumerate(seq):
                if i < len(consensus):
                    # Count exact matches with consensus (gaps don't match)
                    if char == consensus[i] and char != '-':
                        matches += 1
            
            # Calculate percentage
            total_positions = len(seq)
            if total_positions > 0:
                identity = (matches / total_positions) * 100
                scores.append(round(identity, 1))
            else:
                scores.append(0.0)
        
        return scores
    
    def align_fasta(self, fasta_content: str) -> Dict:
        """
        Parse FASTA format and perform alignment.
        
        Bonus feature: Optional FASTA input support.
        
        Args:
            fasta_content: FASTA format string
            
        Returns:
            Alignment results dictionary
        """
        sequences = []
        current_seq = ""
        
        for line in fasta_content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('>'):
                # Header line
                if current_seq:
                    sequences.append(current_seq)
                current_seq = ""
            else:
                # Sequence line
                current_seq += line
        
        # Don't forget last sequence
        if current_seq:
            sequences.append(current_seq)
        
        return self.align(sequences)


def perform_msa(sequences: List[str], match: int = 1, 
                mismatch: int = -1, gap_cost: int = -2) -> Dict:
    """
    Convenience function to perform MSA.
    
    Args:
        sequences: List of DNA sequences
        match: Match score
        mismatch: Mismatch score
        gap_cost: Gap cost
        
    Returns:
        Alignment results
    """
    service = MSAService(match, mismatch, gap_cost)
    return service.align(sequences)
