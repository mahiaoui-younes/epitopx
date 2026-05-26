"""
Django REST Framework views for MSA API.
Handles HTTP endpoints and request/response processing.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .serializers import (
    MSARequestSerializer,
    MSAResponseSerializer,
    FASTAInputSerializer,
    AlignmentStatisticsSerializer,
)
from ..services import MSAService
from ..services.msa_analysis import run_pipeline
import statistics


class MSAViewSet(viewsets.ViewSet):
    """
    ViewSet for Multiple Sequence Alignment operations.
    
    Provides REST endpoints for:
    - Multiple sequence alignment
    - FASTA input parsing
    - Alignment statistics
    """
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'], url_path='align')
    def align(self, request):
        """
        Perform multiple sequence alignment.
        
        POST /api/msa/align/
        
        Request body:
        {
            "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"],
            "match": 1,
            "mismatch": -1,
            "gap": -2
        }
        
        Response:
        {
            "success": true,
            "alignment": ["ATCGTACG-", "AT-GTACG-", "ATCGTTCG-"],
            "consensus": "ATCGTACG",
            "identity_scores": [95.2, 90.1, 88.5],
            "method": "progressive_msa",
            "num_sequences": 3,
            "alignment_length": 9
        }
        """
        serializer = MSARequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Invalid request data',
                    'details': serializer.errors,
                    'alignment': [],
                    'consensus': '',
                    'identity_scores': [],
                    'method': 'progressive_msa'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract validated data
        sequences = serializer.validated_data.get('sequences', [])
        match = serializer.validated_data.get('match', 1)
        mismatch = serializer.validated_data.get('mismatch', -1)
        gap = serializer.validated_data.get('gap', -2)
        
        # Perform alignment
        service = MSAService(match, mismatch, gap)
        result = service.align(sequences)
        
        # Prepare response
        response_serializer = MSAResponseSerializer(result)
        
        if result.get('success'):
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                response_serializer.data,
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='align-fasta')
    def align_fasta(self, request):
        """
        Perform alignment with FASTA format input.
        
        POST /api/msa/align-fasta/
        
        Request body:
        {
            "fasta_content": ">seq1\\nATCGTACG\\n>seq2\\nATGGTACG\\n>seq3\\nATCGTTCG",
            "match": 1,
            "mismatch": -1,
            "gap": -2
        }
        """
        serializer = FASTAInputSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': 'Invalid FASTA input',
                    'details': serializer.errors,
                    'alignment': [],
                    'consensus': '',
                    'identity_scores': [],
                    'method': 'progressive_msa'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fasta_content = serializer.validated_data.get('fasta_content', '')
        match = serializer.validated_data.get('match', 1)
        mismatch = serializer.validated_data.get('mismatch', -1)
        gap = serializer.validated_data.get('gap', -2)
        
        # Perform alignment
        service = MSAService(match, mismatch, gap)
        result = service.align_fasta(fasta_content)
        
        response_serializer = MSAResponseSerializer(result)
        
        if result.get('success'):
            return Response(
                response_serializer.data,
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                response_serializer.data,
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='statistics')
    def statistics(self, request):
        """
        Get statistics about an alignment.
        
        POST /api/msa/statistics/
        
        Request body: Same as /align/
        
        Response includes:
        - Average, min, max identity scores
        - Alignment length
        - Consensus GC content
        """
        serializer = MSARequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sequences = serializer.validated_data.get('sequences', [])
        match = serializer.validated_data.get('match', 1)
        mismatch = serializer.validated_data.get('mismatch', -1)
        gap = serializer.validated_data.get('gap', -2)
        
        # Perform alignment
        service = MSAService(match, mismatch, gap)
        result = service.align(sequences)
        
        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'Alignment failed')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate statistics
        identity_scores = result.get('identity_scores', [])
        consensus = result.get('consensus', '')
        
        if identity_scores:
            avg_identity = statistics.mean(identity_scores)
            min_identity = min(identity_scores)
            max_identity = max(identity_scores)
        else:
            avg_identity = min_identity = max_identity = 0.0
        
        # Calculate GC content of consensus
        gc_count = consensus.count('G') + consensus.count('C')
        gc_content = (gc_count / len(consensus) * 100) if consensus else 0.0
        
        stats = {
            'average_identity': round(avg_identity, 1),
            'min_identity': round(min_identity, 1),
            'max_identity': round(max_identity, 1),
            'num_sequences': result.get('num_sequences', 0),
            'alignment_length': result.get('alignment_length', 0),
            'consensus_gc_content': round(gc_content, 1)
        }
        
        stats_serializer = AlignmentStatisticsSerializer(stats)
        return Response(stats_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='analyze')
    def analyze(self, request):
        """
        Full MSA analysis pipeline (Python / Biopython-powered).

        POST /api/msa/analyze/

        Request body:
        {
            "fasta":        "<aligned multi-FASTA string>",
            "ref_index":    0,              // index of reference sequence (default 0)
            "tree_method":  "nj"            // "nj" | "me" | "ml"  (default "nj")
        }

        Response contains:
          records, validation, snp_result, haplotypes, distance_matrix,
          jc_matrix, tree, population_genetics, viz, summary
        """
        fasta_text  = request.data.get('fasta', '')
        ref_index   = int(request.data.get('ref_index', 0))
        tree_method = str(request.data.get('tree_method', 'nj')).lower()

        if not fasta_text:
            return Response(
                {'error': 'fasta field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if tree_method not in ('nj', 'me', 'ml'):
            tree_method = 'nj'

        result = run_pipeline(fasta_text, ref_index, tree_method)

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class MSAHealthView(APIView):
    """Health check endpoint for MSA service."""
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        GET /api/msa/health/
        Returns service status and version information.
        """
        return Response({
            'status': 'healthy',
            'service': 'Multiple Sequence Alignment API',
            'version': '1.0.0',
            'algorithm': 'Progressive MSA with UPGMA guide tree',
            'max_sequences': 50,
            'max_sequence_length': 10000,
            'supported_formats': ['raw JSON', 'FASTA']
        }, status=status.HTTP_200_OK)
