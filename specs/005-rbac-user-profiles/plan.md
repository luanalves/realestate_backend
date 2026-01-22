# Implementation Plan: RBAC User Profiles System

**Branch**: `005-rbac-user-profiles` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-rbac-user-profiles/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement comprehensive Role-Based Access Control (RBAC) with 9 predefined user profiles (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal User) using Odoo 18.0's native security framework. This feature enforces strict multi-tenancy data isolation via `estate_company_ids`, implements defense-in-depth security with record rules and ACLs at the ORM level, and adds commission split functionality for prospector/agent scenarios. All permissions are enforced through Odoo's `res.groups`, `ir.rule`, and `ir.model.access` mechanisms, ensuring LGPD compliance and zero cross-company data leakage. The implementation extends the existing `quicksol_estate` module with new security groups, record rules for each profile, field-level security, and a new `prospector_id` field on properties for commission split calculations (default 30% prospector, 70% selling agent).

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0 framework)  
**Primary Dependencies**: Odoo 18.0 (ORM, security framework), PostgreSQL 16, existing quicksol_estate module  
**Architecture Pattern**: Event-Driven (Observer Pattern - ADR-020) for decoupled business logic  
**Storage**: PostgreSQL 16 with multi-tenant isolation via `estate_company_ids` field on users  
**Testing**: pytest + Odoo test framework (unit/integration), Cypress 13.x (E2E security scenarios)  
**Target Platform**: Docker containers (Linux) - Odoo 18.0 running on Python 3.11  
**Project Type**: Odoo addon module extension (backend security layer - no frontend changes)  
**Performance Goals**: 
  - Permission checks: <100ms per database query
  - Record rule evaluation: <20% overhead on query execution time
  - Support 50 concurrent users across 10 companies without performance degradation
  - Group membership caching to minimize repeated lookups  
**Constraints**: 
  - Must use Odoo native security mechanisms only (res.groups, ir.rule, ir.model.access)
  - All permissions enforced at ORM level (not UI-only hiding)
  - Zero cross-company data leakage (100% isolation guarantee)
  - Commission split calculations must be deterministic and auditable
  - Backward compatible with existing agent/manager groups
  - No external authentication systems (Phase 1 - native Odoo only)  
**Scale/Scope**: 
  - 9 security groups (5 new + 4 existing groups restructured)
  - 40+ record rules (covering property, agent, lead, contract, commission, lease models)
  - 100+ ACL entries (CRUD permissions for 10+ models × 9 profiles)
  - 1 new field (prospector_id on real.estate.property)
  - 1 commission split calculation method
  - Initial deployment: 10 companies, 50 users
  - Expected growth: 50 companies, 500 users within 6 months

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Principle I: Security First (NON-NEGOTIABLE)

**Status**: PASS - Feature enhances security

- ✅ **Defense-in-depth authentication**: RBAC system enforces permissions at ORM level, complementing existing `@require_jwt`, `@require_session`, `@require_company` decorators
- ✅ **Multi-tenant isolation**: All record rules include `estate_company_ids` filtering per ADR-008
- ✅ **No public endpoints**: This is a backend security feature with no HTTP endpoints
- ✅ **Session protection**: Existing session fingerprinting remains intact

**Rationale**: RBAC strengthens security by implementing principle of least privilege. Each user profile has minimal permissions needed for their role, reducing blast radius of compromised accounts.

### ✅ Principle II: Test Coverage Mandatory (NON-NEGOTIABLE)

**Status**: PASS - Comprehensive test plan included

- ✅ **Unit tests**: Commission split calculation, group hierarchy, field-level security helpers
- ✅ **Integration tests**: Record rule enforcement for each profile (positive + negative tests)
  - Agents can only see their properties
  - Managers see all company data
  - Prospectors see only prospected properties
  - Portal users see only their own contracts
  - Cross-company isolation (Company A cannot see Company B)
- ✅ **E2E tests (Cypress)**: Complete user journeys for each of 9 profiles
- ✅ **Target coverage**: ≥80% per ADR-003

**Test Strategy**:
- 9 profiles × 5 scenarios/profile = 45 integration test cases minimum
- 10 edge cases from spec (multi-company users, profile changes, commission splits)
- Security-focused: test unauthorized access attempts return 403/404, not data

### ✅ Principle III: API-First Design (NON-NEGOTIABLE)

**Status**: PASS - No API changes required

- ✅ **No new REST endpoints**: This feature is backend security layer only
- ✅ **Existing APIs unchanged**: All existing endpoints (`/api/v1/properties`, `/api/v1/agents`, etc.) automatically inherit new permission rules
- ✅ **Transparent to clients**: Headless frontend sees filtered results based on authenticated user's profile
- ✅ **OpenAPI docs**: No updates needed (permissions are transparent to API consumers)

**Rationale**: RBAC is implemented at data access layer (Odoo ORM), so all existing API endpoints automatically respect new permission rules without code changes.

### ✅ Principle IV: Multi-Tenancy by Design (NON-NEGOTIABLE)

**Status**: PASS - Core feature focus

- ✅ **Complete data isolation**: Every record rule filters by `estate_company_ids`
- ✅ **Users belong to companies**: Existing `estate_company_ids` field on `res.users` (ADR-008)
- ✅ **@require_company enforcement**: All queries automatically scoped to user's companies
- ✅ **Zero data leakage**: Integration tests verify Company A users cannot access Company B data
- ✅ **Multi-company users**: Record rules use `('company_ids', 'in', user.estate_company_ids.ids)` to support users in multiple companies

**Example Record Rule (Agent)**:
```python
[
    '|',
        ('agent_id.user_id', '=', user.id),  # Agent's own properties
        ('assignment_ids.agent_id.user_id', '=', user.id),  # Assigned properties
    ('company_ids', 'in', user.estate_company_ids.ids)  # Company isolation
]
```

### ✅ Principle V: ADR Governance

**Status**: PASS - Implements ADR-019, ADR-020, and ADR-021

- ✅ **ADR-019**: This feature directly implements decisions from ADR-019 (RBAC Profiles in Multi-Tenancy)
- ✅ **ADR-020**: Uses Observer Pattern for decoupled business logic (auto-populate prospector, commission split, user validation)
- ✅ **ADR-021**: Uses Async Messaging (RabbitMQ/Celery) for bulk operations performance
- ✅ **ADR-004**: Follows naming convention `group_real_estate_<role>` for group XML IDs, `quicksol.observer.<domain>.<action>` for observers
- ✅ **ADR-008**: Respects multi-tenancy isolation patterns
- ✅ **ADR-003**: Adheres to test coverage mandates (observers tested independently with 80%+ coverage)
- ✅ **ADR-012**: Commission validation for prospector/agent splits
- ✅ **ADR-011**: No controller changes needed (security at ORM level)

**ADR Compliance**:
- Group naming: `group_real_estate_owner`, `group_real_estate_agent`, etc.
- Observer naming: `quicksol.observer.prospector.auto.assign`, `quicksol.observer.commission.split`, etc.
- Event naming: `property.before_create`, `commission.split.calculated`, `user.before_write`, etc.
- Display names: "Real Estate Owner", "Real Estate Agent", etc.
- Hierarchy: Director → Manager → User; Portal User → base.group_portal

### ✅ Principle VI: Headless Architecture (NON-NEGOTIABLE)

**Status**: PASS - Backend security only

- ✅ **Real Estate Agencies**: SSR frontend (Next.js) consumes REST APIs - no changes needed
- ✅ **Platform Managers**: Odoo Web interface benefits from new security groups for better access control
- ✅ **API-first**: All permissions enforced server-side; clients receive pre-filtered data
- ✅ **No frontend coupling**: Security is database/ORM layer, independent of UI

**Dual Interface Impact**:
- **SSR Frontend**: Transparent - API responses automatically filtered by user's profile
- **Odoo Web**: Enhanced - managers now have granular group selection when creating users

### 🎯 GATE STATUS: **PASS**

All 6 constitution principles satisfied. **Proceed to Phase 0 Research.**

**Post-Design Re-Check**: After Phase 1 (data-model.md, contracts/), verify:
- [ ] Record rules don't introduce N+1 query problems
- [ ] Commission split logic is deterministic and testable
- [ ] No `.sudo()` abuse in implementation
- [ ] Test coverage plan covers all 9 profiles × key models

## Project Structure

### Documentation (this feature)

```text
specs/005-rbac-user-profiles/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - existing patterns analysis
├── data-model.md        # Phase 1 output - groups, fields, record rules
├── quickstart.md        # Phase 1 output - developer implementation guide
├── contracts/           # Phase 1 output - N/A (no API changes)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**Odoo Module Structure** (existing `quicksol_estate` addon extension):

```text
18.0/extra-addons/quicksol_estate/
├── security/
│   ├── groups.xml                 # MODIFIED: Add 5 new groups (Owner, Director, Prospector, Receptionist, Financial, Legal)
│   ├── ir.model.access.csv        # MODIFIED: Add ACLs for all 9 profiles × 10+ models
│   ├── record_rules.xml           # MODIFIED: Add 40+ record rules for each profile
│   └── real_estate_security.xml   # EXISTING: Base security config (unchanged)
│
├── models/
│   ├── property.py                # MODIFIED: Add prospector_id field + emit events (ADR-020)
│   ├── commission_rule.py         # MODIFIED: Add commission split calculation + emit events
│   ├── agent.py                   # EXISTING: No changes (already has user_id field)
│   ├── res_users.py               # MODIFIED: Override create/write with event emission (ADR-020)
│   ├── lease.py                   # EXISTING: No changes (used by receptionist)
│   ├── commission_transaction.py  # EXISTING: Referenced by financial profile
│   ├── event_bus.py               # NEW: Central event dispatcher (ADR-020)
│   ├── __init__.py                # MODIFIED: Import updated models + observers
│   │
│   └── observers/                 # NEW DIRECTORY: Observer pattern implementation (ADR-020)
│       ├── __init__.py            # NEW
│       ├── abstract_observer.py  # NEW: Base class for all observers
│       ├── prospector_auto_assign_observer.py  # NEW: Auto-populate prospector_id
│       ├── commission_split_observer.py        # NEW: Create commission transactions
│       ├── user_company_validator_observer.py  # NEW: Validate multi-tenancy
│       └── security_group_audit_observer.py    # NEW: LGPD compliance logging
│
├── migrations/
│   └── 18.0.2.0.0/
│       ├── pre-migrate.py         # NEW: Backup existing group assignments
│       └── post-migrate.py        # NEW: Add prospector_id field, migrate data
│
├── tests/
│   ├── test_rbac_owner.py         # NEW: Owner profile tests (full access, user creation)
│   ├── test_rbac_director.py      # NEW: Director profile tests (reports, inheritance)
│   ├── test_rbac_manager.py       # NEW: Manager profile tests (all company data)
│   ├── test_rbac_agent.py         # NEW: Agent profile tests (own properties only)
│   ├── test_rbac_prospector.py    # NEW: Prospector profile tests (commission split)
│   ├── test_rbac_receptionist.py  # NEW: Receptionist profile tests (contracts, keys)
│   ├── test_rbac_financial.py     # NEW: Financial profile tests (commissions)
│   ├── test_rbac_legal.py         # NEW: Legal profile tests (contracts read-only)
│   ├── test_rbac_portal.py        # NEW: Portal user tests (own data only)
│   ├── test_rbac_multi_tenancy.py # NEW: Cross-company isolation tests
│   ├── test_commission_split.py   # NEW: Commission calculation logic tests
│   │
│   └── observers/                 # NEW DIRECTORY: Observer tests (ADR-020)
│       ├── test_prospector_auto_assign_observer.py  # NEW: Test auto-assign logic
│       ├── test_commission_split_observer.py        # NEW: Test transaction creation
│       ├── test_user_company_validator_observer.py  # NEW: Test validation logic
│       └── test_security_group_audit_observer.py    # NEW: Test audit logging
│
├── data/
│   └── default_groups.xml         # NEW: Optional demo data with sample users per profile
│
├── __manifest__.py                # MODIFIED: Update version to 18.0.2.0.0, add dependencies
└── README.md                      # MODIFIED: Document new RBAC system
```

**Cypress E2E Tests**:

```text
cypress/e2e/
├── rbac-owner-onboarding.cy.js       # NEW: Owner creates company, assigns users
├── rbac-agent-property-access.cy.js  # NEW: Agent creates property, sees only own
├── rbac-manager-oversight.cy.js      # NEW: Manager sees all company data
├── rbac-prospector-commission.cy.js  # NEW: Prospector registers property, commission split
├── rbac-portal-user-isolation.cy.js  # NEW: Portal user sees only own contracts
└── rbac-multi-tenancy-isolation.cy.js # NEW: Verify Company A cannot see Company B
```

**Structure Decision**: 

This is an **Odoo addon module extension** (not standalone app). We modify the existing `quicksol_estate` module by:

1. **Extending security/** - Add new groups and comprehensive record rules
2. **Adding models/observers/** - Implement Observer pattern (ADR-020) for decoupled business logic
3. **Modifying models/** - Add `prospector_id` field, emit events for observers
4. **Adding tests/** - 15+ test files (11 RBAC profiles + 4 observer tests) covering all scenarios
5. **Creating migrations/** - Ensure smooth upgrade from current version to RBAC-enabled version

**No frontend changes** - This is pure backend security. The existing SSR frontend (Next.js) and Odoo Web UI automatically respect new permissions through the ORM layer.

**Architecture Pattern (ADR-020 + ADR-021)**: Event-Driven using Observer Pattern com mensageria assíncrona para:
- Auto-populate prospector_id when prospector creates property
- Calculate and create commission transactions when sale completes
- Validate multi-tenancy isolation when owner creates/edits users
- Audit security group changes for LGPD compliance

**File Count Estimate**:
- Modified: 8 files (groups.xml, ir.model.access.csv, record_rules.xml, property.py, commission_rule.py, res_users.py, __manifest__.py, README.md)
- New: 22 files (4 observer classes + event_bus.py + abstract_observer.py + 11 RBAC test files + 4 observer test files + 2 migration scripts)
- Total touchpoints: ~30 files

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations detected** - All constitution principles are satisfied:

| Principle | Status | Notes |
|-----------|--------|-------|
| Security First | ✅ PASS | Enhances security with least-privilege RBAC |
| Test Coverage | ✅ PASS | 80%+ coverage plan with 11 test modules |
| API-First | ✅ PASS | No API changes; permissions transparent to clients |
| Multi-Tenancy | ✅ PASS | Core focus; all rules filter by estate_company_ids |
| ADR Governance | ✅ PASS | Implements ADR-019 decisions |
| Headless Architecture | ✅ PASS | Backend only; no frontend coupling |

**No complexity justification needed.**

## Phase 0: Research & Discovery

**Objective**: Analyze existing codebase patterns, resolve all NEEDS CLARIFICATION markers from Technical Context

**Output**: [research.md](research.md)

### Key Research Areas

1. **Existing Security Groups** - Analyzed 4 current groups (Manager, User, Agent, Portal User) to determine reuse vs new creation strategy
2. **Record Rule Patterns** - Studied existing multi-company filtering patterns to ensure consistency
3. **Commission Calculation** - Reviewed current commission model to identify integration points for split logic
4. **Test Patterns** - Examined existing test structure to replicate for new RBAC test modules

### Research Findings Summary

- ✅ **Reuse Strategy**: Keep 4 existing groups, add 5 new specialized groups (Owner, Director, Prospector, Receptionist, Financial, Legal)
- ✅ **Record Rule Pattern**: All use `[('company_ids', 'in', user.estate_company_ids.ids)]` for multi-tenancy
- ✅ **Commission Model**: Has `calculate_commission()` method; needs new `calculate_split_commission()` method
- ✅ **Test Structure**: Uses `TransactionCase` with `common.py` for shared test data setup

**Status**: ✅ COMPLETE - See [research.md](research.md) for full analysis

## Phase 1: Data Model & API Design

**Objective**: Define security groups, ACLs, record rules, field changes, and API contracts

### Deliverable 1: Data Model

**Output**: [data-model.md](data-model.md)

**Contents**:
- 9 security group definitions (XML format with hierarchy via `implied_ids`)
- ~100 ACL entries (CSV format: model × profile × CRUD permissions)
- 23+ record rules (XML format with domain logic for each profile)
- `prospector_id` field specification (Many2one to agent model)
- `calculate_split_commission()` method specification (returns dict with prospector/agent breakdown)
- Migration strategy (pre/post-migrate.py scripts, version bump to 18.0.2.0.0)

**Status**: ✅ COMPLETE - See [data-model.md](data-model.md)

### Deliverable 2: API Contracts

**Output**: N/A - No API changes required

**Rationale**: 
This feature implements backend security at the ORM level. All permissions are enforced transparently by Odoo's access control mechanisms. Existing REST API endpoints automatically respect the new security groups through the ORM, requiring no contract changes.

**Status**: ✅ N/A (SKIP)

### Deliverable 3: Developer Quickstart

**Output**: [quickstart.md](quickstart.md)

**Contents**:
- Step-by-step implementation guide (10 steps: groups → ACLs → record rules → fields → methods → tests → migration → deployment)
- Code examples for each step
- Testing commands (unit tests, E2E tests, coverage)
- Deployment checklist
- Troubleshooting guide
- Performance considerations

**Status**: ✅ COMPLETE - See [quickstart.md](quickstart.md)

### Deliverable 4: Agent Context Update

**Output**: Updated [.github/agents/copilot-instructions.md](../../.github/agents/copilot-instructions.md)

**Changes**:
- Added language: Python 3.11 (Odoo 18.0 framework)
- Added framework: Odoo 18.0 (ORM, security framework), PostgreSQL 16
- Added database: PostgreSQL 16 with multi-tenant isolation via `estate_company_ids`

**Status**: ✅ COMPLETE - Agent context registered

## Post-Design Constitution Re-Check

*Re-evaluate all 6 principles after data model design*

### ✅ Principle I: Security First (Re-Check)

**Status**: PASS - Implementation maintains security

- ✅ **No .sudo() abuse**: Record rules use proper domain filtering, no privilege escalation
- ✅ **No performance risks**: All record rules use indexed fields (company_ids, agent_id, prospector_id)
- ✅ **Deterministic logic**: Commission split uses system parameter (configurable, auditable)

### ✅ Principle II: Test Coverage (Re-Check)

**Status**: PASS - Test plan meets 80% target

- ✅ **11 test modules**: Cover all 9 profiles + multi-tenancy + commission split
- ✅ **Integration tests**: Workflow tests for each profile (create property, assign agent, etc.)
- ✅ **E2E tests**: 6 Cypress scenarios covering critical security boundaries
- ✅ **Coverage target**: pytest --cov configured for ≥80% line coverage

### ✅ Principle III: API-First (Re-Check)

**Status**: PASS - No API changes needed

- ✅ **Transparent security**: Existing REST endpoints automatically respect new groups
- ✅ **ORM-level filtering**: Clients receive pre-filtered data based on user profile
- ✅ **No breaking changes**: All existing API contracts remain valid

### ✅ Principle IV: Multi-Tenancy (Re-Check)

**Status**: PASS - Zero cross-company leakage

- ✅ **All record rules include company filter**: `[('company_ids', 'in', user.estate_company_ids.ids)]`
- ✅ **Field-level security**: prospector_id editable only by managers/owners (no cross-company manipulation)
- ✅ **Test coverage**: Multi-tenancy isolation tests verify Company A cannot access Company B data

### ✅ Principle V: ADR Governance (Re-Check)

**Status**: PASS - All ADR patterns followed

- ✅ **ADR-004 naming**: All group IDs follow `group_real_estate_<role>` pattern, observer IDs follow `quicksol.observer.<domain>.<action>`
- ✅ **ADR-020 architecture**: Observer pattern correctly implemented with event bus, abstract base, and concrete observers
- ✅ **ADR-012 validation**: Commission split preserves CRECI number validation
- ✅ **ADR-003 testing**: Test coverage plan exceeds minimum requirements (observers tested independently)

### ✅ Principle VI: Headless Architecture (Re-Check)

**Status**: PASS - Backend only, no frontend coupling

- ✅ **No UI changes**: Security enforced at database layer
- ✅ **SSR compatibility**: Next.js frontend consumes filtered API responses unchanged
- ✅ **Odoo Web enhancement**: Backend UI benefits from granular group selection

### 🎯 POST-DESIGN GATE STATUS: **PASS**

All 6 constitution principles re-validated. **Implementation plan approved.**

## Next Steps

**Planning phase complete.** Run the following command to generate implementation tasks:

```bash
/speckit.tasks
```

This will create [tasks.md](tasks.md) with:
- Prioritized task breakdown for each file change
- Dependency graph (tests depend on models, models depend on groups)
- Estimated effort per task
- Acceptance criteria linked to requirements in [spec.md](spec.md)

**Artifacts Generated**:
- ✅ [spec.md](spec.md) - Feature specification (671 lines, 77 requirements)
- ✅ [research.md](research.md) - Codebase pattern analysis (~400 lines)
- ✅ [data-model.md](data-model.md) - Complete implementation details with Observer pattern (~800 lines)
- ✅ [quickstart.md](quickstart.md) - Developer implementation guide
- ✅ [plan.md](plan.md) - This file
- ✅ [ADR-020](../../docs/adr/ADR-020-observer-pattern-odoo-event-driven-architecture.md) - Observer Pattern documentation
- ✅ [ADR-021](../../docs/adr/ADR-021-async-messaging-rabbitmq-celery.md) - Async Messaging documentation

**Branch**: `005-rbac-user-profiles`  
**Ready for**: Task generation → Implementation → Testing → Deployment

---

## Key Architectural Decisions

### 1. Observer Pattern (ADR-020)

**Rationale**: Desacoplar lógica de negócio dos métodos `create()`/`write()` do ORM para:
- ✅ Facilitar testes unitários isolados (cada observer testável independentemente)
- ✅ Permitir extensões sem modificar código existente (Open/Closed Principle)
- ✅ Melhorar manutenibilidade (cada observer tem responsabilidade única)

**Implementation**:
- Event Bus centralizado (`quicksol.event.bus`) para dispatch de eventos
- Abstract Observer base class (`quicksol.abstract.observer`) para padronizar observers
- 4 observers concretos: auto-assign prospector, commission split, user validation, security audit

**Trade-offs**:
- ➕ Testabilidade: Cada observer é 100% testável isoladamente
- ➕ Extensibilidade: Novos módulos podem adicionar observers sem conflitos
- ➖ Complexidade: Requer entendimento do pattern (mitigado por documentação ADR-020)
- ➖ Indireção: Não é óbvio olhando `property.py` que há lógica de auto-assign (mitigado por eventos bem nomeados)

### 2. Event Naming Convention

**Pattern**: `<model>.<action>` ou `<model>.before_<action>` ou `<model>.after_<action>`

**Examples**:
- `property.before_create` → Modificar vals antes de criar
- `property.created` → Reagir após criação
- `commission.split.calculated` → Processar split calculado
- `user.before_write` → Validar antes de atualizar

**Rationale**: Facilita discovery de observers (buscar por "property" mostra todos eventos relacionados)

### 3. Testing Strategy for Observers

**Pattern**: AAA (Arrange, Act, Assert) com testes isolados

```python
def test_prospector_auto_assign(self):
    # Arrange: Preparar dados sem criar property real
    data = {'vals': {'name': 'Test'}}
    
    # Act: Chamar observer diretamente
    observer.handle('property.before_create', data)
    
    # Assert: Verificar que vals foi modificado
    assert 'prospector_id' in data['vals']
```

**Benefits**:
- ✅ Testes rápidos (não criam registros no banco)
- ✅ Testes isolados (não dependem de outros observers)
- ✅ Fácil mockar dependências (só mockar dentro do observer)

**Coverage**: ≥80% por observer (ADR-003)
## Async Messaging Infrastructure (RabbitMQ + Celery)

### Rationale

Em operações em lote (bulk operations), observers síncronos bloqueiam o request:
- ❌ **Problema**: Importação de 1000 propriedades com audit logs = 1000 observadores síncronos = 30-50 minutos bloqueados
- ✅ **Solução**: Observers assíncronos via RabbitMQ + Celery = request retorna em ~5 segundos, processing em background

**Eventos que DEVEM ser síncronos**:
- Validações (`user.before_create`, `user.before_write`) - DEVEM falhar antes de criar/atualizar
- Auto-populate crítico (`prospector_id`) - Dados devem estar prontos imediatamente
- Cálculos financeiros em vendas individuais - Usuário espera confirmação na tela

**Eventos que PODEM ser assíncronos**:
- Audit logs (`user.created`, `property.created`) - LGPD não exige tempo real, eventual consistency aceitável (5-10 segundos)
- Notificações (emails, webhooks) - Usuário não precisa esperar envio
- Processamento pesado (PDFs, relatórios) - Better UX com background processing
- Bulk operations (importações) - Não bloquear servidor durante processamento massivo

### Architecture

```
Odoo ORM (create/write)
       ↓
   Event Bus
   /        \
Sync       Async (RabbitMQ)
  ↓            ↓
Observers   Celery Workers
            (background)
```

**Components**:
1. **RabbitMQ**: Message broker (rabbitmq:3-management-alpine)
2. **Celery Workers**: Executam observers assíncronos (Python 3.11-slim)
   - `celery_commission_worker`: Alta prioridade, 2 workers concorrentes
   - `celery_audit_worker`: Média prioridade, 1 worker
   - `celery_notification_worker`: Baixa prioridade, 1 worker
3. **Flower**: Dashboard de monitoramento (http://localhost:5555)
4. **Redis**: Result backend para tasks Celery (reuso do Redis existente)

### Queue Division Strategy (Multi-Queue Pattern)

**Problema**: Fila única cria "head-of-line blocking" - task lenta bloqueia tasks rápidas

**Solução**: 4 filas especializadas por domínio

| Queue | Eventos | Prioridade | Workers | Características |
|-------|---------|------------|---------|-----------------|
| **security_events** | `user.before_create`, `user.before_write` | N/A (síncrono) | N/A | Validações críticas processadas inline |
| **commission_events** | `commission.split.calculated` | Alta (9/10) | 2 | Cálculos financeiros, retry agressivo (3x) |
| **audit_events** | `user.created`, `property.created` | Média (5/10) | 1 | LGPD compliance, pode demorar 5-10 segundos |
| **notification_events** | `property.assignment.changed`, emails | Baixa (1/10) | 1 | Notificações, não-crítico se falhar |

**Benefícios**:
- ✅ Isolamento de falhas (fila de notificações parada não afeta comissões)
- ✅ Escalabilidade independente (adicionar workers só para comissões se necessário)
- ✅ Priorização (comissões processadas antes de audit logs)
- ✅ Debugging facilitado (logs por fila)

### EventBus Hybrid Implementation

```python
# models/event_bus.py

class EventBus(models.AbstractModel):
    _name = 'quicksol.event.bus'
    
    ASYNC_EVENTS = {
        'user.created': 'audit_events',
        'property.created': 'audit_events',
        'commission.split.calculated': 'commission_events'
    }
    
    @api.model
    def emit(self, event_name, data, force_sync=False):
        # 'before_*' events ALWAYS sync (validations)
        if event_name.startswith('before_'):
            return self._emit_sync(event_name, data)
        
        # Async events configured
        if event_name in self.ASYNC_EVENTS and not force_sync:
            return self._emit_async(event_name, data)  # Returns task_id
        
        # Default: sync
        return self._emit_sync(event_name, data)
    
    def _emit_async(self, event_name, data):
        from odoo.addons.thedevkitchen_celery.celery_client import process_event_task
        
        queue_name = self.ASYNC_EVENTS[event_name]
        task = process_event_task.apply_async(
            args=[event_name, data],
            queue=queue_name,
            priority=self._get_priority(event_name),
            retry=True,
            retry_policy={'max_retries': 3}
        )
        
        return task.id  # Client can poll status if needed
```

### Infrastructure Services (docker-compose.yml)

**Serviços adicionados**:
- `rabbitmq`: rabbitmq:3-management-alpine (portas 5672 AMQP, 15672 Management UI)
- `celery_commission_worker`: 2 workers concorrentes para commission_events
- `celery_audit_worker`: 1 worker para audit_events
- `celery_notification_worker`: 1 worker para notification_events
- `flower`: Dashboard de monitoramento (porta 5555)

**Variáveis de ambiente** (.env):
```bash
RABBITMQ_USER=odoo
RABBITMQ_PASSWORD=odoo_rabbitmq_secret_2026
CELERY_BROKER_URL=amqp://odoo:odoo_rabbitmq_secret_2026@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1
FLOWER_USER=admin
FLOWER_PASSWORD=flower_admin_2026
```

**Volumes**:
- `rabbitmq-data`: Persistência de mensagens RabbitMQ

**Healthchecks**:
- RabbitMQ: `rabbitmq-diagnostics ping` a cada 10s
- Workers dependem de RabbitMQ healthy antes de iniciar

### Performance Considerations

**Sync Observer (Individual Sale)**:
```
User clicks "Mark as Sold" → 
  emit('commission.split.calculated', sync=True) → 
  Observer creates 2 commission records → 
  Response: 200 OK (300ms total)
```

**Async Observer (Bulk Import)**:
```
Admin imports 1000 sales → 
  emit('commission.split.calculated', async=True) × 1000 → 
  Returns task_id immediately (5s total) →
  Celery processes 1000 events in background (2-3 minutes) →
  Admin can continue working
```

**Trade-offs**:
- ➕ Massive performance gains em bulk operations (5s vs 50 minutos)
- ➕ Resiliente (retry automático, dead letter queue)
- ➕ Escalável horizontalmente (adicionar workers = mais throughput)
- ➖ Complexidade operacional (+5 serviços Docker, +2.3GB RAM)
- ➖ Eventual consistency (audit logs podem demorar 5-10 segundos - aceitável)
- ➖ Debugging distribuído (precisar correlacionar logs de múltiplos workers)

**Fallback Strategy**:
Se RabbitMQ offline, EventBus automaticamente faz fallback para processamento síncrono:
```python
try:
    task_id = self._emit_async(event_name, data)
except ConnectionError:
    _logger.warning("RabbitMQ offline, fallback to sync processing")
    return self._emit_sync(event_name, data)
```

### Testing Async Observers

**Pattern**: Usar `force_sync=True` em testes para evitar dependência de RabbitMQ

```python
def test_audit_observer_creates_log(self):
    # Force sync execution for testing
    self.env['quicksol.event.bus'].emit(
        'user.created',
        {'user_id': 123, 'name': 'John'},
        force_sync=True  # Testa lógica sem RabbitMQ
    )
    
    log = self.env['quicksol.audit.log'].search([('user_id', '=', 123)])
    self.assertEqual(log.data, '{"user_id": 123, "name": "John"}')
```

**Integration Tests**: Validar async behavior com RabbitMQ local (docker-compose up)
```python
def test_async_returns_task_id(self):
    task_id = self.env['quicksol.event.bus'].emit('property.created', {'id': 1})
    self.assertTrue(isinstance(task_id, str))  # Celery task UUID
```

### Monitoring & Operations

**Flower UI** (http://localhost:5555):
- Visualizar filas, tasks, workers em tempo real
- Taxa de processamento, latência, erros por fila
- Retry history, dead letter queue

**RabbitMQ Management UI** (http://localhost:15672):
- Conexões ativas, canais AMQP
- Tamanho de filas, message rates
- Alertas se fila > 10000 mensagens (backlog)

**Key Metrics**:
- Commission queue: Latência média <500ms, taxa de processamento >100 tasks/min
- Audit queue: Latência aceitável <5s, taxa >50 tasks/min
- Retry rate: <5% de todas as tasks

### Deployment Checklist

**Infraestrutura**:
- [ ] RabbitMQ + 3 Celery workers + Flower rodando via `docker-compose up -d`
- [ ] Verificar healthcheck rabbitmq: `docker-compose ps` (should show "healthy")
- [ ] Acessar Flower UI (localhost:5555) e verificar workers conectados
- [ ] Acessar RabbitMQ UI (localhost:15672) e verificar 4 filas criadas

**Código**:
- [ ] EventBus com `emit_async()` implementado
- [ ] Observers com `_async_capable = True` flag
- [ ] Celery tasks em `celery_worker/tasks.py`
- [ ] ASYNC_EVENTS dict configurado com queue mapping

**Testes**:
- [ ] Unit tests de observers com `force_sync=True` (coverage >80%)
- [ ] Integration tests verificam task_id retornado em async mode
- [ ] Load test: importar 1000 propriedades em <10 segundos
- [ ] Fallback test: RabbitMQ offline → processamento síncrono funciona

**Documentação**:
- [ ] ADR-020 (Observer + Async Messaging) publicado
- [ ] docs/architecture/event-driven-rbac.md criado
- [ ] README.md atualizado com instruções de monitoramento

---

## Implementation History

### Portal User (User Story 10) - Resolution Completed (2026-01-20)

**Previous Status**: ⚠️ Record rules disabled due to missing partner fields

**Resolution Implemented**:
1. ✅ Added `buyer_partner_id` field to Sale model
2. ✅ Added `partner_id` field to Tenant model
3. ✅ Added `partner_id` field to PropertyOwner model
4. ✅ Added computed `owner_partner_id` field to Property model (related to owner_id.partner_id)
5. ✅ Enabled 3 Portal record rules in `security/record_rules.xml`
6. ✅ Removed `@unittest.skip` decorators from all 7 tests in `test_rbac_portal.py`
7. ✅ Module deployed successfully (Registry loaded in 2.462s)

**Portal Isolation Now Active**:
- Portal users see only sales where `buyer_partner_id = user.partner_id`
- Portal users see only leases where `tenant_id.partner_id = user.partner_id`
- Portal users see only assignments where `property_id.owner_partner_id = user.partner_id`

**Files Modified**:
- `models/sale.py`: Added buyer_partner_id (Many2one res.partner)
- `models/tenant.py`: Added partner_id (Many2one res.partner)
- `models/property_owner.py`: Added partner_id (Many2one res.partner)
- `models/property.py`: Added owner_partner_id (related field, stored)
- `security/record_rules.xml`: Uncommented 3 Portal rules
- `tests/test_rbac_portal.py`: Updated all 7 tests with required fields, removed skip decorators
- [ ] Swagger/Postman atualizados com endpoints de monitoring