<!--
Sync Impact Report - Constitution v1.1.0
========================================

Version Change: 1.0.0 → 1.1.0
Change Type: MINOR (architectural philosophy expansion)
Date: 2026-01-08

Sections Modified:
- Added "Architecture Philosophy" section (new principle VI)
- Expanded Security Requirements to include SSR context
- Clarified dual-interface design pattern

New Principle Added:
6. Headless Architecture - SSR for agencies, Odoo Web for managers

Rationale for Version Bump:
- Material expansion of architectural guidance
- New non-negotiable principle added (Principle VI)
- Backward compatible (no existing principles removed/redefined)
- Clarifies intended use of Odoo framework vs headless frontend

Template Files Status:
✅ plan-template.md - "Constitution Check" gate remains aligned
✅ spec-template.md - User scenarios compatible with headless SSR architecture
✅ tasks-template.md - Test-first workflow unchanged
✅ docs/constitution.md - Updated with detailed architecture philosophy (source of this amendment)

Propagation Complete:
✅ Core principle added to .specify/memory/constitution.md
✅ Detailed documentation in docs/constitution.md
✅ Architecture diagrams updated in docs/constitution.md

Follow-up Actions: None
Previous Amendment: 2026-01-07 (v1.0.0 initial codification)
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
- HATEOAS hypermedia links (ADR-007, planned Phase 3)
- JSON request/response formats
- Consistent error responses (`success_response()`, `error_response()`)
- Master data endpoints for frontend hydration

**Rationale**: Headless frontend architecture requires well-documented, discoverable APIs. HATEOAS enables frontend evolution without hardcoded URLs.

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
     E2E (54 Cypress tests)
    /____\
   /      \  Integration (190 HTTP tests)
  /________\
 /          \ Unit (99 tests)
```

### Required Tests per Feature
- **Unit**: Services, helpers, serializers, decorators
- **Integration**: All CRUD endpoints (success + 401 + validation + 404 + permissions)
- **E2E**: At least one complete journey per major feature

### Code Quality Gates
- Linting: `ruff` + `black` (automated via `./lint.sh`)
- Coverage: ≥80% (measured, enforced in CI)
- Documentation: OpenAPI schemas for all endpoints
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
- **MINOR**: New principle/section added or material expansion
- **PATCH**: Clarifications, wording, typo fixes

### Compliance Review
- All PRs MUST verify compliance with active ADRs
- Constitution violations require explicit justification + approval
- AI agents MUST consult `.specify/memory/constitution.md` before making architectural decisions

### Runtime Guidance
- AI agents use `.github/copilot-instructions.md` for operational rules
- Constitution provides strategic direction; copilot-instructions provides tactical rules
- Conflicts resolved in favor of constitution (strategic supersedes tactical)

**Version**: 1.1.0 | **Ratified**: 2026-01-03 | **Last Amended**: 2026-01-08
