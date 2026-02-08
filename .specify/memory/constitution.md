<!--
Sync Impact Report - Constitution v1.2.0
========================================

Version Change: 1.1.0 → 1.2.0
Change Type: MINOR (new reference implementation documented)
Date: 2026-02-08

Sections Modified:
- Updated test statistics in Quality & Testing Standards
- Added Feature 007 as reference implementation example
- Updated Postman collection standards reference
- Confirmed ADR-016 compliance for API documentation

New Content Added:
- Postman Collection Standards section (API documentation requirement)
- Feature 007 Owner & Company Management as constitutional compliance example
- Updated test count statistics (E2E, Integration, Unit)

Constitutional Compliance Verification - Feature 007:
✅ Principle I (Security First): Dual auth pattern (@require_jwt + @require_session)
✅ Principle II (Test Coverage): Unit + Integration + E2E tests created
✅ Principle III (API-First): RESTful APIs with HATEOAS, Postman collection
✅ Principle IV (Multi-Tenancy): Company isolation enforced via @require_company
✅ Principle V (ADR Governance): ADR-016 compliance (Postman standards)
✅ Principle VI (Headless Architecture): REST APIs ready for SSR frontend

Reference Implementation:
- 9 REST endpoints (Owner & Company CRUD + relationships)
- Postman collection: docs/postman/feature007_owner_company_v1.0_postman_collection.json
- OAuth 2.0 + Session authentication flow documented
- Test scripts for token auto-population
- HATEOAS links in all responses

Template Files Status:
✅ constitution.md - Updated with Feature 007 reference
✅ ADR-016 standards fully applied
✅ Test pyramid statistics updated
✅ Postman collection examples added

Propagation Complete:
✅ Postman collection created following ADR-016
✅ Integration tests passing (test_feature007_oauth2.sh)
✅ Cypress UI tests created (company-management-ui.cy.js, owner-management-ui.cy.js)
✅ GET and PUT endpoints added to owner_api.py

Follow-up Actions: None - Feature 007 serves as template for future features
Previous Amendment: 2026-01-08 (v1.1.0 headless architecture principle)
-->

# Realestate Backend Platform Constitution

## Core Principles

### I. Security First (NON-NEGOTIABLE)
Every API endpoint MUST use defense-in-depth authentication:
- `@require_jwt` validates OAuth 2.0 JWT tokens
- `@require_session` ensures user identification and state (not replaceable by generic OAuth)
- `@require_company` enforces multi-tenant data isolation
- Public endpoints MUST explicitly document with `# public endpoint` comment
- Session hijacking protection via fingerprinting (IP + User-Agent + Language)

**Rationale**: Brazilian real estate data has legal and privacy implications. Multi-layered security prevents single-point authentication failures and ensures compliance with LGPD (Brazilian data protection law).

### II. Test Coverage Mandatory (NON-NEGOTIABLE)
All code MUST achieve minimum 80% test coverage (per ADR-003):
- Unit tests for business logic and utilities
- Integration tests for API endpoints (auth, validation, permissions, edge cases)
- E2E tests (Cypress) for complete user journeys
- Tests MUST be written before PR submission
- PRs automatically rejected if coverage drops below 80%

**Rationale**: Real estate transactions involve financial and legal commitments. High test coverage prevents regressions that could cause property mismatches, pricing errors, or data corruption.

### III. API-First Design (NON-NEGOTIABLE)
All features expose RESTful APIs with:
- OpenAPI 3.0 documentation (Swagger UI at `/api/docs`)
- Postman collections (ADR-016) for endpoint testing and documentation
- HATEOAS hypermedia links (ADR-007, planned Phase 3)
- JSON request/response formats
- Consistent error responses (`success_response()`, `error_response()`)
- Master data endpoints for frontend hydration

**Postman Collection Requirements** (ADR-016):
- Location: `/docs/postman/`
- Naming: `{feature}_v{major.minor}_postman_collection.json`
- Must include: OAuth flow, session management, test scripts
- Auto-save tokens to collection variables
- Proper headers: GET uses `X-Openerp-Session-Id` header, POST/PUT/DELETE use body
- **Reference**: Feature 007 collection (`feature007_owner_company_v1.0_postman_collection.json`)

**Rationale**: Headless frontend architecture requires well-documented, discoverable APIs. HATEOAS enables frontend evolution without hardcoded URLs. Postman collections provide executable documentation that doubles as integration testing tool.

### IV. Multi-Tenancy by Design (NON-NEGOTIABLE)
Complete data isolation per real estate company (ADR-008):
- Users belong to one or more `estate_company_ids`
- All queries filtered by company context via `@require_company`
- Creation/update operations validate company ownership
- Record Rules enforce isolation in Odoo Web UI
- No cross-company data leakage (tested via isolation tests)

**Rationale**: Brazilian real estate agencies compete directly. Data leakage between companies would violate confidentiality and business trust.

### V. ADR Governance
All architectural decisions documented as ADRs in `docs/adr/`:
- ADRs are authoritative for patterns, naming, workflows
- Code reviews MUST verify ADR compliance (especially ADR-001, ADR-011)
- New patterns require ADR creation before implementation
- ADRs include: context, decision, consequences, examples

**Rationale**: Distributed team + AI agents require consistent, searchable decision history to prevent pattern drift and ensure maintainability.

### VI. Headless Architecture (NON-NEGOTIABLE)
Platform employs dual-interface design:
- **Real Estate Agencies**: Headless SSR frontend (Next.js/React) consuming REST APIs
  - Enhanced security through SSR (credentials never reach client browser)
  - Better SEO for property listings
  - Modern UX/UI tailored for real estate workflows
  - Access via OAuth 2.0 REST APIs only (no direct Odoo Web access)
- **Platform Managers**: Odoo Web interface for system administration
  - Backend management, configuration, database administration
  - Direct Odoo Web UI access for operational oversight

**Why Odoo Framework**: Robust ORM, built-in multi-company support, security framework, proven scalability

**Rationale**: Complete UX control for agencies, SSR security advantages (sensitive data never in client-side code), API-first enables future mobile apps, frontend/backend independent evolution.

## Security Requirements

### Dual-Interface Security Model
- **Headless Frontend (SSR)**: Server-Side Rendering prevents credential exposure in client browser
  - Authentication tokens handled server-side only
  - API calls from SSR backend to Odoo backend
  - Public pages (property listings) benefit from SEO optimization
- **Odoo Web (Managers)**: Standard Odoo authentication for internal platform management

### Authentication Standards (ADR-009, ADR-011)
- OAuth 2.0 for application-to-application (Client Credentials Grant)
- Session-based with JWT for user authentication
- Token lifetime: 24 hours (configurable)
- Redis-backed session storage (DB index 1, AOF persistence)
- Rate limiting on authentication endpoints (brute-force protection)
- Audit logging for all security events

### Forbidden Patterns
- `.sudo()` abuse in controllers (bypasses security)
- `auth='public'` without `# public endpoint` comment
- Single decorator (`@require_jwt` alone without `@require_session`)
- Hardcoded credentials or secrets in code

## Quality & Testing Standards

### Test Pyramid (ADR-002, ADR-003)
```
     E2E (56 Cypress tests)
    /____\
   /      \  Integration (195+ HTTP tests)
  /________\
 /          \ Unit (100+ tests)
```

### Reference Implementations
**Feature 007 - Owner & Company Management** (Constitutional Compliance Template):
- **Security**: Dual auth (`@require_jwt` + `@require_session`), multi-tenancy enforced
- **API Design**: 9 REST endpoints with HATEOAS links
- **Testing**: Integration tests (test_feature007_oauth2.sh), Cypress UI tests (2 files)
- **Documentation**: Postman collection with OAuth flow and test scripts
- **Location**: `18.0/extra-addons/quicksol_estate/controllers/owner_api.py`
- **Postman**: `docs/postman/feature007_owner_company_v1.0_postman_collection.json`

Use Feature 007 as template for implementing new features that comply with all constitutional principles.

### Required Tests per Feature
- **Unit**: Services, helpers, serializers, decorators
- **Integration**: All CRUD endpoints (success + 401 + validation + 404 + permissions)
- **E2E**: At least one complete journey per major feature

### Test Creation - Prompts Obrigatórios
Para criação de testes, **DEVEM ser utilizados** os prompts e agents especializados:

| Recurso | Arquivo | Propósito |
|---------|---------|-----------|
| **Test Strategy Agent** | `.github/prompts/test-strategy.prompt.md` | Consultor que analisa e recomenda o tipo de teste correto (aplica "Regra de Ouro") |
| **Test Executor Agent** | `.github/prompts/test-executor.prompt.md` | Executor que cria código de teste automaticamente baseado nas recomendações |
| **SpecKit Tests Agent** | `.github/agents/speckit.tests.agent.md` | Gerador completo de testes baseado em cenários de aceitação (spec.md) |

**Fluxo Recomendado:**
```
1. Test Strategy Agent → Analisa código e recomenda tipo de teste
2. Test Executor Agent → Cria código baseado na recomendação
   OU
   SpecKit Tests Agent → Gera múltiplos testes a partir da spec.md
```

**Rationale**: Prompts especializados garantem consistência, aderência à ADR-003 e uso correto de credenciais do `.env`.

### Code Quality Gates
- Linting: `ruff` + `black` (automated via `./lint.sh`)
- Coverage: ≥80% (measured, enforced in CI)
- Documentation: OpenAPI schemas for all endpoints
- **API Documentation**: Postman collections (ADR-016) for all new features
- ADR compliance: Verified in code review

## Development Workflow (ADR-006)

### Git Flow
- **Main branches**: `main` (production), `develop` (staging)
- **Feature branches**: `feature/`, `bugfix/`, `hotfix/`
- **PR requirements**: Tests, documentation, ADR compliance, CODEOWNERS approval

### Module Structure (ADR-001, ADR-004)
```
{company}_{domain}/
├── controllers/    # API endpoints
├── models/         # Business logic (ORM)
├── services/       # Reusable business services
├── tests/          # Unit + Integration
│   ├── api/        # HTTP integration tests
│   └── utils/      # Unit tests
├── security/       # Access rules, record rules
└── data/           # Master data (XML)
```

### Naming Conventions (ADR-004)
- **Modules**: `{company}_{domain}` (e.g., `quicksol_estate`)
- **Models**: `{company}.{domain}.{entity}` (e.g., `thedevkitchen.estate.property`)
- **Controllers**: `{entity}_api.py` (e.g., `property_api.py`)
- **Tests**: `test_{entity}_{scope}.py` (e.g., `test_property_api.py`)

## Governance

### Amendment Process
1. Propose change via ADR (if architectural) or constitution amendment
2. Document rationale, impact, migration plan
3. Update constitution version (semantic versioning)
4. Propagate changes to templates and dependent docs
5. Require CODEOWNERS approval for constitution changes

### Versioning Policy
- **MAJOR**: Breaking governance changes (principle removal/redefinition)
- **MINOR**: New principle/section added, material expansion, or reference implementations documented
- **PATCH**: Clarifications, wording, typo fixes

### Compliance Review
- All PRs MUST verify compliance with active ADRs
- Constitution violations require explicit justification + approval
- AI agents MUST consult `.specify/memory/constitution.md` before making architectural decisions

### Runtime Guidance
- AI agents use `.github/copilot-instructions.md` for operational rules
- Constitution provides strategic direction; copilot-instructions provides tactical rules
- Conflicts resolved in favor of constitution (strategic supersedes tactical)

**Version**: 1.2.0 | **Ratified**: 2026-01-03 | **Last Amended**: 2026-02-08
