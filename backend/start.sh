#!/bin/sh
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Creating superuser (if not exists)..."
python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists or skipped."

echo "==> Starting Gunicorn..."
exec gunicorn \
  --bind            0.0.0.0:8000 \
  --workers         4 \
  --worker-class    sync \
  --threads         2 \
  --timeout         120 \
  --keep-alive      5 \
  --access-logfile  - \
  --error-logfile   - \
  config.wsgi:application
