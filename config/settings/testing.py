"""
Testing settings — optimized for fast test runs.
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# Use a separate test database
DATABASES["default"]["NAME"] = "prop_trader_test"  # noqa: F405

# Faster password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable throttling in tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405
