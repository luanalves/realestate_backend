# Integration Tests - REST API E2E

**Location**: `/integration_tests/` (raiz do repositório)  
**Framework**: curl/bash scripts  
**Purpose**: Test REST API endpoints against real running Odoo instance

## ⚠️ Diferença Importante

Este diretório é **diferente** de `18.0/extra-addons/quicksol_estate/tests/integration/`:

| Localização | Framework | Propósito |
|-------------|-----------|-----------|
| **`integration_tests/`** (raiz) | curl/bash | Testa **endpoints REST** via HTTP |
| `quicksol_estate/tests/integration/` | TransactionCase | Testa **models Odoo** via ORM |

## Por que curl em vez de HttpCase?

Segundo **ADR-002**, HttpCase é proibido porque:
- ❌ Executa em transações read-only
- ❌ OAuth tokens não podem ser persistidos
- ❌ Sessions não funcionam corretamente
- ❌ Dados não persistem entre requisições
- ✅ **curl testa contra Odoo real** com persistência completa

## Test Structure

Each test file follows this pattern:
1. Start services: `docker compose up -d`
2. Obtain OAuth token
3. Execute API calls with curl
4. Validate responses with jq
5. Clean up test data

## Running Tests

```bash
# Start services first
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
docker compose up -d

# Wait for services to be ready
sleep 10

# Run all API tests
cd ../integration_tests
bash test_properties_api.sh
bash test_auth_api.sh

# Stop services
cd ../18.0
docker compose down
```

## Test Files

- `test_properties_api.sh` - Property CRUD operations
- `test_auth_api.sh` - OAuth authentication flow
- `test_agents_api.sh` - Agent management
- `test_rbac_api.sh` - RBAC permissions validation

## Guidelines

**✅ DO:**
- Use curl with proper error handling
- Validate HTTP status codes
- Parse JSON responses with jq
- Clean up created test data
- Test against localhost:8069

**❌ DON'T:**
- Use HttpCase (prohibited by ADR-002)
- Run tests without starting services
- Hardcode tokens or secrets
- Leave test data in database
