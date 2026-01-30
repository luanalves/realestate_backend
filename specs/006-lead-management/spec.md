# Feature Specification: Real Estate Lead Management System

**Feature Branch**: `006-lead-management`  
**Created**: 2026-01-29  
**Status**: Draft  
**Input**: User description: "Implementar sistema de gerenciamento de leads imobiliários (real.estate.lead) para rastreamento de clientes potenciais. Agents devem poder criar leads com informações de contato, preferências de imóvel (tipo, localização, orçamento, quartos), e acompanhar o pipeline de vendas através de estados (Novo, Contatado, Qualificado, Convertido, Perdido). Managers devem visualizar todos os leads da company, enquanto Agents veem apenas seus próprios leads (isolamento por agent_id). Cada lead deve rastrear: nome do cliente, telefone, email, orçamento min/max, tipo de imóvel desejado, localização preferida, número de quartos, data do primeiro contato, data prevista de fechamento, e histórico de atividades (integração com mail.thread). Quando um lead é convertido em venda, deve criar vínculo com real.estate.property. Sistema deve respeitar multi-tenancy (filtro por estate_company_ids em todos os record rules) e integrar com RBAC existente (branch 005-rbac-user-profiles). Success criteria: Agent cria lead em menos de 2 minutos, Manager visualiza dashboard com todos leads da company em menos de 3 segundos, conversão de lead para property rastreia origem no histórico, zero vazamento de dados entre companies. Este sistema resolve o teste US3-S3 que está SKIP (test_us3_s3_agent_own_leads.sh). Modelo custom sem dependência do módulo CRM do Odoo."

## Clarifications

### Session 2026-01-29

- Q: Lead Duplicate Detection Strategy → A: Per-agent duplicate prevention. Same agent cannot create duplicate lead for same client (phone/email match), but different agents can have leads for same client/property.
- Q: Lost Lead Reactivation Trigger → A: Both agents and managers can reopen their accessible leads freely
- Q: Property Match Strategy for Lead Conversion → A: Manual search and selection. Agent searches property catalog and selects property manually during conversion (no automatic suggestion system)
- Q: Success Criteria Metrics Definition → A: Agent productivity (<2min create) + data isolation (0% cross-company leakage) + dashboard performance (<3sec)
- Q: Activity History Retention Policy → A: Soft delete only (archive flag), activities preserved indefinitely for reporting and audit trails

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent Creates and Manages Own Leads (Priority: P1) 🎯 MVP

An Agent receives an inquiry from a potential client and needs to register it as a lead in the system to track the sales pipeline. The agent enters the client's contact information, property preferences (budget, location, type, bedrooms), and follows up through different pipeline stages until the lead is either converted to a sale or marked as lost.

**Why this priority**: Core functionality enabling agents to capture and manage their sales pipeline. Without this, agents cannot track potential clients systematically. This is the minimum viable feature that delivers immediate value.

**Independent Test**: Agent logs in, creates a new lead with client info and preferences, updates lead status through pipeline stages, and converts lead to property sale. Agent can only see their own leads, not other agents' leads.

**Acceptance Scenarios**:

1. **Given** Agent is logged in, **When** Agent clicks "New Lead" and fills contact info (name, phone, email) and preferences (budget R$200k-300k, 2 bedrooms, Centro location), **Then** system creates lead with status "New" and assigns agent_id automatically
2. **Given** Agent has 5 leads in pipeline, **When** Agent views "My Leads" dashboard, **Then** system shows only those 5 leads assigned to this agent, not other agents' leads
3. **Given** Lead is in "Contacted" state, **When** Agent updates status to "Qualified", **Then** system records status change with timestamp in activity history
4. **Given** Lead is "Qualified" and property match found, **When** Agent clicks "Convert to Sale" and selects property, **Then** system creates sale record and populates lead's converted_property_id and converted_sale_id fields
5. **Given** Lead cannot be closed, **When** Agent marks as "Lost" and adds reason "Budget constraints", **Then** system updates state and records lost_reason in history

---

### User Story 2 - Manager Oversees All Company Leads (Priority: P2)

A Manager needs visibility into all leads across all agents in their company to monitor team performance, identify bottlenecks in the pipeline, reassign leads when needed, and forecast potential sales. Manager can view all company leads but respects multi-tenancy (cannot see other companies' leads).

**Why this priority**: Enables operational oversight and team coordination. Essential for managing sales teams but not blocking for individual agent productivity.

**Independent Test**: Manager logs in, views dashboard showing all leads from all agents in their company (Company A), filters by status/agent, and verifies zero visibility into Company B leads.

**Acceptance Scenarios**:

1. **Given** Manager is logged in to Company A with 3 agents having 15 total leads, **When** Manager opens "All Leads" dashboard, **Then** system displays all 15 leads with agent names, statuses, and last activity dates
2. **Given** Manager views pipeline kanban board, **When** Manager filters by status "Qualified", **Then** system shows only qualified leads across all agents
3. **Given** Manager identifies stalled lead (30 days in "Contacted" without update), **When** Manager reassigns lead from Agent A to Agent B, **Then** system updates agent_id and notifies both agents
4. **Given** Manager is from Company A, **When** Manager attempts to view leads, **Then** system shows zero leads from Company B (multi-tenancy isolation)
5. **Given** Manager analyzes conversion rates, **When** Manager generates report for last quarter, **Then** system shows leads created vs converted by agent and status distribution

---

### User Story 3 - Lead Lifecycle Tracking with Activities (Priority: P2)

Agents and Managers need to track all interactions with leads (calls, emails, meetings) to maintain context across the sales cycle. The system should integrate with Odoo's activity/mail system to provide a unified communication history.

**Why this priority**: Improves sales effectiveness by maintaining context. Important for professional operations but system works without it initially.

**Independent Test**: Agent creates lead, logs multiple activities (call, email, meeting scheduled), and verifies all activities appear in chronological order in lead's activity timeline.

**Acceptance Scenarios**:

1. **Given** Lead exists in "New" state, **When** Agent logs "Called client - interested in condos", **Then** system creates activity record linked to lead with timestamp and agent name
2. **Given** Lead has 3 activities logged, **When** Agent opens lead detail view, **Then** system displays activities in reverse chronological order with icons (phone, email, meeting)
3. **Given** Agent schedules follow-up meeting, **When** Agent sets reminder for 2 days from now, **Then** system creates calendar activity and sends notification when due
4. **Given** Manager views lead assigned to Agent, **When** Manager checks activity history, **Then** system shows all activities including who performed each action
5. **Given** Lead is converted to sale, **When** viewing property deal, **Then** system shows link to original lead with full activity history preserved

---

### User Story 4 - Lead Search and Filtering (Priority: P3)

Agents and Managers need to quickly find leads based on various criteria (budget range, location, property type, status, date range) to match clients with available properties or identify similar leads for bulk outreach.

**Why this priority**: Efficiency improvement for power users. System is functional without advanced search but becomes cumbersome at scale.

**Independent Test**: Agent enters search criteria (budget R$200k-400k, 3 bedrooms, Centro location, status "Qualified"), system returns matching leads only.

**Acceptance Scenarios**:

1. **Given** Agent has 50 leads, **When** Agent searches for leads with budget R$300k-500k AND 2-3 bedrooms, **Then** system returns only leads matching both criteria
2. **Given** Manager needs to contact all leads inactive >14 days, **When** Manager filters by "Last activity >14 days ago", **Then** system lists leads sorted by oldest activity first
3. **Given** Agent wants leads for specific location, **When** Agent filters by "Property type: Apartamento" AND "Location: Jardins", **Then** system shows relevant leads
4. **Given** Multiple search filters applied, **When** Agent saves filter as "High-value Centro leads", **Then** system saves filter for quick reuse
5. **Given** Manager exports filtered lead list, **When** Manager clicks "Export to CSV", **Then** system generates file with selected fields respecting security (no other company data)

---

### Edge Cases

- **Empty pipeline**: What happens when agent has zero leads? → Show empty state with "Create Your First Lead" prompt
- **Lead without preferences**: What if client is undecided on property type/location? → Allow optional fields, show as "To be determined" in filters
- **Duplicate lead detection**: What if same client contacted multiple agents? → Allowed - different agents can have leads for same client. System prevents only same agent creating duplicate lead for same client (phone/email match within agent's own leads)
- **Agent duplicate prevention**: What if agent tries to create second lead for same client? → System blocks creation, shows existing lead, offers to edit or add new activity instead
- **Lead conversion failure**: What if agent converts lead but property deal creation fails? → Transaction rollback, lead stays in "Qualified" state with error message
- **Multi-company user**: What if user belongs to 2 companies? → Show combined leads from both companies with company indicator badge
- **Lead without agent**: What happens to leads created by managers directly? → Require agent selection during creation, validate agent belongs to same companies
- **Status regression**: Can lead go back from "Qualified" to "Contacted"? → Allow status changes in any direction, log reason for backward movement
- **Lost lead reactivation**: Can lost lead be reopened? → Yes, both agents (for own leads) and managers (for company leads) can reopen. "Reopen Lead" action changes state from "Lost" to "Contacted" with activity note explaining reactivation reason
- **Lead deletion**: What happens to deleted leads? → Soft delete only (active=False flag). Archived leads hidden from normal views but preserved in database with full activity history for reporting and compliance. No hard delete allowed
- **Performance with 10k+ leads**: How to handle large datasets? → Implement pagination (50 per page), indexed searches on agent_id/company_ids/state
- **Concurrent edits**: Two agents update same lead simultaneously? → Last write wins with conflict notification, show "Lead modified by X at Y" warning

## Requirements *(mandatory)*

### Functional Requirements

#### Core Lead Management

- **FR-001**: System MUST provide a `real.estate.lead` model with fields: name (Char, required), partner_id (Many2one res.partner), agent_id (Many2one real.estate.agent, required), company_ids (Many2many thedevkitchen.estate.company), phone (Char), email (Char), state (Selection: new/contacted/qualified/won/lost, required, default='new')
- **FR-002**: System MUST auto-assign agent_id when agent creates lead (based on current user's linked agent record)
- **FR-003**: System MUST inherit from mail.thread and mail.activity.mixin for activity tracking integration
- **FR-004**: System MUST track lead creation date (create_date), first contact date (first_contact_date), and expected closing date (expected_closing_date)
- **FR-005**: System MUST allow lead state transitions in any direction (New ↔ Contacted ↔ Qualified ↔ Won/Lost) with reason logging
- **FR-005a**: System MUST prevent agent from creating duplicate lead for same client (duplicate = same agent_id AND matching phone OR email on non-lost leads). Validation MUST show existing lead and offer to edit or add activity instead
- **FR-005b**: System MUST allow different agents to create leads for same client (cross-agent duplicates are permitted)

#### Property Preferences & Budget

- **FR-006**: System MUST track client budget as budget_min and budget_max (Float, currency BRL)
- **FR-007**: System MUST track property preferences: property_type_interest (Many2one real.estate.property.type), location_preference (Char), bedrooms_needed (Integer), min_area (Float), max_area (Float)
- **FR-008**: System MUST allow partial preferences (all preference fields including budget are optional - leads can be created with minimal info and preferences added later)
- **FR-009**: System MUST link lead to specific property of interest via property_interest field (Many2one real.estate.property, optional)

#### Lead Conversion

- **FR-010**: System MUST provide "Convert to Sale" action that creates real.estate.sale record linked to selected property. Agent MUST manually search and select property from catalog (no automatic property matching)
- **FR-011**: System MUST populate converted_property_id (selected property) and converted_sale_id (created sale record) fields when lead is converted, preserving lead record for history
- **FR-012**: System MUST change lead state to "Won" automatically when conversion succeeds
- **FR-013**: System MUST copy lead contact info (partner_id, phone, email) to sale record during conversion
- **FR-014**: Conversion MUST be atomic transaction (either both lead update and sale creation succeed, or both fail)
- **FR-014a**: System MUST validate selected property exists and agent has access to it before allowing conversion

#### Activity & History Tracking

- **FR-015**: System MUST log all lead field changes in mail.thread history with timestamps and user names
- **FR-016**: System MUST allow agents to log activities (calls, emails, meetings) via mail.activity.mixin
- **FR-017**: System MUST track lost leads with lost_reason field (Text) and lost_date (Date)
- **FR-018**: Activity history MUST be preserved when lead is converted (historical record)
- **FR-018a**: System MUST allow agents to reopen their own lost leads and managers to reopen any company lost leads. Reopen action MUST change state from "Lost" to "Contacted" and log reactivation with reason in activity history
- **FR-018b**: System MUST implement soft delete only (active field). Deleted leads MUST be archived (active=False) and hidden from normal views while preserving all data and activity history indefinitely for reporting, compliance, and potential restoration

#### Agent Access & Permissions

- **FR-019**: Agents MUST see only leads where agent_id matches their linked agent record (record rule)
- **FR-020**: Agents MUST have CRUD permissions on their own leads (create, read, update, archive). Delete operations MUST be soft delete only (active=False)
- **FR-021**: Agents MUST NOT be able to view or modify other agents' leads (enforced by record rules)
- **FR-022**: Agents MUST NOT be able to change agent_id field on existing leads (prevents ownership transfer)
- **FR-023**: System MUST validate agent_id belongs to same companies as lead's company_ids

#### Manager Oversight

- **FR-024**: Managers MUST see all leads from all agents in their assigned companies (record rule with company_ids filter)
- **FR-025**: Managers MUST have full CRUD permissions on all company leads regardless of agent_id
- **FR-026**: Managers MUST be able to reassign leads between agents (modify agent_id field)
- **FR-027**: System MUST log agent reassignments in activity history with previous and new agent names
- **FR-028**: Managers MUST be able to generate reports filtering by agent, status, date range, and budget

#### Multi-Tenancy & Security

- **FR-029**: All record rules MUST include company_ids filter: `[('company_ids', 'in', user.estate_company_ids.ids)]`
- **FR-030**: System MUST prevent users from viewing leads from companies they're not assigned to (zero data leakage)
- **FR-031**: System MUST validate company_ids on lead creation matches user's estate_company_ids
- **FR-032**: Multi-company users MUST see combined leads from all their assigned companies
- **FR-033**: System MUST scope all searches, filters, and reports to user's assigned companies automatically

#### UI & UX

- **FR-034**: System MUST provide list view with columns: name, partner_id, agent_id, state, budget_min, budget_max, phone, email, create_date
- **FR-035**: System MUST provide form view with tabs: General Info, Property Preferences, Activities, Conversion
- **FR-036**: System MUST provide kanban view grouped by state with drag-and-drop status updates
- **FR-037**: System MUST provide calendar view showing expected_closing_date for pipeline forecasting
- **FR-038**: System MUST show lead counts by status in dashboard (pie chart: New, Contacted, Qualified, Won, Lost)

#### Integration & Dependencies

- **FR-039**: System MUST integrate with existing RBAC system from branch 005-rbac-user-profiles (reuse Agent and Manager profiles)
- **FR-040**: System MUST link to real.estate.property model for property_interest and conversion
- **FR-041**: System MUST link to real.estate.agent model for agent_id assignment
- **FR-042**: System MUST use res.partner for partner_id (client contact)
- **FR-043**: System MUST NOT depend on Odoo CRM module (custom implementation)

#### Performance & Scalability

- **FR-044**: System MUST support pagination in list views (50 records per page default)
- **FR-045**: System MUST index agent_id, company_ids, and state fields for fast filtering
- **FR-046**: Dashboard load time MUST be under 3 seconds for datasets up to 5000 leads per company
- **FR-047**: Lead creation form MUST load in under 2 seconds

### Key Entities

- **Lead (real.estate.lead)**: Represents a potential client/sale opportunity. Contains client contact info, property preferences, budget range, pipeline status, and activity history. Linked to agent (owner), companies (multi-tenancy), and optionally to property of interest and converted sale record.

- **Agent (real.estate.agent)**: Represents sales agent who owns and manages leads. Already exists from RBAC implementation. Used in agent_id field for lead ownership and filtering.

- **Company (thedevkitchen.estate.company)**: Represents real estate agency in multi-tenancy system. Leads belong to one or more companies via company_ids. Used for data isolation between agencies.

- **Property (real.estate.property)**: Represents real estate listing. Leads can reference a specific property of interest. When lead converts, creates link to property via sale record.

- **Sale (real.estate.sale)**: Represents closed deal. Created when lead is successfully converted. Contains lead_id field referencing original lead. Lead model stores inverse references via converted_property_id (which property) and converted_sale_id (which sale record).

- **Partner (res.partner)**: Represents client contact. Stores name, phone, email. Linked via partner_id for unified contact management.

- **Activity (mail.activity)**: Represents scheduled task or logged interaction. Inherited via mail.activity.mixin. Tracks calls, emails, meetings with due dates and reminders.
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agent can create a new lead with complete information (contact + preferences) in under 2 minutes from clicking "New Lead" to saving the record
- **SC-002**: Manager can view dashboard showing all company leads (up to 5000 records) in under 3 seconds from menu click to full page render
- **SC-003**: Zero data leakage between companies - agents and managers from Company A cannot view, edit, or access any leads from Company B under any circumstances (validated by security audit)
- **SC-004**: Lead conversion to property sale successfully tracks origin - 100% of converted leads have populated converted_property_id field and activity history showing conversion timestamp, agent, and selected property
