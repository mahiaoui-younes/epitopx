"""
Guide tree construction using UPGMA (Unweighted Pair Group Method with Arithmetic Mean).
Creates a hierarchical clustering tree to guide progressive alignment.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import math


@dataclass
class TreeNode:
    """Represents a node in the UPGMA guide tree."""
    name: str  # Sequence name or internal node ID
    left: Optional['TreeNode'] = None
    right: Optional['TreeNode'] = None
    height: float = 0.0  # Vertical position in tree (for visualization)
    distance: float = 0.0  # Distance from parent
    is_leaf: bool = True
    sequence_index: Optional[int] = None  # Original sequence index if leaf node


class UPGMATree:
    """
    UPGMA (Unweighted Pair Group Method with Arithmetic Mean) algorithm.
    
    Creates a hierarchical clustering tree from a distance matrix.
    Used to guide progressive multiple sequence alignment by determining
    the order in which sequences should be aligned.
    """
    
    def __init__(self, distance_matrix: List[List[float]], sequence_names: List[str]):
        """
        Initialize UPGMA with distance matrix.
        
        Args:
            distance_matrix: Square matrix of pairwise distances
            sequence_names: Names/IDs of sequences
        """
        if len(distance_matrix) != len(sequence_names):
            raise ValueError("Distance matrix size must match number of sequences")
        
        self.n_sequences = len(sequence_names)
        self.distance_matrix = [row[:] for row in distance_matrix]  # Deep copy
        self.sequence_names = sequence_names[:]
        self.root = None
    
    def build(self) -> TreeNode:
        """
        Build UPGMA tree from distance matrix.
        
        Algorithm:
        1. Each sequence is initially a separate cluster
        2. Find pair of clusters with minimum distance
        3. Merge them into new internal node
        4. Recalculate distances from new cluster to all others
        5. Repeat until single root cluster remains
        
        Returns:
            Root node of the constructed tree
        """
        # Create leaf nodes for each sequence
        clusters = {
            i: TreeNode(
                name=self.sequence_names[i],
                is_leaf=True,
                sequence_index=i
            ) for i in range(self.n_sequences)
        }
        
        # Active cluster indices
        active = set(range(self.n_sequences))
        
        # Keep track of cluster sizes for UPGMA weighted average
        cluster_sizes = {i: 1 for i in range(self.n_sequences)}
        
        # Node counter for internal nodes
        node_counter = self.n_sequences
        
        # Merge until single cluster remains
        while len(active) > 1:
            # Find pair with minimum distance
            min_distance = float('inf')
            merge_i, merge_j = None, None
            
            active_list = sorted(active)
            for i_idx, i in enumerate(active_list):
                for j in active_list[i_idx + 1:]:
                    if self.distance_matrix[i][j] < min_distance:
                        min_distance = self.distance_matrix[i][j]
                        merge_i, merge_j = i, j
            
            # Create new internal node from merged clusters
            new_node = TreeNode(
                name=f"internal_{node_counter}",
                left=clusters[merge_i],
                right=clusters[merge_j],
                is_leaf=False,
                distance=min_distance / 2  # UPGMA uses equal branch lengths
            )
            
            # Update tree structure
            clusters[merge_i] = new_node
            
            # Recalculate distances to new cluster
            # UPGMA uses simple arithmetic mean
            new_size = cluster_sizes[merge_i] + cluster_sizes[merge_j]
            
            for k in active:
                if k != merge_i and k != merge_j:
                    # Weighted average distance
                    old_dist_i = self.distance_matrix[merge_i][k]
                    old_dist_j = self.distance_matrix[merge_j][k]
                    
                    new_dist = (
                        (cluster_sizes[merge_i] * old_dist_i + 
                         cluster_sizes[merge_j] * old_dist_j) / 
                        new_size
                    )
                    
                    self.distance_matrix[merge_i][k] = new_dist
                    self.distance_matrix[k][merge_i] = new_dist
            
            # Update cluster size
            cluster_sizes[merge_i] = new_size
            
            # Remove merged cluster from active set
            active.remove(merge_j)
            node_counter += 1
        
        # The last remaining cluster is the root
        self.root = clusters[active.pop()]
        return self.root
    
    def get_merge_order(self) -> List[Tuple[int, int]]:
        """
        Get the sequence of merge operations from the tree.
        Useful for debugging and understanding the clustering hierarchy.
        
        Returns:
            List of (i, j) tuples representing merge order
        """
        if not self.root:
            self.build()
        
        merges = []
        
        def traverse(node: TreeNode):
            if not node.is_leaf:
                # Get sequence indices from subtrees
                left_indices = self._get_leaf_indices(node.left)
                right_indices = self._get_leaf_indices(node.right)
                
                if left_indices and right_indices:
                    # Record first index from each subtree
                    merges.append((min(left_indices), min(right_indices)))
                
                traverse(node.left)
                traverse(node.right)
        
        traverse(self.root)
        return merges
    
    def _get_leaf_indices(self, node: Optional[TreeNode]) -> List[int]:
        """Get all leaf indices in subtree."""
        if not node:
            return []
        if node.is_leaf:
            return [node.sequence_index] if node.sequence_index is not None else []
        
        return self._get_leaf_indices(node.left) + self._get_leaf_indices(node.right)
    
    def get_alignment_order(self) -> List[int]:
        """
        Get the order in which sequences should be aligned in progressive alignment.
        Uses a simple traversal to determine alignment sequence.
        
        Returns:
            List of sequence indices in alignment order
        """
        if not self.root:
            self.build()
        
        order = []
        
        def traverse(node: TreeNode):
            if node.is_leaf:
                if node.sequence_index is not None:
                    order.append(node.sequence_index)
            else:
                if node.left:
                    traverse(node.left)
                if node.right:
                    traverse(node.right)
        
        traverse(self.root)
        return order


def build_distance_matrix(sequences: List[str], similarity_scores: callable) -> List[List[float]]:
    """
    Build distance matrix from sequences using pairwise comparison.
    
    Distance = 1 - (similarity / 100)
    This converts similarity percentages to distances for clustering.
    
    Args:
        sequences: List of DNA sequences
        similarity_scores: Function that returns similarity score (0-100) between two sequences
        
    Returns:
        Distance matrix
    """
    n = len(sequences)
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            # Get similarity score (0-100)
            similarity = similarity_scores(sequences[i], sequences[j])
            
            # Convert to distance (0-1 scale, where 0 = identical, 1 = completely different)
            distance = 1.0 - (similarity / 100.0)
            
            matrix[i][j] = distance
            matrix[j][i] = distance
    
    return matrix
