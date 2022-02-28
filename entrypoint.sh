#!/usr/bin/env bash
set -e

if [ -v "ALEMBIC_AUTOGENERATE" ]; then
    echo Running alembic
    python -m alembic revision --autogenerate
    exit
fi

if [ -v "RUN_MIGRATIONS" ]; then
  echo "Running migrations"
  python -m alembic upgrade head
  echo "Migrations complete, starting application"
fi

python -m starbot
