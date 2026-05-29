"""
Management command: reset_monthly_quotas

Resets all monthly usage counters (analyses_month, agent_messages_month)
for every subscription whose quota_reset_at is from a previous calendar month.

Usage:
    python manage.py reset_monthly_quotas

Schedule this with cron / Windows Task Scheduler to run on the 1st of each month:
    # cron example (1st of month at 00:05 UTC)
    5 0 1 * * cd /app && python manage.py reset_monthly_quotas
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Reset monthly usage quotas (analyses_month, agent_messages_month) for all subscriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many subscriptions would be reset without making changes.',
        )

    def handle(self, *args, **options):
        from api.models import Subscription

        now = timezone.now()
        dry_run = options['dry_run']

        # Find subscriptions that haven't been reset this calendar month
        stale = Subscription.objects.filter(
            status__in=('active', 'trialing')
        ).exclude(
            quota_reset_at__year=now.year,
            quota_reset_at__month=now.month,
        )

        count = stale.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {count} subscription(s) would be reset."
                )
            )
            return

        updated = stale.update(
            analyses_month=0,
            agent_messages_month=0,
            quota_reset_at=now,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset monthly quotas for {updated} subscription(s)."
            )
        )
