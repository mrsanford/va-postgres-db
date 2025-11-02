#!/usr/bin/env bash
set -e

PBF_URL=${PBF_URL:-"https://download.geofabrik.de/north-america/us/virginia-latest.osm.pbf"}
PBF_FILE=/data/virginia-latest.osm.pbf

echo "[INFO] Downloading OSM .pbf"
wget -q -O "$PBF_FILE" "$PBF_URL"

osm2pgsql \
  -H "$POSTGRES_HOST" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -W \
  --create \
  --slim \
  --hstore \
  --latlong \
  "$PBF_FILE" <<EOF
$POSTGRES_PASSWORD
EOF
