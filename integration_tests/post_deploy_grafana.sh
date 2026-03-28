#!/usr/bin/env bash
# post_deploy_grafana.sh
#
# Run this script after any Dokploy deploy to fix Grafana dashboard service_name
# per environment. Grafana does not interpolate ${__env:} in template variable
# current fields, so we patch the files directly via SSH.
#
# Usage:
#   ./integration_tests/post_deploy_grafana.sh
#
# Requirements:
#   - SSH access to root@148.230.76.211
#   - jq (optional, for pretty output)

set -euo pipefail

SERVER="root@148.230.76.211"
STACKS=("hsxgpe" "z1yrzg" "f7tnmf")

echo "=== Grafana post-deploy: patching service_name per environment ==="

ssh -o StrictHostKeyChecking=no "$SERVER" '
for stack in hsxgpe z1yrzg f7tnmf; do
  CONTAINER="imobiliaria-backoffice-${stack}-grafana-1"
  DASH_DIR="/etc/dokploy/compose/imobiliaria-backoffice-${stack}/code/18.0/observability/grafana/dashboards"

  # Get service name from container env (set via GF_DEFAULT_SERVICE_NAME in docker-compose)
  SVC=$(docker inspect "$CONTAINER" --format "{{range .Config.Env}}{{println .}}{{end}}" \
    | grep GF_DEFAULT_SERVICE_NAME | cut -d= -f2-)

  if [ -z "$SVC" ]; then
    echo "[$stack] WARNING: GF_DEFAULT_SERVICE_NAME not found in container, skipping"
    continue
  fi

  echo "[$stack] patching → $SVC"

  # Replace current value in all dashboard JSONs for this environment
  # Works whether coming from ${__env:} placeholder or previous odoo-production default
  sed -i \
    -e "s|\"text\": \"odoo-production\"|\"text\": \"$SVC\"|g" \
    -e "s|\"value\": \"odoo-production\"|\"value\": \"$SVC\"|g" \
    -e "s|\"text\": \"odoo-dev\"|\"text\": \"$SVC\"|g" \
    -e "s|\"value\": \"odoo-dev\"|\"value\": \"$SVC\"|g" \
    -e "s|\"text\": \"odoo-homol\"|\"text\": \"$SVC\"|g" \
    -e "s|\"value\": \"odoo-homol\"|\"value\": \"$SVC\"|g" \
    "$DASH_DIR/distributed-tracing.json" \
    "$DASH_DIR/full-stack-apm.json" 2>/dev/null || true

  # Reload Grafana provisioning
  PASS=$(docker inspect "$CONTAINER" --format "{{range .Config.Env}}{{println .}}{{end}}" \
    | grep GF_SECURITY_ADMIN_PASSWORD | cut -d= -f2-)
  IP=$(docker inspect "$CONTAINER" --format "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}" \
    | awk "{print \$1}")
  AUTH=$(printf "admin:%s" "$PASS" | base64 -w0)

  RESULT=$(curl -s -X POST \
    -H "Authorization: Basic $AUTH" \
    -H "Content-Type: application/json" \
    "http://${IP}:3000/api/admin/provisioning/dashboards/reload" 2>&1)

  if echo "$RESULT" | grep -q "reloaded"; then
    echo "[$stack] reload OK"
  else
    echo "[$stack] reload FAILED: $RESULT"
    echo "[$stack] Trying docker restart instead..."
    docker restart "$CONTAINER"
    echo "[$stack] restarted"
  fi
done
echo "Done."
'
