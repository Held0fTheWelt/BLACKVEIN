#!/bin/sh
set -e
cd /app
export FLASK_APP="${FLASK_APP:-run:app}"
flask db upgrade
exec "$@"
