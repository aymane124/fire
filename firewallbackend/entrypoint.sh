#!/bin/sh
set -e

# Wait for DB if using external DBs; skip for SQLite
if [ "$DATABASE_URL" != "" ]; then
  echo "Waiting for database..."
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Setting up admin user..."
python setup_database.py

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting ASGI server..."
exec "$@"


