"""
EpitopX — custom DRF throttle classes.
"""
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'


class AuthRateThrottle(AnonRateThrottle):
    """Strict throttle for login / register endpoints (per IP)."""
    scope = 'auth'


class AnalysisRateThrottle(UserRateThrottle):
    """Heavy compute throttle for epitope analysis endpoints."""
    scope = 'analysis'
