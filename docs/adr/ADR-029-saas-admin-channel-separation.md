# ADR-029: SaaS Admin Channel Separation — Odoo Web UI Only

**Status**: Accepted  
**Date**: 2026-06-05  
**Author**: Platform Engineering  
**Feature**: 022 — Admin UI Cross-Company Access for System Admin

---

## Context

The platform uses `base.group_system` (System Admin / uid=2) as the SaaS-level super-user role that
manages all tenant companies. Two security gaps existed before Feature 022:

1. **Visibility gap**: Multi-tenancy `ir.rule` records designed for business profiles (`company_id in
   company_ids`) also applied to `base.group_system`, effectively blocking the System Admin from
   viewing records from companies other than their own in the Odoo web UI. This forced workarounds
   (switching active company repeatedly) and created operational blind spots.

2. **Channel confusion**: The REST API login endpoint (`POST /api/v1/users/login`) had no guard
   preventing System Admins from authenticating through a headless API channel that is explicitly
   designed for company-scoped business users only. A successful admin API session would bypass
   multi-tenancy controls, exposing all tenant data via the headless API.

---

## Decision

### 1. Cross-company visibility via `ir.rule` overrides

For every Odoo model that has a company-filtering `ir.rule`, add a **complementary rule** with
`domain_force=[(1,'=',1)]` assigned exclusively to `base.group_system`:

```xml
<!-- ADR-008 §3: Admin accesses via administrative interface -->
<!-- ADR-019: SaaS Admin operates above business role hierarchy -->
<record id="rule_admin_all_{entity}" model="ir.rule">
    <field name="name">System Admin: All {Entity} (Cross-Company)</field>
    <field name="model_id" ref="model_{underscore_name}"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

**Why this works (Odoo native OR-union)**: When a user belongs to groups that each have separate
`ir.rule` entries for the same model, Odoo combines them with OR (union). The `[(1,'=',1)]` rule
for `base.group_system` therefore overrides any narrower company-filtered rule the admin may also
inherit from `base.group_user`.

### 2. noupdate="1" compatibility

When the target XML file contains `<data noupdate="1">`, the new admin override rules go in a
**separate** `<data noupdate="0">` block within the same file. This ensures the rules are applied
on `--update` without disturbing the existing noupdate rules (which are intentionally protected
from re-application on upgrade).

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- existing rules — do NOT touch -->
    </data>

    <!-- Feature 022: SaaS Admin cross-company overrides -->
    <data noupdate="0">
        <record id="rule_admin_all_{entity}" model="ir.rule">
            ...
        </record>
    </data>
</odoo>
```

### 3. REST API login block (anti-enumeration)

In the login controller, check for `base.group_system` **after** credential validation and **before**
session token issuance. Return HTTP 401 with a response body **identical** to a bad-credential failure:

```python
# Feature 022 / ADR-029: Block SaaS Admin from REST API
# System Admins must use Odoo web interface (Principle VI).
# 401 (not 403): anti-enumeration — response must be indistinguishable from invalid credentials.
if user.has_group('base.group_system'):
    _logger.warning(f"Admin login attempt via API blocked: {email}")
    AuditLogger.log_failed_login(ip_address, email, 'Admin API login blocked')
    return request.make_json_response(
        {'error': {'status': 401, 'message': 'Invalid credentials'}},
        status=401
    )
```

**Why HTTP 401, not 403**: Anti-enumeration principle (ADR-008) — the response for a blocked admin
login MUST be indistinguishable from an invalid-credential failure. HTTP 403 would reveal that the
credentials are valid, enabling targeted credential enumeration and phishing.

### 4. FR-007: Admin not invitable via API

`base.group_system` is excluded from Feature 009's invitable profile authorization matrix by design.
No additional guard code is required for this ADR — Feature 009 already enforces FR-007. New modules
should be aware that this exclusion is intentional and must not be removed.

---

## Rationale

### Why Odoo's native OR-union is the right mechanism

Alternatives considered:

| Option | Why Rejected |
|---|---|
| Remove company filter from System Admin rules | Would break business-profile isolation for all users sharing a rule, not just admins |
| `sudo()` in controllers | Violates ADR-011 (`.sudo()` abuse forbidden in controllers) |
| Separate admin-only views | High maintenance burden; duplicates all existing views |
| `active_test=False` context bypass | Bypasses `active` field, not just company filter; too broad |

Odoo's OR-union semantics for `ir.rule` are the **zero-overhead, idiomatic** solution: the existing
business-profile rules are completely untouched; a new, additive rule for `base.group_system` grants
cross-company access only to that group.

### Why the admin must not use the REST API

The REST API (`/api/v1/*`) is designed for company-scoped business profiles. It assumes every
authenticated user belongs to exactly one active company context (`@require_company`). `base.group_system`
users are explicitly above this model — they must not be shoehorned into a company-scoped API session:

- `@require_company` would arbitrarily bind the admin to one company, masking cross-company data
- Any headless frontend consuming the API would receive unfiltered admin data, violating tenant isolation
- System Admin tasks (user creation, configuration) are performed through the Odoo web interface, which
  natively supports multi-company switching

---

## Consequences

### Positive
- System Admin can view and manage all records from all tenant companies in the Odoo web UI without
  any workarounds.
- Business-profile record isolation is completely unchanged — no existing `ir.rule` is modified.
- The REST API channel remains exclusively for company-scoped business users.
- All blocked admin API login attempts are audit-logged (ADR-008 §4).
- The noupdate-safe approach ensures production upgrades apply the new rules without re-writing
  protected operational data.

### Negative / Trade-offs
- Every new module that introduces company-filtering `ir.rule` records **must** also add a
  `base.group_system` cross-company override. Omitting this silently locks the admin out of new
  data — see [Knowledge Base KB-013](../../knowledge_base/13-saas-admin-module-checklist.md).
- The `ir.rule` table gains 18 additional rows. No measurable performance impact (Odoo evaluates
  all rules per query anyway; OR-union short-circuits on first match for the admin).
- **Timing side-channel (accepted risk — CHK024)**: The admin block path executes `has_group()`
  after `session.authenticate()`, adding ~1–5 ms overhead compared to the bad-credential path.
  The dominant latency on both paths is `session.authenticate()` (full DB round-trip with
  password hash verification); the marginal difference is not reliably measurable under normal
  network jitter. **Mitigation**: Kong API Gateway applies rate limiting and connection throttling
  to all login endpoint traffic (existing gateway policy), preventing timing-based enumeration
  at scale. No application-level timing equalization is added (doing so would require constant
  artificial delays, degrading all login performance for negligible security gain given Kong coverage).
- **Guard ordering**: The `has_group('base.group_system')` check is placed **before** the
  `user.active` check in the controller. This is intentional — if the active check came first,
  an inactive System Admin would receive `403 "User inactive"` instead of `401`, revealing that
  the account exists with valid credentials (anti-enumeration violation, ADR-008).

---

## New Module Obligation (Convention)

> **Every** new module that adds `ir.rule` records with company filtering **MUST** include a
> corresponding `base.group_system` cross-company override rule in a `noupdate="0"` block.

This is enforced by the checklist at [knowledge_base/13-saas-admin-module-checklist.md](../../knowledge_base/13-saas-admin-module-checklist.md).

---

## Affected Modules (Feature 022 implementation)

| Module | File | Strategy |
|---|---|---|
| `quicksol_estate` | `security/record_rules.xml` | New `noupdate="0"` block (9 models) |
| `quicksol_estate` | `security/proposal_record_rules.xml` | Append to existing `noupdate="0"` block |
| `quicksol_estate` | `security/service_record_rules.xml` | Append to existing `noupdate="0"` block |
| `thedevkitchen_cms` | `security/cms_record_rules.xml` | New `noupdate="0"` block (3 models) |
| `thedevkitchen_estate_goals` | `security/record_rules.xml` | Append to existing `noupdate="0"` block |
| `thedevkitchen_estate_credit_check` | `security/record_rules.xml` | New `noupdate="0"` block (1 model) |
| `thedevkitchen_user_onboarding` | `security/record_rules.xml` | New `noupdate="0"` block (1 model) |

---

## References

- [ADR-008 — Multi-tenancy and Anti-Enumeration](ADR-008-multi-tenancy-anti-enumeration.md)
- [ADR-009 — Authentication Standards](ADR-009-authentication-standards.md)
- [ADR-011 — Security Decorators](ADR-011-security-decorators.md)
- [ADR-019 — RBAC Role Hierarchy](ADR-019-rbac-role-hierarchy.md)
- [Feature 022 spec](../../specs/022-admin-ui-cross-company/spec.md)
- [Knowledge Base KB-013 — SaaS Admin Module Checklist](../../knowledge_base/13-saas-admin-module-checklist.md)
