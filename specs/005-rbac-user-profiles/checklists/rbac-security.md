# Checklist: RBAC Security Requirements Quality

**Purpose**: Validate requirements quality for RBAC User Profiles feature against Odoo security model patterns, ensuring specifications are complete, clear, consistent, and implementable.

**Created**: 2026-01-22  
**Focus**: Deep validation of security requirements, permission specifications, and Odoo model alignment  
**Depth**: Deep (validates against Odoo security patterns, ACL structure, record rule domains)

---

## Requirement Completeness

- [ ] CHK001 - Are `ir.model.access` CSV specifications complete for all 9 profiles × all relevant models? [Completeness, Gap]
- [ ] CHK002 - Are `ir.rule` record rule domain filters explicitly specified for each profile/model combination? [Completeness, Gap]
- [ ] CHK003 - Are field-level security requirements (`groups=` attribute) defined for sensitive fields (commission_amount, prospector_id, payment_status)? [Completeness, Gap]
- [ ] CHK004 - Are group hierarchy relationships (implied_ids) explicitly documented for all 9 profiles? [Completeness, Spec §FR-075]
- [ ] CHK005 - Are base Odoo groups (base.group_user, base.group_portal, base.group_system) inheritance requirements specified? [Completeness, Gap]
- [ ] CHK006 - Are CRUD permissions (perm_read, perm_write, perm_create, perm_unlink) explicitly defined per profile for property, agent, commission, lead, contract models? [Completeness, Spec §FR-064]
- [ ] CHK007 - Are record rule domains specified for multi-company isolation (estate_company_ids filtering) on all models? [Completeness, Spec §FR-066]
- [ ] CHK008 - Are requirements defined for models beyond core 5 (sale, lease, commission.rule, commission.transaction, partner)? [Coverage, Gap]
- [ ] CHK009 - Are permission requirements specified for auxiliary models (property.type, location.type, state)? [Coverage, Gap]
- [ ] CHK010 - Are XML file structures (security/groups.xml, security/ir.model.access.csv, security/security.xml) explicitly documented? [Completeness, Gap]

## Requirement Clarity

- [ ] CHK011 - Is "full CRUD access" (FR-011) quantified with specific perm_read/write/create/unlink values? [Clarity, Spec §FR-011]
- [ ] CHK012 - Is "read-only access" (FR-041, FR-046, FR-052) clearly defined as perm_read=1, perm_write=0, perm_create=0, perm_unlink=0? [Clarity, Spec §FR-041/046/052]
- [ ] CHK013 - Is "automatically assigned" (FR-024, FR-033) implemented via default_get() method or @api.model_create_multi override? [Clarity, Spec §FR-024/033]
- [ ] CHK014 - Are "cannot create users" (FR-022) and "can create users" (FR-012) mapped to specific Odoo groups (base.group_erp_manager or base.group_system)? [Ambiguity, Spec §FR-012/022]
- [ ] CHK015 - Is "only see their own" (FR-025, FR-034) translated into specific record rule domain syntax ([('agent_id.user_id', '=', user.id)])? [Clarity, Spec §FR-025/034]
- [ ] CHK016 - Are commission split percentages (FR-037: 30%/70%) stored in which fields and calculated in which methods? [Clarity, Spec §FR-037]
- [ ] CHK017 - Is "cannot modify" (FR-042, FR-054) enforced via ir.model.access (perm_write=0) or via field groups attribute? [Ambiguity, Spec §FR-042/054]
- [ ] CHK018 - Are "manager can reassign" (FR-020) permission requirements specified (write access to lead.user_id field)? [Clarity, Spec §FR-020]
- [ ] CHK019 - Is "portal users only see partner_id matches" (FR-057) domain specified as [('partner_id', '=', user.partner_id.id)]? [Clarity, Spec §FR-057]
- [ ] CHK020 - Are temporal requirements ("immediately", FR-068) defined with implementation approach (ORM-level decorators vs write() overrides)? [Measurability, Spec §FR-068]

## Requirement Consistency

- [ ] CHK021 - Do Owner permissions (FR-011: full CRUD) align with user creation requirements (FR-012) without requiring base.group_system? [Conflict, Spec §FR-011/012]
- [ ] CHK022 - Are Manager permissions (FR-019: CRUD on properties) consistent with "cannot create users" (FR-022)? [Consistency, Spec §FR-019/022]
- [ ] CHK023 - Do Agent "cannot modify commission amounts" (FR-028) and "can create properties" (FR-024) permissions avoid overlapping field access? [Consistency, Spec §FR-024/028]
- [ ] CHK024 - Are Prospector "cannot edit properties after creation" (FR-038) and "can create properties" (FR-032) reconciled with write permissions? [Conflict, Spec §FR-032/038]
- [ ] CHK025 - Do Receptionist "read-only properties" (FR-041) and "CRUD contracts" (FR-039) align with property.lease model access? [Consistency, Spec §FR-039/041]
- [ ] CHK026 - Are Financial "read-only sales/leases" (FR-046) and "CRUD commission transactions" (FR-047) permissions non-overlapping on commission_amount field? [Consistency, Spec §FR-046/047]
- [ ] CHK027 - Do Director "inherits Manager" (FR-016) and Manager "CRUD access" (FR-019) create proper implied_ids hierarchy? [Consistency, Spec §FR-016/019]
- [ ] CHK028 - Are multi-profile users (FR-004) permission combinations evaluated with AND logic as per Odoo record rule engine? [Consistency, Spec §FR-004]
- [ ] CHK029 - Do User Story 2 acceptance scenarios align with FR-012 (Owner creates users) without base.group_system conflict? [Traceability, US2/FR-012]
- [ ] CHK030 - Are success criteria SC-003 (zero unauthorized access) and FR-067 (prevent privilege escalation) measurably testable? [Consistency, SC-003/FR-067]

## Acceptance Criteria Quality

- [ ] CHK031 - Can US1 scenario 1 "owner can log in and sees full access" be objectively verified with specific model access assertions? [Measurability, US1]
- [ ] CHK032 - Can US3 scenario 2 "agent sees only their 5 properties" be tested with record count assertions and search domain validation? [Measurability, US3]
- [ ] CHK033 - Can US2 scenario 4 "cannot assign to other companies" be verified with ValidationError or AccessError assertions? [Measurability, US2]
- [ ] CHK034 - Are US4 manager scenarios testable without requiring UI interaction (pure ORM-level permission checks)? [Testability, US4]
- [ ] CHK035 - Can US5 commission split scenario be validated with commission.transaction.commission_amount field calculations? [Measurability, US5]
- [ ] CHK036 - Are acceptance scenarios independent (US3 agent scenarios don't require US2 owner setup to pass)? [Testability, All US]
- [ ] CHK037 - Do success criteria SC-001 to SC-030 include specific assertion methods (assertEqual, assertIn, assertRaises)? [Measurability, SC-001+]
- [ ] CHK038 - Can SC-002 "zero cross-company data leaks" be verified with automated tests on search() results? [Measurability, SC-002]
- [ ] CHK039 - Are time-based success criteria (SC-001: "under 2 minutes") measurable without manual timing? [Measurability, SC-001]
- [ ] CHK040 - Do acceptance scenarios specify expected record counts, error types (AccessError/ValidationError), or field values? [Clarity, All US]

## Scenario Coverage

- [ ] CHK041 - Are requirements defined for zero-state scenarios (agent with no properties, prospector with no prospected records)? [Coverage, Edge Case]
- [ ] CHK042 - Are requirements specified for multi-company user scenarios (user assigned to both Company A and Company B)? [Coverage, Spec §FR-008]
- [ ] CHK043 - Are permission requirements defined for property with both agent_id and prospector_id assigned? [Coverage, Spec §FR-036]
- [ ] CHK044 - Are requirements specified for orphaned records (property.agent_id references deleted user)? [Coverage, Exception Flow]
- [ ] CHK045 - Are rollback/cancellation requirements defined for commission.transaction.payment_status changes? [Coverage, Exception Flow]
- [ ] CHK046 - Are requirements specified for user profile changes (agent → manager promotion mid-session)? [Coverage, Alternate Flow]
- [ ] CHK047 - Are concurrent modification scenarios addressed (two managers reassigning same lead simultaneously)? [Coverage, Exception Flow]
- [ ] CHK048 - Are permission requirements defined for bulk operations (mass property reassignment, bulk commission approval)? [Coverage, Gap]
- [ ] CHK049 - Are requirements specified for users with zero company assignments (edge case or validation error)? [Coverage, Edge Case]
- [ ] CHK050 - Are portal user document upload limits and file type validations specified? [Coverage, Spec §FR-059]

## Edge Case Coverage

- [ ] CHK051 - Are requirements defined for prospector_id field when agent creates property (should be False/None)? [Edge Case, Spec §FR-033]
- [ ] CHK052 - Are permission requirements specified for properties with company_ids=[] (empty multi-company field)? [Edge Case, Gap]
- [ ] CHK053 - Are requirements defined for commission.rule with split_percentage=0 or split_percentage=100? [Edge Case, Spec §FR-037]
- [ ] CHK054 - Are validation requirements specified for negative commission amounts or zero-value transactions? [Edge Case, Gap]
- [ ] CHK055 - Are requirements defined for users assigned to >10 companies (performance/UI implications)? [Edge Case, Gap]
- [ ] CHK056 - Are permission requirements specified for archived/inactive users accessing historical data? [Edge Case, Gap]
- [ ] CHK057 - Are requirements defined for property.agent_id = property.prospector_id (same person)? [Edge Case, Spec §FR-036]
- [ ] CHK058 - Are validation requirements specified for lead.user_id assignment to user outside estate_company_ids? [Edge Case, Spec §FR-020]
- [ ] CHK059 - Are requirements defined for partner.user_id linkage in portal scenarios (multiple portal users per partner)? [Edge Case, Spec §FR-057]
- [ ] CHK060 - Are permission requirements specified for legal user adding notes to contracts outside their company? [Edge Case, Spec §FR-053]

## Non-Functional Requirements

- [ ] CHK061 - Are performance requirements for record rule evaluation quantified (target query time, index requirements)? [Gap, Spec §SC-023]
- [ ] CHK062 - Are security requirements specified for preventing SQL injection in record rule domains? [Gap, Spec §FR-068]
- [ ] CHK063 - Are audit requirements defined for tracking permission changes (user.groups_id write operations)? [Gap, Gap]
- [ ] CHK064 - Are session management requirements specified for profile changes (logout required vs immediate effect)? [Gap, Spec §SC-025]
- [ ] CHK065 - Are database migration requirements defined for adding prospector_id field to existing properties? [Gap, Gap]
- [ ] CHK066 - Are backward compatibility requirements specified for properties created before prospector feature? [Gap, Gap]
- [ ] CHK067 - Are caching requirements defined for record rule evaluation (per-request vs per-query)? [Gap, Gap]
- [ ] CHK068 - Are requirements specified for handling permission errors in bulk operations (partial success)? [Gap, Gap]
- [ ] CHK069 - Are localization requirements defined for error messages (AccessError, ValidationError text)? [Gap, Gap]
- [ ] CHK070 - Are requirements specified for maximum concurrent users per performance target (SC-024)? [Measurability, Spec §SC-024]

## Dependencies & Assumptions

- [ ] CHK071 - Are dependencies on base Odoo modules (base, mail, portal) explicitly documented? [Traceability, Gap]
- [ ] CHK072 - Is assumption A-015 (agent model user_id field exists) validated in existing codebase? [Assumption, Spec §A-015]
- [ ] CHK073 - Is assumption A-003 (models have company_ids) validated for all relevant models? [Assumption, Spec §A-003]
- [ ] CHK074 - Are requirements specified for creating missing assumptions (if agent.user_id doesn't exist)? [Gap, Spec §A-015]
- [ ] CHK075 - Is assumption A-012 (session-based auth sufficient) reconciled with API authentication requirements? [Assumption, Spec §A-012]
- [ ] CHK076 - Are version compatibility requirements specified (Odoo 18.0 vs 17.0 vs 16.0)? [Dependency, Spec §A-001]
- [ ] CHK077 - Are ADR dependencies documented (ADR-008 multi-tenancy, ADR-011 controller security)? [Traceability, Gap]
- [ ] CHK078 - Is assumption A-005 (manual owner creation by SaaS admin) defined with implementation approach? [Assumption, Spec §A-005]
- [ ] CHK079 - Are requirements specified for validating assumption A-011 (rare property transfers)? [Assumption, Spec §A-011]
- [ ] CHK080 - Is assumption A-020 (3-10 agents per company) used to size permission rule complexity? [Assumption, Spec §A-020]

## Ambiguities & Conflicts

- [ ] CHK081 - Does FR-012 "Owner can create users" conflict with Odoo's base.group_system requirement for res.users.create()? [Conflict, Spec §FR-012]
- [ ] CHK082 - Is "Owner" profile distinct from "System Administrator" profile in permission scope? [Ambiguity, Gap]
- [ ] CHK083 - Are "cannot modify commission amounts" (FR-028) fields explicitly listed (commission_amount, rule_id, split_percentage)? [Ambiguity, Spec §FR-028]
- [ ] CHK084 - Is "automatically set prospector_id" (FR-033) behavior specified when prospector edits property via manager reassignment? [Ambiguity, Spec §FR-033]
- [ ] CHK085 - Are "cannot edit properties after creation" (FR-038) exceptions documented (typo fixes, manager overrides)? [Ambiguity, Spec §FR-038]
- [ ] CHK086 - Is "add notes and legal opinions" (FR-053) permission mapped to specific model/fields? [Ambiguity, Spec §FR-053]
- [ ] CHK087 - Are "publicly available" property listings (FR-061) filtering criteria explicitly defined? [Ambiguity, Spec §FR-061]
- [ ] CHK088 - Is "upload documents" (FR-059) permission mapped to ir.attachment model access? [Ambiguity, Spec §FR-059]
- [ ] CHK089 - Does "combined data from all assigned companies" (FR-008) use OR logic in record rule domains? [Ambiguity, Spec §FR-008]
- [ ] CHK090 - Is "enforced at ORM level" (FR-068) implementation approach specified (@api.model decorators vs record rules)? [Ambiguity, Spec §FR-068]

## Odoo Model Alignment

- [ ] CHK091 - Are group XML IDs following Odoo naming convention (group_real_estate_<role>, not group_<role>_real_estate)? [Consistency, Spec §FR-003]
- [ ] CHK092 - Are record rule domains using Odoo ORM syntax ([('field', 'operator', value)]) not Python expressions? [Clarity, Gap]
- [ ] CHK093 - Are ir.model.access CSV column headers matching Odoo 18 schema (id, name, model_id:id, group_id:id, perm_*)? [Completeness, Gap]
- [ ] CHK094 - Are group inheritance relationships using implied_ids field not category_id? [Consistency, Spec §FR-075]
- [ ] CHK095 - Are record rules specifying global=True or groups field, not both simultaneously? [Consistency, Gap]
- [ ] CHK096 - Are Many2many field definitions using correct rel, column1, column2 parameters for estate_company_ids? [Clarity, Gap]
- [ ] CHK097 - Are field-level security definitions using groups="base.group_x,module.group_y" comma-separated syntax? [Clarity, Gap]
- [ ] CHK098 - Are @api.model_create_multi decorators used instead of deprecated @api.model create() for auto-assignment? [Consistency, Gap]
- [ ] CHK099 - Are record rule domain_force fields using recordset expressions not direct SQL? [Consistency, Gap]
- [ ] CHK100 - Are security file load order dependencies specified in __manifest__.py data list? [Completeness, Gap]

## Implementation Readiness

- [ ] CHK101 - Can a developer implement ir.model.access.csv with zero ambiguity from spec? [Completeness, All FR]
- [ ] CHK102 - Can a developer implement ir.rule records with exact domain syntax from spec? [Completeness, All FR]
- [ ] CHK103 - Can a developer implement groups.xml with clear implied_ids relationships from spec? [Completeness, Spec §FR-075]
- [ ] CHK104 - Are migration scripts specified for adding prospector_id field to existing properties? [Gap, Gap]
- [ ] CHK105 - Are data fixtures specified for testing each profile's permissions? [Gap, Gap]
- [ ] CHK106 - Are required Odoo module dependencies listed (__depends__ in __manifest__.py)? [Gap, Gap]
- [ ] CHK107 - Are views/menus visibility requirements (groups="...") specified per profile? [Gap, Gap]
- [ ] CHK108 - Are required indexes specified for performance (estate_company_ids, agent_id, prospector_id)? [Gap, Gap]
- [ ] CHK109 - Are Python field definitions specified for prospector_id (Many2one, domain, ondelete)? [Gap, Spec §FR-069]
- [ ] CHK110 - Are commission split calculation methods (compute= or action method) explicitly specified? [Gap, Spec §FR-036]

## Testing Strategy Validation

- [ ] CHK111 - Are unit tests (TransactionCase) and integration tests (curl/HTTP) clearly separated in spec? [Gap]
- [ ] CHK112 - Are OAuth/API authentication tests explicitly documented as requiring live server (not TransactionCase)? [Ambiguity, Gap]
- [ ] CHK113 - Is test execution strategy documented (which tests run in CI vs manually, skip patterns)? [Gap]
- [ ] CHK114 - Are integration test prerequisites specified (running server, OAuth app setup, test credentials)? [Gap]
- [ ] CHK115 - Is rationale documented for why OAuth tests cannot use Odoo's TransactionCase framework? [Gap]
- [ ] CHK116 - Are curl/Postman test scripts location and naming conventions specified (docs/api-testing.sh)? [Gap]
- [ ] CHK117 - Are test isolation requirements defined (unit tests use rollback, integration tests use test database)? [Gap]
- [ ] CHK118 - Are expected test counts documented per strategy (X unit tests, Y integration tests)? [Gap]
- [ ] CHK119 - Are CI pipeline test execution phases defined (unit → integration → E2E)? [Gap]
- [ ] CHK120 - Is migration path specified for moving OAuth tests from TransactionCase to curl scripts? [Gap]

## Testing Strategy Alignment (ADR-003)

- [ ] CHK121 - Is testing strategy aligned with ADR-003 (unittest.mock for unit, Cypress+curl for E2E)? [Compliance, ADR-003]
- [ ] CHK122 - Are unit tests specified to use unittest.mock WITHOUT database interaction? [Compliance, ADR-003 §Testes Unitários]
- [ ] CHK123 - Are E2E tests specified to use curl for all OAuth/session/database-dependent flows? [Compliance, ADR-003 §E2E Tests]
- [ ] CHK124 - Is rationale documented: "login/permissions require DB writes → must use curl, not unittest"? [Clarity, ADR-003]
- [ ] CHK125 - Are TransactionCase tests explicitly rejected per ADR-003 (not in 3 approved test types)? [Conflict, ADR-003 violation]
- [ ] CHK126 - Is 100% validation coverage (@api.constrains, required fields) requirement specified? [Compliance, ADR-003 §Cobertura 100%]
- [ ] CHK127 - Are curl test scripts structure specified (docs/api-testing.sh, .env for credentials)? [Completeness, ADR-003]
- [ ] CHK128 - Are unit test file requirements specified (tests/test_*_unit.py, Mock objects, no self.env)? [Completeness, ADR-003]
- [ ] CHK129 - Is test execution sequence documented (flake8 → unittest → curl E2E)? [Completeness, ADR-003]
- [ ] CHK130 - Are existing ~160 TransactionCase tests marked for deletion/migration per ADR-003? [Critical Gap, ADR-003 violation]

---

**Summary**: 130 requirement quality validation items across 11 dimensions (Completeness, Clarity, Consistency, Acceptance Criteria, Scenario Coverage, Edge Cases, Non-Functional, Dependencies, Ambiguities, Odoo Alignment, Implementation Readiness, Testing Strategy).

**Critical Finding**: CHK121-130 reveal severe ADR-003 compliance gap - current implementation uses TransactionCase (not approved by ADR-003). All RBAC permission tests must be migrated to curl E2E tests per "ações que dependem de escrita na base → curl" rule.

**Next Steps**: 
1. Execute CHK121-130 to validate ADR-003 compliance
2. Review CHK001-010 (security specifications)
3. Resolve CHK081-090 (ambiguities including Owner create users conflict)
4. Plan migration of 160 TransactionCase tests → curl scripts
