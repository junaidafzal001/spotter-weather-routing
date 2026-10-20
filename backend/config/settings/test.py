"""Settings used by pytest. No network calls ever leave the test-suite."""
from .base import *

DEBUG = False
ALLOWED_HOSTS = ["*"]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "swr-test",
    }
}
