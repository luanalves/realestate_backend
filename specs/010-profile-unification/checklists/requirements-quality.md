# Requirements Quality Checklist: Profile Unification

**Purpose**: Validate clarity, completeness, consistency, and testability of Feature 010 requirements for QA team validation
**Created**: 2026-02-19
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [data-model.md](../data-model.md)
**Audience**: QA Team (Testing and validation)

**Note**: This checklist validates the QUALITY OF REQUIREMENTS, not implementation correctness. Each item checks whether requirements are well-written, complete, unambiguous, and ready for testing.

---

## Requirement Completeness

- [ ] CHK001 - Are all 9 RBAC profile types explicitly documented with their code, name, and purpose? [Completeness, Spec §Executive Summary]
- [ ] CHK002 - Are required fields specified for ALL 9 profile types without ambiguity? [Completeness, Spec D9, D14]
- [ ] CHK003 - Are optional fields clearly marked as optional with conditions specified (e.g., occupation for portal)? [Completeness, Spec FR1.5]
- [ ] CHK004 - Is the compound unique constraint formula documented precisely: (document, company_id, profile_type_id)? [Completeness, Spec FR1.3, Data Model §3.1]
- [ ] CHK005 - Are all 6 API endpoints documented with HTTP method, path, and purpose? [Completeness, Plan §Project Structure]
- [ ] CHK006 - Are RBAC authorization rules specified for each profile type creation scenario? [Completeness, Spec §Clarifications D1, ADR-024]
- [ ] CHK007 - Are soft delete field requirements complete (active, deactivation_date, deactivation_reason)? [Completeness, Spec FR1.11, ADR-015]
- [ ] CHK008 - Are audit timestamp fields documented (created_at, updated_at) with explicit rejection of Odoo defaults? [Completeness, Spec D10]
- [ ] CHK009 - Are validator function signatures documented (validate_document, normalize_document, is_cpf, is_cnpj)? [Completeness, Spec D11, Tasks T01]
- [ ] CHK010 - Are Feature 009 integration touchpoints documented (profile_id in invite payload)? [Completeness, Spec D7, Plan §Modified Feature 009 Files]

## Requirement Clarity

- [ ] CHK011 - Is "multi-tenancy" operationally defined with specific parameter (company_ids) and validation rules? [Clarity, Spec D5.2, FR1.13]
- [ ] CHK012 - Is the "two-step flow" integration with Feature 009 described with explicit sequencing? [Clarity, Spec D7]
- [ ] CHK013 - Is the agent extension auto-creation behavior defined with atomicity requirement? [Clarity, Spec FR1.4]
- [ ] CHK014 - Is "compound unique constraint allows same document in different companies" explicitly stated? [Clarity, Spec AC1.5]
- [ ] CHK015 - Is the performance requirement quantified (< 200ms p95 for CRUD operations)? [Clarity, Plan §Technical Context]
- [ ] CHK016 - Is the source of company_id (body vs header) unambiguously specified for POST? [Clarity, Spec D5.1, FR1.6]
- [ ] CHK017 - Is the source of company_ids (query param) unambiguously specified for GET? [Clarity, Spec D5.2]
- [ ] CHK018 - Are CPF (11 digits) and CNPJ (14 digits) format requirements explicitly stated? [Clarity, Spec FR1.7]
- [ ] CHK019 - Is "soft delete" defined with specific field changes (active=False, timestamps)? [Clarity, Spec FR1.11]
- [ ] CHK020 - Are HATEOAS link requirements specified with exact link names (self, invite, company)? [Clarity, Spec FR1.9]

## Requirement Consistency

- [ ] CHK021 - Do plan.md and spec.md agree on the number of API endpoints (6)? [Consistency, Spec §FR vs Plan §Project Structure]
- [ ] CHK022 - Are field names consistent between spec.md (FR1.1) and data-model.md (§2.2)? [Consistency]
- [ ] CHK023 - Does the RBAC authorization matrix match between spec and ADR-024? [Consistency, Spec FR1.10 vs ADR-024]
- [ ] CHK024 - Are authentication requirements consistent across all endpoints (@require_jwt + @require_session + @require_company)? [Consistency, Plan §Constitution Check I]
- [ ] CHK025 - Is the compound unique constraint formula consistent across spec, plan, and data-model? [Consistency]
- [ ] CHK026 - Are validator function references consistent (utils/validators.py) across spec D11 and tasks T01? [Consistency]
- [ ] CHK027 - Are required fields (birthdate, document) consistently marked as mandatory for all 9 types? [Consistency, Spec D9, D14]
- [ ] CHK028 - Do error response codes align with ADR patterns (409 for conflict, 403 for RBAC)? [Consistency, Spec AC1.4, AC1.6]

## Acceptance Criteria Quality

- [ ] CHK029 - Can AC1.1 be objectively verified (profile created in correct table with correct company_id)? [Measurability, Spec AC1.1]
- [ ] CHK030 - Can AC1.2 be objectively verified (agent extension created with profile_id link)? [Measurability, Spec AC1.2]
- [ ] CHK031 - Can AC1.3 be objectively verified (occupation field accepted for portal type)? [Measurability, Spec AC1.3]
- [ ] CHK032 - Can AC1.4 be objectively verified (409 Conflict response for duplicate)? [Measurability, Spec AC1.4]
- [ ] CHK033 - Can AC1.5 be objectively verified (profile created in different company)? [Measurability, Spec AC1.5]
- [ ] CHK034 - Can AC1.6 be objectively verified (403 Forbidden for RBAC violation)? [Measurability, Spec AC1.6]
- [ ] CHK035 - Can AC1.7 be objectively verified (400 Bad Request for invalid profile_type)? [Measurability, Spec AC1.7]
- [ ] CHK036 - Are success criteria defined as specific HTTP status codes rather than vague terms? [Measurability]
- [ ] CHK037 - Are test coverage percentages specified (≥80% per ADR-003)? [Measurability, Plan §Constitution Check II]

## Scenario Coverage - Primary Flows

- [ ] CHK038 - Are requirements defined for Owner creating all 9 profile types? [Coverage, Spec US1, RBAC matrix]
- [ ] CHK039 - Are requirements defined for Manager creating 5 authorized types? [Coverage, Spec US1, RBAC matrix]
- [ ] CHK040 - Are requirements defined for Agent creating 2 authorized types (owner, portal)? [Coverage, Spec US1, RBAC matrix]
- [ ] CHK041 - Are requirements defined for listing profiles with pagination? [Coverage, Spec US2]
- [ ] CHK042 - Are requirements defined for filtering profiles by profile_type? [Coverage, Spec D5.2]
- [ ] CHK043 - Are requirements defined for updating profile mutable fields? [Coverage, Spec US3]
- [ ] CHK044 - Are requirements defined for soft deleting profiles? [Coverage, Spec US4]
- [ ] CHK045 - Are requirements defined for two-step profile creation + invitation flow? [Coverage, Spec US5, D7]

## Scenario Coverage - Alternate Flows

- [ ] CHK046 - Are requirements defined for creating same document in multiple companies? [Coverage, Spec AC1.5, FR1.3]
- [ ] CHK047 - Are requirements defined for creating same document with different profile_types in one company? [Coverage, Test T1.3]
- [ ] CHK048 - Are requirements defined for listing profile types (GET /api/v1/profile-types)? [Coverage, Plan endpoints]

## Scenario Coverage - Exception Flows

- [ ] CHK049 - Are requirements defined for duplicate document+company+type rejection (409)? [Coverage, Spec AC1.4]
- [ ] CHK050 - Are requirements defined for RBAC matrix violation (403)? [Coverage, Spec AC1.6]
- [ ] CHK051 - Are requirements defined for invalid profile_type (400)? [Coverage, Spec AC1.7]
- [ ] CHK052 - Are requirements defined for invalid CPF/CNPJ format (400)? [Coverage, Spec FR1.7, Test T1.5]
- [ ] CHK053 - Are requirements defined for inactive profile_type rejection (400)? [Coverage, Test T1.7]
- [ ] CHK054 - Are requirements defined for cross-company access (404 anti-enumeration)? [Coverage, Spec FR1.12]
- [ ] CHK055 - Are requirements defined for missing required fields (400)? [Coverage, Spec FR1.1]
- [ ] CHK056 - Are requirements defined for invalid email format (400)? [Coverage, Spec FR1.7]

## Scenario Coverage - Recovery Flows

- [ ] CHK057 - Are rollback requirements defined if agent extension creation fails? [Coverage, Gap - atomic transaction]
- [ ] CHK058 - Are requirements defined for handling profile update when linked agent exists? [Coverage, Spec - agent sync logic]
- [ ] CHK059 - Are requirements defined for handling profile deactivation cascade to agent? [Coverage, Spec US4]

## Scenario Coverage - Non-Functional Requirements

- [ ] CHK060 - Are performance requirements specified for all CRUD operations? [Coverage, Plan §Technical Context]
- [ ] CHK061 - Are authentication requirements specified for all 6 endpoints? [Coverage, Plan §Constitution Check I]
- [ ] CHK062 - Are company isolation requirements specified for all data access? [Coverage, Plan §Constitution Check IV]
- [ ] CHK063 - Are audit trail requirements specified (created_at, updated_at, deactivation timestamps)? [Coverage, Spec D10, FR1.11]

## Edge Case Coverage

- [ ] CHK064 - Are requirements defined for profile_type lookup table soft delete behavior? [Edge Case, Data Model §2.1]
- [ ] CHK065 - Are requirements defined for profile with missing optional fields (phone, mobile)? [Edge Case, Spec FR1.1]
- [ ] CHK066 - Are requirements defined for profile creation when partner_id does not exist yet? [Edge Case, Data Model §2.2]
- [ ] CHK067 - Are requirements defined for document normalization edge cases (masks, special chars)? [Edge Case, Spec FR1.8]
- [ ] CHK068 - Are requirements defined for pagination boundary conditions (offset > total)? [Edge Case, Spec US2]
- [ ] CHK069 - Are requirements defined for profile update attempting to change immutable fields? [Edge Case, Data Model §4 Constraints]
- [ ] CHK070 - Are requirements defined for profile with same name but different documents? [Edge Case, Duplicate detection]
- [ ] CHK071 - Are requirements defined for reactivating a soft-deleted profile? [Edge Case, ADR-015 soft delete]
- [ ] CHK072 - Are requirements defined for listing profiles with no results (empty state)? [Edge Case, Pagination]
- [ ] CHK073 - Are requirements defined for agent profile when agent extension already exists? [Edge Case, Constraint violation]

## Non-Functional Requirements Quality

- [ ] CHK074 - Are security patterns specified (dual auth decorators, anti-enumeration)? [NFR Security, Plan §Constitution Check I]
- [ ] CHK075 - Are database constraints documented (compound unique at DB level)? [NFR Data Integrity, Spec FR1.3]
- [ ] CHK076 - Are performance targets quantified with percentile (p95 < 200ms)? [NFR Performance, Plan §Technical Context]
- [ ] CHK077 - Are multi-tenancy isolation mechanisms specified (record rules, company_ids validation)? [NFR Multi-tenancy, Plan §Constitution Check IV]
- [ ] CHK078 - Are test coverage requirements quantified (≥80% per ADR-003)? [NFR Quality, Plan §Constitution Check II]
- [ ] CHK079 - Are API-first patterns specified (RESTful, HATEOAS, OpenAPI)? [NFR Architecture, Plan §Constitution Check III]
- [ ] CHK080 - Are concurrency patterns defined (atomic transaction for agent+profile)? [NFR Concurrency, Spec FR1.4]
- [ ] CHK081 - Are storage requirements specified (PostgreSQL + Redis)? [NFR Infrastructure, Plan §Technical Context]

## Dependencies & Assumptions Validation

- [ ] CHK082 - Is the Feature 009 dependency documented with specific integration points? [Dependency, Spec D7, Plan §Modified Feature 009 Files]
- [ ] CHK083 - Is the validators.py dependency documented with function list? [Dependency, Spec D11, Tasks T01]
- [ ] CHK084 - Is the ADR-019 RBAC matrix dependency documented? [Dependency, Spec FR1.10]
- [ ] CHK085 - Is the ADR-024 (Profile Unification) reference documented? [Dependency, Spec ADR References]
- [ ] CHK086 - Is the KB-09 (Database Best Practices) reference documented for lookup tables? [Dependency, Spec D6]
- [ ] CHK087 - Is the assumption "development environment, no legacy data" explicitly stated? [Assumption, Spec Executive Summary]
- [ ] CHK088 - Is the assumption "agent has 611 LOC domain logic" validated with file reference? [Assumption, Spec D2]
- [ ] CHK089 - Is the assumption "tenant is simple (35 LOC)" validated with file reference? [Assumption, Spec D3]
- [ ] CHK090 - Are PostgreSQL 14+ and Redis 7+ version requirements documented? [Dependency, Plan §Technical Context]

## Traceability & Documentation

- [ ] CHK091 - Are all functional requirements tagged with FR IDs (FR1.1 through FR1.14)? [Traceability, Spec §Functional Requirements]
- [ ] CHK092 - Are all acceptance criteria tagged with AC IDs (AC1.1 through AC1.7+)? [Traceability, Spec §Acceptance Criteria]
- [ ] CHK093 - Are all test cases tagged with Test IDs (T1.1 through T1.15+)? [Traceability, Spec §Test Coverage]
- [ ] CHK094 - Are all decisions tagged with Decision IDs (D1 through D12+)? [Traceability, Spec §Clarifications & Decisions]
- [ ] CHK095 - Do all requirements reference their source section? [Traceability]
- [ ] CHK096 - Is the OpenAPI specification requirement documented in plan.md? [Traceability, Plan contracts/openapi.yaml]
- [ ] CHK097 - Is the Postman collection requirement documented in plan.md? [Traceability, Plan docs/postman/]
- [ ] CHK098 - Are all ADR references traceable to actual ADR documents? [Traceability, Spec ADR References]

## Ambiguities & Conflicts

- [ ] CHK099 - Is the term "profile" consistently used (never "user profile" or "account")? [Ambiguity, Terminology]
- [ ] CHK100 - Is "active company" defined when user belongs to multiple companies? [Ambiguity, Multi-tenancy]
- [ ] CHK101 - Is "atomic transaction" scope defined for agent+profile creation? [Ambiguity, Spec FR1.4]
- [ ] CHK102 - Is "same document" behavior unambiguous (allows different companies AND types)? [Ambiguity, Spec FR1.3]
- [ ] CHK103 - Are validation error messages specified or left to implementation? [Gap, Error handling]
- [ ] CHK104 - Is profile update behavior defined when profile_type is agent (sync to extension)? [Ambiguity, Sync logic]
- [ ] CHK105 - Is the order of validation checks specified (AuthZ→Isolation→Validation per FR1.12)? [Clarity, Error precedence]
- [ ] CHK106 - Are filter parameters for GET /api/v1/profiles exhaustively listed? [Completeness, Spec D5.2]
- [ ] CHK107 - Is pagination default behavior specified (limit, offset defaults)? [Gap, Spec US2]
- [ ] CHK108 - Is HATEOAS link generation conditional on user permissions? [Gap, Spec FR1.9]

## Requirements Evolution & Maintenance

- [ ] CHK109 - Is the requirements version/date specified in spec.md header? [Maintenance, Spec metadata]
- [ ] CHK110 - Are requirement changes traceable to specific sessions/dates? [Maintenance, Spec §Clarifications & Decisions]
- [ ] CHK111 - Are "Out of Scope" items documented to prevent scope creep? [Scope Management, Spec §Out of Scope]
- [ ] CHK112 - Are future phases documented (ADR-019 Phase 2: profile customization)? [Evolution, Spec §Out of Scope]
- [ ] CHK113 - Is the ADR-024 status tracked (Draft vs Accepted)? [Governance, Spec header]

---

## Notes

- ✅ Check items off as requirements are validated: `[x]`
- 💬 Add comments inline for findings (e.g., "Ambiguous: define 'active company'")
- 🔗 Link to relevant documentation sections with line numbers
- 🚩 Flag critical gaps or conflicts with priority markers
- Items are numbered sequentially (CHK001-CHK113) for easy reference in QA reports

## Validation Process

1. **Read Requirements**: Review spec.md, plan.md, data-model.md completely
2. **Check Each Item**: For each checklist item, verify requirement exists and is clear
3. **Document Findings**: Add inline comments for ambiguities, gaps, or conflicts  
4. **Prioritize Issues**: Mark critical items affecting testability or implementation
5. **Report Results**: Summarize checked/unchecked items with issue count

## Success Criteria

- ✅ **≥90% items checked** = Requirements ready for implementation
- ⚠️ **80-89% items checked** = Minor clarifications needed
- ❌ **<80% items checked** = Major gaps, requires spec revision
