"""
EpitopX — quota / subscription enforcement service.
"""
import logging
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


def check_protein_quota(user) -> None:
    """
    Raise PermissionError if the user has reached their protein limit.
    Creates a free Subscription if one does not yet exist (back-compat).
    """
    sub = _get_or_create_subscription(user)
    if not sub.is_active():
        raise PermissionError("Your subscription is not active.")
    limit = sub.get_limit('proteins')
    if sub.proteins_used >= limit:
        raise PermissionError(
            f"You have reached your protein limit ({limit}) for the {sub.plan} plan. "
            "Upgrade to add more proteins."
        )


def increment_protein_count(user) -> None:
    from api.models import Subscription
    Subscription.objects.filter(user=user).update(
        proteins_used=F('proteins_used') + 1
    )


def decrement_protein_count(user) -> None:
    from api.models import Subscription
    Subscription.objects.filter(user=user, proteins_used__gt=0).update(
        proteins_used=F('proteins_used') - 1
    )


def check_analysis_quota(user) -> None:
    """
    Raise PermissionError if the user has reached their monthly analysis limit.
    """
    sub = _get_or_create_subscription(user)
    if not sub.is_active():
        raise PermissionError("Your subscription is not active.")

    _maybe_reset_monthly_quota(sub)
    limit = sub.get_limit('analyses_month')
    if sub.analyses_month >= limit:
        raise PermissionError(
            f"You have reached your monthly analysis limit ({limit}) for the {sub.plan} plan. "
            "Upgrade or wait until next month."
        )


def increment_analysis_count(user) -> None:
    from api.models import Subscription
    Subscription.objects.filter(user=user).update(
        analyses_used=F('analyses_used') + 1,
        analyses_month=F('analyses_month') + 1,
    )


def check_agent_quota(user) -> None:
    """
    Raise PermissionError if the user has reached their monthly AI agent message limit.
    """
    sub = _get_or_create_subscription(user)
    if not sub.is_active():
        raise PermissionError("Your subscription is not active.")

    _maybe_reset_monthly_quota(sub)
    limit = sub.get_limit('agent_messages_month')
    if sub.agent_messages_month >= limit:
        raise PermissionError(
            f"You have reached your monthly AI agent message limit ({limit}) for the {sub.plan} plan. "
            "Upgrade or wait until next month."
        )


def increment_agent_count(user) -> None:
    from api.models import Subscription
    Subscription.objects.filter(user=user).update(
        agent_messages_month=F('agent_messages_month') + 1,
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _get_or_create_subscription(user):
    from api.models import Subscription
    sub, created = Subscription.objects.get_or_create(
        user=user,
        defaults={'plan': 'free', 'status': 'active'},
    )
    return sub


def _maybe_reset_monthly_quota(sub) -> None:
    """Reset all monthly counters when a new calendar month begins."""
    now = timezone.now()
    if (sub.quota_reset_at is None
            or now.month != sub.quota_reset_at.month
            or now.year != sub.quota_reset_at.year):
        sub.analyses_month = 0
        sub.agent_messages_month = 0
        sub.quota_reset_at = now
        sub.save(update_fields=['analyses_month', 'agent_messages_month', 'quota_reset_at'])
        logger.info("Monthly quota reset for user_id=%s (plan=%s)", sub.user_id, sub.plan)
