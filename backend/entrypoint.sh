#!/bin/bash
# ------------------------------------------------------------------
# Entrypoint: run pending Alembic migrations, THEN exec whatever CMD
# was passed (multi-worker Uvicorn in production, or an overridden
# command for one-off tasks like `python -m app.ai_engine.train`).
#
# Using `exec "$@"` (not just running the command) replaces this shell
# process with the app process, so signals (SIGTERM on container stop)
# reach the app directly instead of being swallowed by a wrapper shell.
# ------------------------------------------------------------------
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding demo data (idempotent)..."
python -m scripts.render_seed

echo "Starting application..."
exec "$@"
