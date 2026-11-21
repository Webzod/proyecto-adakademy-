"""Django settings for the academic resources project."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver"
    ).split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured(
            "Set DJANGO_SECRET_KEY when running with DJANGO_DEBUG=False."
        )
    SECRET_KEY = "django-insecure-development-key-do-not-use-in-production"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "resources",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

DATABASES = {
    "default": {}
}
DATABASE_ENGINE = os.environ.get(
    "DJANGO_DB_ENGINE",
    "django.db.backends.sqlite3" if DEBUG else "django.db.backends.postgresql",
)
if not DEBUG and DATABASE_ENGINE != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        "Production requires PostgreSQL; set DJANGO_DB_ENGINE accordingly."
    )
if DATABASE_ENGINE == "django.db.backends.sqlite3":
    DATABASES["default"] = {
        "ENGINE": DATABASE_ENGINE,
        "NAME": os.environ.get("DJANGO_DB_NAME", str(BASE_DIR / "db.sqlite3")),
    }
elif DATABASE_ENGINE == "django.db.backends.postgresql":
    database_config = {
        "ENGINE": DATABASE_ENGINE,
        "NAME": os.environ.get("DJANGO_DB_NAME", ""),
        "USER": os.environ.get("DJANGO_DB_USER", ""),
        "PASSWORD": os.environ.get("DJANGO_DB_PASSWORD", ""),
        "HOST": os.environ.get("DJANGO_DB_HOST", ""),
        "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
    if not DEBUG:
        missing_database_settings = [
            setting
            for setting in ("NAME", "USER", "PASSWORD", "HOST")
            if not database_config[setting]
        ]
        if missing_database_settings:
            raise ImproperlyConfigured(
                "Set DJANGO_DB_NAME, DJANGO_DB_USER, DJANGO_DB_PASSWORD, "
                "and DJANGO_DB_HOST for production PostgreSQL."
            )
        database_config["OPTIONS"] = {
            "sslmode": os.environ.get("DJANGO_DB_SSLMODE", "verify-full")
        }
    DATABASES["default"] = database_config
else:
    raise ImproperlyConfigured(
        "DJANGO_DB_ENGINE must be django.db.backends.sqlite3 or "
        "django.db.backends.postgresql."
    )

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(
    os.environ.get("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))
).expanduser()
if not DEBUG and not os.environ.get("DJANGO_MEDIA_ROOT"):
    raise ImproperlyConfigured(
        "Set DJANGO_MEDIA_ROOT to a persistent volume path in production."
    )

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get(
    "DJANGO_SECURE_SSL_REDIRECT",
    str(not DEBUG),
).lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
