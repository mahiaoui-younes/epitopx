"""
EpitopX — User service layer.
All business logic relating to user auth / account management lives here.
Views call services; services call models.
"""
import logging
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token

from api.models import (
    EmailVerificationToken,
    PasswordResetToken,
    Subscription,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Token lifetimes
_EMAIL_TOKEN_TTL_HOURS = 24
_RESET_TOKEN_TTL_MINUTES = 30


def register_user(username: str, email: str, password: str) -> dict:
    """
    Create a new user and initialize their free subscription.
    Returns {'user': User, 'token': str} on success.
    Raises ValueError with a human-readable message on validation failure.
    """
    if User.objects.filter(username=username).exists():
        raise ValueError("Username already taken.")
    if User.objects.filter(email=email).exists():
        raise ValueError("An account with this email already exists.")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        is_admin=False,
        is_email_verified=False,
    )

    # Initialize free subscription
    Subscription.objects.create(user=user, plan='free', status='active')

    # Auth token (legacy — kept for backwards compat alongside JWT)
    token, _ = Token.objects.get_or_create(user=user)

    # Queue email verification (fire-and-forget; failure is non-fatal)
    try:
        _create_and_send_verification(user)
    except Exception:
        logger.exception("Failed to send verification email to %s", email)

    logger.info("New user registered: %s (id=%s)", username, user.id)
    return {'user': user, 'token': token.key}


def login_user(username: str, password: str) -> dict:
    """
    Authenticate and return token.
    Raises ValueError on invalid credentials.
    """
    user = authenticate(username=username, password=password)
    if user is None:
        raise ValueError("Invalid credentials.")
    if not user.is_active:
        raise ValueError("This account has been deactivated.")

    token, _ = Token.objects.get_or_create(user=user)
    logger.info("User logged in: %s (id=%s)", username, user.id)
    return {'user': user, 'token': token.key}


def logout_user(user) -> None:
    """Invalidate the user's auth token."""
    Token.objects.filter(user=user).delete()


def request_password_reset(email: str) -> None:
    """
    Create a password-reset token and send the email.
    Always returns None (no info leakage whether email exists).
    """
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        return  # Silently ignore — prevents email enumeration

    # Invalidate previous tokens
    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

    token = PasswordResetToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES),
    )
    _send_password_reset_email(user, token)


def confirm_password_reset(token_str: str, new_password: str) -> None:
    """
    Validate reset token and set new password.
    Raises ValueError on invalid / expired token.
    """
    try:
        token_uuid = uuid.UUID(str(token_str))
        token = PasswordResetToken.objects.select_related('user').get(token=token_uuid)
    except (PasswordResetToken.DoesNotExist, ValueError):
        raise ValueError("Invalid or expired reset token.")

    if not token.is_valid():
        raise ValueError("Reset token has expired or already been used.")

    user = token.user
    user.set_password(new_password)
    user.save(update_fields=['password'])

    token.used = True
    token.save(update_fields=['used'])

    # Rotate auth token
    Token.objects.filter(user=user).delete()
    Token.objects.create(user=user)

    logger.info("Password reset completed for user id=%s", user.id)


def verify_email(token_str: str) -> None:
    """
    Mark email as verified.
    Raises ValueError on invalid / expired token.
    """
    try:
        token_uuid = uuid.UUID(str(token_str))
        token = EmailVerificationToken.objects.select_related('user').get(token=token_uuid)
    except (EmailVerificationToken.DoesNotExist, ValueError):
        raise ValueError("Invalid verification token.")

    if token.is_expired():
        raise ValueError("Verification token has expired. Request a new one.")

    user = token.user
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified'])
    token.delete()
    logger.info("Email verified for user id=%s", user.id)


# ── Private helpers ───────────────────────────────────────────────────────────

def _create_and_send_verification(user) -> None:
    from django.core.mail import send_mail
    from django.conf import settings

    EmailVerificationToken.objects.filter(user=user).delete()
    token = EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=_EMAIL_TOKEN_TTL_HOURS),
    )
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token.token}"
    send_mail(
        subject="Verify your EpitopX email",
        message=f"Click the link to verify your email:\n\n{verify_url}\n\nThis link expires in {_EMAIL_TOKEN_TTL_HOURS} hours.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _send_password_reset_email(user, token) -> None:
    from django.core.mail import send_mail
    from django.conf import settings

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token.token}"
    send_mail(
        subject="Reset your EpitopX password",
        message=f"Click the link to reset your password:\n\n{reset_url}\n\nThis link expires in {_RESET_TOKEN_TTL_MINUTES} minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
