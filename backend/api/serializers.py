from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Article, DNASequence, ProteinConversion, Protein, Epitope, Subscription

User = get_user_model()


# ── User serializers ──────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_admin', 'is_email_verified', 'date_joined']
        read_only_fields = fields


class UserRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, min_length=3)
    email    = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_username(self, value):
        import re
        if not re.match(r'^[\w.@+-]+$', value):
            raise serializers.ValidationError("Username contains invalid characters.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        return value.lower().strip()


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token    = serializers.UUIDField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_limits = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'plan', 'status', 'proteins_used', 'analyses_used',
            'analyses_month', 'agent_messages_month', 'current_period_end', 'plan_limits',
        ]
        read_only_fields = fields

    def get_plan_limits(self, obj):
        return Subscription.PLAN_LIMITS.get(obj.plan, {})


# ── Article serializer ────────────────────────────────────────────────────────

class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ['id', 'titre', 'contenu', 'created_at']
        read_only_fields = ['id', 'created_at']


# ── DNA / Protein conversion serializers ─────────────────────────────────────

class DNASequenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNASequence
        fields = ['id', 'name', 'sequence', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProteinConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProteinConversion
        fields = ['id', 'original_dna', 'rna', 'protein', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversionRequestSerializer(serializers.Serializer):
    dna_sequence = serializers.CharField(max_length=500_000)


class ConversionResponseSerializer(serializers.Serializer):
    dna     = serializers.CharField()
    rna     = serializers.CharField()
    protein = serializers.CharField()
    id      = serializers.IntegerField()


# ── Protein serializers ───────────────────────────────────────────────────────

class ProteinSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()
    epitope_count       = serializers.IntegerField(read_only=True)
    pdb_file            = serializers.SerializerMethodField()

    class Meta:
        model = Protein
        fields = [
            'id', 'name', 'fullname', 'sequence', 'organism', 'description',
            'method', 'is_public', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'epitope_count', 'pdb_file',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'epitope_count',
        ]

    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by_id else None

    def get_pdb_file(self, obj):
        """Return a stable /media/ relative URL for the PDB file.

        DRF's FileField with request context returns an absolute URL, but
        without context it returns just the storage path (e.g.
        'proteins/pdb/file.pdb').  We normalise it to a /media/ path so the
        frontend proxy can always fetch it via the same relative route.
        """
        if not obj.pdb_file:
            return None
        name = obj.pdb_file.name  # always the storage-relative path
        if not name:
            return None
        # Build a consistent /media/ relative URL
        if name.startswith('/media/'):
            return name
        if name.startswith('http'):
            # Strip origin if an absolute URL slipped in
            idx = name.find('/media/')
            return name[idx:] if idx != -1 else name
        return '/media/' + name

    def validate_name(self, value):
        return value.strip()

    def validate_sequence(self, value):
        # Strip FASTA header lines (lines starting with '>')
        lines = value.strip().splitlines()
        seq_lines = [l for l in lines if not l.startswith('>')]
        cleaned = ''.join(seq_lines).upper().replace(' ', '').replace('\t', '').replace('\r', '')
        # Standard 20 AAs + ambiguous (B,Z,J) + rare standard (O,U) + gap/stop/unknown
        valid_chars = set('ACDEFGHIKLMNPQRSTVWYBZJOUX*-')
        invalid = set(cleaned) - valid_chars
        if invalid:
            raise serializers.ValidationError(
                f"Sequence contains invalid amino acid characters: {sorted(invalid)}"
            )
        return cleaned


# ── Epitope serializers ───────────────────────────────────────────────────────

class EpitopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Epitope
        fields = [
            'id', 'epitope_id', 'epitope_sequence', 'method',
            'start', 'end', 'length', 'score',
            'hopp_woods', 'kyte_doolittle', 'karplus_schulz',
            'emini', 'kolaskar', 'created_at',
        ]
        read_only_fields = fields


class EpitopeListSerializer(serializers.ModelSerializer):
    sequence = serializers.CharField(source='epitope_sequence')

    class Meta:
        model = Epitope
        fields = ['id', 'sequence', 'start', 'end', 'length', 'score', 'method']


class EpitopeFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = Epitope
        fields = '__all__'


class EpitopeAnalysisRequestSerializer(serializers.Serializer):
    sequence   = serializers.CharField(max_length=50_000)
    method     = serializers.ChoiceField(choices=['core', 'bio', 'iedb'], default='core')
    protein_id = serializers.IntegerField(required=False, allow_null=True)
    organism   = serializers.CharField(required=False, allow_blank=True, default='')
    min_length = serializers.IntegerField(default=9,  min_value=4,  max_value=50)
    max_length = serializers.IntegerField(default=20, min_value=4,  max_value=100)
    min_score  = serializers.FloatField(default=0.5,  min_value=0.0, max_value=1.0)
    top_n      = serializers.IntegerField(default=20, min_value=1,  max_value=200)
    pdb_file   = serializers.FileField(required=False, allow_null=True)
    chain_id   = serializers.CharField(required=False, default='A', max_length=2)

    def validate(self, data):
        if data['min_length'] > data['max_length']:
            raise serializers.ValidationError("min_length must be <= max_length.")
        return data
