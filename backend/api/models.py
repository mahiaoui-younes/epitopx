import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# User & authentication models
# ─────────────────────────────────────────────────────────────────────────────

class User(AbstractUser):
    """Extended user model with SaaS-specific fields."""
    email = models.EmailField(unique=True)
    is_admin = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Soft-delete flag (never hard-delete users — regulatory / audit trail)
    is_active = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [models.Index(fields=['email'])]

    def __str__(self):
        return self.username


class EmailVerificationToken(models.Model):
    """One-time token for email address verification."""
    user  = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_token')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"EmailToken({self.user.username})"


class PasswordResetToken(models.Model):
    """One-time token for password reset."""
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and timezone.now() <= self.expires_at

    def __str__(self):
        return f"PasswordResetToken({self.user.username})"


# ─────────────────────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    """Immutable audit trail for security-sensitive operations."""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action     = models.CharField(max_length=100, db_index=True)
    resource   = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=36, blank=True, db_index=True)
    extra      = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action} by {self.user}"


# ─────────────────────────────────────────────────────────────────────────────
# Subscription / plan
# ─────────────────────────────────────────────────────────────────────────────

PLAN_CHOICES = [
    ('free',    'Free'),
    ('pro',     'Pro'),
    ('team',    'Team'),
    ('enterprise', 'Enterprise'),
]

SUBSCRIPTION_STATUS = [
    ('active',    'Active'),
    ('trialing',  'Trialing'),
    ('past_due',  'Past Due'),
    ('cancelled', 'Cancelled'),
    ('paused',    'Paused'),
]


class Subscription(models.Model):
    """SaaS subscription record per user (one active at a time)."""
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan            = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    status          = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='active')
    # Stripe / payment gateway identifiers
    stripe_customer_id      = models.CharField(max_length=100, blank=True)
    stripe_subscription_id  = models.CharField(max_length=100, blank=True)
    trial_ends_at   = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    # Usage quotas (enforced in views via check_quota())
    proteins_used   = models.PositiveIntegerField(default=0)
    analyses_used   = models.PositiveIntegerField(default=0)
    analyses_month  = models.PositiveIntegerField(default=0)
    quota_reset_at  = models.DateTimeField(null=True, blank=True)

    PLAN_LIMITS = {
        'free':       {'proteins': 10,   'analyses_month': 20},
        'pro':        {'proteins': 100,  'analyses_month': 500},
        'team':       {'proteins': 500,  'analyses_month': 2000},
        'enterprise': {'proteins': 9999, 'analyses_month': 99999},
    }

    def get_limit(self, resource: str) -> int:
        return self.PLAN_LIMITS.get(self.plan, {}).get(resource, 0)

    def is_active(self) -> bool:
        return self.status in ('active', 'trialing')

    def __str__(self):
        return f"{self.user.username} [{self.plan}]"


# ─────────────────────────────────────────────────────────────────────────────
# Bioinformatics content models
# ─────────────────────────────────────────────────────────────────────────────

class Article(models.Model):
    titre      = models.CharField(max_length=200)
    contenu    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.titre


class DNASequence(models.Model):
    name       = models.CharField(max_length=200)
    sequence   = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProteinConversion(models.Model):
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversions')
    original_dna = models.TextField()
    rna          = models.TextField()
    protein      = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversion {self.id}"


METHOD_CHOICES = [
    ('core', 'Core Module (5 methods)'),
    ('bio',  'Bio Module (7 methods)'),
    ('iedb', 'IEDB Tools API'),
]


class Protein(models.Model):
    name        = models.CharField(max_length=200, db_index=True)
    sequence    = models.TextField()
    organism    = models.CharField(max_length=200, blank=True, db_index=True)
    description = models.TextField(blank=True)
    method      = models.CharField(max_length=20, choices=METHOD_CHOICES, default='core')
    is_public   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(
        'api.User',
        on_delete=models.CASCADE,
        related_name='proteins',
        null=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'is_public']),
        ]

    def __str__(self):
        return self.name


class Epitope(models.Model):
    protein          = models.ForeignKey(Protein, on_delete=models.CASCADE, related_name='epitopes', null=True, blank=True)
    epitope_sequence = models.CharField(max_length=200, default='', db_index=True)
    epitope_id       = models.IntegerField(default=1)
    method           = models.CharField(max_length=20, choices=METHOD_CHOICES, default='core')
    start            = models.IntegerField(default=0)
    end              = models.IntegerField(default=0)
    length           = models.IntegerField(default=0)
    score            = models.FloatField(default=0.0, db_index=True)
    hopp_woods       = models.FloatField(null=True, blank=True)
    kyte_doolittle   = models.FloatField(null=True, blank=True)
    karplus_schulz   = models.FloatField(null=True, blank=True)
    emini            = models.FloatField(null=True, blank=True)
    kolaskar         = models.FloatField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']
        unique_together = [('protein', 'epitope_sequence', 'start', 'end')]
        indexes = [
            models.Index(fields=['protein', 'score']),
        ]

    def __str__(self):
        return f"Epitope {self.epitope_sequence} (score={self.score})"
