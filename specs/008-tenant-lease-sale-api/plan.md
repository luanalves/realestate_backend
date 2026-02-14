# Implementation Plan: Feature 008 - Tenant, Lease & Sale API

**Feature Branch**: `008-tenant-lease-sale-api`
**Estimated Duration**: 4 days
**Reference Spec**: [spec.md](spec.md)

---

## Overview

Implementar 18 endpoints REST para gerenciamento de Inquilinos (Tenants), Contratos de Aluguel (Leases) e Vendas (Sales), seguindo os padrões estabelecidos nos módulos existentes.

---

## Phase 1: Tenant API (Day 1)

### Tasks

| # | Task | File | Status |
|---|------|------|--------|
| 1.1 | Criar controller `tenant_api.py` | `controllers/tenant_api.py` | ⬜ |
| 1.2 | Implementar GET /api/v1/tenants (list) | `tenant_api.py` | ⬜ |
| 1.3 | Implementar POST /api/v1/tenants (create) | `tenant_api.py` | ⬜ |
| 1.4 | Implementar GET /api/v1/tenants/{id} | `tenant_api.py` | ⬜ |
| 1.5 | Implementar PUT /api/v1/tenants/{id} | `tenant_api.py` | ⬜ |
| 1.6 | Implementar DELETE /api/v1/tenants/{id} | `tenant_api.py` | ⬜ |
| 1.7 | Implementar GET /api/v1/tenants/{id}/leases | `tenant_api.py` | ⬜ |
| 1.8 | Registrar controller em `__init__.py` | `controllers/__init__.py` | ⬜ |
| 1.9 | Adicionar Swagger documentation | `data/api_endpoints.xml` | ⬜ |
| 1.10 | Testar manualmente via curl/Postman | - | ⬜ |

### Acceptance Criteria
- [ ] Todos os 6 endpoints de tenant funcionando
- [ ] company_ids required no list
- [ ] Soft delete funcionando (active=false)
- [ ] Swagger atualizado

---

## Phase 2: Lease API (Day 2)

### Tasks

| # | Task | File | Status |
|---|------|------|--------|
| 2.1 | Criar controller `lease_api.py` | `controllers/lease_api.py` | ⬜ |
| 2.2 | Implementar GET /api/v1/leases (list) | `lease_api.py` | ⬜ |
| 2.3 | Implementar POST /api/v1/leases (create) | `lease_api.py` | ⬜ |
| 2.4 | Implementar GET /api/v1/leases/{id} | `lease_api.py` | ⬜ |
| 2.5 | Implementar PUT /api/v1/leases/{id} | `lease_api.py` | ⬜ |
| 2.6 | Implementar DELETE /api/v1/leases/{id} | `lease_api.py` | ⬜ |
| 2.7 | Implementar POST /api/v1/leases/{id}/renew | `lease_api.py` | ⬜ |
| 2.8 | Implementar POST /api/v1/leases/{id}/terminate | `lease_api.py` | ⬜ |
| 2.9 | Registrar controller em `__init__.py` | `controllers/__init__.py` | ⬜ |
| 2.10 | Adicionar Swagger documentation | `data/api_endpoints.xml` | ⬜ |
| 2.11 | Validar date constraints no model | `models/lease.py` | ⬜ |
| 2.12 | Testar manualmente | - | ⬜ |

### Acceptance Criteria
- [ ] Todos os 7 endpoints de lease funcionando
- [ ] Validação end_date > start_date
- [ ] Renew cria novo período com start_date = old end_date
- [ ] Terminate encerra contrato antecipadamente
- [ ] company_ids required no list

---

## Phase 3: Sale API (Day 3)

### Tasks

| # | Task | File | Status |
|---|------|------|--------|
| 3.1 | Criar controller `sale_api.py` | `controllers/sale_api.py` | ⬜ |
| 3.2 | Implementar GET /api/v1/sales (list) | `sale_api.py` | ⬜ |
| 3.3 | Implementar POST /api/v1/sales (create) | `sale_api.py` | ⬜ |
| 3.4 | Implementar GET /api/v1/sales/{id} | `sale_api.py` | ⬜ |
| 3.5 | Implementar PUT /api/v1/sales/{id} | `sale_api.py` | ⬜ |
| 3.6 | Implementar POST /api/v1/sales/{id}/cancel | `sale_api.py` | ⬜ |
| 3.7 | Registrar controller em `__init__.py` | `controllers/__init__.py` | ⬜ |
| 3.8 | Adicionar Swagger documentation | `data/api_endpoints.xml` | ⬜ |
| 3.9 | Validar sale_price > 0 no model | `models/sale.py` | ⬜ |
| 3.10 | Verificar evento sale.created | - | ⬜ |
| 3.11 | Testar manualmente | - | ⬜ |

### Acceptance Criteria
- [ ] Todos os 5 endpoints de sale funcionando
- [ ] Validação sale_price > 0
- [ ] Cancel altera status para 'cancelled'
- [ ] Agent validation (same company)
- [ ] company_ids required no list

---

## Phase 4: Testing & Documentation (Day 4)

### Tasks

| # | Task | File | Status |
|---|------|------|--------|
| 4.1 | Criar test_us8_s1_tenants.sh | `integration_tests/` | ⬜ |
| 4.2 | Criar test_us8_s2_leases.sh | `integration_tests/` | ⬜ |
| 4.3 | Criar test_us8_s3_sales.sh | `integration_tests/` | ⬜ |
| 4.4 | Criar test_us8_s4_multitenancy.sh | `integration_tests/` | ⬜ |
| 4.5 | Atualizar Postman collection v1.9 | `docs/postman/` | ⬜ |
| 4.6 | Rodar linter (lint.sh) | - | ⬜ |
| 4.7 | Rodar todos os testes | - | ⬜ |
| 4.8 | Commit e PR | - | ⬜ |

### Acceptance Criteria
- [ ] Todos os testes passando
- [ ] Linter sem erros
- [ ] Postman collection atualizado
- [ ] PR criado e aprovado

---

## Dependencies

### Pre-requisites
- [x] Models existem: `real.estate.tenant`, `real.estate.lease`, `real.estate.sale`
- [x] Authentication decorators disponíveis
- [x] Padrão company_ids estabelecido

### Files to Modify

| File | Action |
|------|--------|
| `controllers/__init__.py` | Import novos controllers |
| `data/api_endpoints.xml` | 18 novos endpoints Swagger |

### Files to Create

| File | Description |
|------|-------------|
| `controllers/tenant_api.py` | Tenant REST controller |
| `controllers/lease_api.py` | Lease REST controller |
| `controllers/sale_api.py` | Sale REST controller |
| `integration_tests/test_us8_s1_tenants.sh` | Tenant tests |
| `integration_tests/test_us8_s2_leases.sh` | Lease tests |
| `integration_tests/test_us8_s3_sales.sh` | Sale tests |
| `integration_tests/test_us8_s4_multitenancy.sh` | Isolation tests |
| `docs/postman/quicksol_api_v1.9_postman_collection.json` | Updated collection |

---

## Reference Code Patterns

### Controller Pattern (from agent_api.py)

```python
@http.route('/api/v1/tenants', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def list_tenants(self, **kwargs):
    # Validate company_ids required
    company_ids_param = kwargs.get('company_ids')
    if not company_ids_param:
        return error_response(400, 'company_ids parameter is required')
    
    # Parse and validate
    requested_company_ids = [int(cid.strip()) for cid in company_ids_param.split(',')]
    if request.user_company_ids:
        unauthorized = [cid for cid in requested_company_ids if cid not in request.user_company_ids]
        if unauthorized:
            return error_response(403, f'Access denied to company IDs: {unauthorized}')
    
    # Query with domain
    domain = [('company_ids', 'in', requested_company_ids)]
    # ... rest of implementation
```

### Soft Delete Pattern

```python
def delete_tenant(self, id, **kwargs):
    tenant = request.env['real.estate.tenant'].sudo().browse(int(id))
    if not tenant.exists():
        return error_response(404, 'Tenant not found')
    
    tenant.write({'active': False})  # Soft delete
    return json_response({'message': 'Tenant archived successfully'})
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Models may have different field names | Review models before implementation |
| Missing company_ids in sale model | Add if needed, or use company_id |
| Lease renew logic complexity | Start with simple implementation |

---

## Success Metrics

- [ ] **18 endpoints** implemented and working
- [ ] **100% test coverage** on validations
- [ ] **Postman v1.9** with all new endpoints
- [ ] **Swagger** updated with all endpoints
- [ ] **Linter passing** (pylint >= 8.0)
- [ ] **PR merged** to main

