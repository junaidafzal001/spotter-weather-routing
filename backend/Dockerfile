# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

# Collect static assets for WhiteNoise (admin/DRF browsable API in non-prod).
# A dummy secret is supplied because prod settings refuse to boot without one.
RUN DJANGO_SECRET_KEY=build-time-only DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
