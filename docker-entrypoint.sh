#!/bin/sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} ..."
until python -c "import socket; socket.create_connection(('${DB_HOST}', ${DB_PORT}), 3)" 2>/dev/null; do
    echo "  database not ready yet, retrying..."
    sleep 2
done
echo "Database is up."

echo "Running migrations..."
alembic upgrade head

echo "Seeding admin user and keywords (idempotent)..."
python seed_admin.py "${ADMIN_EMAIL:-admin@example.com}" "${ADMIN_PASSWORD:-Admin@123}" || true
python seed_keywords.py || true

echo "Starting API server on :8001 ..."
exec uvicorn main:app --host 0.0.0.0 --port 8001
