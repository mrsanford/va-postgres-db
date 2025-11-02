#!/usr/bin/env bash
set -e

# Need this because the project needs hstore
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'EOF'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;
EOF
