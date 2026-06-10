#!/bin/sh

set -e

while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -q; do
  sleep 1
done

python manage.py collectstatic --noinput
python manage.py makemigrations
python manage.py migrate

python manage.py shell <<EOF
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'adminpassword')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
EOF

python manage.py rqworker default &

exec gunicorn videoflix.wsgi:application --bind 0.0.0.0:8000 --reload
