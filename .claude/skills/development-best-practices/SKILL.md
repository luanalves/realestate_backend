---
name: development-best-practices
description: "Use when creating or reviewing ANY Odoo code in this project — models, controllers, modules, services — or when naming a module/model/table, adding auth decorators, or touching Redis cache/query performance. Triggers: model, models, _name, controller, endpoint, @http.route, @require_jwt, @require_session, @require_company, module naming, thedevkitchen_ prefix, security decorator, authentication, authorization, PostgreSQL, Redis, cache, performance, query optimization, criar, create, implementar, implement, desenvolver, revisar, review. Covers module/model naming (ADR-004), controller security decorators (ADR-011), PostgreSQL/Redis storage split, and performance/cache anti-patterns."
---

# Development Best Practices — Odoo Real Estate

> **🚨 CONSULT THIS SKILL FOR ANY DEVELOPMENT TASK 🚨**
> Creating models? ✅ Implementing controllers? ✅ Writing services? ✅ Refactoring? ✅
> This is the mandatory reference before writing any Odoo code in this project.

**Scope**: Models, Controllers, Modules, Security, Storage Architecture, Performance
**Other areas**: For testing, validation, API docs, and Git workflow, see the ADR list in [Quick Reference](#quick-reference)

## When to Use

- Creating ANY Odoo code: models, controllers, modules, services
- Naming validation: modules (`_name`), tables, fields, XML IDs
- Security implementation: authentication decorators, authorization checks
- Performance optimization: Redis cache, query patterns, N+1 prevention
- Code review: validating patterns, security, nomenclature
- Finding the relevant ADR by context

## Prerequisites

1. Read `.github/copilot-instructions.md` for the authentication dual-decorator rules
2. Know the project structure (working in `18.0/` directory)
3. Access to ADRs: `docs/adr/`

---

## 1. Module & Model Naming Conventions

**Reference**: `docs/adr/ADR-004-nomenclatura-modulos-tabelas.md`

**Use this section when**: creating modules, defining models (`_name`), naming tables, creating XML IDs.

### Required Patterns

**Module directory name**:
```
Format: thedevkitchen_<functional_name>
Example: thedevkitchen_estate, thedevkitchen_user_onboarding
```

**Odoo model name (`_name`)** — critical for every model:
```python
class MyModel(models.Model):
    _name = 'thedevkitchen.<category>.<entity>'
    _description = 'Description'

# ✅ CORRECT:
# 'thedevkitchen.oauth.application'
# 'thedevkitchen.estate.property'
# 'thedevkitchen.estate.agent'

# ❌ WRONG:
# 'estate.property'      # Missing thedevkitchen prefix
# 'property'              # No prefix at all
# 'real.estate.property'  # Wrong prefix
```

**Database table name** (auto-generated): `thedevkitchen_<category>_<entity>`

### Never Do

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
- `docs/adr/ADR-011-controller-security-authentication-storage.md`
- `docs/adr/ADR-017-session-hijacking-prevention-jwt-fingerprint.md`

**Note**: Authentication dual-decorator rules (`@require_jwt` + `@require_session`) live in `.github/copilot-instructions.md`.

### Storage Architecture

**PostgreSQL** (persistence): OAuth tokens (SHA256 hashed), user credentials, business data, audit logs.

**Redis** (cache/sessions): session IDs and user context, query cache, message bus.

**❌ NEVER store in plaintext**: passwords, OAuth `client_secret`, access tokens.

### Security Checklist

- [ ] Endpoint uses `@require_jwt` AND `@require_session` (if private)
- [ ] Public endpoint has a `# public endpoint` comment
- [ ] Multi-tenancy validated with `@require_company`
- [ ] Sensitive data never in logs or plaintext

---

## 3. Performance & Cache

**Reference**: `docs/adr/ADR-011-controller-security-authentication-storage.md`

### Redis Configuration

Redis is configured for HTTP sessions (DB index 1), ORM cache, asset cache, message bus:
```ini
session_redis = True
session_redis_host = redis
session_redis_port = 6379
session_redis_dbindex = 1
session_redis_prefix = odoo18_
```

### Performance Anti-patterns

- ❌ N+1 queries (use `read()` or `search_read()`)
- ❌ Fetching all records without a limit
- ❌ Unnecessary `sudo()` (breaks cache)
- ❌ Compute fields without `store=True` when needed

### Performance Checklist

- [ ] Queries optimized (no N+1)
- [ ] Appropriate cache usage
- [ ] Limits in `search()`
- [ ] Indexes created for filtered fields

---

## Quick Reference

**This skill covers**: Naming (ADR-004), Security/Storage (ADR-011, ADR-017), Performance (Redis/Cache).

**For other areas, consult ADRs directly**:

| Area | ADR(s) |
|------|--------|
| Python virtual env | ADR-010 |
| API multi-tenancy | ADR-008 |
| Testing | ADR-003 (coverage), ADR-002 (Cypress E2E) |
| OpenAPI/Swagger | ADR-005 — see `swagger-updater` skill |
| Postman collections | ADR-016 — see `postman-collection-manager` skill |
| Input validation | ADR-018 |
| HATEOAS | ADR-007 |
| Many2Many patterns | ADR-014 |
| Soft delete | ADR-015 |
| CRECI validation | ADR-012 |
| Commission calculation | ADR-013 |
| RBAC / access profiles | ADR-019 — see `odoo-module-security` skill |
| Observer pattern | ADR-020 |
| Async messaging (RabbitMQ/Celery) | ADR-021 |
| Git flow | ADR-006 |

---

## Pre-Coding Checklist

**Use before ANY development**: models, controllers, services, modules, or refactoring.

- [ ] Module name follows `thedevkitchen_<name>` (ADR-004)
- [ ] Model `_name` follows `thedevkitchen.<category>.<entity>` (ADR-004)
- [ ] Auth decorators chosen (`@require_jwt` + `@require_session` [+ `@require_company`])
- [ ] Sensitive data storage confirmed (PostgreSQL vs Redis)
- [ ] Queries optimized, no N+1
- [ ] Multi-tenancy: ADR-008, ADR-019 (see `odoo-module-security` skill)
- [ ] Documentation: ADR-005, ADR-016 (see `swagger-updater`, `postman-collection-manager` skills)

---

## Related Skills

- `swagger-updater` — add/update/remove Swagger endpoints (DB-driven, ADR-005)
- `postman-collection-manager` — API documentation/testing collections (ADR-016)
- `odoo-module-security` — RBAC groups, `ir.model.access.csv`, menu visibility (ADR-019)

## Enforcement

Violations should be identified in code review, rejected in pull requests, corrected before merge, and documented if a justified exception exists. ADRs exist to prevent production issues, facilitate maintenance, and ensure quality — follow them always.
