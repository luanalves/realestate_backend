#!/bin/sh
# grafana-entrypoint.sh
#
# Copies dashboard JSONs from the read-only source mount (/tmp/dashboards-src)
# to the writable volume (/var/lib/grafana/dashboards), patches the template
# variable current.value with the correct service name per environment, then
# starts Grafana normally.
#
# This runs automatically on every container start (including after Dokploy deploy)
# without any manual intervention.

set -e

SVC="${GF_DEFAULT_SERVICE_NAME:-odoo-production}"
SRC="/tmp/dashboards-src"
DEST="/var/lib/grafana/dashboards"

echo "[grafana-entrypoint] environment service: $SVC"

mkdir -p "$DEST"
cp "$SRC"/*.json "$DEST"/

for f in "$DEST"/*.json; do
  sed -i \
    -e 's/"text": "odoo-production"/"text": "'"$SVC"'"/g' \
    -e 's/"value": "odoo-production"/"value": "'"$SVC"'"/g' \
    -e 's/"text": "odoo-dev"/"text": "'"$SVC"'"/g' \
    -e 's/"value": "odoo-dev"/"value": "'"$SVC"'"/g' \
    -e 's/"text": "odoo-homol"/"text": "'"$SVC"'"/g' \
    -e 's/"value": "odoo-homol"/"value": "'"$SVC"'"/g' \
    "$f"
done

echo "[grafana-entrypoint] dashboards patched → $DEST"
exec /run.sh
