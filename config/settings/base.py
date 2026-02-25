"""
Django base settings for Proprietary Accounts Auto-Trader.

Shared settings used by all environments (development, production, testing).
Environment-specific overrides live in their respective files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "INSECURE-dev-key-change-me")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Project apps
    "apps.webhooks",
    "apps.broker_connector",
    "apps.execution_engine",
    "apps.risk_management",
    "apps.market_data",
    "apps.dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database — MongoDB via Djongo
# Override in environment-specific settings if needed
DATABASES = {
    "default": {
        "ENGINE": "djongo",
        "NAME": os.environ.get("DB_MONGO_NAME", "prop_trader"),
        "ENFORCE_SCHEMA": False,
        "CLIENT": {
            "host": os.environ.get("DB_MONGO_HOST", "localhost"),
            "port": int(os.environ.get("DB_MONGO_PORT", 27017)),
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/New_York"  # US Eastern — stock market hours
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S.%fZ",
}

# CORS
CORS_ALLOW_ALL_ORIGINS = False  # Override in development.py

# Redis (used by Channels + Celery)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Django Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Alpaca Broker
BROKER_ALPACA_API_KEY = os.environ.get("BROKER_ALPACA_API_KEY", "")
BROKER_ALPACA_SECRET_KEY = os.environ.get("BROKER_ALPACA_SECRET_KEY", "")
BROKER_ALPACA_BASE_URL = os.environ.get(
    "BROKER_ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
)

# Webhook Security
WEBHOOK_AUTH_TOKEN = os.environ.get("WEBHOOK_AUTH_TOKEN", "dev-token-change-me")

# Encryption Key (for API key vault)
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
