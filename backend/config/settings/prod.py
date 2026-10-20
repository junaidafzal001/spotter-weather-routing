"""Production settings.

Requires DJANGO_SECRET_KEY and DJANGO_ALLOWED_HOSTS to be set in the
environment.  Deployed on Render behind gunicorn (see backend/Dockerfile).
"""
from .base import *

DEBUG = False

if os.environ.get("DJANGO_SECRET_KEY") is None:
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

# Behind Render/Vercel proxies
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "true").lower() == "true"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
