"""
Django REST Framework serializers for MSA API.
Handles input/output validation and serialization.
"""

from rest_framework import serializers
from typing import List


class MSARequestSerializer(serializers.Serializer):
    """
    Serializer for MSA API request.
    Validates input sequences and scoring parameters.
    """
    
    sequences = serializers.ListField(
        child=serializers.CharField(
            max_length=10000,
            help_text="DNA sequence (A, T, C, G only)"
        ),
        min_length=2,
        max_length=50,
        help_text="List of DNA sequences to align (2-50 sequences)"
    )
    
    match = serializers.IntegerField(
        default=1,
        required=False,
        help_text="Score for matching bases (typically positive)"
    )
    
    mismatch = serializers.IntegerField(
        default=-1,
        required=False,
        help_text="Score for mismatched bases (typically negative)"
    )
    
    gap = serializers.IntegerField(
        default=-2,
        required=False,
        help_text="Cost per gap position (typically negative)"
    )
    
    fasta = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Alternative input: FASTA format sequences"
    )
    
    def validate_sequences(self, sequences):
        """Validate sequences list."""
        if not sequences:
            raise serializers.ValidationError("Sequences list cannot be empty")
        
        for i, seq in enumerate(sequences):
            if not isinstance(seq, str):
                raise serializers.ValidationError(f"Sequence {i} must be a string")
            
            if len(seq.strip()) == 0:
                raise serializers.ValidationError(f"Sequence {i} cannot be empty")
            
            # Check DNA alphabet (allow lowercase)
            valid_chars = set('ATCGATCG')  # Add lowercase variants
            if not all(c.upper() in valid_chars for c in seq):
                raise serializers.ValidationError(
                    f"Sequence {i} contains invalid characters. Use only A, T, C, G"
                )
        
        return sequences
    
    def validate(self, data):
        """Validate entire request."""
        # If FASTA provided, use that instead
        fasta = data.get('fasta', '').strip()
        if fasta:
            # Parse FASTA and update sequences
            sequences = []
            current_seq = ""
            
            for line in fasta.split('\n'):
                line = line.strip()
                if not line:
                    continue
                if line.startswith('>'):
                    if current_seq:
                        sequences.append(current_seq)
                    current_seq = ""
                else:
                    current_seq += line
            
            if current_seq:
                sequences.append(current_seq)
            
            if sequences:
                data['sequences'] = sequences
        
        # Validate scoring parameters
        if data.get('match', 1) == 0:
            raise serializers.ValidationError(
                "Match score cannot be zero"
            )
        
        return data


class MSAResponseSerializer(serializers.Serializer):
    """
    Serializer for MSA API response.
    Includes alignment, consensus, and identity scores.
    """
    
    success = serializers.BooleanField(
        help_text="Whether alignment was successful"
    )
    
    alignment = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of aligned sequences"
    )
    
    consensus = serializers.CharField(
        help_text="Consensus sequence derived from alignment"
    )
    
    identity_scores = serializers.ListField(
        child=serializers.FloatField(),
        help_text="Identity percentage for each sequence (0-100)"
    )
    
    method = serializers.CharField(
        help_text="MSA method used (progressive_msa)"
    )
    
    num_sequences = serializers.IntegerField(
        required=False,
        help_text="Number of sequences aligned"
    )
    
    alignment_length = serializers.IntegerField(
        required=False,
        help_text="Length of aligned sequences"
    )
    
    error = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Error message if alignment failed"
    )


class FASTAInputSerializer(serializers.Serializer):
    """Serializer for FASTA format input."""
    
    fasta_content = serializers.CharField(
        help_text="FASTA format sequences (>header\\nsequence...)"
    )
    
    match = serializers.IntegerField(default=1, required=False)
    mismatch = serializers.IntegerField(default=-1, required=False)
    gap = serializers.IntegerField(default=-2, required=False)


class AlignmentStatisticsSerializer(serializers.Serializer):
    """Serializer for alignment statistics."""
    
    average_identity = serializers.FloatField(
        help_text="Average identity across all sequences"
    )
    
    min_identity = serializers.FloatField(
        help_text="Minimum identity score"
    )
    
    max_identity = serializers.FloatField(
        help_text="Maximum identity score"
    )
    
    num_sequences = serializers.IntegerField(
        help_text="Number of sequences in alignment"
    )
    
    alignment_length = serializers.IntegerField(
        help_text="Length of aligned sequences"
    )
    
    consensus_gc_content = serializers.FloatField(
        help_text="GC content percentage of consensus"
    )
