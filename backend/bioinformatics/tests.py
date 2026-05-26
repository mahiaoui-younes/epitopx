"""
Unit tests for bioinformatics alignment algorithms.
Tests Needleman-Wunsch, UPGMA, and progressive alignment.
"""

import unittest
from backend_api.bioinformatics.alignment import (
    ScoringMatrix,
    NeedlemanWunsch,
    UPGMATree,
    ProgressiveAligner,
    build_distance_matrix,
)


class TestScoringMatrix(unittest.TestCase):
    """Tests for scoring matrix functionality."""
    
    def setUp(self):
        self.scoring = ScoringMatrix(match=1, mismatch=-1)
    
    def test_valid_dna_sequence(self):
        """Test DNA sequence validation."""
        self.assertTrue(self.scoring.validate_sequence("ATCG"))
        self.assertTrue(self.scoring.validate_sequence("atcg"))
        self.assertFalse(self.scoring.validate_sequence("ATCGX"))
        self.assertFalse(self.scoring.validate_sequence(""))
    
    def test_scoring(self):
        """Test scoring of character pairs."""
        self.assertEqual(self.scoring.score('A', 'A'), 1)
        self.assertEqual(self.scoring.score('A', 'T'), -1)
        self.assertEqual(self.scoring.score('a', 'a'), 1)


class TestNeedlemanWunsch(unittest.TestCase):
    """Tests for Needleman-Wunsch pairwise alignment."""
    
    def setUp(self):
        self.aligner = NeedlemanWunsch(match=1, mismatch=-1, gap_cost=-2)
    
    def test_identical_sequences(self):
        """Test alignment of identical sequences."""
        seq1, seq2, score = self.aligner.align("ATCG", "ATCG")
        self.assertEqual(seq1, "ATCG")
        self.assertEqual(seq2, "ATCG")
        self.assertEqual(score, 4)  # 4 matches * 1
    
    def test_completely_different_sequences(self):
        """Test alignment of different sequences."""
        seq1, seq2, score = self.aligner.align("AAAA", "TTTT")
        self.assertEqual(len(seq1), len(seq2))
    
    def test_gap_insertion(self):
        """Test that gaps are properly inserted."""
        seq1, seq2, score = self.aligner.align("ATG", "AT")
        self.assertEqual(len(seq1), len(seq2))
        # One sequence should have a gap
        self.assertTrue('-' in seq1 or '-' in seq2)
    
    def test_invalid_sequence(self):
        """Test that invalid sequences raise error."""
        with self.assertRaises(ValueError):
            self.aligner.align("ATCGX", "ATCG")
    
    def test_similarity_score(self):
        """Test similarity scoring."""
        score = self.aligner.similarity_score("ATCG", "ATCG")
        self.assertGreater(score, 90)  # Should be very high for identical
        
        score = self.aligner.similarity_score("AAAA", "TTTT")
        self.assertLess(score, 50)  # Should be low for different
    
    def test_simple_example(self):
        """Test with simple example."""
        seq1, seq2, score = self.aligner.align("ATG", "ACG")
        # A matches A (1), T-C mismatch (-1), G matches G (1), no gaps needed
        # Expected score around 1 or -1 depending on exact alignment
        self.assertEqual(len(seq1), len(seq2))


class TestUPGMATree(unittest.TestCase):
    """Tests for UPGMA guide tree construction."""
    
    def test_simple_tree_building(self):
        """Test basic tree construction."""
        # Simple distance matrix for 3 sequences
        distances = [
            [0.0, 0.1, 0.5],
            [0.1, 0.0, 0.4],
            [0.5, 0.4, 0.0],
        ]
        names = ["seq1", "seq2", "seq3"]
        
        tree = UPGMATree(distances, names)
        root = tree.build()
        
        self.assertIsNotNone(root)
        self.assertFalse(root.is_leaf)
    
    def test_tree_size_mismatch(self):
        """Test error handling for mismatched sizes."""
        distances = [[0.0, 0.1], [0.1, 0.0]]
        names = ["seq1", "seq2", "seq3"]
        
        with self.assertRaises(ValueError):
            UPGMATree(distances, names)


class TestDistanceMatrix(unittest.TestCase):
    """Tests for distance matrix building."""
    
    def test_distance_matrix_building(self):
        """Test distance matrix construction."""
        aligner = NeedlemanWunsch()
        sequences = ["ATCG", "ATCG", "TTTT"]
        
        matrix = build_distance_matrix(sequences, aligner.similarity_score)
        
        # Same sequences should have 0 distance
        self.assertLess(matrix[0][1], 0.1)  # seq1 vs seq2 (identical)
        # Different sequences should have higher distance
        self.assertGreater(matrix[0][2], 0.5)  # seq1 vs seq3 (very different)
        
        # Matrix should be symmetric
        self.assertEqual(matrix[0][1], matrix[1][0])


class TestProgressiveAligner(unittest.TestCase):
    """Tests for progressive alignment."""
    
    def setUp(self):
        self.aligner = ProgressiveAligner()
    
    def test_consensus_generation(self):
        """Test consensus sequence generation."""
        alignment = [
            "ATCG",
            "ATCG",
            "ATCG",
        ]
        consensus = self.aligner._get_consensus(alignment)
        self.assertEqual(consensus, "ATCG")
    
    def test_consensus_with_gaps(self):
        """Test consensus with gaps in alignment."""
        alignment = [
            "AT-G",
            "ATCG",
            "AT-G",
        ]
        consensus = self.aligner._get_consensus(alignment)
        self.assertEqual(len(consensus), 4)


class TestEndToEnd(unittest.TestCase):
    """End-to-end alignment tests."""
    
    def test_msa_service_simple(self):
        """Test MSA service with simple sequences."""
        from backend_api.bioinformatics.services import MSAService
        
        service = MSAService()
        sequences = ["ATCG", "ATCG", "ATCG"]
        result = service.align(sequences)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['alignment']), 3)
        self.assertGreater(len(result['consensus']), 0)
        self.assertEqual(len(result['identity_scores']), 3)
    
    def test_msa_service_different_sequences(self):
        """Test MSA service with different sequences."""
        from backend_api.bioinformatics.services import MSAService
        
        service = MSAService()
        sequences = ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
        result = service.align(sequences)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['alignment']), 3)
        self.assertEqual(len(result['identity_scores']), 3)
        # Identity scores should be in valid range
        for score in result['identity_scores']:
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)


if __name__ == '__main__':
    unittest.main()
