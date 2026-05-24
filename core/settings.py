"""
core/settings.py

Production-ready settings for GoAttend.

Environment tiers:
  - Local dev  : DEBUG=True, SQLite, console email, local media
  - Production : DEBUG=False, Supabase PostgreSQL, SMTP, Cloudinary media

All secrets are read exclusively from environment variables.
No secret has a production-safe default — the app refuses to start
if a required variable is missing in production.
"""

from pathlib import Path
from datetime import timedelta
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Base path
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env in local development. On Render, env vars are injected directly
# and this call is a safe no-op (it won't override already-set env vars).
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------
# Default is FALSE — developer must explicitly opt in to debug mode.
# On Render: set DEBUG=False (or leave unset — defaults to False).
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# ---------------------------------------------------------------------------
# Secret key
# ---------------------------------------------------------------------------
# WHY: If SECRET_KEY is missing in production, all JWTs, sessions,
# and CSRF tokens are signed with a predictable key — full compromise.
# We raise immediately on startup rather than silently using a weak key.
SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    if DEBUG:
        # Safe local fallback — never reaches production because DEBUG=False
        # requires a real SECRET_KEY (enforced below)
        SECRET_KEY = "local-dev-only-insecure-key-do-not-use-in-production"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY environment variable is not set. "
            "This is required in production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
        )

# ---------------------------------------------------------------------------
# Allowed hosts
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "cloudinary",
    "cloudinary_storage",
    # Local apps
    "accounts",
    "events",
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
# ORDER IS CRITICAL:
#   1. CorsMiddleware  — must be first (before CommonMiddleware)
#   2. SecurityMiddleware — must be second (sets HTTPS redirect etc.)
#   3. WhiteNoiseMiddleware — must be third (serves static files efficiently)
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",           # 1. CORS headers (must be first)
    "django.middleware.security.SecurityMiddleware",   # 2. Security (HTTPS, HSTS)
    "whitenoise.middleware.WhiteNoiseMiddleware",      # 3. Static file serving (prod)
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "core.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# WHY dj_database_url: Supabase (and Render) provide a single DATABASE_URL
# connection string. Without this, you'd need to manually parse the string
# into host/port/name/user/password — error-prone and fragile.
#
# IMPORTANT — Render free tier is IPv4 only. Supabase's direct connection
# (db.xxx.supabase.co:5432) resolves to IPv6 and will FAIL on Render free.
# Solution: use Supabase's Connection Pooler URL (IPv4) from the dashboard:
#   Supabase → Project Settings → Database → Connection Pooling
#
#   Session Pooler    → port 5432  (recommended for Django — full SQL support)
#   Transaction Pooler → port 6543 (pgBouncer — requires DISABLE_SERVER_SIDE_CURSORS)
#
# SSL: Supabase pooler URLs already include ?sslmode=require natively.
# We set ssl_require=True only when the URL doesn't already specify sslmode,
# to prevent conflicting SSL parameters and connection errors.
import dj_database_url

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Detect if this is a Supabase Transaction Pooler URL (port 6543 / pgBouncer).
    # Transaction Pooler (pgBouncer) does not support server-side cursors or
    # persistent connections — both must be disabled for Django to work correctly.
    _is_transaction_pooler = ":6543" in DATABASE_URL

    # Supabase pooler URLs include ?sslmode=require natively.
    # Only force ssl_require if it's not already present in the URL.
    _ssl_required = "sslmode" not in DATABASE_URL

    db_config = dj_database_url.parse(
        DATABASE_URL,
        # Transaction Pooler (pgBouncer) owns the connection lifecycle —
        # Django must NOT persist connections on its own side.
        conn_max_age=0 if _is_transaction_pooler else 600,
        ssl_require=_ssl_required,
    )

    # pgBouncer in transaction mode does not support PostgreSQL server-side
    # cursors (used internally by Django for large querysets). Disabling this
    # prevents "unexpected message from server" errors at runtime.
    if _is_transaction_pooler:
        db_config["DISABLE_SERVER_SIDE_CURSORS"] = True

    DATABASES = {"default": db_config}
else:
    # Local development fallback — SQLite requires zero configuration.
    # WHY SQLite: Developers can run the project with no Postgres installed.
    # SQLite is fine for local testing; it's automatically replaced by
    # PostgreSQL on Render via DATABASE_URL.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (WhiteNoise)
# ---------------------------------------------------------------------------
# WHY WhiteNoise: Render has no nginx/CDN layer to serve static files.
# Without WhiteNoise, the Django admin panel has no CSS — it looks broken.
# WhiteNoise compresses and caches static files with immutable cache headers.
#
# CompressedManifestStaticFilesStorage: Adds a content hash to filenames
# (e.g., main.abc123.css) so browsers always get fresh files after deploy.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------------------------------------------------------
# Media files (Cloudinary in production, local in development)
# ---------------------------------------------------------------------------
# WHY Cloudinary: Render's filesystem is EPHEMERAL — every redeploy wipes
# the disk. Any image uploaded to MEDIA_ROOT is permanently lost on deploy.
# Cloudinary stores images in the cloud, surviving infinite redeploys.
#
# Pattern: If CLOUDINARY_URL env var is set → use Cloudinary.
#          Otherwise → local filesystem (development convenience).
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")

if CLOUDINARY_URL:
    # Cloudinary parses its credentials from the CLOUDINARY_URL env var
    # automatically when the SDK is imported. We just need to set the
    # DEFAULT_FILE_STORAGE to redirect Django's file operations to Cloudinary.
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
    CLOUDINARY_STORAGE = {
        "CLOUDINARY_URL": CLOUDINARY_URL,
    }
    # When using Cloudinary, MEDIA_URL is not used for serving
    # (Cloudinary serves via its own CDN URLs)
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
else:
    # Development: serve from local filesystem
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # Global rate throttling — prevents API abuse without per-view decorators.
    # AnonRateThrottle: limits unauthenticated requests (discovery, login attempts)
    # UserRateThrottle: limits authenticated requests (ticket purchases, etc.)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
    },
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    # ROTATE_REFRESH_TOKENS: Issues a new refresh token on every use.
    # Old refresh token is immediately blacklisted.
    # WHY: Limits the damage of a stolen refresh token to a single use.
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS — Cross-Origin Resource Sharing
# ---------------------------------------------------------------------------
# WHY: The Vercel frontend (https://go-attend.vercel.app) is a different
# "origin" than the Render API (https://eventmanagement-api1.onrender.com).
# Without CORS headers, browsers will block ALL fetch() calls from the frontend.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173",
).split(",")

# In DEBUG mode, allow all origins for convenience (file:// opened HTML files)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ---------------------------------------------------------------------------
# CSRF Trusted Origins
# ---------------------------------------------------------------------------
# WHY: Without this, Django's CSRF middleware rejects requests from your
# Vercel frontend in production (POST/PUT/DELETE will all fail with 403).
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
).split(",")

# ---------------------------------------------------------------------------
# Production Security Headers (only when DEBUG=False)
# ---------------------------------------------------------------------------
# WHY: These settings only make sense on HTTPS (production).
# Enabling them in local development would break http://localhost.
if not DEBUG:
    # Force all HTTP traffic to HTTPS
    SECURE_SSL_REDIRECT = True

    # HSTS: Tell browsers to ONLY use HTTPS for 1 year
    # Once set, cannot be easily undone — browsers cache this aggressively
    SECURE_HSTS_SECONDS = 31536000          # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Prevent session cookie from being sent over HTTP
    SESSION_COOKIE_SECURE = True

    # Prevent CSRF cookie from being sent over HTTP
    CSRF_COOKIE_SECURE = True

    # Prevent browsers from sniffing content type
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Enable XSS filter in older browsers
    SECURE_BROWSER_XSS_FILTER = True

    # Proxy header — Render terminates SSL at the load balancer
    # Without this, SECURE_SSL_REDIRECT causes an infinite redirect loop
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# WHY: Without logging, when something breaks in production you have NO
# visibility. Render captures stdout — so logging to console works perfectly.
# We log WARNING+ to console always, and ERROR+ with full stack traces.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        # App-level logger — use logging.getLogger('accounts') in your views
        "accounts": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "events": {
            "handlers": ["console"],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
    },
}
