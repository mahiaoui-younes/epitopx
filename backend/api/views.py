import logging
from datetime import datetime
import statistics

from django.contrib.auth import authenticate, get_user_model
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Article, DNASequence, ProteinConversion, Protein, Epitope
from .bio_utils import translate_dna, translate_all_six_frames, protein_stats, compute_similarity
from .permissions import IsOwnerOrAdmin
from .serializers import (
    ArticleSerializer,
    DNASequenceSerializer,
    ProteinConversionSerializer,
    ProteinSerializer,
    ConversionRequestSerializer,
    ConversionResponseSerializer,
    EpitopeAnalysisRequestSerializer,
    EpitopeFullSerializer,
    EpitopeListSerializer,
    EpitopeSerializer,
    UserRegisterSerializer,
    UserLoginSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    SubscriptionSerializer,
)
from .throttles import AuthRateThrottle, AnalysisRateThrottle
from .services import (
    register_user, login_user, logout_user,
    request_password_reset, confirm_password_reset, verify_email,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def dna_to_rna(dna):
    """Convert DNA to RNA (T -> U)"""
    return dna.upper().replace('T', 'U')


def rna_to_protein(rna):
    """Convert RNA to Protein using genetic code"""
    rna = rna.upper()
    protein = ""
    for i in range(0, len(rna) - 2, 3):
        codon = rna[i:i+3]
        if len(codon) == 3 and codon in GENETIC_CODE:
            protein += GENETIC_CODE[codon]
    return protein


def dna_to_protein(dna):
    """Convert DNA to Protein via RNA"""
    rna = dna_to_rna(dna)
    return rna_to_protein(rna)


class ArticleViewSet(viewsets.ModelViewSet):
    """Articles — read-only for authenticated users, write for admins."""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsAuthenticated]


class DNASequenceViewSet(viewsets.ModelViewSet):
    """DNA sequences — requires authentication."""
    queryset = DNASequence.objects.all()
    serializer_class = DNASequenceSerializer
    permission_classes = [IsAuthenticated]


class ProteinConversionViewSet(viewsets.ViewSet):
    """Convert DNA sequences to RNA and Protein"""

    @action(detail=False, methods=['post'])
    def convert(self, request):
        """Convert DNA sequence to RNA and Protein"""
        serializer = ConversionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dna = serializer.validated_data['dna_sequence']

        # Validate DNA sequence
        if not all(c in 'ATGCatgc' for c in dna):
            return Response(
                {'error': 'Invalid DNA sequence. Only A, T, G, C allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rna = dna_to_rna(dna)
        protein = rna_to_protein(rna)

        # Save conversion to database
        conversion = ProteinConversion.objects.create(
            original_dna=dna,
            rna=rna,
            protein=protein
        )

        response_data = {
            'dna': dna,
            'rna': rna,
            'protein': protein,
            'id': conversion.id
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def convert_large(self, request):
        """Convert large DNA sequence using form-data (better for long sequences)"""
        dna = request.POST.get('dna_sequence', '').strip()
        
        if not dna:
            return Response(
                {'error': 'dna_sequence is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate DNA sequence (remove whitespace and newlines)
        dna_clean = ''.join(dna.split())
        
        if not all(c in 'ATGCatgc' for c in dna_clean):
            return Response(
                {'error': 'Invalid DNA sequence. Only A, T, G, C allowed (spaces and newlines are removed)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rna = dna_to_rna(dna_clean)
        protein = rna_to_protein(rna)

        # Save conversion to database
        conversion = ProteinConversion.objects.create(
            original_dna=dna_clean,
            rna=rna,
            protein=protein
        )

        response_data = {
            'dna_length': len(dna_clean),
            'rna_length': len(rna),
            'protein_length': len(protein),
            'dna': dna_clean,
            'rna': rna,
            'protein': protein,
            'id': conversion.id
        }

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get conversion history"""
        conversions = ProteinConversion.objects.all().order_by('-created_at')
        serializer = ProteinConversionSerializer(conversions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search for DNA sequence in database"""
        dna = request.POST.get('dna_sequence', '').strip()
        
        if not dna:
            return Response(
                {'error': 'dna_sequence is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clean DNA sequence (remove whitespace and newlines)
        dna_clean = ''.join(dna.split())
        
        if not all(c in 'ATGCatgc' for c in dna_clean):
            return Response(
                {'error': 'Invalid DNA sequence. Only A, T, G, C allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Search for exact match in database
        existing = DNASequence.objects.filter(sequence=dna_clean).first()
        
        if existing:
            return Response({
                'found': True,
                'message': 'Sequence found',
                'id': existing.id,
                'name': existing.name,
                'sequence_length': len(dna_clean)
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'found': False,
                'message': 'Sequence not found in database'
            }, status=status.HTTP_200_OK)


class DNASequenceViewSet(viewsets.ModelViewSet):
    queryset = DNASequence.objects.all()
    serializer_class = DNASequenceSerializer

    @action(detail=False, methods=['post'])
    def add_sequence(self, request):
        """Add a new DNA sequence to the database"""
        dna = request.POST.get('dna_sequence', '').strip()
        name = request.POST.get('name', 'Unknown sequence').strip()
        
        if not dna:
            return Response(
                {'error': 'dna_sequence is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not name:
            return Response(
                {'error': 'name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clean DNA sequence (remove whitespace and newlines)
        dna_clean = ''.join(dna.split())
        
        if not all(c in 'ATGCatgc' for c in dna_clean):
            return Response(
                {'error': 'Invalid DNA sequence. Only A, T, G, C allowed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if sequence already exists
        existing = DNASequence.objects.filter(sequence=dna_clean).first()
        if existing:
            return Response({
                'error': 'This sequence already exists',
                'id': existing.id,
                'name': existing.name
            }, status=status.HTTP_400_BAD_REQUEST)

        # Add new sequence
        new_sequence = DNASequence.objects.create(
            name=name,
            sequence=dna_clean
        )
        
        return Response({
            'message': 'Sequence added successfully',
            'id': new_sequence.id,
            'name': new_sequence.name,
            'sequence_length': len(dna_clean)
        }, status=status.HTTP_201_CREATED)


# ============================================================================
# USER AUTHENTICATION VIEWSET
# ============================================================================

class UserViewSet(viewsets.ViewSet):
    """User authentication & account management endpoints."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], throttle_classes=[AuthRateThrottle])
    def register(self, request):
        """Register a new user account."""
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = register_user(
                username=serializer.validated_data['username'],
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'user':    UserSerializer(result['user']).data,
            'token':   result['token'],
            'message': 'Registration successful. Please verify your email.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], throttle_classes=[AuthRateThrottle])
    def login(self, request):
        """Authenticate and return an auth token."""
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'error': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = login_user(username, password)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({
            'user':     UserSerializer(result['user']).data,
            'token':    result['token'],
            'is_admin': result['user'].is_admin,
            'message':  'Login successful',
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Invalidate current session token."""
        logout_user(request.user)
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Return or update the authenticated user's profile."""
        from .models import Subscription
        user = request.user

        if request.method == 'PATCH':
            allowed = {'email', 'first_name', 'last_name'}
            data = {k: v for k, v in request.data.items() if k in allowed}
            serializer = UserSerializer(user, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        data = UserSerializer(user).data
        try:
            sub = user.subscription
            data['subscription'] = SubscriptionSerializer(sub).data
        except Subscription.DoesNotExist:
            data['subscription'] = None
        return Response(data)

    @action(detail=False, methods=['post'], throttle_classes=[AuthRateThrottle])
    def password_reset(self, request):
        """Request a password-reset email."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data['email'])
        return Response({'message': 'If that email exists, a reset link has been sent.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='password-reset-confirm')
    def password_reset_confirm(self, request):
        """Confirm password reset with token and new password."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(
                token_str=serializer.validated_data['token'],
                new_password=serializer.validated_data['password'],
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='verify-email')
    def verify_email_action(self, request):
        """Confirm email address with one-time token."""
        token = request.data.get('token', '')
        try:
            verify_email(token)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)


# ============================================================================
# PROTEIN VIEWSET
# ============================================================================

class ProteinViewSet(viewsets.ModelViewSet):
    """Protein management with user permissions"""
    serializer_class = ProteinSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        - Admins see all proteins.
        - Authenticated users see public proteins + their own.
        """
        user = self.request.user
        base_qs = Protein.objects.select_related('created_by').annotate(
            epitope_count=Count('epitopes')
        ).order_by('-created_at')
        if getattr(user, 'is_admin', False):
            return base_qs.all()
        return base_qs.filter(is_public=True) | base_qs.filter(created_by=user)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def public_list(self, request):
        """List all PUBLIC proteins (no authentication required)"""
        proteins = Protein.objects.filter(is_public=True).order_by('-created_at')
        serializer = self.get_serializer(proteins, many=True)
        return Response({
            'count': proteins.count(),
            'message': 'Public proteins (no token required)',
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_proteins(self, request):
        """List user's own proteins + public proteins (authentication required)"""
        user = request.user
        if user.is_admin:
            proteins = Protein.objects.all().order_by('-created_at')
        else:
            proteins = Protein.objects.filter(
                is_public=True
            ) | Protein.objects.filter(
                created_by=user
            )
        proteins = proteins.order_by('-created_at')
        serializer = self.get_serializer(proteins, many=True)
        return Response({
            'count': proteins.count(),
            'username': user.username,
            'is_admin': user.is_admin,
            'message': 'Your visible proteins (authenticated)',
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def all_proteins(self, request):
        """List ALL proteins - ADMIN ONLY (authentication required)"""
        user = request.user
        if not user.is_admin:
            return Response({
                'error': 'Only admins can access all proteins'
            }, status=status.HTTP_403_FORBIDDEN)
        
        proteins = Protein.objects.all().order_by('-created_at')
        serializer = self.get_serializer(proteins, many=True)
        return Response({
            'count': proteins.count(),
            'message': 'All proteins (admin access)',
            'admin': user.username,
            'results': serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_own(self, request):
        """List ONLY proteins created by current user (no public proteins)"""
        user = request.user
        
        # Get only proteins created by this user
        proteins = Protein.objects.filter(created_by=user).order_by('-created_at')
        serializer = self.get_serializer(proteins, many=True)
        return Response({
            'count': proteins.count(),
            'username': user.username,
            'message': 'Only proteins you created',
            'results': serializer.data
        })
    
    def perform_create(self, serializer):
        """Auto-assign created_by and is_public based on user role"""
        user = self.request.user
        
        # Admin proteins are public, user proteins are private
        is_public = user.is_admin
        serializer.save(created_by=user, is_public=is_public)
    
    def perform_update(self, serializer):
        """Only owner or admin can update."""
        protein = self.get_object()
        user = self.request.user
        if protein.created_by != user and not user.is_admin:
            raise PermissionDenied('You can only edit your own proteins.')
        serializer.save()

    def perform_destroy(self, instance):
        """Only owner or admin can delete."""
        user = self.request.user
        if instance.created_by != user and not user.is_admin:
            raise PermissionDenied('You can only delete your own proteins.')
        instance.delete()


class EpitopeAnalysisViewSet(viewsets.ModelViewSet):
    """
    ViewSet for B-cell epitope prediction using EpiTop1.
    
    Supports multiple analysis methods:
    - core: 5 core methods (Hopp & Woods, Kyte & Doolittle, Karplus & Schulz, Emini, Kolaskar)
    - bio: 7 bio methods (core + Parker, Chou & Fasman)
    - iedb: IEDB Tools API integration
    
    NOTE: analyze() action allows unauthenticated access (AllowAny)
    """
    queryset = Epitope.objects.all()
    serializer_class = EpitopeFullSerializer
    permission_classes = [IsAuthenticated]  # Default for other actions
    
    def get_serializer_class(self):
        """Use appropriate serializer based on action"""
        if self.action == 'list':
            return EpitopeListSerializer
        elif self.action == 'create':
            return EpitopeAnalysisRequestSerializer
        return EpitopeFullSerializer
    
    def _calculate_amino_acid_composition(self, sequence):
        """Calculate amino acid composition statistics"""
        sequence_upper = sequence.upper()
        
        hydrophilic = {'E', 'D', 'K', 'R', 'Q', 'N', 'S'}
        hydrophobic = {'L', 'I', 'V', 'F', 'W'}
        charged = {'D', 'E', 'K', 'R', 'H'}
        
        hydrophilic_count = sum(1 for aa in sequence_upper if aa in hydrophilic)
        hydrophobic_count = sum(1 for aa in sequence_upper if aa in hydrophobic)
        charged_count = sum(1 for aa in sequence_upper if aa in charged)
        
        seq_len = len(sequence_upper)
        
        return {
            'hydrophilic': {
                'count': hydrophilic_count,
                'percentage': round(100 * hydrophilic_count / seq_len, 1) if seq_len > 0 else 0,
                'residues': 'EDKRQNS'
            },
            'hydrophobic': {
                'count': hydrophobic_count,
                'percentage': round(100 * hydrophobic_count / seq_len, 1) if seq_len > 0 else 0,
                'residues': 'LIVFW'
            },
            'charged': {
                'count': charged_count,
                'percentage': round(100 * charged_count / seq_len, 1) if seq_len > 0 else 0,
                'residues': 'DEKRH'
            }
        }
    
    def _calculate_residue_statistics(self, residue_scores):
        """Calculate statistics from residue scores"""
        if not residue_scores:
            return {}
        
        scores = [rs.get('global_score', 0) for rs in residue_scores if isinstance(rs, dict) and 'global_score' in rs]
        
        if not scores:
            scores = [0] * len(residue_scores)
        
        exposed_count = len([s for s in scores if s > 0])
        
        return {
            'mean_global_score': round(sum(scores) / len(scores), 4) if scores else 0,
            'median': round(statistics.median(scores), 4) if scores else 0,
            'std_deviation': round(statistics.stdev(scores), 4) if len(scores) > 1 else 0,
            'min': round(min(scores), 4) if scores else 0,
            'max': round(max(scores), 4) if scores else 0,
            'exposed_residues': f"{exposed_count}/{len(residue_scores)} ({round(100*exposed_count/len(residue_scores), 1)}%)" if residue_scores else "0/0 (0%)"
        }
    
    def _format_epitopes_table(self, epitopes):
        """
        Format epitopes as a formatted ASCII table like:
        Top candidates:
          Rank         Pos   Len   Score Sequence
          ----
          1      156-180    25   0.7651  GKESKSDHDKRPKDKKPFVPKTSQC
        """
        if not epitopes:
            return "No epitopes found"
        
        lines = ["Top candidates:"]
        lines.append("  Rank         Pos   Len   Score Sequence")
        lines.append("  " + "-" * 60)
        
        for rank, epitope in enumerate(epitopes, 1):
            start = epitope['start']
            end = epitope['end']
            length = epitope['length']
            score = epitope['score']
            sequence = epitope['sequence']
            
            # Format: Rank, Position range, Length, Score, Sequence
            line = f"  {rank:4d}      {start}-{end}    {length:2d}   {score:.4f}  {sequence}"
            lines.append(line)
        
        return "\n".join(lines)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def analyze(self, request):
        """
        Perform epitope analysis on a protein sequence (NO AUTHENTICATION REQUIRED).
        
        Parameters:
            - sequence: Protein sequence (FASTA or raw)
            - method: 'core', 'bio', or 'iedb' (default: 'core')
            - protein_id: Optional ID of existing protein to associate epitopes with (if not provided, creates new protein)
            - min_length: Minimum epitope length (default: 9)
            - max_length: Maximum epitope length (default: 20)
            - min_score: Minimum epitope score 0-1 (default: 0.5)
            - top_n: Number of top epitopes to return (default: 20)
            - pdb_file: Optional PDB structure file
            - chain_id: PDB chain ID (default: 'A')
        """
        serializer = EpitopeAnalysisRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse and validate sequence
        sequence_input = serializer.validated_data['sequence']
        method = serializer.validated_data['method']
        min_length = serializer.validated_data['min_length']
        max_length = serializer.validated_data['max_length']
        min_score = serializer.validated_data['min_score']
        top_n = serializer.validated_data['top_n']
        pdb_file = serializer.validated_data.get('pdb_file')
        chain_id = serializer.validated_data.get('chain_id', 'A')
        protein_id = serializer.validated_data.get('protein_id')

        try:
            # Import EpiTop1 modules with careful handling of sys.path and sys.modules
            import sys
            import os
            from pathlib import Path
            
            epitop1_path = Path(__file__).resolve().parent.parent / 'epitop1'
            
            # Temporarily remove Django's config from sys.modules to avoid ImportError
            django_config = sys.modules.pop('config', None)
            
            # Add epitop1 to sys.path
            sys.path.insert(0, str(epitop1_path))
            
            try:
                from io_utils import parse_sequence_input
                from core.scoring import GlobalScorer
                from core.epitope_selector import EpitopeSelector
                from core.hydrophobicity import KyteDoolittlePredictor
                from config import EPITOPE_CRITERIA
                import numpy as np

                # Parse sequence
                header, sequence = parse_sequence_input(sequence_input)
                
                # Validate sequence (should be amino acids)
                if not all(c in 'ACDEFGHIKLMNPQRSTVWYBZJOUX*-' for c in sequence.upper()):
                    return Response(
                        {'error': 'Invalid protein sequence. Contains invalid amino acid characters.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                sequence = sequence.upper()

                # Parse PDB if provided
                structural_sasa = None
                excluded_regions = []
                
                if pdb_file:
                    try:
                        from structure.pdb_parser import PDBParser
                        
                        # Save uploaded PDB temporarily
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdb') as tmp:
                            for chunk in pdb_file.chunks():
                                tmp.write(chunk)
                            pdb_path = tmp.name
                        
                        pdb_parser = PDBParser(probe_radius=1.4, n_sasa_points=92)
                        pdb_parser.parse(pdb_path, chain_id=chain_id or 'A')
                        pdb_parser.compute_sasa()
                        
                        pdb_seq = pdb_parser.get_sequence()
                        if pdb_seq:
                            alignment = pdb_parser.align_to_sequence(sequence)
                            structural_sasa = np.zeros(len(sequence))
                            for seq_pos, pdb_idx in alignment.items():
                                if pdb_idx < len(pdb_parser.residues):
                                    structural_sasa[seq_pos] = pdb_parser.residues[pdb_idx].relative_sasa
                        
                        # Clean up temp file
                        os.unlink(pdb_path)
                    except Exception as e:
                        return Response(
                            {'error': f'PDB parsing error: {str(e)}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                # Compute epitope analysis based on method
                if method == 'core':
                    epitopes, residue_scores = self._run_core_analysis(
                        sequence, structural_sasa, excluded_regions,
                        min_length, max_length, min_score, top_n
                    )
                elif method == 'bio':
                    epitopes, residue_scores = self._run_bio_analysis(
                        sequence, structural_sasa, excluded_regions,
                        min_length, max_length, min_score, top_n
                    )
                elif method == 'iedb':
                    epitopes, residue_scores = self._run_iedb_analysis(
                        sequence, excluded_regions,
                        min_length, max_length, min_score, top_n
                    )
                else:
                    return Response(
                        {'error': f'Unknown method: {method}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Get existing protein or create new one
                if protein_id:
                    try:
                        protein_obj = Protein.objects.get(id=protein_id)
                        # Update sequence/method if provided
                        if sequence:
                            protein_obj.sequence = sequence
                        if method:
                            protein_obj.method = method
                        protein_obj.save()
                    except Protein.DoesNotExist:
                        return Response(
                            {'error': f'Protein with ID {protein_id} not found'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                else:
                    # Create new protein
                    protein_obj, created = Protein.objects.get_or_create(
                        name=header or f"Analyzed_Sequence_{len(sequence)}_aa",
                        defaults={
                            'sequence': sequence,
                            'organism': serializer.validated_data.get('organism', ''),
                            'method': method,
                        }
                    )

                # Save each individual epitope linked to the protein
                created_epitopes = []
                epitope_id_counter = 1  # Simple epitope_id counter
                
                for epitope_data in epitopes:
                    epitope_obj, _ = Epitope.objects.get_or_create(
                        protein=protein_obj,
                        epitope_sequence=epitope_data['sequence'],
                        start=epitope_data['start'],
                        end=epitope_data['end'],
                        defaults={
                            'epitope_id': epitope_id_counter,
                            'method': method,
                            'length': epitope_data['length'],
                            'score': epitope_data['score'],
                            'hopp_woods': epitope_data.get('hopp_woods'),
                            'kyte_doolittle': epitope_data.get('kyte_doolittle'),
                            'karplus_schulz': epitope_data.get('karplus_schulz'),
                            'emini': epitope_data.get('emini'),
                            'kolaskar': epitope_data.get('kolaskar'),
                        }
                    )
                    created_epitopes.append(epitope_obj)
                    epitope_id_counter += 1

                # Calculate statistics
                residue_stats = self._calculate_residue_statistics(residue_scores)
                aa_composition = self._calculate_amino_acid_composition(sequence)
                
                # Prepare detailed response
                analysis_result = {
                    'timestamp': datetime.now().isoformat(),
                    'protein_id': protein_obj.id,
                    'method': method,
                    
                    # SEQUENCE INFORMATION
                    'sequence_information': {
                        'header': header or f'Analyzed_Sequence_{len(sequence)}_aa',
                        'length': f'{len(sequence)} residues',
                        'pdb': 'Not provided' if not pdb_file else f'Provided (Chain {chain_id})',
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    },
                    
                    # CORE/BIO MODULE RESULTS
                    'module_results': {
                        'methods': 'Hopp-Woods, Kyte-Doolittle, Karplus-Schulz, Emini, Kolaskar' if method == 'core' else 
                                  'Parker, Emini, K-S, Chou-Fasman, K-T, BepiPred-1.0, Levitt, Welling' if method == 'bio' else 
                                  'IEDB Tools API',
                        'epitopes_found': len(epitopes),
                        'top_candidates': self._format_epitopes_table(epitopes[:top_n])
                    },
                    
                    # RESIDUE SCORE STATISTICS
                    'residue_statistics': {
                        'mean_global_score': residue_stats.get('mean_global_score', 0),
                        'median': residue_stats.get('median', 0),
                        'std_deviation': residue_stats.get('std_deviation', 0),
                        'min': residue_stats.get('min', 0),
                        'max': residue_stats.get('max', 0),
                        'exposed_residues': residue_stats.get('exposed_residues', '0/0 (0%)')
                    },
                    
                    # AMINO ACID COMPOSITION
                    'amino_acid_composition': {
                        'hydrophilic': f"{aa_composition['hydrophilic']['count']}/{len(sequence)} ({aa_composition['hydrophilic']['percentage']}%)",
                        'hydrophobic': f"{aa_composition['hydrophobic']['count']}/{len(sequence)} ({aa_composition['hydrophobic']['percentage']}%)",
                        'charged': f"{aa_composition['charged']['count']}/{len(sequence)} ({aa_composition['charged']['percentage']}%)"
                    },
                    
                    # Detailed epitope list
                    'epitopes': EpitopeListSerializer(created_epitopes[:top_n], many=True).data,
                    'epitope_count': len(created_epitopes),
                    'message': 'Analysis completed successfully'
                }

                return Response(analysis_result, status=status.HTTP_201_CREATED)

            finally:
                # Cleanup: restore sys.path and sys.modules
                if str(epitop1_path) in sys.path:
                    sys.path.remove(str(epitop1_path))
                if django_config:
                    sys.modules['config'] = django_config
        
        except Exception:
            logger.exception("Epitope analysis failed [rid=%s]", getattr(request, 'request_id', '-'))
            return Response(
                {'error': 'Analysis failed due to an internal error. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _run_core_analysis(self, sequence, structural_sasa, excluded_regions,
                          min_length, max_length, min_score, top_n):
        """Run core module analysis (5 methods)"""
        import sys
        from pathlib import Path
        
        epitop1_path = Path(__file__).resolve().parent.parent / 'epitop1'
        
        # Temporarily remove Django's config from sys.modules
        django_config = sys.modules.pop('config', None)
        sys.path.insert(0, str(epitop1_path))
        
        try:
            from core.scoring import GlobalScorer
            from core.epitope_selector import EpitopeSelector
            from core.hydrophobicity import KyteDoolittlePredictor
            from config import EPITOPE_CRITERIA
            import numpy as np

            scorer = GlobalScorer()
            residue_scores_obj = scorer.get_residue_scores(sequence, structural_sasa)

            # Detect TM regions
            kd = KyteDoolittlePredictor(window_size=11)
            tm_regions = kd.detect_transmembrane_regions(sequence)
            for tm in tm_regions:
                excluded_regions.append((tm["start"], tm["end"]))

            # Select epitopes
            criteria = dict(EPITOPE_CRITERIA)
            criteria["min_length"] = min_length
            criteria["max_length"] = max_length
            criteria["min_global_score"] = min_score
            criteria["top_n_epitopes"] = top_n

            selector = EpitopeSelector(criteria=criteria)
            epitopes_obj = selector.find_epitopes(sequence, residue_scores_obj, excluded_regions)

            # Format epitopes for response
            epitopes = [
                {
                    'start': e.start,
                    'end': e.end,
                    'sequence': e.sequence,
                    'length': e.length,
                    'score': float(e.global_score),
                    'hopp_woods': float(e.hopp_woods) if hasattr(e, 'hopp_woods') else None,
                    'kyte_doolittle': float(e.kyte_doolittle) if hasattr(e, 'kyte_doolittle') else None,
                    'karplus_schulz': float(e.karplus_schulz) if hasattr(e, 'karplus_schulz') else None,
                    'emini': float(e.emini) if hasattr(e, 'emini') else None,
                    'kolaskar': float(e.kolaskar) if hasattr(e, 'kolaskar') else None,
                }
                for e in epitopes_obj
            ]

            # Format residue scores
            residue_scores = [
                {
                    'position': rs.position,
                    'amino_acid': rs.amino_acid,
                    'global_score': float(rs.global_score),
                    'hydrophilicity': float(rs.hydrophilicity),
                    'hydrophobicity': float(rs.hydrophobicity),
                    'flexibility': float(rs.flexibility),
                    'accessibility': float(rs.accessibility),
                    'antigenicity': float(rs.antigenicity),
                }
                for rs in residue_scores_obj
            ]

            return epitopes, residue_scores
        
        finally:
            # Cleanup
            if str(epitop1_path) in sys.path:
                sys.path.remove(str(epitop1_path))
            if django_config:
                sys.modules['config'] = django_config

    def _run_bio_analysis(self, sequence, structural_sasa, excluded_regions,
                         min_length, max_length, min_score, top_n):
        """Run bio module analysis (7 methods)"""
        # Import bio module components
        import sys
        from pathlib import Path
        
        epitop1_path = Path(__file__).resolve().parent.parent / 'epitop1'
        
        # Temporarily remove Django's config from sys.modules
        django_config = sys.modules.pop('config', None)
        sys.path.insert(0, str(epitop1_path))
        
        try:
            try:
                from bio.combined_scorer import BioModuleScorer
            except ImportError:
                # If bio module doesn't exist, fall back to core
                from core.scoring import GlobalScorer as BioModuleScorer
            
            from core.epitope_selector import EpitopeSelector
            from config import EPITOPE_CRITERIA
            
            # Use BioModuleScorer instead
            bio_scorer = BioModuleScorer()
            residue_scores_obj = bio_scorer.get_residue_scores(sequence, structural_sasa)

            criteria = dict(EPITOPE_CRITERIA)
            criteria["min_length"] = min_length
            criteria["max_length"] = max_length
            criteria["min_global_score"] = min_score
            criteria["top_n_epitopes"] = top_n

            selector = EpitopeSelector(criteria=criteria)
            epitopes_obj = selector.find_epitopes(sequence, residue_scores_obj, excluded_regions)

            epitopes = [
                {
                    'start': e.start,
                    'end': e.end,
                    'sequence': e.sequence,
                    'length': e.length,
                    'score': float(e.global_score),
                }
                for e in epitopes_obj
            ]

            residue_scores = [
                {
                    'position': rs.position,
                    'amino_acid': rs.amino_acid,
                    'global_score': float(rs.global_score),
                }
                for rs in residue_scores_obj
            ]

            return epitopes, residue_scores
        
        except Exception as e:
            raise RuntimeError(f"Bio analysis failed: {str(e)}")
        
        finally:
            # Cleanup
            if str(epitop1_path) in sys.path:
                sys.path.remove(str(epitop1_path))
            if django_config:
                sys.modules['config'] = django_config


# ============================================================================
# BIOINFORMATICS VIEWSET
# ============================================================================

class BioinformaticsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def translate(self, request):
        sequence = request.data.get('sequence', '')
        if not sequence:
            return Response({'error': 'sequence is required'}, status=status.HTTP_400_BAD_REQUEST)
        result = translate_dna(str(sequence))
        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='six-frames')
    def six_frames(self, request):
        sequence = request.data.get('sequence', '')
        if not sequence:
            return Response({'error': 'sequence is required'}, status=status.HTTP_400_BAD_REQUEST)
        frames = translate_all_six_frames(str(sequence))
        return Response({'frames': frames}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='protein-stats')
    def protein_stats_view(self, request):
        sequence = request.data.get('sequence', '')
        if not sequence:
            return Response({'error': 'sequence is required'}, status=status.HTTP_400_BAD_REQUEST)
        stats = protein_stats(str(sequence).upper())
        if not stats:
            return Response({'error': 'Could not compute stats'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(stats, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def similarity(self, request):
        seq1 = request.data.get('seq1', '')
        seq2 = request.data.get('seq2', '')
        if not seq1 or not seq2:
            id1 = request.data.get('id1')
            id2 = request.data.get('id2')
            if id1 and id2:
                try:
                    p1 = Protein.objects.get(id=id1)
                    p2 = Protein.objects.get(id=id2)
                    seq1, seq2 = p1.sequence, p2.sequence
                except Protein.DoesNotExist:
                    return Response({'error': 'Protein not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'error': 'seq1 and seq2 (or id1 and id2) are required'}, status=status.HTTP_400_BAD_REQUEST)
        result = compute_similarity(str(seq1).upper(), str(seq2).upper())
        return Response(result, status=status.HTTP_200_OK)
