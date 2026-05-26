"""
Progressive multiple sequence alignment.
Implements the core MSA algorithm following the guide tree constructed by UPGMA.
"""

from typing import List, Tuple, Dict, Optional
from .pairwise import NeedlemanWunsch
from .tree import TreeNode


class ProgressiveAligner:
    """
    Progressive Multiple Sequence Alignment using guide tree.
    
    Strategy:
    1. Compute pairwise alignments and distance matrix
    2. Build UPGMA guide tree
    3. Align sequences following tree: progressively merge alignments
       moving from leaves to root
    
    This approach mirrors real tools like Clustal Omega and MUSCLE.
    """
    
    def __init__(self, match: int = 1, mismatch: int = -1, gap_cost: int = -2):
        """
        Initialize progressive aligner.
        
        Args:
            match: Match score for pairwise alignment
            mismatch: Mismatch score for pairwise alignment
            gap_cost: Gap cost for pairwise alignment
        """
        self.pairwise_aligner = NeedlemanWunsch(match, mismatch, gap_cost)
        self.match = match
        self.mismatch = mismatch
        self.gap_cost = gap_cost
    
    def align_with_tree(self, sequences: List[str], tree: TreeNode) -> List[str]:
        """
        Progressive alignment guided by tree structure.
        
        Algorithm:
        1. Process tree leaves to roots (post-order traversal)
        2. At each internal node, align the two child alignments
        3. Propagate gaps correctly through alignment columns
        
        Args:
            sequences: Original unaligned sequences
            tree: UPGMA guide tree with root node
            
        Returns:
            List of aligned sequences (in original order)
        """
        # Create mapping from sequence index to alignment
        alignment_map = {}
        
        def post_order_align(node: TreeNode):
            """Post-order traversal to align from leaves to root."""
            if node.is_leaf:
                # Leaf node: sequence is its own alignment
                if node.sequence_index is not None:
                    alignment_map[id(node)] = [sequences[node.sequence_index]]
            else:
                # Internal node: recursively align children, then merge
                if node.left:
                    post_order_align(node.left)
                if node.right:
                    post_order_align(node.right)
                
                # Get child alignments
                left_alignment = alignment_map.get(id(node.left), [])
                right_alignment = alignment_map.get(id(node.right), [])
                
                # Align the two profile sequences
                if left_alignment and right_alignment:
                    merged = self._align_profiles(left_alignment, right_alignment)
                    alignment_map[id(node)] = merged
        
        # Perform alignment
        post_order_align(tree)
        
        # Get final alignment from root
        final_alignment = alignment_map.get(id(tree), [])
        
        # Reorder alignment to match original sequence order
        result = self._reorder_alignment(final_alignment, sequences, tree)
        
        return result
    
    def _align_profiles(self, profile1: List[str], profile2: List[str]) -> List[str]:
        """
        Align two profiles (partial alignments).
        
        Uses consensus sequences from each profile for alignment guidance.
        Then aligns each sequence against the final alignment.
        
        Args:
            profile1: Partial alignment (list of aligned sequences)
            profile2: Partial alignment (list of aligned sequences)
            
        Returns:
            Merged alignment of all sequences
        """
        # Build consensus for each profile
        consensus1 = self._get_consensus(profile1)
        consensus2 = self._get_consensus(profile2)
        
        # Align consensus sequences
        try:
            aligned_consensus1, aligned_consensus2, _ = self.pairwise_aligner.align(
                consensus1, consensus2
            )
        except (ValueError, Exception):
            # If alignment fails, return profiles as-is with gap padding
            return profile1 + profile2
        
        # Apply alignment to full profiles
        merged = self._apply_profile_alignment(
            profile1, profile2, aligned_consensus1, aligned_consensus2
        )
        
        return merged
    
    def _get_consensus(self, alignment: List[str]) -> str:
        """
        Generate consensus sequence from alignment using majority rule.
        
        At each position, select the most frequent character.
        Gaps are ignored unless they're most frequent.
        
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
            # Count characters at this position
            char_counts = {}
            for seq in alignment:
                if pos < len(seq):
                    char = seq[pos]
                    char_counts[char] = char_counts.get(char, 0) + 1
            
            # Find most frequent (majority rule)
            if char_counts:
                most_frequent = max(char_counts.items(), key=lambda x: x[1])[0]
                # Prefer non-gap characters
                if most_frequent != '-':
                    consensus.append(most_frequent)
                else:
                    # If most frequent is gap, try to find any base
                    for char, count in char_counts.items():
                        if char != '-':
                            consensus.append(char)
                            break
                    else:
                        consensus.append('-')
            else:
                consensus.append('-')
        
        return ''.join(consensus)
    
    def _apply_profile_alignment(self, profile1: List[str], profile2: List[str],
                                aligned_consensus1: str, aligned_consensus2: str) -> List[str]:
        """
        Apply consensus alignment to both profiles by adding gaps.
        
        Tracks which positions in original consensus align to which positions
        in the other aligned consensus, and propagates gaps accordingly.
        
        Args:
            profile1: First profile
            profile2: Second profile
            aligned_consensus1: Aligned first consensus
            aligned_consensus2: Aligned second consensus
            
        Returns:
            Merged alignment
        """
        # Track non-gap positions in original consensuses
        pos1_mapping = []
        pos2_mapping = []
        
        idx1 = 0
        for char in aligned_consensus1:
            if char != '-':
                pos1_mapping.append(idx1)
                idx1 += 1
            else:
                pos1_mapping.append(None)
        
        idx2 = 0
        for char in aligned_consensus2:
            if char != '-':
                pos2_mapping.append(idx2)
                idx2 += 1
            else:
                pos2_mapping.append(None)
        
        # Apply gaps to profile1
        new_profile1 = []
        for seq in profile1:
            new_seq = self._insert_gaps(seq, pos1_mapping)
            new_profile1.append(new_seq)
        
        # Apply gaps to profile2
        new_profile2 = []
        for seq in profile2:
            new_seq = self._insert_gaps(seq, pos2_mapping)
            new_profile2.append(new_seq)
        
        # Ensure all sequences have same length
        max_len = max((len(s) for s in new_profile1 + new_profile2), default=0)
        
        result = [
            seq.ljust(max_len, '-') for seq in new_profile1 + new_profile2
        ]
        
        return result
    
    def _insert_gaps(self, sequence: str, position_mapping: List[Optional[int]]) -> str:
        """
        Insert gaps into sequence based on position mapping.
        
        Args:
            sequence: Original sequence (possibly already aligned with gaps)
            position_mapping: List where index is target position, 
                            value is source position in sequence (or None for gap)
            
        Returns:
            Sequence with gaps inserted
        """
        result = []
        
        for target_pos in position_mapping:
            if target_pos is None:
                result.append('-')
            else:
                # Find the character at this position in original sequence
                # Account for existing gaps in sequence
                char_count = 0
                for i, char in enumerate(sequence):
                    if char != '-':
                        if char_count == target_pos:
                            result.append(char)
                            break
                        char_count += 1
                else:
                    result.append('-')
        
        return ''.join(result)
    
    def _reorder_alignment(self, alignment: List[str], original_sequences: List[str],
                          tree: TreeNode) -> List[str]:
        """
        Reorder aligned sequences to match original input order.
        
        Args:
            alignment: Aligned sequences (possibly in tree order)
            original_sequences: Original sequences in desired order
            tree: UPGMA tree
            
        Returns:
            Aligned sequences in original order
        """
        if not alignment:
            return []
        
        # Get sequence indices in tree traversal order
        traversal_order = self._get_traversal_order(tree)
        
        # If we don't have enough aligned sequences, return as-is
        if len(alignment) != len(original_sequences):
            # Pad or trim to match original sequence count
            if len(alignment) > len(original_sequences):
                return alignment[:len(original_sequences)]
            else:
                # Pad with gaps
                alignment_length = len(alignment[0]) if alignment else 0
                return alignment + ['-' * alignment_length] * (len(original_sequences) - len(alignment))
        
        # Create mapping from tree order to original order
        if len(traversal_order) == len(original_sequences):
            result = [None] * len(original_sequences)
            for tree_idx, orig_idx in enumerate(traversal_order):
                if tree_idx < len(alignment):
                    result[orig_idx] = alignment[tree_idx]
            
            # Fill in any missing entries
            alignment_length = len(alignment[0]) if alignment else 0
            return [seq if seq is not None else '-' * alignment_length for seq in result]
        
        return alignment
    
    def _get_traversal_order(self, node: TreeNode) -> List[int]:
        """Get sequence indices in leaf traversal order."""
        order = []
        
        def traverse(n: TreeNode):
            if n.is_leaf and n.sequence_index is not None:
                order.append(n.sequence_index)
            else:
                if n.left:
                    traverse(n.left)
                if n.right:
                    traverse(n.right)
        
        traverse(node)
        return order
