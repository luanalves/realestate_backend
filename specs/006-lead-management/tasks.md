# Tasks: Real Estate Lead Management System

**Input**: Design documents from `/specs/006-lead-management/`  
**Branch**: `006-lead-management` | **Generated**: 2026-01-29

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Constitution v1.1.0 requires 80% test coverage. All test tasks use specialized test agents:
- `.github/prompts/test-strategy.prompt.md` for test type analysis
- `.github/prompts/test-executor.prompt.md` for test code generation
- `.github/agents/speckit.tests.agent.md` for acceptance scenario-based tests

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

All paths relative to repository root `/opt/homebrew/var/www/realestate/realestate_backend/`:
- **Module root**: `18.0/extra-addons/quicksol_estate/`
- **Tests**: Unit (`18.0/extra-addons/quicksol_estate/tests/unit/`), E2E API (`18.0/extra-addons/quicksol_estate/tests/api/`), Cypress (`cypress/e2e/`), Integration (`integration_tests/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create git branch `006-lead-management` from `main`
- [X] T002 [P] Create model directory structure in `18.0/extra-addons/quicksol_estate/models/` if not exists
- [X] T003 [P] Create controller directory structure in `18.0/extra-addons/quicksol_estate/controllers/` if not exists
- [X] T004 [P] Create security directory structure in `18.0/extra-addons/quicksol_estate/security/` if not exists
- [X] T005 [P] Create views directory structure in `18.0/extra-addons/quicksol_estate/views/` if not exists
- [X] T006 [P] Create test directories: `18.0/extra-addons/quicksol_estate/tests/unit/` and `18.0/extra-addons/quicksol_estate/tests/api/`
- [X] T007 Update `18.0/extra-addons/quicksol_estate/__manifest__.py` to include new model, views, security files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Verify real.estate.agent model exists (dependency from branch 005-rbac-user-profiles)
- [X] T009 Verify thedevkitchen.estate.company model exists (multi-tenancy dependency)
- [X] T010 Verify real.estate.property model exists (dependency for lead conversion)
- [X] T011 Verify real.estate.property.type model exists (property type master data)
- [X] T012 Create real.estate.sale model stub if not exists in `18.0/extra-addons/quicksol_estate/models/real_estate_sale.py` (required for lead conversion)
- [X] T013 Verify triple decorator pattern (`@require_jwt`, `@require_session`, `@require_company`) exists in controllers (ADR-011 compliance)
- [X] T014 Verify `success_response()` and `error_response()` helper functions exist for API responses

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Agent Creates and Manages Own Leads (Priority: P1) 🎯 MVP

**Goal**: Enable agents to register client inquiries as leads, track them through pipeline stages, and convert qualified leads to property sales. Agents see only their own leads (agent isolation).

**Independent Test**: Agent logs in → creates lead with contact info and preferences → updates status through pipeline (New → Contacted → Qualified) → converts to sale → verifies only own leads visible.

### Test Strategy for User Story 1

- [ ] T015 [P] [US1] Run test strategy agent using `.github/prompts/test-strategy.prompt.md` to analyze User Story 1 acceptance scenarios and determine test types (unit, E2E API, E2E UI)
- [ ] T016 [US1] Review test strategy output and confirm test plan covers: duplicate prevention, state transitions, agent isolation, lead conversion

### Unit Tests for User Story 1

**Write these tests FIRST using test executor agent, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Generate unit test for duplicate prevention validation using `.github/prompts/test-executor.prompt.md` in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_duplicate_validation.py`
- [ ] T018 [P] [US1] Generate unit test for budget range validation using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_budget_validation.py`
- [ ] T019 [P] [US1] Generate unit test for lost reason requirement using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_lost_reason_validation.py`
- [ ] T020 [P] [US1] Generate unit test for company validation using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_company_validation.py`
- [ ] T021 [P] [US1] Generate unit test for state transitions and logging using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_state_transitions.py`
- [ ] T022 [P] [US1] Generate unit test for soft delete behavior using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_soft_delete.py`
- [ ] T023 [US1] Run unit tests and verify they FAIL (no implementation exists yet)

### E2E API Tests for User Story 1

- [ ] T024 [P] [US1] Generate E2E test for lead CRUD operations using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_crud_api.py` (create, list, get, update, archive endpoints with auth/validation/permissions)
- [ ] T025 [P] [US1] Generate E2E test for lead conversion endpoint using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_conversion_api.py` (convert action with transaction atomicity)
- [ ] T026 [P] [US1] Generate E2E test for agent isolation using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_agent_isolation_api.py` (agent sees only own leads)
- [ ] T027 [US1] Run E2E API tests and verify they FAIL (no endpoints exist yet)

### Integration Tests for User Story 1

- [ ] T028 [P] [US1] Generate shell integration test for agent lead creation using SpecKit tests agent in `integration_tests/test_us6_s1_agent_creates_lead.sh` (curl-based with real DB)
- [ ] T029 [P] [US1] Generate shell integration test for agent lead pipeline using SpecKit tests agent in `integration_tests/test_us6_s2_agent_lead_pipeline.sh` (state transitions)
- [ ] T030 [P] [US1] Generate shell integration test for lead conversion using SpecKit tests agent in `integration_tests/test_us6_s3_lead_conversion.sh` (convert to sale)
- [ ] T031 [P] [US1] Generate shell integration test for agent isolation using SpecKit tests agent in `integration_tests/test_us6_s4_agent_isolation.sh` (no cross-agent access)
- [ ] T032 [US1] Run integration tests and verify they FAIL (no implementation exists yet)

### Cypress E2E UI Tests for User Story 1

- [ ] T033 [P] [US1] Generate Cypress test for agent lead creation flow using SpecKit tests agent in `cypress/e2e/lead-agent-crud.cy.js` (login, create lead, fill form, submit)
- [ ] T034 [P] [US1] Generate Cypress test for lead pipeline management using SpecKit tests agent in `cypress/e2e/lead-agent-pipeline.cy.js` (update status, log activities, convert)
- [ ] T035 [US1] Run Cypress tests and verify they FAIL (no UI/API exists yet)

### Implementation for User Story 1

**Core Model Implementation**

- [X] T036 [US1] Create `real.estate.lead` model in `18.0/extra-addons/quicksol_estate/models/real_estate_lead.py` with all 25 fields per data-model.md (core identity, contact info, ownership, preferences, lifecycle, conversion)
- [X] T037 [US1] Add mail.thread and mail.activity.mixin inheritance to model for activity tracking (FR-003)
- [X] T038 [US1] Implement 4 validation constraints in model: duplicate prevention (_check_duplicate_per_agent), budget range (_check_budget_range), company validation (_check_agent_company), lost reason (_check_lost_reason)
- [X] T039 [US1] Implement default value methods: _default_agent_id (auto-assign current user's agent), _default_company_ids (auto-assign user's companies)
- [X] T040 [US1] Implement computed fields: _compute_display_name (name with partner info), _compute_days_in_state (pipeline metrics)
- [X] T041 [US1] Override unlink() method for soft delete (set active=False instead of hard delete per FR-018b)
- [X] T042 [US1] Override write() method to log state changes in chatter with timestamps
- [X] T043 [US1] Implement action_reopen() method for lost lead reactivation (changes lost → contacted per FR-018a)
- [X] T044 [US1] Import real_estate_lead in `18.0/extra-addons/quicksol_estate/models/__init__.py`

**Security Implementation**

- [X] T045 [P] [US1] Create security file `18.0/extra-addons/quicksol_estate/security/real_estate_lead_security.xml` with record rules
- [X] T046 [US1] Add agent record rule: domain `[('agent_id.user_id', '=', user.id), ('company_ids', 'in', user.estate_company_ids.ids)]` with CRUD permissions (FR-019, FR-020, FR-021)
- [X] T047 [US1] Update `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv` with lead model access: agent (CRUD), manager (CRUD), owner (CRUD)

**API Controller Implementation**

- [X] T048 [US1] Create lead controller in `18.0/extra-addons/quicksol_estate/controllers/lead_api.py` with base structure and triple decorators
- [X] T049 [US1] Implement POST /api/v1/leads (create lead) with auto-agent assignment, duplicate validation, success_response() on 201
- [X] T050 [US1] Implement GET /api/v1/leads (list leads) with pagination (page, limit, default 50), state/agent filters, search_read() optimization
- [X] T051 [US1] Implement GET /api/v1/leads/{id} (get lead) with related fields (partner, agent, property, activities)
- [X] T052 [US1] Implement PUT /api/v1/leads/{id} (update lead) with validation, agent_id immutability check for agents
- [X] T053 [US1] Implement DELETE /api/v1/leads/{id} (archive lead) with soft delete, 204 response
- [X] T054 [US1] Implement POST /api/v1/leads/{id}/convert (convert to sale) with atomic transaction, property validation, sale record creation, state update to 'won'
- [X] T054b [US1] Implement POST /api/v1/leads/{id}/reopen (reopen lost lead) with state validation (must be 'lost'), state change to 'contacted', activity logging per FR-018a
- [X] T055 [US1] Import lead_api in `18.0/extra-addons/quicksol_estate/controllers/__init__.py`

**Odoo Web Views (Manager Oversight)**

- [X] T056 [P] [US1] Create views file `18.0/extra-addons/quicksol_estate/views/real_estate_lead_views.xml`
- [X] T057 [P] [US1] Implement list view with columns: name, partner_id, agent_id, state, budget_min/max, phone, email, create_date (FR-034)
- [X] T058 [P] [US1] Implement form view with tabs: General Info (contact + ownership), Property Preferences (budget + type + location), Activities (chatter), Conversion (converted fields) (FR-035)
- [X] T059 [P] [US1] Implement kanban view grouped by state with drag-and-drop for status updates (FR-036)
- [X] T060 [P] [US1] Implement calendar view showing expected_closing_date for pipeline forecasting (FR-037)
- [X] T061 [US1] Add menu item for leads under Real Estate app in views file

**Integration & Testing**

- [ ] T062 [US1] Run all unit tests and verify they PASS (duplicate prevention, budget validation, state transitions, soft delete)
- [ ] T063 [US1] Run all E2E API tests and verify they PASS (CRUD endpoints, conversion, agent isolation)
- [ ] T064 [US1] Run all integration tests (shell scripts) and verify they PASS (agent creates lead, pipeline, conversion, isolation)
- [ ] T065 [US1] Run Cypress tests and verify they PASS (UI flows for agent lead management)
- [ ] T066 [US1] Verify test coverage ≥80% for User Story 1 using coverage report
- [ ] T067 [US1] Test duplicate prevention: Agent tries to create lead with same phone/email → blocked with existing lead shown
- [ ] T068 [US1] Test agent isolation: Agent A logs in → sees only own 3 leads → Agent B logs in → sees only own 5 leads (zero overlap)
- [ ] T069 [US1] Test lead conversion: Agent creates lead → qualifies it → converts to sale → verifies sale record created with lead reference
- [ ] T070 [US1] Test soft delete: Agent archives lead → lead hidden from list view → database record preserved with active=False

**Checkpoint**: At this point, User Story 1 (Agent CRUD + Conversion) should be fully functional and independently testable. Agents can create leads, manage pipeline, and convert to sales with full isolation.

---

## Phase 4: User Story 2 - Manager Oversees All Company Leads (Priority: P2)

**Goal**: Enable managers to view all leads across all agents in their company for team performance monitoring, bottleneck identification, lead reassignment, and sales forecasting. Multi-tenancy respected (Company A manager sees zero Company B leads).

**Independent Test**: Manager logs in to Company A (3 agents, 15 leads) → views dashboard showing all 15 leads with agent names → filters by status/agent → reassigns lead from Agent A to Agent B → verifies zero visibility into Company B leads.

### Test Strategy for User Story 2

- [ ] T071 [P] [US2] Run test strategy agent to analyze User Story 2 acceptance scenarios and determine test types (focus on manager permissions and multi-tenancy)

### Unit Tests for User Story 2

- [ ] T072 [P] [US2] Generate unit test for lead reassignment logging using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_reassignment.py` (activity history tracking per FR-027)
- [ ] T073 [US2] Run unit tests and verify they FAIL

### E2E API Tests for User Story 2

- [ ] T074 [P] [US2] Generate E2E test for manager all-leads access using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_manager_access_api.py` (manager sees all company leads)
- [ ] T075 [P] [US2] Generate E2E test for multi-tenancy isolation using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_multitenancy_api.py` (Company A manager sees zero Company B data)
- [ ] T076 [P] [US2] Generate E2E test for lead reassignment using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_reassignment_api.py` (manager updates agent_id with validation)
- [ ] T077 [US2] Run E2E API tests and verify they FAIL

### Integration Tests for User Story 2

- [ ] T078 [P] [US2] Generate shell integration test for manager views all leads using SpecKit tests agent in `integration_tests/test_us6_s5_manager_all_leads.sh` (Company A manager sees 15 leads from 3 agents)
- [ ] T079 [P] [US2] Generate shell integration test for manager reassigns lead using SpecKit tests agent in `integration_tests/test_us6_s6_manager_reassignment.sh` (update agent_id, verify activity log)
- [ ] T080 [P] [US2] Generate shell integration test for multi-tenancy isolation using SpecKit tests agent in `integration_tests/test_us6_s7_manager_multitenancy.sh` (Company A manager sees zero Company B leads)
- [ ] T081 [US2] Run integration tests and verify they FAIL

### Cypress E2E UI Tests for User Story 2

- [ ] T082 [P] [US2] Generate Cypress test for manager dashboard using SpecKit tests agent in `cypress/e2e/lead-manager-dashboard.cy.js` (login as manager, view all leads, filter by status/agent)
- [ ] T083 [P] [US2] Generate Cypress test for lead reassignment using SpecKit tests agent in `cypress/e2e/lead-manager-reassignment.cy.js` (manager selects lead, changes agent, verifies notification)
- [ ] T084 [US2] Run Cypress tests and verify they FAIL

### Implementation for User Story 2

**Security Implementation**

- [ ] T085 [US2] Add manager record rule to `18.0/extra-addons/quicksol_estate/security/real_estate_lead_security.xml`: domain `[('company_ids', 'in', user.estate_company_ids.ids)]` with full CRUD (FR-024, FR-025)
- [ ] T086 [US2] Verify agent rule does NOT apply to managers (separate group_estate_manager rule takes precedence)

**API Enhancements**

- [ ] T087 [US2] Update GET /api/v1/leads to return all company leads for managers (record rules auto-filter), keep agent_id filter optional
- [ ] T088 [US2] Update PUT /api/v1/leads/{id} to allow managers to update agent_id field (reassignment per FR-026), log reassignment in chatter per FR-027
- [ ] T089 [US2] Add validation in PUT endpoint: prevent reassignment to agent from different company

**Analytics & Reporting**

- [ ] T090 [US2] Implement GET /api/v1/leads/statistics endpoint in `18.0/extra-addons/quicksol_estate/controllers/lead_api.py` returning lead counts by status, agent, date range (FR-028, acceptance scenario 5)
- [ ] T091 [US2] Add response schema: `{ total: int, by_status: {new: int, contacted: int, ...}, by_agent: [{agent_id: int, agent_name: str, count: int}], conversion_rate: float }`

**Odoo Web Views Enhancements**

- [ ] T092 [P] [US2] Add search filters to list view: state, agent_id, create_date range, budget range in `18.0/extra-addons/quicksol_estate/views/real_estate_lead_views.xml` (FR-028, acceptance scenario 2)
- [ ] T093 [P] [US2] Add dashboard pivot view for lead analysis in views file: rows=agent_id, columns=state, measure=count (acceptance scenario 5)
- [ ] T094 [P] [US2] Add graph view showing lead counts by status (pie chart per FR-038) in views file

**Integration & Testing**

- [ ] T095 [US2] Run all unit tests for US2 and verify they PASS (reassignment logging)
- [ ] T096 [US2] Run all E2E API tests for US2 and verify they PASS (manager access, multi-tenancy, reassignment)
- [ ] T097 [US2] Run all integration tests for US2 and verify they PASS (manager all leads, reassignment, isolation)
- [ ] T098 [US2] Run Cypress tests for US2 and verify they PASS (manager dashboard, reassignment UI)
- [ ] T099 [US2] Verify test coverage ≥80% for User Story 2
- [ ] T100 [US2] Test manager access: Manager logs in → sees all 15 company leads from 3 agents
- [ ] T101 [US2] Test multi-tenancy: Company A manager logs in → GET /api/v1/leads returns only Company A leads → verify zero Company B leads in response
- [ ] T102 [US2] Test lead reassignment: Manager updates lead from Agent A to Agent B → verify agent_id changed → check activity history shows "Reassigned from Agent A to Agent B by Manager X"
- [ ] T103 [US2] Test analytics: Manager generates quarterly report → verify lead counts by agent and status distribution accurate

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Managers can oversee all company leads, reassign them, and generate reports while respecting multi-tenancy.

---

## Phase 5: User Story 3 - Lead Lifecycle Tracking with Activities (Priority: P2)

**Goal**: Enable agents and managers to track all interactions with leads (calls, emails, meetings) to maintain sales context across the cycle. Integration with Odoo's activity/mail system provides unified communication history.

**Independent Test**: Agent creates lead → logs 3 activities (call, email, meeting scheduled) → opens lead detail view → verifies activities appear in chronological order with icons → manager views same lead → sees all activities with agent names.

### Test Strategy for User Story 3

- [ ] T104 [P] [US3] Run test strategy agent to analyze User Story 3 acceptance scenarios and determine test types (focus on activity logging and mail.thread integration)

### Unit Tests for User Story 3

- [ ] T105 [P] [US3] Generate unit test for activity logging via mail.thread using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_activities.py` (message_post, activity creation)
- [ ] T106 [P] [US3] Generate unit test for activity history preservation after conversion using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_activity_preservation.py` (FR-018)
- [ ] T107 [US3] Run unit tests and verify they FAIL

### E2E API Tests for User Story 3

- [ ] T108 [P] [US3] Generate E2E test for activity logging via API using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_activities_api.py` (create activity, list activities, verify timestamps)
- [ ] T109 [P] [US3] Generate E2E test for activity reminders using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_activity_reminders_api.py` (schedule meeting, set reminder, verify notification)
- [ ] T110 [US3] Run E2E API tests and verify they FAIL

### Integration Tests for User Story 3

- [ ] T111 [P] [US3] Generate shell integration test for activity logging using SpecKit tests agent in `integration_tests/test_us6_s8_lead_activities.sh` (create lead, log activity, verify in history)
- [ ] T112 [P] [US3] Generate shell integration test for activity preservation using SpecKit tests agent in `integration_tests/test_us6_s9_activity_preservation.sh` (convert lead, verify activities still accessible)
- [ ] T113 [US3] Run integration tests and verify they FAIL

### Cypress E2E UI Tests for User Story 3

- [ ] T114 [P] [US3] Generate Cypress test for activity logging UI using SpecKit tests agent in `cypress/e2e/lead-activities.cy.js` (open lead, log call, log email, schedule meeting, verify timeline)
- [ ] T115 [US3] Run Cypress test and verify it FAILS

### Implementation for User Story 3

**Model already has mail.thread/mail.activity.mixin from US1 - just need API/UI exposure**

**API Enhancements for Activities**

- [ ] T116 [US3] Add POST /api/v1/leads/{id}/activities endpoint in `18.0/extra-addons/quicksol_estate/controllers/lead_api.py` for logging activities (body, activity_type_id)
- [ ] T117 [US3] Add GET /api/v1/leads/{id}/activities endpoint to list all activities with timestamps, user names, and types
- [ ] T118 [US3] Update GET /api/v1/leads/{id} response to include recent_activities array (last 5 activities)
- [ ] T119 [US3] Add activity reminder support: POST /api/v1/leads/{id}/schedule-activity with date_deadline field

**Odoo Web Views Enhancements**

- [ ] T120 [US3] Verify chatter widget exists in form view Activities tab from US1 (should already be present due to mail.thread inheritance)
- [ ] T121 [US3] Add activity timeline view to views file showing all lead activities chronologically (FR-016)

**Integration & Testing**

- [ ] T122 [US3] Run all unit tests for US3 and verify they PASS (activity logging, preservation)
- [ ] T123 [US3] Run all E2E API tests for US3 and verify they PASS (activity endpoints, reminders)
- [ ] T124 [US3] Run all integration tests for US3 and verify they PASS (activity logging, preservation)
- [ ] T125 [US3] Run Cypress test for US3 and verify it PASSES (activity UI)
- [ ] T126 [US3] Verify test coverage ≥80% for User Story 3
- [ ] T127 [US3] Test activity logging: Agent creates lead → logs "Called client - interested in condos" → verify activity created with timestamp
- [ ] T128 [US3] Test activity timeline: Agent logs 3 activities → opens lead detail → verifies reverse chronological order with icons (phone, email, meeting)
- [ ] T129 [US3] Test activity reminders: Agent schedules meeting 2 days from now → verify calendar activity created → verify notification triggers
- [ ] T130 [US3] Test activity history preservation: Agent converts lead to sale → views property deal → verifies link to original lead with full activity history

**Checkpoint**: All user stories (US1, US2, US3) should now be independently functional. Full activity tracking integrated with lead lifecycle.

---

## Phase 6: User Story 4 - Lead Search and Filtering (Priority: P3)

**Goal**: Enable agents and managers to quickly find leads using various criteria (budget, location, property type, status, date range) for matching clients with properties or bulk outreach. Improves efficiency at scale (50+ leads).

**Independent Test**: Agent enters search criteria (budget R$200k-400k, 3 bedrooms, Centro location, status "Qualified") → system returns only matching leads → agent saves filter as "High-value Centro leads" → reuses filter later.

### Test Strategy for User Story 4

- [ ] T131 [P] [US4] Run test strategy agent to analyze User Story 4 acceptance scenarios and determine test types (focus on search performance and filter accuracy)

### Unit Tests for User Story 4

- [ ] T132 [P] [US4] Generate unit test for search domain building using test executor agent in `18.0/extra-addons/quicksol_estate/tests/unit/test_lead_search.py` (complex filters, budget ranges, date filters)
- [ ] T133 [US4] Run unit test and verify it FAILS

### E2E API Tests for User Story 4

- [ ] T134 [P] [US4] Generate E2E test for advanced search using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_search_api.py` (multiple filters combined with AND logic)
- [ ] T135 [P] [US4] Generate E2E test for search performance using test executor agent in `18.0/extra-addons/quicksol_estate/tests/api/test_lead_search_performance_api.py` (50 leads, <3sec response)
- [ ] T136 [US4] Run E2E API tests and verify they FAIL

### Integration Tests for User Story 4

- [ ] T137 [P] [US4] Generate shell integration test for advanced search using SpecKit tests agent in `integration_tests/test_us6_s10_lead_search.sh` (multiple filters, verify results)
- [ ] T138 [US4] Run integration test and verify it FAILS

### Cypress E2E UI Tests for User Story 4

- [ ] T139 [P] [US4] Generate Cypress test for search and filter UI using SpecKit tests agent in `cypress/e2e/lead-search-filter.cy.js` (apply filters, verify results, save filter, reuse saved filter)
- [ ] T140 [US4] Run Cypress test and verify it FAILS

### Implementation for User Story 4

**API Enhancements for Advanced Search**

- [ ] T141 [US4] Update GET /api/v1/leads to accept additional query params: budget_min, budget_max, bedrooms, property_type_id, location, last_activity_before (date) in `18.0/extra-addons/quicksol_estate/controllers/lead_api.py`
- [ ] T142 [US4] Implement domain building logic in controller: combine filters with AND logic, handle optional params, respect agent/manager access rules
- [ ] T143 [US4] Add sorting support: sort_by (field name), sort_order (asc/desc), default to create_date desc
- [ ] T144 [US4] Add CSV export endpoint: GET /api/v1/leads/export with same filters, returns CSV file respecting security (FR-028 acceptance scenario 5)

**Database Optimization**

- [ ] T145 [P] [US4] Add database indexes to lead model in `18.0/extra-addons/quicksol_estate/models/real_estate_lead.py`: index on state, agent_id, create_date (FR-045)
- [ ] T146 [P] [US4] Add composite index on (company_ids, state, agent_id) for common filter combinations in model
- [ ] T147 [US4] Verify search_read() used in GET /api/v1/leads instead of search() + read() for performance (FR-044, FR-046)

**Saved Filters (Optional Enhancement)**

- [ ] T148 [US4] Create real.estate.lead.filter model in `18.0/extra-addons/quicksol_estate/models/real_estate_lead_filter.py` with fields: name, user_id, filter_domain (JSON)
- [ ] T149 [US4] Add POST /api/v1/leads/filters endpoint to save filter with name and criteria
- [ ] T150 [US4] Add GET /api/v1/leads/filters endpoint to list user's saved filters
- [ ] T151 [US4] Add DELETE /api/v1/leads/filters/{id} to remove saved filter

**Odoo Web Views Enhancements**

- [ ] T152 [US4] Add advanced search filters to list view in `18.0/extra-addons/quicksol_estate/views/real_estate_lead_views.xml`: budget range, bedrooms, location, property_type, date range (acceptance scenarios 1-3)
- [ ] T153 [US4] Add saved filter functionality to Odoo Web search view (use Odoo's built-in favorites feature)

**Integration & Testing**

- [ ] T154 [US4] Run all unit tests for US4 and verify they PASS (search domain building)
- [ ] T155 [US4] Run all E2E API tests for US4 and verify they PASS (advanced search, performance)
- [ ] T156 [US4] Run integration test for US4 and verify it PASSES (advanced search)
- [ ] T157 [US4] Run Cypress test for US4 and verify it PASSES (search UI)
- [ ] T158 [US4] Verify test coverage ≥80% for User Story 4
- [ ] T159 [US4] Test advanced search: Agent searches budget R$300k-500k AND 2-3 bedrooms → verify only matching leads returned
- [ ] T160 [US4] Test inactive leads filter: Manager filters by "Last activity >14 days ago" → verify results sorted by oldest activity first
- [ ] T161 [US4] Test saved filters: Agent creates filter "High-value Centro leads" → reuses later → verify same results
- [ ] T162 [US4] Test CSV export: Manager exports filtered leads → verify CSV contains correct fields and respects multi-tenancy (no other company data)
- [ ] T163 [US4] Test search performance: Generate 50 leads → apply filters → verify response time <3 seconds (FR-046)

**Checkpoint**: All 4 user stories should now be independently functional. Advanced search enables power users to efficiently manage large lead datasets.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

### Documentation

- [ ] T164 [P] Update OpenAPI spec at `docs/openapi/lead-management-api-spec.yaml` with final endpoint signatures (if changed during implementation)
- [ ] T165 [P] Update Postman collection at `docs/postman/lead-management-collection.json` with example requests/responses from real API
- [ ] T166 [P] Add lead management section to main README.md with feature overview and links to spec
- [ ] T167 [P] Update Copilot instructions at `.github/agents/copilot-instructions.md` with lead model patterns if needed

### Code Quality

- [ ] T168 Run linting on all new Python files: `cd 18.0 && ./lint.sh`
- [ ] T169 Fix any linting errors in model, controller, test files
- [ ] T170 Review code for triple decorator pattern consistency across all endpoints (constitution check)
- [ ] T171 Review record rules for multi-tenancy completeness (all rules include company_ids filter)

### Performance Validation

- [ ] T172 [P] Load test: Create 1000 leads in test database, measure GET /api/v1/leads response time (target <3sec per FR-046)
- [ ] T173 [P] Load test: Create 5000 leads, measure manager dashboard load time (target <3sec per FR-046)
- [ ] T174 Optimize queries if performance targets not met (add indexes, use read_group for aggregations)

### Security Audit

- [ ] T175 Verify all endpoints use triple decorator pattern: `@require_jwt`, `@require_session`, `@require_company` (constitution principle I)
- [ ] T176 Test cross-company data leakage: Company A user attempts to access Company B lead via direct ID → verify 403 or 404 response
- [ ] T177 Test agent cannot modify agent_id on own leads (FR-022)
- [ ] T178 Test soft delete cannot be bypassed (verify no direct SQL delete)

### Test Coverage Final Check

- [ ] T179 Run full test suite: unit + E2E API + E2E UI + integration tests
- [ ] T180 Generate coverage report: `cd 18.0/extra-addons/quicksol_estate && python -m pytest --cov=. --cov-report=html`
- [ ] T181 Review coverage report and verify ≥80% for all lead-related files (constitution principle II)
- [ ] T182 Add additional unit tests if coverage below 80% for any module

### Quickstart Validation

- [ ] T183 Follow quickstart.md step-by-step as new developer: setup, create lead, test API, run tests
- [ ] T184 Update quickstart.md with any missing steps or corrections discovered during validation
- [ ] T185 Verify all curl examples in quickstart.md work with real .env credentials

### Integration Verification

- [ ] T186 Test full lead lifecycle end-to-end: Agent creates lead → contacts client (logs activities) → qualifies → converts to sale → manager views report
- [ ] T187 Test multi-tenancy isolation end-to-end: Create leads for Company A and B → verify managers see only their company data
- [ ] T188 Test agent reassignment: Manager reassigns lead from Agent A to Agent B → verify Agent A loses access, Agent B gains access

### Final Acceptance

- [ ] T189 Verify all acceptance scenarios from spec.md pass for all 4 user stories
- [ ] T190 Verify all success criteria met: Agent creates lead <2min (FR-047), Manager dashboard <3sec (FR-046), conversion tracked in history, zero cross-company leakage
- [ ] T191 Verify User Story 1 is independently deployable as MVP (agents can create and manage leads without US2/3/4)
- [ ] T192 Update branch 006-lead-management status to "Ready for Merge"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3): Can start after Foundational - MVP priority
  - User Story 2 (Phase 4): Can start after Foundational - Manager features
  - User Story 3 (Phase 5): Can start after Foundational - Activity tracking
  - User Story 4 (Phase 6): Can start after Foundational - Advanced search
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - 100% independent
- **User Story 2 (P2)**: No dependencies on US1 but enhances manager experience - independent
- **User Story 3 (P2)**: Extends US1 model (mail.thread already in place) - mostly independent
- **User Story 4 (P3)**: Uses US1 model and endpoints - extends with search - independent

### Critical Path (MVP)

1. Setup (Phase 1): 7 tasks
2. Foundational (Phase 2): 7 tasks - BLOCKING
3. User Story 1 (Phase 3): 55 tasks - MVP complete at this point
4. Total for MVP: 69 tasks

### Parallel Opportunities

- **Setup phase**: T002-T006 can run in parallel (5 directory creations)
- **Foundational phase**: T008-T011 verifications can run in parallel (4 model checks)
- **User Story 1 tests**: T017-T022 unit tests can run in parallel (6 tests)
- **User Story 1 tests**: T024-T026 E2E API tests can run in parallel (3 tests)
- **User Story 1 tests**: T028-T031 integration tests can run in parallel (4 tests)
- **User Story 1 tests**: T033-T034 Cypress tests can run in parallel (2 tests)
- **User Story 1 views**: T057-T060 Odoo views can run in parallel (4 views)
- **All user stories after Foundational**: US1, US2, US3, US4 can run in parallel by different team members

### Parallel Example: User Story 1 Tests

```bash
# Launch all unit tests in parallel (6 tests):
T017: test_lead_duplicate_validation.py
T018: test_lead_budget_validation.py
T019: test_lead_lost_reason_validation.py
T020: test_lead_company_validation.py
T021: test_lead_state_transitions.py
T022: test_lead_soft_delete.py

# Launch all E2E API tests in parallel (3 tests):
T024: test_lead_crud_api.py
T025: test_lead_conversion_api.py
T026: test_lead_agent_isolation_api.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (7 tasks)
2. Complete Phase 2: Foundational (7 tasks) - CRITICAL
3. Complete Phase 3: User Story 1 (55 tasks)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready - agents can now manage leads

**Result**: Functional lead management system for agents in ~69 tasks. All core features work: create leads, track pipeline, convert to sales, agent isolation.

### Incremental Delivery

1. **Foundation**: Setup + Foundational → Development environment ready
2. **MVP**: Add User Story 1 → Test independently → Deploy/Demo (agents manage own leads)
3. **Manager Features**: Add User Story 2 → Test independently → Deploy/Demo (manager oversight + reassignment)
4. **Activity Tracking**: Add User Story 3 → Test independently → Deploy/Demo (full communication history)
5. **Power User Features**: Add User Story 4 → Test independently → Deploy/Demo (advanced search + filters)
6. **Production Ready**: Complete Phase 7 (Polish) → Final validation → Merge to main

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With 4 developers after Foundational phase completes:

- **Developer A**: User Story 1 (Agent CRUD + Conversion) - Priority 1
- **Developer B**: User Story 2 (Manager Oversight) - Priority 2
- **Developer C**: User Story 3 (Activity Tracking) - Priority 2
- **Developer D**: User Story 4 (Advanced Search) - Priority 3

Stories integrate independently. Team synchronizes on Phase 7 (Polish).

### Test-First Workflow (Per Constitution)

For each user story:

1. **Strategy**: Run test strategy agent to identify test types
2. **Write Tests**: Generate tests using test executor agent (unit + E2E + integration + Cypress)
3. **Verify Failure**: Run tests and confirm they FAIL (no implementation yet)
4. **Implement**: Write model + controller + views to make tests PASS
5. **Validate**: Run full test suite and verify ≥80% coverage
6. **Checkpoint**: Story is complete and independently testable

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **Test agents**: All test tasks use constitution-required test agents (Strategy, Executor, SpecKit)
- **Independent stories**: Each user story is independently completable and testable
- **MVP = US1**: User Story 1 alone delivers core value (agent lead management)
- **Commit strategy**: Commit after each task or logical group for easy rollback
- **Checkpoints**: Stop at story completion to validate independently before proceeding
- **Constitution compliance**: 80% test coverage mandatory, triple decorator pattern enforced, multi-tenancy validated

---

**Total Tasks**: 193  
**MVP Tasks** (Setup + Foundational + US1): 70  
**Estimated MVP Duration**: 3-4 weeks (single developer) or 1-2 weeks (team of 3)

**Next Step**: Start with Phase 1 (Setup) or run `/speckit.implement` to begin code generation.
