"""
Test settings — overrides the main settings to use SQLite in-memory.
Usage:  python manage.py test --settings=config.test_settings api.tests
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up tests — Argon2 is slow; use MD5 only in test mode
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable throttling during tests — keep the rate keys so custom throttle
# classes don't raise ImproperlyConfigured, but set absurdly high limits.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'burst':     '100000/min',
        'sustained': '1000000/day',
        'auth':      '100000/min',
        'analysis':  '100000/hour',
    },
}

# Keep emails silent
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable HTTPS redirect so the test client (plain HTTP) works
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Suppress unnecessary logging
LOGGING = {}
