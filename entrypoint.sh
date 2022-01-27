#!/usr/bin/env bash
set -e

if [ -v "RUN_MIGRATIONS" ]; then
  echo "Running migrations"
  python -m alembic upgrade head
  echo "Migrations complete, starting application"
fi

python -m starbot
