#!/usr/bin/env bash
# Render start command. Seed data separately once after the first deployment.
set -e

python manage.py migrate --noinput

export GUNICORN_BIND="0.0.0.0:${PORT:-8000}"
exec gunicorn -c gunicorn.conf.py config.asgi:application
