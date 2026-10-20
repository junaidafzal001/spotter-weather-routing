"""
Base Django settings for the Spotter Weather-Aware Truck Routing backend.

All provider configuration is environment driven.  Nothing here is
provider-specific: adapters read their own settings via ``django.conf.settings``.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load backend/.env (development convenience; production sets real env vars).
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = False
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

# whitenoise is only installed with requirements-prod.txt; keep import optional.
try:
    import whitenoise
except ImportError:  # pragma: no cover
    MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES: list = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
try:
    import whitenoise  # noqa: F401
except ImportError:  # pragma: no cover
    STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "api.exceptions.service_exception_handler",
    "UNAUTHENTICATED_USER": None,
}

# CORS
_frontend_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ALLOWED_ORIGINS = [o.strip() for o in _frontend_origins.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = False

# Cache: LocMem by default, Redis when REDIS_URL is provided.
if os.environ.get("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ["REDIS_URL"],
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "swr",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "swr-default",
        }
    }

# External providers (all overridable for tests / self-hosting)
APP_USER_AGENT = os.environ.get("APP_USER_AGENT", "spotter-weather-routing/1.0 (assessment)")

NOMINATIM_BASE_URL = os.environ.get("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
ORS_BASE_URL = os.environ.get("ORS_BASE_URL", "https://api.openrouteservice.org")
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")
GRAPHHOPPER_BASE_URL = os.environ.get("GRAPHHOPPER_BASE_URL", "https://graphhopper.com/api/1")
GRAPHHOPPER_API_KEY = os.environ.get("GRAPHHOPPER_API_KEY", "")
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org")
OPEN_METEO_BASE_URL = os.environ.get("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")

# Outbound HTTP behaviour
PROVIDER_TIMEOUT_SECONDS = float(os.environ.get("PROVIDER_TIMEOUT_SECONDS", "15"))
MAX_ROUTE_ALTERNATIVES = 3

# Cache TTLs (seconds)
GEOCODE_CACHE_TTL = int(os.environ.get("GEOCODE_CACHE_TTL", str(60 * 60 * 24)))
ROUTE_CACHE_TTL = int(os.environ.get("ROUTE_CACHE_TTL", str(60 * 60)))
WEATHER_CACHE_TTL = int(os.environ.get("WEATHER_CACHE_TTL", str(60 * 30)))
ANALYSIS_CACHE_TTL = int(os.environ.get("ANALYSIS_CACHE_TTL", str(60 * 60 * 6)))
