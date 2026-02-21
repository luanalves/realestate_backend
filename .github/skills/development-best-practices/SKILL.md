---
name: development-best-practices
description: "**TRIGGER KEYWORDS**: model, models, _name, controller, endpoint, @http.route, @require_jwt, @require_session, @require_company, module, naming, thedevkitchen_, security decorator, authentication, authorization, PostgreSQL, Redis, cache, performance, query optimization, development, criar, create, implementar, implement, desenvolver, revisar, review. **COVERS**: (1) Module/table naming conventions (thedevkitchen_ prefix - ADR-004), (2) Model naming (_name format), (3) Controller security patterns (triple decorators: @require_jwt + @require_session + @require_company - ADR-011), (4) Storage architecture (PostgreSQL for persistence, Redis for sessions/cache), (5) Performance optimization (cache strategies, N+1 queries, limits). **AUTO-CONSULT WHEN**: Creating/reviewing ANY code (models, controllers, modules), implementing endpoints, validating security, optimizing performance, any development task. References ADR-004, ADR-011, ADR-017."
---

# Development Best Practices - Odoo Real Estate

> **🚨 CONSULT THIS SKILL FOR ANY DEVELOPMENT TASK 🚨**  
> Creating models? ✅ Implementing controllers? ✅ Writing services? ✅ Refactoring? ✅  
> This is your **mandatory reference** before writing any Odoo code.

This skill provides quick reference for **ALL development tasks**: model naming, module structure, controller security, and performance optimization.

**Scope**: Models, Controllers, Modules, Security, Storage Architecture, Performance  
**Other areas**: For testing, validation, API docs, and Git workflow, see ADRs in [Quick Reference](#quick-reference) section

## When to Use This Skill

- **Creating ANY Odoo code**: models, controllers, modules, services
- **Naming validation**: modules (_name), tables, fields, XML IDs
- **Security implementation**: authentication decorators, authorization checks
- **Performance optimization**: Redis cache, query patterns, N+1 prevention
- **Code review**: validating patterns, security, nomenclature
- **Development tasks**: any implementation, refactoring, or architecture decision
- **Finding relevant ADRs** by context

## Prerequisites

1. Read [.github/copilot-instructions.md](../../copilot-instructions.md) for authentication dual decorators rules
2. Know project structure (working in `18.0/` directory)
3. Access to ADRs: `docs/adr/`

---

## 1. Module & Model Naming Conventions

**Reference**: [ADR-004: Nomenclatura de Módulos e Tabelas](../../../docs/adr/ADR-004-nomenclatura-modulos-tabelas.md)

**🎯 Use this section when**: Creating modules, defining models (_name), naming tables, creating XML IDs

### ✅ Required Patterns

**Module Directory Name**:
```
Format: thedevkitchen_<functional_name>
Example: thedevkitchen_estate, thedevkitchen_user_onboarding
```

**Odoo Model Name (_name)** - CRITICAL for every model:
```python
class MyModel(models.Model):
    _name = 'thedevkitchen.<category>.<entity>'
    _description = 'Description'

# ✅ CORRECT Examples:
# 'thedevkitchen.oauth.application'
# 'thedevkitchen.estate.property'
# 'thedevkitchen.estate.agent'
# 'thedevkitchen.estate.profile'

# ❌ WRONG Examples:
# 'estate.property'  # Missing thedevkitchen prefix
# 'property'  # No prefix at all
# 'real.estate.property'  # Wrong prefix
```

**Database Table Name** (auto-generated):
```
Format: thedevkitchen_<category>_<entity>
# Generated from _name
```

### ❌ Never Do

- ❌ Generic module names: `api_gateway`, `estate`, `property`
- ❌ Models without prefix: `estate.property`
- ❌ Custom tables without `thedevkitchen_`
- ❌ Generic XML IDs without module context

### Checklist

- [ ] Module name starts with `thedevkitchen_`
- [ ] Model uses format `thedevkitchen.<category>.<entity>`
- [ ] XML IDs follow `<module>.<identifier>`
- [ ] Access rules use `access_<model>_<group>`

---

## 2. Controller Security & Storage

**References**: 
- [ADR-011: Controller Security - Authentication & Storage](../../../docs/adr/ADR-011-controller-security-authentication-storage.md)
- [ADR-017: Session Hijacking Prevention](../../../docs/adr/ADR-017-session-hijacking-prevention-jwt-fingerprint.md)

**Note**: Authentication dual decorator rules (`@require_jwt` + `@require_session`) are in [copilot-instructions.md](../../copilot-instructions.md)

### Storage Architecture

**PostgreSQL** (Persistence):
- OAuth tokens (SHA256 hashed)
- User credentials
- Business data
- Audit logs

**Redis** (Cache/Sessions):
- Session IDs and user context
- Query cache
- Message bus

**❌ NEVER store in plaintext**:
- Passwords
- OAuth client_secret
- Access tokens

### Security Checklist

- [ ] Endpoint uses `@require_jwt` AND `@require_session` (if private)
- [ ] Public endpoint has `# public endpoint` comment
- [ ] Multi-tenancy validated with `@require_company`
- [ ] Sensitive data never in logs or plaintext
- [ ] Consult [copilot-instructions.md](../../copilot-instructions.md) for auth patterns

---

## 3. Performance & Cache

**Reference**: [ADR-011: Redis Cache Configuration](../../../docs/adr/ADR-011-controller-security-authentication-storage.md)

### Redis Configuration

**Redis is configured for**:
- HTTP sessions (DB index 1)
- ORM cache
- Asset cache
- Message bus

**Configuration in `odoo.conf`**:
```ini
session_redis = True
session_redis_host = redis
session_redis_port = 6379
session_redis_dbindex = 1
session_redis_prefix = odoo18_
```

### ❌ Performance Anti-patterns

- ❌ N+1 queries (use `read()` or `search_read()`)
- ❌ Fetching all records without limit
- ❌ Unnecessary `sudo()` (breaks cache)
- ❌ Compute fields without `store=True` when needed

### Performance Checklist

- [ ] Queries optimized (no N+1)
- [ ] Appropriate cache usage
- [ ] Limits in search()
- [ ] Indexes created for filtered fields
- [ ] Redis configured and running

---

## Quick Reference

**This skill covers**: Naming (ADR-004), Security/Storage (ADR-011, ADR-017), Performance (Redis/Cache)

**For other areas, consult ADRs directly**:

### Module Development
- ✅ [ADR-004: Nomenclatura](../../../docs/adr/ADR-004-nomenclatura-modulos-tabelas.md) - Covered in this skill
- [ADR-010: Python Virtual Environment](../../../docs/adr/ADR-010-python-virtual-environment.md)

### Security & Authentication
- ✅ [ADR-011: Controller Security](../../../docs/adr/ADR-011-controller-security-authentication-storage.md) - Storage covered, auth in copilot-instructions.md
- ✅ [ADR-017: Session Hijacking Prevention](../../../docs/adr/ADR-017-session-hijacking-prevention-jwt-fingerprint.md) - Referenced here
- [ADR-008: API Security & Multi-Tenancy](../../../docs/adr/ADR-008-api-security-multi-tenancy.md)

### Testing (consult ADRs)
- [ADR-003: Mandatory Test Coverage](../../../docs/adr/ADR-003-mandatory-test-coverage.md)
- [ADR-002: Cypress E2E Testing](../../../docs/adr/ADR-002-cypress-end-to-end-testing.md)
- [.github/instructions/test-strategy.instructions.md](../../instructions/test-strategy.instructions.md)

### APIs & Documentation (consult ADRs)
- [ADR-005: OpenAPI 3.0](../../../docs/adr/ADR-005-openapi-30-swagger-documentation.md)
- [ADR-016: Postman Collections](../../../docs/adr/ADR-016-postman-collection-standards.md) - Use [postman-collection-manager](../postman-collection-manager/SKILL.md) skill
- [ADR-018: Input Validation](../../../docs/adr/ADR-018-input-validation-schema-validation-rest-apis.md)
- [ADR-007: HATEOAS](../../../docs/adr/ADR-007-hateoas-hypermedia-rest-api.md)

### Data Modeling (consult ADRs)
- [ADR-014: Many2Many Relationships](../../../docs/adr/ADR-014-odoo-many2many-agent-property-relationship.md)
- [ADR-015: Soft Delete](../../../docs/adr/ADR-015-soft-delete-logical-deletion-odoo-models.md)

### Business Rules (consult ADRs)
- [ADR-012: CRECI Validation](../../../docs/adr/ADR-012-creci-validation-brazilian-real-estate.md)
- [ADR-013: Commission Calculation](../../../docs/adr/ADR-013-commission-calculation-rule-management.md)
- [ADR-019: RBAC - Perfis de Acesso](../../../docs/adr/ADR-019-rbac-perfis-acesso-multi-tenancy.md)

### Architecture Patterns (consult ADRs)
- [ADR-020: Observer Pattern](../../../docs/adr/ADR-020-observer-pattern-odoo-event-driven-architecture.md)
- [ADR-021: Async Messaging (RabbitMQ/Celery)](../../../docs/adr/ADR-021-async-messaging-rabbitmq-celery.md)

### Git Workflow (consult ADRs)
- [ADR-006: Git Flow](../../../docs/adr/ADR-006-git-flow-workflow.md)

---

## Pre-Coding Checklist

**Use before ANY development**: models, controllers, services, modules, or refactoring

### Naming & Structure
- [ ] Read ADR-004 for module/table/model naming
- [ ] Module name follows `thedevkitchen_<name>`
- [ ] Model _name follows `thedevkitchen.<category>.<entity>`
- [ ] All naming patterns validated (tables, fields, XML IDs)

### Security
- [ ] Read [copilot-instructions.md](../../copilot-instructions.md) for auth rules
- [ ] Know which security decorators to use (`@require_jwt` + `@require_session`)
- [ ] Sensitive data will be stored correctly (PostgreSQL/Redis)

### Performance
- [ ] Understand Redis configuration (sessions/cache)
- [ ] Queries optimized (no N+1)
- [ ] Appropriate cache usage

### Other Areas (consult ADRs)
- [ ] Testing: ADR-003, ADR-002
- [ ] Validation: ADR-018
- [ ] Multi-tenancy: ADR-008, ADR-019
- [ ] Documentation: ADR-005, ADR-016
- [ ] Git: ADR-006

---

## Related Resources

- [copilot-instructions.md](../../copilot-instructions.md) - Authentication dual decorators and project context
- [postman-collection-manager](../postman-collection-manager/SKILL.md) - API documentation skill
- [controllers.instructions.md](../../instructions/controllers.instructions.md) - Controller-specific instructions
- [test-strategy.instructions.md](../../instructions/test-strategy.instructions.md) - Testing strategy

---

## Enforcement

This skill covers **naming, security/storage, and performance**. For other areas (testing, validation, Git, etc.), consult ADRs directly in Quick Reference section.

**Violations** should be:
1. Identified in code review
2. Rejected in pull requests
3. Corrected before merge
4. Documented if justified exception exists

**Remember**: ADRs exist to prevent production issues, facilitate maintenance, and ensure quality. Follow them always!
