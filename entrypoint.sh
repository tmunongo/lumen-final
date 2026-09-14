#!/bin/sh
set -e

echo "Running migrations..."
uv run python manage.py migrate --noinput

echo "Starting Gunicorn server on 0.0.0.0:8000..."
exec uv run gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
