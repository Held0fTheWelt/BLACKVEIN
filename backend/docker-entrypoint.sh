#!/bin/sh
set -e
cd /app
export FLASK_APP="${FLASK_APP:-run:app}"
flask db upgrade
flask seed-base-governance-setup
exec "$@"
