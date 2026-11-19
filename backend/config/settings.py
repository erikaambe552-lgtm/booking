"""
CampBlazer Django settings.

All secrets and credentials come from environment variables (.env file in
development). PostgreSQL is required because the concurrency controls rely on
row-level locking (SELECT ... FOR UPDATE), partial unique indexes and
exclusion constraints.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_list(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY is not set. Copy .env.example to .env.")

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

INSTALLED_APPS = [
    "daphne",  # makes `manage.py runserver` serve ASGI (HTTP + WebSockets)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "channels",
    "accounts",
    "destinations",
    "bookings",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Adds X-Worker-PID / X-Processing-Time-ms headers so the concurrency
    # demo can show WHICH server process handled each request.
    "config.middleware.WorkerInfoMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Real-time layer: Django Channels + Redis.
# Every server worker process subscribes to Redis, so an event published by the
# worker that handled an approval reaches a WebSocket held open by ANY worker.
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer",
                                  "CONFIG": {"hosts": [REDIS_URL]}}}
else:
    # Development fallback: works only with ONE server process (no cross-worker delivery).
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL:
    # Hosted Postgres (Neon, Render...) gives one connection string. Use the DIRECT
    # (non "-pooler") Neon string: row locks need a normal session.
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0, ssl_require=True)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "campblazer"),
            "USER": os.getenv("POSTGRES_USER", "campblazer"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 0,  # ASGI: persistent connections are not safe across async threads
            "OPTIONS": {"connect_timeout": 5},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Django's default hasher is PBKDF2-SHA256 (salted, iterated) — passwords are never stored in plain text.

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    # Raise these with env vars while running load tests (see README).
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("ANON_THROTTLE", "300/min"),
        "login": os.getenv("LOGIN_THROTTLE", "20/min"),
    },
}

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
# Django admin login over HTTPS on a hosted domain, e.g. https://campblazer-api.onrender.com
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
# Origins allowed to open the WebSocket: the server's own hosts + the frontend's address(es).
WS_ALLOWED_ORIGINS = ALLOWED_HOSTS + CORS_ALLOWED_ORIGINS
# Behind a hosting proxy (Render, Railway...) the original scheme arrives in this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Security headers (cookies become Secure automatically when DEBUG is off).
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"bookings": {"handlers": ["console"], "level": "INFO"}},
}
