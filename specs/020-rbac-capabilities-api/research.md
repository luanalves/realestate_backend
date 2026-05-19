# Research: RBAC Capabilities API

**Phase**: 0 — Outline & Research  
**Feature**: `020-rbac-capabilities-api`  
**Branch**: `020-rbac-capabilities-api`  
**Date**: 2026-05-18

All items that were NEEDS CLARIFICATION have been resolved below. No open unknowns remain.

---

## 1. Role Resolution Strategy

**Decision**: Reuse the existing ordered `role_map` lookup from `me_controller.py` — do not invent a parallel resolver.

**Rationale**: FR2.1 mandates parity with `/api/v1/me`. The current resolver iterates a Python dict whose insertion order (Python 3.7+) defines precedence. The declared precedence is:

```
owner → director → manager → agent → prospector →
receptionist → financial → legal → property_owner → tenant
```

First group match wins (`next(... if user.has_group(xml_id), None)`).

**Action (FR2.2 — SHOULD)**: Extract this resolution logic into a shared helper
`thedevkitchen_apigateway/services/role_resolver.py` (or inline as a module-level function)
so that both `me_controller.py` and `capabilities_controller.py` import the same function.
This prevents the two endpoints from drifting if the precedence order ever changes.
Implementation is SHOULD-level; the MVP can duplicate and note a TODO if extraction adds risk.

**Alternative considered**: A session-level `active_role` marker on `thedevkitchen.api.session`
that stores the resolved role at login time. Rejected for MVP — would require a schema migration
and a coordinated update to login flow; spec-idea explicitly states "Until a session-level
active-role marker exists" (FR2.3), confirming code-based resolution is the intended path.

---

## 2. Service Layer Location

**Decision**: `quicksol_estate/services/capability_service.py`

**Rationale**:
- The service calls `user.has_group('quicksol_estate.group_real_estate_*')` which requires
  the calling module to have `quicksol_estate` as a dependency. Placing the service in
  `thedevkitchen_apigateway` would invert the existing dependency direction.
- All domain services (`agent_service.py`, `assignment_service.py`, etc.) live in
  `quicksol_estate/services/`; this is the established pattern.
- The controller also lives in `quicksol_estate/controllers/capabilities_controller.py` and
  imports middleware from `odoo.addons.thedevkitchen_apigateway.middleware` — the same
  cross-module import pattern used by every existing `quicksol_estate` controller.

**Alternatives considered**: Placing service in `thedevkitchen_apigateway` — rejected; would
require `thedevkitchen_apigateway` to depend on `quicksol_estate`, reversing established dependency.

---

## 3. ROLE_RULES Data Structure

**Decision**: A module-level Python dict `ROLE_RULES` mapping role string → list of `(action, subject)` tuples, declared in `capability_service.py`. Rules are stored in canonical contract order.

**Rationale**:
- FR6.3: service emits rules from a backend whitelist only.
- FR3.4 + FR-016: response must be deterministic and preserve canonical order.
- Using tuples (not dicts) for internal representation keeps the mapping readable and avoids
  accidental key conflicts. Serialized to `{"action": ..., "subject": ...}` at output time.
- `ROLE_RULES` in code (not DB) was explicitly specified in spec-idea: "ROLE_RULES is stored
  in code, not in the database, for MVP simplicity and auditability."

**Structure skeleton**:
```python
ROLE_RULES: dict[str, list[tuple[str, str]]] = {
    "owner": [
        ("view", "MenuCRM"),
        ("view", "MenuAdmin"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        # ... declared order is canonical contract order
    ],
    "agent": [...],
    # ... all 10 roles
}
```

**Whitelists (FR3.3)**:
```python
ALLOWED_ACTIONS = {"view", "create", "update", "delete", "reassign", "approve", "cancel", "export"}
ALLOWED_SUBJECTS = {
    "MenuCRM", "MenuAdmin", "MenuCMS",
    "Dashboard", "Property", "Lead", "Service", "Proposal",
    "Agent", "Company", "Settings", "Appointment",
    "Report", "Goal", "CMSPage", "CMSMedia",
}
```

`manage` is intentionally excluded from MVP allowed actions.

---

## 4. Canonical Rule Ordering

**Decision**: Order is determined by the backend's declarative `ROLE_RULES` list, not by sorting. Subjects appear in business/navigation order; actions within a subject follow semantic progression.

**Canonical subject order** (derived from plan_rbac.md + spec-idea.md example response):
```
MenuCRM → MenuAdmin → MenuCMS →
Dashboard → Property → Lead → Service → Proposal →
Agent → Company → Settings → Appointment → Report → Goal →
CMSPage → CMSMedia
```

**Canonical action order** within a subject:
```
view → create → update → delete → reassign → approve → cancel → export
```

**Rationale**: Deterministic ordering is contractually required (FR-016, FR-015) so that
contract tests, integration tests, and frontend snapshot tests remain stable across identical
role configurations. Alphabetical ordering was explicitly rejected in the spec clarifications.

**Implementation**: The `ROLE_RULES` dict entries are typed in declared order. The service
emits them in that order after deduplication. No sort call is applied at runtime. Deduplication
preserves first occurrence (since declared entries should not repeat).

---

## 5. Deduplication Strategy

**Decision**: Deduplicate using a `seen: set[tuple[str, str]]` set during projection. First
occurrence wins; subsequent duplicates (if any exist in `ROLE_RULES` due to authoring error)
are silently dropped.

**Rationale**: FR-015 forbids duplicate `action + subject` pairs. A `seen` set check is O(1)
per rule and adds no meaningful latency. Silent drop is safer than raising — failing closed
on ambiguity per FR6.4.

---

## 6. No-Role Fallback

**Decision**: When the resolved role is `None` (user has no mapped real-estate group for their
active session context), return `200 OK` with `{"user": {"id": ..., "role": null, "company_id": ...}, "rules": []}`.

**Rationale**: FR-007 and FR2.4 explicitly require this. Returning 403 or 401 for an
authenticated-but-unroled user would break CASL initialization on the frontend.

---

## 7. Error Response Shape

**Decision**: Follow the existing error shape already used in `me_controller.py` and other
`quicksol_estate` controllers:
```json
{"error": "unauthorized"}       // 401
{"error": "forbidden"}          // 403
{"error": "internal_server_error"}  // 500
```

**Note**: The existing `me_controller.py` uses `{"error": {"status": ..., "message": ...}}`
(nested object). The spec-idea (FR-017) documents flat `{"error": "<code>"}` for capability
errors. Use the flat form in the new endpoint to match the spec contract. Do NOT change
`me_controller.py` shape as part of this feature (FR-003, FR7.1).

---

## 8. OpenAPI / Swagger Registration

**Decision**: The `contracts/capabilities.yaml` file in the spec directory serves as the
design contract reference only. The live Swagger registration MUST be done via
`thedevkitchen_api_endpoint` DB records per ADR-005 — not by editing static files.
Swagger registration is a post-implementation step (distinct workflow).

**Rationale**: ADR-005 and FR-018 are explicit: "do not rely on static Swagger file edits."
The `swagger_controller.py` serves docs from DB-backed records. Static YAML in `contracts/`
is a planning artefact for contract-first design, reviewed by implementer before coding.

---

## 9. Testing Strategy

**Decision**: Follow the existing test pyramid already in place:

| Layer | Framework | Location | Key coverage |
|-------|-----------|----------|-------------|
| Unit | Odoo `TestCase` (no HTTP) | `tests/utils/test_capability_service.py` | Role resolver parity, deduplication, ordering, omission, whitelist enforcement |
| E2E API | `TransactionCase` + bash | `tests/api/test_capabilities_api.py` + bash scripts | 10-role matrix, 401/403 error paths, multi-company isolation, non-leakage, `/api/v1/me` regression |

Minimum unit tests per spec-idea.md:
- `test_role_resolver_matches_me_endpoint_order()`
- `test_capability_service_deduplicates_rules()`
- `test_capability_service_omits_denied_rules()`
- `test_capability_service_stable_sort_order()`
- `test_only_whitelisted_subjects_are_serialized()`
- `test_only_whitelisted_actions_are_serialized()`

Minimum E2E tests: full 10-role matrix smoke, 401/403 guards, multi-company isolation, non-leakage, regression guard for `/api/v1/me`.

**Rationale**: ADR-003 mandates ≥80% coverage. Pattern follows Feature 009 (unit + E2E bash).
Using `TestCase` (no DB) for pure service unit tests keeps them fast. `TransactionCase`/`HttpCase`
for integration tests that need real DB state.

---

## 10. Performance Considerations

**Decision**: No Redis cache for MVP. The capability projection is purely in-memory (group check +
dict lookup). No DB reads beyond what `@require_session` and `@require_company` already perform.

**Rationale**: SC-005 requires 95% of requests < 1 second. Group membership checks
(`user.has_group(xml_id)`) in Odoo are cached at the ORM level within a request. `ROLE_RULES`
is a constant dict. The endpoint will be faster than any cached alternative since it performs
no additional I/O. If profiling later reveals a bottleneck (e.g., many concurrent users doing
group checks), a short-lived Redis cache keyed by `capabilities:{user_id}:{company_id}` with
TTL 30s can be added following the Aggregation Endpoint pattern from the constitution.

---

## 11. Module Version Bump

**Decision**: Bump `quicksol_estate` version from `18.0.4.0.0` to `18.0.5.0.0` when the
feature is merged, following the existing semantic versioning established in the manifest
(Feature 015 = version 4).

**Rationale**: Each major feature increments the minor version segment. Adding a new endpoint
group qualifies as a MINOR increment under the project's versioning convention.

---

## Summary of Resolved Unknowns

| Unknown | Resolution |
|---------|-----------|
| Where does the service live? | `quicksol_estate/services/capability_service.py` |
| Where does the controller live? | `quicksol_estate/controllers/capabilities_controller.py` |
| Should we extract the role resolver? | Yes (SHOULD); deferred to implementation decision |
| What data structure for ROLE_RULES? | Module-level `dict[str, list[tuple[str, str]]]` |
| How is ordering enforced? | Declarative list order — no runtime sort |
| How are duplicates handled? | `seen` set; first occurrence wins |
| What happens with no-role user? | `200 OK`, `role=null`, `rules=[]` |
| Error shape for this endpoint? | Flat `{"error": "<code>"}` per spec-idea contract |
| Swagger registration? | DB-driven only (ADR-005); `contracts/capabilities.yaml` is design reference |
| Performance: cache needed? | No for MVP — in-memory projection is sufficient |
| Module version bump? | `quicksol_estate` → `18.0.5.0.0` on merge |
