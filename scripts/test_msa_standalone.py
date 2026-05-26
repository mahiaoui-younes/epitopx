#!/usr/bin/env python
"""
Standalone test script for MSA implementation.
Run this to verify all alignment algorithms work correctly.

Usage: python test_msa_standalone.py
"""

import sys
import os

# Add backend_api to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_scoring_matrix():
    """Test scoring matrix functionality."""
    print("\n" + "="*60)
    print("TEST 1: Scoring Matrix")
    print("="*60)
    
    from backend_api.bioinformatics.alignment.scoring import ScoringMatrix
    
    scoring = ScoringMatrix(match=1, mismatch=-1)
    
    # Test validation
    assert scoring.validate_sequence("ATCG"), "Valid sequence should pass"
    assert scoring.validate_sequence("atcg"), "Lowercase should be valid"
    assert not scoring.validate_sequence("ATCGX"), "Invalid char should fail"
    
    # Test scoring
    assert scoring.score('A', 'A') == 1, "Match should score 1"
    assert scoring.score('A', 'T') == -1, "Mismatch should score -1"
    
    print("✓ Scoring matrix tests passed")
    return True


def test_needleman_wunsch():
    """Test Needleman-Wunsch pairwise alignment."""
    print("\n" + "="*60)
    print("TEST 2: Needleman-Wunsch Pairwise Alignment")
    print("="*60)
    
    from backend_api.bioinformatics.alignment.pairwise import NeedlemanWunsch
    
    aligner = NeedlemanWunsch(match=1, mismatch=-1, gap_cost=-2)
    
    # Test identical sequences
    seq1, seq2, score = aligner.align("ATCG", "ATCG")
    assert seq1 == "ATCG" and seq2 == "ATCG", "Identical sequences should match exactly"
    assert score == 4, f"Score should be 4, got {score}"
    print(f"  Identical sequences: score={score}")
    
    # Test similarity scoring
    sim = aligner.similarity_score("ATCG", "ATCG")
    assert sim > 95, f"Identical sequences should have high similarity, got {sim}"
    print(f"  Identical similarity: {sim:.1f}%")
    
    # Test with differences
    seq1, seq2, score = aligner.align("ATG", "ACG")
    assert len(seq1) == len(seq2), "Aligned sequences should have same length"
    print(f"  Different sequences aligned: {seq1} vs {seq2}")
    
    # Test invalid sequence
    try:
        aligner.align("ATCGX", "ATCG")
        assert False, "Should raise error for invalid sequence"
    except ValueError as e:
        print(f"  Invalid sequence rejected: {e}")
    
    print("✓ Needleman-Wunsch tests passed")
    return True


def test_upgma_tree():
    """Test UPGMA guide tree construction."""
    print("\n" + "="*60)
    print("TEST 3: UPGMA Guide Tree")
    print("="*60)
    
    from backend_api.bioinformatics.alignment.tree import UPGMATree
    
    # Simple distance matrix
    distances = [
        [0.0, 0.1, 0.5],
        [0.1, 0.0, 0.4],
        [0.5, 0.4, 0.0],
    ]
    names = ["seq1", "seq2", "seq3"]
    
    tree = UPGMATree(distances, names)
    root = tree.build()
    
    assert root is not None, "Tree root should exist"
    assert not root.is_leaf, "Root should be internal node"
    print(f"  Root node: {root.name}")
    print(f"  Left child: {root.left.name}")
    print(f"  Right child: {root.right.name}")
    
    # Test merge order
    merges = tree.get_merge_order()
    print(f"  Merge order: {merges}")
    
    print("✓ UPGMA tree tests passed")
    return True


def test_progressive_alignment():
    """Test progressive alignment."""
    print("\n" + "="*60)
    print("TEST 4: Progressive Alignment")
    print("="*60)
    
    from backend_api.bioinformatics.alignment.progressive import ProgressiveAligner
    
    aligner = ProgressiveAligner()
    
    # Test consensus
    alignment = ["ATCG", "ATCG", "ATCG"]
    consensus = aligner._get_consensus(alignment)
    assert consensus == "ATCG", f"Expected ATCG, got {consensus}"
    print(f"  Consensus (identical): {consensus}")
    
    # Test consensus with gaps
    alignment = ["AT-G", "ATCG", "AT-G"]
    consensus = aligner._get_consensus(alignment)
    assert len(consensus) == 4, "Consensus length should match alignment"
    print(f"  Consensus (with gaps): {consensus}")
    
    print("✓ Progressive alignment tests passed")
    return True


def test_distance_matrix():
    """Test distance matrix building."""
    print("\n" + "="*60)
    print("TEST 5: Distance Matrix")
    print("="*60)
    
    from backend_api.bioinformatics.alignment.tree import build_distance_matrix
    from backend_api.bioinformatics.alignment.pairwise import NeedlemanWunsch
    
    aligner = NeedlemanWunsch()
    sequences = ["ATCG", "ATCG", "TTTT"]
    
    matrix = build_distance_matrix(sequences, aligner.similarity_score)
    
    # Identical sequences should have small distance
    assert matrix[0][1] < 0.1, f"Identical sequences should have distance < 0.1, got {matrix[0][1]}"
    print(f"  Distance (identical): {matrix[0][1]:.3f}")
    
    # Different sequences should have larger distance
    assert matrix[0][2] >= 0.3, f"Different sequences should have distance >= 0.3, got {matrix[0][2]}"
    print(f"  Distance (different): {matrix[0][2]:.3f}")
    
    # Matrix should be symmetric
    assert matrix[0][1] == matrix[1][0], "Distance matrix should be symmetric"
    
    print("✓ Distance matrix tests passed")
    return True


def test_msa_service():
    """Test high-level MSA service."""
    print("\n" + "="*60)
    print("TEST 6: MSA Service")
    print("="*60)
    
    from backend_api.bioinformatics.services.msa_service import MSAService
    
    service = MSAService()
    
    # Test validation
    is_valid, msg = service.validate_sequences([])
    assert not is_valid, "Empty sequences should fail validation"
    print(f"  Empty sequences validation: {msg}")
    
    is_valid, msg = service.validate_sequences(["ATCG"])
    assert not is_valid, "Single sequence should fail validation"
    print(f"  Single sequence validation: {msg}")
    
    is_valid, msg = service.validate_sequences(["ATCG", "ATCG"])
    assert is_valid, "Valid sequences should pass"
    print(f"  Valid sequences: passed")
    
    # Test alignment
    sequences = ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
    result = service.align(sequences)
    
    assert result['success'], f"Alignment should succeed: {result.get('error')}"
    assert len(result['alignment']) == 3, "Should have 3 aligned sequences"
    assert len(result['consensus']) > 0, "Should have consensus"
    assert len(result['identity_scores']) == 3, "Should have 3 identity scores"
    
    print(f"  Alignment successful")
    print(f"  Sequences: {len(result['alignment'])}")
    print(f"  Alignment length: {result['alignment_length']}")
    print(f"  Consensus: {result['consensus']}")
    print(f"  Identity scores: {result['identity_scores']}")
    print(f"  Alignment:")
    for i, seq in enumerate(result['alignment']):
        print(f"    {i+1}: {seq}")
    
    # Test with different sequences
    result = service.align(["AAAA", "TTTT", "CCCC", "GGGG"])
    assert result['success'], "Should handle diverse sequences"
    print(f"  Diverse sequences alignment: success")
    
    print("✓ MSA Service tests passed")
    return True


def test_fasta_parsing():
    """Test FASTA input parsing."""
    print("\n" + "="*60)
    print("TEST 7: FASTA Parsing")
    print("="*60)
    
    from backend_api.bioinformatics.services.msa_service import MSAService
    
    service = MSAService()
    
    fasta = """>sequence_1
ATCGTACG
>sequence_2
ATGGTACG
>sequence_3
ATCGTTCG"""
    
    result = service.align_fasta(fasta)
    
    assert result['success'], f"FASTA alignment should succeed: {result.get('error')}"
    assert len(result['alignment']) == 3, "Should parse 3 sequences"
    print(f"  FASTA parsing: {len(result['alignment'])} sequences parsed")
    print(f"  Consensus: {result['consensus']}")
    
    print("✓ FASTA parsing tests passed")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MSA IMPLEMENTATION - STANDALONE TESTS")
    print("="*60)
    
    tests = [
        test_scoring_matrix,
        test_needleman_wunsch,
        test_upgma_tree,
        test_progressive_alignment,
        test_distance_matrix,
        test_msa_service,
        test_fasta_parsing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed! MSA implementation is working correctly.")
        print("\nNext steps:")
        print("1. Run: python manage.py runserver")
        print("2. Test endpoints at http://localhost:8000/api/msa/")
        print("3. Review MSA_DOCUMENTATION.md for complete API reference")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
