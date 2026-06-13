#!/bin/sh
set -e

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Ensuring admin user from environment..."
# Attempt to create/update admin from repository helper script (reads DJANGO_ADMIN_* env vars)
if [ -f ../scripts/create_admin_from_env.py ]; then
  python ../scripts/create_admin_from_env.py || echo "Admin creation script failed, falling back to createsuperuser"
fi
echo "==> Creating superuser (if not exists)..."
python manage.py createsuperuser --noinput 2>/dev/null || echo "Superuser already exists or skipped."

echo "==> Setting is_admin=True for superusers..."
python manage.py shell -c "
from api.models import User
updated = User.objects.filter(is_superuser=True).update(is_admin=True, is_email_verified=True)
print(f'Updated {updated} superuser(s) to is_admin=True')
"

echo "==> Seeding sample data (idempotent)..."
python manage.py seed_sample_data

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
