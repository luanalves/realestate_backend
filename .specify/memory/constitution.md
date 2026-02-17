## Utilitários de Validação de CPF/CNPJ (Governança de Dados)

Para garantir unicidade, integridade e reutilização de validação de documentos fiscais brasileiros, o backend implementa as seguintes funções utilitárias em `utils/validators.py`:

- `normalize_document(document)`: Remove pontuação/máscara, retorna apenas dígitos.
- `is_cpf(document)`: Retorna True se for CPF válido.
- `is_cnpj(document)`: Retorna True se for CNPJ válido.
- `validate_document(document)`: Retorna True se for CPF ou CNPJ válido.

Essas funções devem ser usadas em todos os endpoints e modelos que aceitam documentos fiscais, garantindo padronização e governança de dados.
<!--
Sync Impact Report - Constitution v1.3.0
========================================

Version Change: 1.2.0 → 1.3.0
Change Type: MINOR (new reference implementation + security patterns documented)
Date: 2026-02-16

Sections Modified:
- Updated test statistics in Quality & Testing Standards
- Added Feature 009 as reference implementation for security patterns
- Added new security patterns section (token-based auth, anti-enumeration)
- Updated Forbidden Patterns with public endpoint marker requirement
- Added transactional email patterns (mail.template)
- Added singleton configuration model pattern
- Added rate limiting pattern documentation

New Content Added:
- **Security Patterns Section**: Token-based onboarding, anti-enumeration, public endpoint markers
- **Email Integration Patterns**: mail.template usage for transactional emails
- **Configuration Patterns**: Singleton model with validation constraints
- **Rate Limiting Patterns**: Redis-based with placeholder pattern
- **Atomic Transactions**: Dual record creation for portal entities
- **Session Management**: Session invalidation after password reset
- Feature 009 User Onboarding & Password Management as constitutional compliance example
- Updated test count statistics (Unit: 100+ → 190+)

Constitutional Compliance Verification - Feature 009:
✅ Principle I (Security First): Triple auth for invite (@require_jwt + @require_session + @require_company), anti-enumeration on forgot-password
✅ Principle II (Test Coverage): 90+ unit tests (4 test files), E2E tests, integration tests
✅ Principle III (API-First): 5 REST endpoints (1 authenticated invite, 3 public password, 1 resend)
✅ Principle IV (Multi-Tenancy): Token isolation via company_id, record rules enforced
✅ Principle V (ADR Governance): ADR-003 (testing), ADR-008 (anti-enumeration), ADR-011 (security), ADR-018 (validation)
✅ Principle VI (Headless Architecture): Public password endpoints for SSR frontend, authenticated invite for management

Reference Implementation - Feature 009:
- 5 REST endpoints (invite, set-password, forgot-password, reset-password, resend-invite)
- SHA-256 token hashing (UUID v4 → SHA-256 stored, raw token in email only)
- Anti-enumeration: forgot-password always returns 200 regardless of email existence
- Public endpoint pattern: `# public endpoint` comment above @http.route
- Email templates: mail.template integration with context variables
- Singleton settings: thedevkitchen.email.link.settings (TTL, rate limits)
- Authorization matrix: Owner→all 9 profiles, Manager→5 operational, Agent→owner+portal
- Portal dual record: Atomic res.users + real.estate.tenant via partner_id
- Session invalidation: api_session.is_active=False after password reset
- Rate limiting: Redis placeholder with TODO for production implementation
- Unit tests: 90+ test methods across 4 files (authorization, validation, token lifecycle, settings)
- Location: `18.0/extra-addons/thedevkitchen_user_onboarding/`

New Security Patterns Documented:
1. **Token-Based Onboarding**: Generate UUID v4, hash with SHA-256, store hash only, send raw token once
2. **Anti-Enumeration**: Public endpoints never reveal user existence (always 200 on forgot-password)
3. **Public Endpoint Marker**: `# public endpoint` comment mandatory for auth='none' routes
4. **Mail Template Integration**: Use mail.template model with context variables for transactional emails
5. **Singleton Configuration**: Single record configuration with get_settings() class method
6. **Rate Limiting Placeholder**: Log warning if Redis not available, allow request (fail-open for dev)
7. **Atomic Dual Record**: Odoo transaction for res.users + domain entity via partner_id linkage
8. **Session Invalidation**: Mark all user sessions inactive after security-sensitive operations

Template Files Status:
✅ constitution.md - Updated with Feature 009 reference and security patterns
✅ ADR-003 compliance (unit tests), ADR-008 (anti-enumeration), ADR-011 (security)
✅ Test pyramid statistics updated (190+ unit tests)
✅ Security patterns section added for token handling and session management

Propagation Complete:
✅ Unit tests passing (90+ test methods)
✅ All models with proper validation constraints
✅ Controllers following public endpoint marker pattern
✅ Services implementing authorization matrix
✅ Email templates created in Portuguese (pt_BR)
✅ Settings UI with Odoo 18.0 standards (no attrs, field grouping)

Follow-up Actions: E2E tests, Postman collection (ADR-016), translations, linting validation
Previous Amendment: 2026-02-08 (v1.2.0 Feature 007 reference implementation)
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
- `auth='public'` without `# public endpoint` comment above route
- Single decorator (`@require_jwt` alone without `@require_session`)
- Hardcoded credentials or secrets in code
- Exposing user existence in public endpoints (anti-enumeration violation)

### Token-Based Authentication Patterns (Feature 009)
For invite links, password reset tokens, or similar one-time-use tokens:
1. **Generation**: Generate UUID v4 (32 hex chars), hash with SHA-256 (64 hex chars), store hash only
2. **Distribution**: Send raw token via email/SMS once, never log or expose again
3. **Validation**: Compute SHA-256 of received token, search by hash
4. **State Machine**: Token states: pending → used/expired/invalidated
5. **Expiry**: Use TTL from configuration singleton, auto-expire in cron or on validation
6. **Invalidation**: Mark previous tokens as invalidated when generating new token for same user+type

**Rationale**: SHA-256 prevents rainbow table attacks. Raw token never stored. State machine ensures single use. Auto-expiry limits attack window.

### Anti-Enumeration Patterns (ADR-008)
Public endpoints that accept user identifiers (email, username, document) MUST NOT reveal whether the identifier exists:
- **Forgot Password**: Always return 200 with generic message, only send email if user exists
- **User Lookup**: Return 404 for both "not found" and "not authorized"
- **Login Attempts**: Rate limit by IP, delay response by constant time regardless of success/failure

**Example** (forgot-password endpoint):
```python
# Always return success, log attempts for non-existent emails
def forgot_password(self, email):
    user = env['res.users'].search([('login', '=', email), ('active', '=', True)])
    if not user:
        _logger.info(f"Forgot password attempt for non-existent email: {email}")
        return True  # Never reveal user doesn't exist
    # Only send email if user exists
    self._send_reset_email(user)
    return True
```

**Rationale**: Prevents enumeration attacks where adversaries discover valid emails/usernames, reducing phishing and targeted attacks.

### Transactional Email Patterns (mail.template)
Use Odoo's `mail.template` model for all transactional emails (invites, resets, notifications):
1. **Template Creation**: Create `mail.template` records in data XML
2. **Context Variables**: Use `${ctx.get('variable')}` for dynamic values from service layer
3. **User Variables**: Use `${object.field}` for res.users fields (name, email, company)
4. **HTML + Plain Text**: Provide body_html for rich formatting, fallback to body_text
5. **Language Support**: Use `lang="${object.lang}"` for multi-language support
6. **Async Sending**: Use `force_send=False` to queue emails (better performance)
7. **Error Handling**: Catch send failures, log error, continue operation (email failure shouldn't block user creation)

**Example** (invite email template):
```xml
<record id="email_template_user_invite" model="mail.template">
    <field name="name">User Invitation Email</field>
    <field name="model">res.users</field>
    <field name="subject">Convite para ${object.company_id.name}</field>
    <field name="body_html" type="html">
        <p>Olá ${object.name},</p>
        <p>Você foi convidado para: <a href="${ctx.get('invite_link')}">${ctx.get('invite_link')}</a></p>
        <p>Este link expira em ${ctx.get('expires_hours')} horas.</p>
    </field>
</record>
```

**Rationale**: Centralized email templates enable multi-language support, consistent branding, and A/B testing without code changes. Odoo's queue prevents email slowdowns.

### Singleton Configuration Model Pattern
For application-wide settings (link TTL, rate limits, feature flags):
1. **Model**: Create model with no explicit uniqueness, enforce in class method
2. **get_settings() Class Method**: Search for first record, create default if none exists
3. **Validation Constraints**: Use `@api.constrains` for value range validation (e.g., 1-720 hours)
4. **UI**: Form view in singleton mode (`view_mode='form'`, auto-open single record)
5. **Default Data**: Provide default record in data XML with sensible values

**Example**:
```python
class EmailLinkSettings(models.Model):
    _name = 'thedevkitchen.email.link.settings'
    _description = 'Email Link Configuration'
    
    invite_link_ttl_hours = fields.Integer(default=24)
    
    @api.constrains('invite_link_ttl_hours')
    def _check_link_ttl_positive(self):
        for record in self:
            if not (1 <= record.invite_link_ttl_hours <= 720):
                raise ValidationError("TTL must be between 1 and 720 hours")
    
    @classmethod
    def get_settings(cls, env):
        settings = env['thedevkitchen.email.link.settings'].search([], limit=1)
        if not settings:
            settings = env['thedevkitchen.email.link.settings'].create({})
        return settings
```

**Rationale**: Singleton pattern avoids configuration ambiguity. Validation prevents invalid states. Class method ensures default creation. UI provides admin control without code deployment.

### Rate Limiting Pattern (Redis-based with Placeholder)
For public endpoints vulnerable to abuse (forgot-password, login):
1. **Redis Key**: `rate_limit:{endpoint}:{identifier}` (e.g., `rate_limit:forgot_password:user@example.com`)
2. **INCR + EXPIRE**: Atomic increment with TTL (e.g., 3600s for 1 hour window)
3. **Check Before Operation**: Call `check_rate_limit()` before expensive operations
4. **Fail-Open in Dev**: If Redis unavailable, log warning and allow request (dev environment)
5. **Fail-Closed in Prod**: If Redis unavailable in prod, return 503 (circuit breaker)
6. **Return Metadata**: Return `{allowed: bool, attempts: int, limit: int, window_seconds: int}`

**Placeholder Pattern** (for development without Redis):
```python
def check_rate_limit(self, identifier, limit_key):
    settings = self.env['thedevkitchen.email.link.settings'].get_settings()
    limit = getattr(settings, limit_key)
    
    # TODO: Implement Redis integration
    _logger.warning(f"Rate limiting not implemented (Redis integration pending), allowing request for {identifier}")
    return {'allowed': True, 'attempts': 0, 'limit': limit, 'window_seconds': 3600}
```

**Rationale**: Rate limiting prevents brute-force and DOS attacks. Redis INCR is atomic and fast. Placeholder pattern enables development without full infrastructure. Fail-open in dev balances security and developer experience.

### Atomic Dual Record Creation (Portal Entities)
When creating portal users that require domain entity (e.g., res.users + real.estate.tenant):

### Atomic Dual Record Creation (Portal Entities)
When creating portal users that require domain entity (e.g., res.users + real.estate.tenant):
1. **Single Transaction**: Use Odoo's implicit transaction (no explicit `with env.cr.savepoint()`)
2. **Order Matters**: Create res.users first (Odoo auto-creates res.partner), then create domain entity with `partner_id=user.partner_id.id`
3. **Validation First**: Check for conflicts (duplicate document, existing tenant without user) before creation
4. **Link via partner_id**: Domain entity references res.partner, which links to res.users
5. **Error Handling**: If domain entity creation fails, transaction rolls back (res.users also deleted)
6. **Return Both**: Return both user_id and domain_entity_id in API response

**Example** (portal tenant creation):
```python
def create_portal_user(self, name, email, document, phone, birthdate, company_id):
    # Step 1: Check for conflicts
    existing_tenant = env['real.estate.tenant'].search([('document', '=', document)])
    if existing_tenant and not existing_tenant.user_id:
        raise ValidationError("Document already exists for unlinked tenant")
    
    # Step 2: Create res.users (portal group, password=False)
    user = env['res.users'].create({
        'name': name,
        'login': email,
        'email': email,
        'password': False,
        'signup_pending': True,
        'groups_id': [(6, 0, [env.ref('base.group_portal').id])],
    })
    
    # Step 3: Create domain entity linked via partner_id
    tenant = env['real.estate.tenant'].create({
        'partner_id': user.partner_id.id,  # Link to auto-created partner
        'document': document,
        'phone': phone,
        'birthdate': birthdate,
        'company_id': company_id,
    })
    
    return user, tenant
```

**Rationale**: Atomic transaction ensures data consistency. Order prevents orphaned partners. partner_id linkage is Odoo's standard pattern. Conflict check prevents data corruption. Rollback on failure maintains database integrity.

### Session Invalidation After Security Operations
After password reset or account compromise, invalidate all active sessions:
1. **Session Model**: Search `thedevkitchen.api.session` for user_id where is_active=True
2. **Bulk Update**: Write {is_active: False} to all matching sessions
3. **Logging**: Log count of invalidated sessions for audit trail
4. **Timing**: Invalidate AFTER password change succeeds (not before)
5. **User Communication**: Email user about active sessions terminated (security notification)

**Example**:
```python
def _invalidate_user_sessions(self, user):
    sessions = self.env['thedevkitchen.api.session'].search([
        ('user_id', '=', user.id),
        ('is_active', '=', True)
    ])
    count = len(sessions)
    sessions.write({'is_active': False})
    _logger.info(f"Invalidated {count} sessions for user {user.id} after password reset")
    return count
```

**Rationale**: Session invalidation prevents session hijacking after password change. Attacker with stolen session token loses access. User receives security notification. Audit log enables forensic analysis.

## Quality & Testing Standards

### Test Pyramid (ADR-002, ADR-003)
```
     E2E (56 Cypress tests)
    /____\
   /      \  Integration (195+ HTTP tests)
  /________\
 /          \ Unit (190+ tests)
```

### Reference Implementations
**Feature 007 - Owner & Company Management** (Constitutional Compliance Template):
- **Security**: Dual auth (`@require_jwt` + `@require_session`), multi-tenancy enforced
- **API Design**: 9 REST endpoints with HATEOAS links
- **Testing**: Integration tests (test_feature007_oauth2.sh), Cypress UI tests (2 files)
- **Documentation**: Postman collection with OAuth flow and test scripts
- **Location**: `18.0/extra-addons/quicksol_estate/controllers/owner_api.py`
- **Postman**: `docs/postman/feature007_owner_company_v1.0_postman_collection.json`

**Feature 009 - User Onboarding & Password Management** (Security Patterns Template):
- **Security**: Triple auth for invite, anti-enumeration on forgot-password, SHA-256 token hashing
- **API Design**: 5 REST endpoints (1 authenticated invite, 3 public password, 1 resend)
- **Token Lifecycle**: UUID v4 → SHA-256, state machine (pending/used/expired/invalidated), TTL configuration
- **Authorization Matrix**: Owner→all 9 profiles, Manager→5 operational, Agent→owner+portal
- **Portal Pattern**: Atomic res.users + real.estate.tenant via partner_id linkage
- **Session Management**: Invalidate all sessions after password reset
- **Email Integration**: mail.template with context variables (Portuguese pt_BR)
- **Configuration**: Singleton model with validation constraints (1-720h TTL range)
- **Rate Limiting**: Redis placeholder pattern (fail-open in dev, TODO for prod)
- **Testing**: 90+ unit tests (4 files), E2E integration tests (shell scripts)
- **Location**: `18.0/extra-addons/thedevkitchen_user_onboarding/`

Use Feature 007 for standard CRUD patterns with HATEOAS. Use Feature 009 for security-sensitive flows requiring token-based authentication, anti-enumeration, and session management.

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

**Version**: 1.3.0 | **Ratified**: 2026-01-03 | **Last Amended**: 2026-02-16
