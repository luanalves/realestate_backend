#!/usr/bin/env bash
# validate_openapi_sync.sh
#
# Compara as rotas declaradas em docs/openapi/proposals.yaml com as rotas
# realmente registradas em proposal_controller.py.
# Falha (exit 1) se houver rota no controller sem entrada no YAML ou vice-versa.
#
# Uso: bash scripts/validate_openapi_sync.sh
# CI:  executar antes do merge de qualquer PR que toque controllers ou proposals.yaml

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTROLLER="$REPO_ROOT/18.0/extra-addons/quicksol_estate/controllers/proposal_controller.py"
OPENAPI_YAML="$REPO_ROOT/docs/openapi/proposals.yaml"

# --------------------------------------------------------------------------- #
# Normaliza rota Odoo (<int:proposal_id>) → OpenAPI ({id})                    #
# --------------------------------------------------------------------------- #
normalize_odoo_route() {
    echo "$1" | sed 's|<[^>]*:\([^>]*\)>|{\1}|g' | sed 's|{proposal_id}|{id}|g'
}

# --------------------------------------------------------------------------- #
# Extrai rotas do controller (sem duplicatas)                                  #
# --------------------------------------------------------------------------- #
controller_routes() {
    grep "@http.route(" "$CONTROLLER" \
        | sed "s/.*route('\\([^']*\\)'.*/\\1/" \
        | sort -u \
        | while read -r route; do
            normalize_odoo_route "$route"
        done \
        | sort -u
}

# --------------------------------------------------------------------------- #
# Extrai paths do YAML OpenAPI                                                 #
# --------------------------------------------------------------------------- #
yaml_paths() {
    grep -E "^  /api" "$OPENAPI_YAML" \
        | sed 's|:||' \
        | tr -d ' ' \
        | sort -u
}

# --------------------------------------------------------------------------- #
# Comparação                                                                   #
# --------------------------------------------------------------------------- #
CONTROLLER_ROUTES=$(controller_routes)
YAML_PATHS=$(yaml_paths)

MISSING_IN_YAML=$(comm -23 <(echo "$CONTROLLER_ROUTES") <(echo "$YAML_PATHS"))
ORPHAN_IN_YAML=$(comm -13 <(echo "$CONTROLLER_ROUTES") <(echo "$YAML_PATHS"))

EXIT=0

if [[ -n "$MISSING_IN_YAML" ]]; then
    echo "❌ Rotas no controller SEM entrada em proposals.yaml:"
    echo "$MISSING_IN_YAML" | sed 's/^/   - /'
    EXIT=1
fi

if [[ -n "$ORPHAN_IN_YAML" ]]; then
    echo "⚠️  Paths em proposals.yaml SEM rota correspondente no controller:"
    echo "$ORPHAN_IN_YAML" | sed 's/^/   - /'
    EXIT=1
fi

if [[ $EXIT -eq 0 ]]; then
    echo "✅ proposals.yaml em sincronia com proposal_controller.py ($(echo "$CONTROLLER_ROUTES" | wc -l | tr -d ' ') rotas)"
fi

exit $EXIT
