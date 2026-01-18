# Agent Management - Quick Start Guide

Guia rápido para implementar o sistema de gerenciamento de agentes imobiliários.

## 🎯 Overview

Este módulo implementa gerenciamento completo de agentes com:
- ✅ Validação CRECI (ADR-012)
- ✅ Regras de comissão versionadas (ADR-013)
- ✅ Atribuição many2many agente-propriedade (ADR-014)
- ✅ Soft-delete com preservação de histórico (ADR-015)
- ✅ Multi-tenancy (ADR-008)
- ✅ REST API com OpenAPI 3.0 (ADR-005)

## 📋 Prerequisites

### Sistema
- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (cache/sessions)
- Odoo 18.0

### Bibliotecas Python
```bash
pip install validate-docbr  # Validação CPF/CNPJ
pip install phonenumbers     # Validação telefone
pip install requests         # HTTP client para CRECI API
```

### Configuração Odoo
```ini
# odoo.conf
[options]
db_name = realestate
admin_passwd = admin
http_port = 8069

# Redis cache (ADR-011)
enable_redis = True
redis_host = localhost
redis_port = 6379
redis_dbindex = 1
redis_pass = False

# Multi-tenancy
dbfilter = ^realestate$
```

## 🚀 Installation

### Step 1: Clonar repositório

```bash
cd 18.0/extra-addons
git clone <repo-url> quicksol_estate
cd quicksol_estate
```

### Step 2: Instalar módulo

```bash
# Método 1: Via Odoo CLI
docker compose exec odoo odoo -d realestate -i quicksol_estate --stop-after-init

# Método 2: Via web interface
# 1. Acessar http://localhost:8069
# 2. Apps > Update Apps List
# 3. Buscar "Real Estate - Agent Management"
# 4. Instalar
```

### Step 3: Configurar companies (Multi-tenancy)

```python
# Via Odoo shell
docker compose exec odoo odoo shell -d realestate

# Criar empresa teste
Company = env['thedevkitchen.estate.company']
company = Company.create({
    'name': 'Imobiliária ABC',
    'email': 'contato@imobiliariabc.com',
    'phone': '+55 11 3333-4444',
})
```

## 📁 Project Structure

```
quicksol_estate/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── agent.py                      # 🆕 real.estate.agent
│   ├── commission_rule.py            # 🆕 real.estate.commission.rule
│   ├── commission_transaction.py     # 🆕 real.estate.commission.transaction
│   └── agent_property_assignment.py  # 🆕 real.estate.agent.property.assignment
├── controllers/
│   ├── __init__.py
│   └── agent_controller.py           # 🆕 REST API endpoints
├── services/
│   ├── __init__.py
│   └── creci_validator.py            # 🆕 CRECI validation service
├── security/
│   ├── ir.model.access.csv           # 🆕 Access rights
│   └── agent_security.xml            # 🆕 Record rules
├── views/
│   ├── agent_views.xml               # 🆕 Agent form/tree/search
│   ├── commission_rule_views.xml     # 🆕 Commission rules
│   └── assignment_views.xml          # 🆕 Assignments
├── data/
│   └── agent_demo.xml                # 🆕 Demo data
└── tests/
    ├── __init__.py
    ├── test_agent_crud.py            # 🆕 Unit tests
    ├── test_creci_validation.py      # 🆕 CRECI tests
    ├── test_commission_calculation.py # 🆕 Commission tests
    └── test_soft_delete.py           # 🆕 Soft-delete tests
```

## 🔧 Implementation Steps

### Phase 1: Models (Week 1)

**Priority**: HIGH

```bash
# 1. Create model files
touch models/agent.py
touch models/commission_rule.py
touch models/commission_transaction.py
touch models/agent_property_assignment.py

# 2. Implement models (see data-model.md for details)

# 3. Add to __init__.py
# models/__init__.py
from . import agent
from . import commission_rule
from . import commission_transaction
from . import agent_property_assignment

# 4. Update module
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init
```

**Checklist**:
- [ ] Agent model with CRECI fields
- [ ] CommissionRule model with versioning
- [ ] CommissionTransaction model with snapshots
- [ ] Assignment many2many junction table
- [ ] SQL constraints (CRECI format, percentage range)
- [ ] Computed fields (is_active, commission_count)
- [ ] Security rules (ir.model.access.csv)

### Phase 2: CRECI Validation (Week 1)

**Priority**: HIGH

```bash
# 1. Create CRECI validator service
touch services/creci_validator.py

# 2. Implement validation logic
# See ADR-012 for validation algorithm

# 3. Add validation to Agent model
# models/agent.py
@api.constrains('creci_number', 'creci_state')
def _check_creci_format(self):
    # Validation logic here
    pass
```

**Checklist**:
- [ ] CRECI format validation (6-8 digits)
- [ ] UF validation (valid Brazilian states)
- [ ] Duplicate CRECI check (unique per state)
- [ ] Optional: COFECI API integration
- [ ] Unit tests for all validation scenarios

### Phase 3: REST API Endpoints (Week 2)

**Priority**: HIGH

```bash
# 1. Create controller
touch controllers/agent_controller.py

# 2. Implement endpoints (see contracts/agent.schema.yaml)

# 3. Add security decorators (ADR-011)
@http.route('/api/v1/agents', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def list_agents(self, **kwargs):
    pass
```

**Checklist**:
- [ ] GET /api/v1/agents (list with filtering)
- [ ] POST /api/v1/agents (create)
- [ ] GET /api/v1/agents/{id} (retrieve)
- [ ] PUT /api/v1/agents/{id} (update)
- [ ] DELETE /api/v1/agents/{id} (soft-delete)
- [ ] POST /api/v1/agents/{id}/deactivate
- [ ] POST /api/v1/agents/{id}/reactivate
- [ ] HATEOAS links (ADR-007)
- [ ] OpenAPI documentation (ADR-005)

### Phase 4: Commission System (Week 2)

**Priority**: MEDIUM

```bash
# 1. Implement commission calculation
# models/agent.py
def calculate_commission(self, transaction_value, transaction_type, transaction_date):
    # Find active rule at transaction_date
    # Calculate based on structure_type (percentage/fixed/tiered)
    # Return amount + metadata
    pass

# 2. Integrate with sale/lease confirmation
# models/sale.py
def action_confirm_sale(self):
    super().action_confirm_sale()
    self._create_commission_transactions()
```

**Checklist**:
- [ ] Commission calculation algorithm
- [ ] Tiered commission support
- [ ] Min/max caps
- [ ] Rule versioning (create_new_version)
- [ ] Snapshot creation (rule_snapshot JSON)
- [ ] Multi-agent split (split_percentage)
- [ ] Payment tracking (payment_status)

### Phase 5: Views & UI (Week 3)

**Priority**: MEDIUM

```bash
# 1. Create view files
touch views/agent_views.xml
touch views/commission_rule_views.xml

# 2. Implement Odoo views
# - Tree view (list)
# - Form view (detail)
# - Search view (filters)
# - Kanban view (cards)

# 3. Add menu items
```

**Checklist**:
- [ ] Agent tree/form/search views
- [ ] Commission rule tree/form views
- [ ] Assignment kanban view
- [ ] Smart buttons (properties count, commissions count)
- [ ] Notebook tabs (commission rules, assignments, history)
- [ ] Archive/Unarchive actions

### Phase 6: Tests (Week 3)

**Priority**: MANDATORY (ADR-003)

```bash
# 1. Create test files
touch tests/test_agent_crud.py
touch tests/test_creci_validation.py
touch tests/test_commission_calculation.py
touch tests/test_soft_delete.py

# 2. Run tests
docker compose exec odoo odoo -d realestate --test-enable --test-tags=quicksol_estate --stop-after-init

# 3. Cypress E2E tests (ADR-002)
cd ../../cypress
npm test -- --spec e2e/agent-management.cy.js
```

**Checklist**:
- [ ] Unit: Agent CRUD operations
- [ ] Unit: CRECI validation (format, duplicates)
- [ ] Unit: Commission calculation (%, fixed, tiered)
- [ ] Unit: Soft-delete (active field, queries)
- [ ] Integration: Sale → Commission transaction creation
- [ ] Integration: Multi-agent commission split
- [ ] Isolation: Multi-tenancy (company filtering)
- [ ] E2E: Complete agent lifecycle (Cypress)

## 🔍 Testing

### Unit Tests

```bash
# Run all quicksol_estate tests
docker compose exec odoo odoo -d realestate \
  --test-enable \
  --test-tags=quicksol_estate \
  --stop-after-init

# Run specific test class
docker compose exec odoo odoo -d realestate \
  --test-enable \
  --test-tags=quicksol_estate.test_agent_crud \
  --stop-after-init
```

### API Tests (Cypress)

```bash
cd ../../cypress
npm install
npm test -- --spec e2e/agent-management.cy.js
```

### Manual Testing (Postman/curl)

```bash
# 1. Get OAuth token
curl -X POST http://localhost:8069/api/v1/oauth/token \
  -d "grant_type=password&username=admin&password=admin"

# 2. Create agent
curl -X POST http://localhost:8069/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao@example.com",
    "creci_number": "123456",
    "creci_state": "SP",
    "company_ids": [1]
  }'
```

## 📊 Data Model Summary

### Tables Created

| Table | Rows (estimated) | Purpose |
|-------|------------------|---------|
| `real_estate_agent` | 100-1000 | Agent master data |
| `real_estate_commission_rule` | 200-2000 | Commission templates |
| `real_estate_commission_transaction` | 10k-100k | Immutable commission records |
| `real_estate_agent_property_assignment` | 1k-10k | Many2many junction |
| `thedevkitchen_company_agent_rel` | 100-1000 | Company-agent many2many |

### Indexes Created

```sql
-- Agent CRECI lookup
CREATE UNIQUE INDEX idx_agent_creci_unique 
ON real_estate_agent(creci_number, creci_state, company_id) 
WHERE active = true;

-- Commission rule active lookup
CREATE INDEX idx_commission_rule_active_lookup 
ON real_estate_commission_rule(agent_id, transaction_type, valid_from DESC, valid_until) 
WHERE active = true;

-- Assignment queries
CREATE INDEX idx_assignment_agent_property 
ON real_estate_agent_property_assignment(agent_id, property_id);
```

## 🎯 Quick Wins

### Day 1: Basic Agent CRUD
- Create Agent model
- Add REST API endpoints
- Test with curl

### Day 2: CRECI Validation
- Implement CRECI format validation
- Add unique constraint
- Test edge cases

### Day 3: Commission Rules
- Create CommissionRule model
- Implement percentage calculation
- Test non-retroactivity

### Week 1: MVP
- Agent CRUD working
- CRECI validation complete
- Basic commission calculation
- Unit tests passing

## 🚨 Common Pitfalls

### ❌ Pitfall 1: Forgetting `active_test=False`

```python
# WRONG - only returns active agents
agents = env['real.estate.agent'].search([])

# CORRECT - returns all agents
agents = env['real.estate.agent'].with_context(active_test=False).search([])
```

### ❌ Pitfall 2: Hard-coding company_id

```python
# WRONG - breaks multi-tenancy
agent = env['real.estate.agent'].create({
    'name': 'João',
    'company_id': 1,  # Hard-coded!
})

# CORRECT - use context company
agent = env['real.estate.agent'].create({
    'name': 'João',
    'company_ids': [(6, 0, env.context.get('allowed_company_ids', []))],
})
```

### ❌ Pitfall 3: Modifying commission transactions

```python
# WRONG - transactions are immutable!
transaction.write({'commission_amount': 20000})

# CORRECT - create new transaction if needed
# (Usually not needed - snapshots prevent retroactive changes)
```

## 📚 Next Steps

1. **Read ADRs**: 
   - [ADR-012](../../docs/adr/ADR-012-creci-validation-brazilian-real-estate.md)
   - [ADR-013](../../docs/adr/ADR-013-commission-calculation-rule-management.md)
   - [ADR-014](../../docs/adr/ADR-014-odoo-many2many-agent-property-relationship.md)
   - [ADR-015](../../docs/adr/ADR-015-soft-delete-logical-deletion-odoo-models.md)

2. **Review Research**: [research.md](./research.md)

3. **Check Data Models**: [data-model.md](./data-model.md)

4. **Read API Contracts**: [contracts/](./contracts/)

5. **Follow Implementation**: Track progress in [plan.md](./plan.md)

## 🆘 Support

- **Issues**: GitHub Issues
- **Docs**: `/docs/adr/`
- **Tests**: Run with `--test-enable`
- **API Docs**: http://localhost:8069/api/v1/docs

## ✅ Success Criteria

Agent management is production-ready when:
- ✅ All unit tests pass (100% coverage)
- ✅ All Cypress E2E tests pass
- ✅ CRECI validation working correctly
- ✅ Commission calculation accurate (non-retroactive)
- ✅ Multi-tenancy isolation verified
- ✅ OpenAPI docs complete
- ✅ Performance: < 500ms for agent list, < 100ms for commission calc
