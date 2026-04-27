# Feature Specification: Property Proposals Management

**Feature Branch**: `013-property-proposals`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "Property Proposals Management — based on spec-idea.md at specs/012-property-proposals/spec-idea.md"
**Source Idea**: [specs/012-property-proposals/spec-idea.md](../012-property-proposals/spec-idea.md)

## Clarifications

### Session 2026-04-27

- Q: For lead de-duplication (FR-030/FR-031), which lead states count as "active" (so a new proposal is linked instead of creating a new lead)? → A: Active = `new`, `contacted`, `qualified`, `won` (the existing `real.estate.lead.state` non-closed values). The state `lost` and soft-deleted leads (`active=false`) do NOT count — a new lead with source `proposal` is created in those cases.
- Q: How should the system behave when the email subsystem fails during a critical state transition (e.g., acceptance) per FR-014/FR-015/FR-041? → A: State transition always succeeds; notifications are enqueued asynchronously with retry (Outbox pattern); email failures are logged in the proposal activity timeline without blocking the transition.
- Q: What are the bounds for a client-supplied `valid_until` on a proposal? → A: Must be strictly greater than today and at most 90 days from creation. Default remains 7 days from send date when omitted.
- Q: What happens to existing proposals when their underlying property is archived/withdrawn from the market? → A: All non-terminal proposals (Draft, Queued, Sent, Negotiation) on that property are auto-cancelled with reason "Property withdrawn from market" and the responsible agents are notified. Terminal proposals (Accepted, Rejected, Expired, Cancelled) are untouched.
- Q: What is the data-retention / PII anonymization policy for terminal proposals (LGPD)? → A: Out of scope for this feature. To be defined and applied uniformly by a future global data-retention policy feature; this feature retains all proposal data indefinitely until that policy is in place.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent registers and sends a proposal (Priority: P1) 🎯 MVP

An agent receives interest from a client about a property under their portfolio and needs to formally register a proposal containing client identification, the chosen property, the offered amount, and optional notes. After registering, the agent reviews the draft and sends it to the client, which records the official offer date and notifies all parties.

**Why this priority**: Core capability — without this, no proposal can exist. Delivers immediate value as a standalone slice (agent can register an offer and have it tracked even without negotiation/acceptance flow).

**Independent Test**: Can be fully tested by registering a new proposal for an unoccupied property, sending it, and verifying that the system records the proposal with a unique identifier, links it to client/property/agent, and produces a notification event.

**Acceptance Scenarios**:

1. **Given** a property the agent is responsible for and no other active proposal exists, **When** the agent submits the proposal data (client name, document, contact, property, value, notes), **Then** the proposal is created in *Draft* state with an automatically generated unique code (e.g., `PRP001`).
2. **Given** the client identifier (document) already exists in the system, **When** a new proposal is created for that client, **Then** the existing client record is reused and no duplicate is created.
3. **Given** a proposal in *Draft* state, **When** the agent sends it to the client, **Then** the proposal moves to *Sent* state, the send date is recorded, the client is notified by email, and the activity timeline registers the event.
4. **Given** a proposal value of zero or below, **When** creation is attempted, **Then** the system rejects it with a validation error.
5. **Given** an agent attempting to create a proposal for a property they are not assigned to, **When** the request is made, **Then** the system denies the operation.

---

### User Story 2 - Multiple proposals on the same property with FIFO queue (Priority: P1)

When a property already has an active proposal, additional proposals from other agents (or the same agent for a different client) are not blocked — they enter a queue. The first proposal stays the official one; subsequent proposals wait. If the active proposal ends without acceptance (rejected, expired, or cancelled), the next in line is automatically promoted and its agent is notified.

**Why this priority**: Critical business rule explicitly defined by the user — ensures fairness ("first to arrive") and avoids losing client interest when a property is under negotiation. Without it, agents would either lose opportunities or create conflicting offers.

**Independent Test**: Create one proposal on a property (becomes active), then create a second one (becomes queued at position 1), then reject the active one and verify the queued proposal is promoted automatically with notification.

**Acceptance Scenarios**:

1. **Given** a property has an active proposal (in any non-terminal state), **When** another proposal is created for the same property, **Then** the new proposal is placed in *Queued* state with its queue position recorded.
2. **Given** a queued proposal, **When** anyone tries to send it directly, **Then** the system blocks the action and explains the proposal must first be promoted.
3. **Given** the active proposal terminates as rejected, expired, or cancelled (i.e., not accepted), **When** the system processes that transition, **Then** the next queued proposal (oldest first) is automatically promoted to *Draft*, queue positions for remaining ones are recalculated, and the responsible agent is notified by email and timeline entry.
4. **Given** two agents simultaneously try to create a proposal for the same currently-empty property, **When** both submit at the same instant, **Then** the system guarantees exactly one becomes the active proposal (Draft) and the other is automatically queued — never two actives.
5. **Given** a queued proposal, **When** the agent edits the value, validity, or notes, **Then** the edits are accepted while the proposal remains queued.

---

### User Story 3 - Negotiation through counter-proposals (Priority: P1)

When a client requests changes to a sent proposal, the agent registers a counter-proposal preserving full history. The original moves into a *Negotiation* state and a new linked proposal is created with the revised terms. Any number of counter-proposals can chain over time, and the full negotiation history is visible.

**Why this priority**: Real estate negotiations are iterative; without versioned counter-proposals, history is lost and audit/reporting becomes impossible.

**Independent Test**: Send a proposal, then create a counter-proposal with new value. Verify original goes to *Negotiation*, new one is created linked to the parent, and querying the proposal returns the full chain.

**Acceptance Scenarios**:

1. **Given** a proposal in *Sent* state, **When** a counter-proposal is created with new value/notes, **Then** the original moves to *Negotiation*, a new proposal is created with a parent link, inheriting client/property/agent.
2. **Given** several chained counter-proposals on the same property, **When** any one of them is consulted, **Then** the response includes the complete chain ordered chronologically.
3. **Given** a counter-proposal is the new active negotiation, **When** the system evaluates the property's slot, **Then** the counter-proposal occupies the active slot (it does not enter the queue).

---

### User Story 4 - Accept or reject a proposal (Priority: P1)

The agent or manager finalizes a proposal by marking it as accepted or rejected. Acceptance freezes the proposal, records the date, automatically cancels all competing proposals on the same property (queued or otherwise active), and offers the next step toward formalizing a contract. Rejection requires a reason and frees the property's active slot for the next queued proposal.

**Why this priority**: Closing decisions are the core business outcome. Without acceptance/rejection workflow, the pipeline cannot conclude.

**Independent Test**: Accept a proposal that has 3 queued competitors → verify the 3 are auto-cancelled with a "superseded by..." reason and the original agents are notified. Reject another proposal with reason → verify the next queued one is auto-promoted.

**Acceptance Scenarios**:

1. **Given** a proposal in *Sent* or *Negotiation*, **When** it is accepted, **Then** state moves to *Accepted*, accepted date is recorded, and the response indicates a "create contract" follow-up action is now available (without auto-creating any contract).
2. **Given** an accepted proposal with competing proposals on the same property (queued, draft, sent, or negotiation), **When** acceptance is processed, **Then** all competitors are automatically cancelled with cancellation reason "Superseded by accepted proposal *PRPxxx*", a link back to the winner is preserved on each, and each respective agent receives email + timeline notification.
3. **Given** a rejection request, **When** the rejection reason is missing or empty, **Then** the system rejects the request and requires a reason.
4. **Given** a proposal is rejected, **When** there are queued proposals on the same property, **Then** the next in line is automatically promoted to *Draft* with notification.
5. **Given** a proposal in a terminal state (Accepted, Rejected, Expired, Cancelled), **When** any update is attempted, **Then** the system blocks the change.

---

### User Story 5 - Capture lead from proposal contact (Priority: P2)

When a proposal is created for a client whose contact data does not yet exist as a sales lead, the system creates a corresponding lead with origin "proposal" so the marketing/sales pipeline gains visibility into opportunities arriving directly through proposals. If the contact is already a lead, the proposal is linked to that lead instead of duplicating it.

**Why this priority**: Connects proposal management with the lead pipeline, providing 360° view of customer journeys without manual data entry. Not blocking for proposal creation itself, hence P2.

**Independent Test**: Create a proposal for a brand-new contact (never seen before). Verify a new lead exists with source = "proposal" linked to the proposal. Then create a second proposal for the same contact (now an existing lead) and verify the proposal is linked to that same lead — no duplicate.

**Acceptance Scenarios**:

1. **Given** a proposal is being created for a contact whose document is not registered as an active lead, **When** the proposal is saved, **Then** a new lead is created with source = "proposal" and linked to the proposal.
2. **Given** the contact already exists as an active lead, **When** the proposal is saved, **Then** the proposal is linked to the existing lead and no new lead is created.
3. **Given** the lead source list, **When** users browse it, **Then** "proposal" is one of the available sources.

---

### User Story 6 - Listing, filtering, and metrics (Priority: P1)

Managers and owners need a consolidated view of all proposals in their organization with filters by status, agent, property, client, date range, and free-text search. Aggregated counts per status feed the dashboard cards (Total, Draft, Active, Accepted, Rejected, etc.). Agents see only their own proposals; receptionists have read-only access.

**Why this priority**: Without listing and metrics, managers cannot oversee the pipeline. The dashboard cards visible in the design mockups depend on this.

**Independent Test**: As manager, list all proposals filtered by negotiation state. As agent, list and confirm only own proposals appear. Request the metrics endpoint and verify counts match each filter.

**Acceptance Scenarios**:

1. **Given** several proposals across statuses, **When** a manager lists with state, agent, property, date range, and search filters, **Then** results are paginated (max 100 per page) and isolated to the manager's organization.
2. **Given** an agent is logged in, **When** the agent requests the proposal list without filters, **Then** only proposals owned by that agent are returned.
3. **Given** a receptionist is logged in, **When** they list proposals, **Then** they see all organization proposals as read-only (no mutation actions offered).
4. **Given** the metrics endpoint, **When** queried, **Then** it returns total and per-status counts (draft, queued, sent, negotiation, accepted, rejected, expired, cancelled) for the user's organization.
5. **Given** a request to inspect a property's queue, **When** the queue endpoint is called, **Then** the system returns the active proposal and the ordered queue with positions and agents.

---

### User Story 7 - Document attachments (Priority: P2)

Agents upload supporting documents (PDF proposals, ID copies, financing letters) to a proposal so it becomes complete and auditable. The documents are listed alongside the proposal and can be downloaded by authorized users.

**Why this priority**: Improves auditability and professionalism, but proposal flow can function without it for the MVP.

**Independent Test**: Attach 2 PDFs to a proposal, retrieve the proposal and confirm document count and metadata are returned. Try uploading an unauthorized type or a 15 MB file → verify rejection.

**Acceptance Scenarios**:

1. **Given** a proposal, **When** an authorized user uploads a document of allowed type and size, **Then** the document is stored, linked to the proposal, and the document count is incremented.
2. **Given** a file larger than 10 MB or of disallowed type, **When** upload is attempted, **Then** the system rejects it with a clear error.
3. **Given** a proposal with attached documents, **When** the proposal detail is consulted, **Then** documents appear with name, type, size, and download link.

---

### User Story 8 - Automatic expiration (Priority: P3)

Proposals have a validity date. After it passes without resolution, the system automatically moves them to *Expired*, freeing the property's active slot so the next queued proposal is promoted. By default, when a proposal is sent, it gets a 7-day validity if none was specified.

**Why this priority**: Hygiene/automation feature — pipeline accuracy improves but core flow works without it.

**Independent Test**: Create a proposal with validity date in the past, run the daily expiration job, confirm the proposal is *Expired* and any queued one is now active.

**Acceptance Scenarios**:

1. **Given** a proposal in *Sent* or *Negotiation* whose validity date has passed, **When** the daily expiration routine runs, **Then** the proposal moves to *Expired* and timeline records the event.
2. **Given** a proposal is sent without an explicit validity date, **When** sent, **Then** the system defaults validity to 7 days from the send date.
3. **Given** an expired proposal frees a property slot, **When** there is a queued proposal, **Then** the next queued one is automatically promoted.
4. **Given** an expired proposal, **When** consulted, **Then** the response offers a "renew" follow-up action that creates a new draft (subject to slot availability).

---

### Edge Cases

- **Concurrent creation race**: two agents create proposals for the same currently-empty property at the exact same instant — the system MUST guarantee exactly one becomes active and the other is queued; no two actives can coexist.
- **Counter-proposal during negotiation**: a counter-proposal does NOT enter the queue — it directly succeeds the parent in the active slot.
- **Acceptance with no queue**: accepting a proposal when no other proposals exist behaves identically (no extra cancellations).
- **Editing a proposal in terminal state**: any edit attempt MUST be blocked.
- **Cross-organization access**: a user from organization A requesting a proposal from organization B MUST receive a "not found" response (no information leakage).
- **Agent reassignment of property**: if an agent is unassigned from a property, their existing proposals on that property remain valid until terminal state (no cascading cancellation).
- **Empty rejection reason**: rejection without reason MUST be blocked.
- **Soft-deleted (cancelled) proposal**: cancelled proposals do NOT count for the property's active slot.
- **Lead with same document but inactive (lost / archived / cancelled / soft-deleted)**: treat as non-existent — create a new lead with source "proposal" (per FR-030).
- **Acceptance does NOT promote queue**: when a proposal is accepted, the property remains "occupied" by the accepted proposal (queue is auto-cancelled, not promoted).
- **Multiple competing proposals when property is sold elsewhere outside the system**: when the property is archived/withdrawn (active=false), all non-terminal proposals on it are auto-cancelled with reason "Property withdrawn from market" (per FR-046a). Terminal proposals remain untouched.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Lifecycle

- **FR-001**: System MUST allow authorized users (Owner, Manager, Agent for own properties) to register a property proposal containing client identification (name + document), property reference, agent in charge, proposal type (sale or lease), monetary value, optional validity date, and optional description.
- **FR-002**: System MUST automatically generate a unique, human-readable proposal code per organization (e.g., `PRP001`) at creation time.
- **FR-003**: System MUST reject proposals with non-positive monetary value.
- **FR-004**: System MUST require the proposal type to be either "sale" or "lease".
- **FR-005**: System MUST persist proposals with full audit trail (creator, last modifier, creation date, last modification date) and a timeline of state changes.
- **FR-006**: System MUST support eight workflow states: Draft, Queued, Sent, Negotiation, Accepted, Rejected, Expired, Cancelled — and enforce valid transitions only.
- **FR-007**: System MUST treat Accepted, Rejected, Expired, and Cancelled as terminal states (no further updates allowed).

#### Active Slot & FIFO Queue (key business rule)

- **FR-008**: System MUST allow at most one *active* proposal (state in Draft, Sent, Negotiation, Accepted) per property at any given time.
- **FR-009**: System MUST automatically place additional proposals on the same property into Queued state, ordered by creation timestamp (FIFO).
- **FR-010**: System MUST compute and expose, for every proposal, its queue position (0 if active, ≥1 if queued, undefined if terminal) and a flag indicating whether it is the currently active proposal.
- **FR-011**: System MUST automatically promote the oldest queued proposal to Draft when the active proposal of a property terminates as Rejected, Expired, or Cancelled.
- **FR-012**: System MUST notify the agent of the promoted proposal by email and timeline entry.
- **FR-013**: System MUST recalculate queue positions for remaining queued proposals after each promotion or cancellation.
- **FR-014**: System MUST automatically cancel all other non-terminal proposals (Queued, Draft, Sent, Negotiation) on the same property when one is Accepted, recording cancellation reason "Superseded by accepted proposal *PRPxxx*" and a back-reference to the winning proposal.
- **FR-015**: System MUST notify each affected agent of automatic cancellation by email and timeline entry.
- **FR-016**: System MUST guarantee correctness under concurrent creation attempts: even if two requests arrive simultaneously for the same currently-empty property, exactly one becomes Draft and the other becomes Queued.
- **FR-017**: System MUST block sending a proposal that is currently Queued; the user MUST be informed it can only be sent after promotion.

#### Negotiation

- **FR-018**: System MUST support counter-proposals: creating one MUST move the parent to Negotiation, link the new proposal to its parent, and have the new proposal occupy the property's active slot (NOT enter the queue).
- **FR-019**: System MUST expose, for any proposal, the complete chain of related proposals (parent + descendants) in chronological order.
- **FR-020**: System MUST require a rejection reason when transitioning to Rejected.
- **FR-021**: System MUST require a cancellation reason when transitioning to Cancelled (whether manual or automatic).

#### State Transitions

- **FR-022**: System MUST allow transitioning Draft → Sent (registering the send date).
- **FR-023**: System MUST allow transitioning Sent or Negotiation → Accepted, Rejected, Expired, or Cancelled.
- **FR-024**: System MUST allow Queued → Draft (auto-promotion only) and Queued → Cancelled (manual or auto-supersede).
- **FR-025**: System MUST default the validity date to 7 days after the send date when a proposal is sent without an explicit validity.
- **FR-025a**: System MUST validate any client-supplied `valid_until` to be strictly greater than today (`> today`) and at most 90 days from the proposal's creation date (`<= create_date + 90 days`). Requests violating these bounds MUST be rejected with a clear validation error.
- **FR-026**: System MUST run a daily routine that moves Sent or Negotiation proposals whose validity date has passed to Expired.

#### Acceptance Outcomes

- **FR-027**: System MUST NOT automatically create any contract or downstream artifact when a proposal is accepted; instead, it MUST present a "create contract" follow-up action so the user can decide.
- **FR-028**: System MUST emit a domain event signalling acceptance so other capabilities (notifications, contract generation, observers) can react.

#### Lead Integration

- **FR-029**: System MUST add "proposal" as a valid value in the lead source list.
- **FR-030**: System MUST automatically create a lead with source "proposal" when the contact (identified by document) is not already linked to a lead in an *active* state, and link it to the new proposal. *Active* lead states are: `new`, `contacted`, `qualified`, `won` (existing values of `real.estate.lead.state`). Leads in state `lost` or soft-deleted (`active=false`) do NOT count and trigger creation of a new lead.
- **FR-031**: System MUST link the new proposal to an existing lead (without duplicating) only when that lead is in an *active* state as defined in FR-030.

#### Client Records

- **FR-032**: System MUST reuse an existing client record when the document already exists in the system; otherwise it MUST create one.
- **FR-033**: System MUST validate that the document is a valid CPF or CNPJ.

#### Listing, Filtering & Metrics

- **FR-034**: System MUST provide a paginated listing of proposals (default and maximum page size 100) filterable by state, agent, property, client, date range, and free-text search across proposal code / client name / property name.
- **FR-035**: System MUST scope listing for agents to their own proposals only.
- **FR-036**: System MUST allow managers, owners, and receptionists to list all proposals in their organization, with receptionists in read-only mode (no mutation actions visible).
- **FR-037**: System MUST provide a metrics summary returning total count and per-state counts for the user's organization.
- **FR-038**: System MUST provide a queue inspection capability returning the active proposal and the ordered queue (with positions and assigned agents) for a given property.

#### Attachments

- **FR-039**: System MUST allow authorized users to attach documents to a proposal, restricting file types to PDF, JPEG, PNG, DOC/DOCX, XLS/XLSX and individual file size to 10 MB.
- **FR-040**: System MUST expose document count and metadata (name, type, size, download link) in proposal detail responses.

#### Notifications

- **FR-041**: System MUST send transactional emails (Portuguese, pt_BR) to relevant parties on these events: proposal sent, counter-proposal generated, accepted, rejected, expired, superseded by acceptance, promoted from queue.
- **FR-041a**: System MUST decouple email dispatch from the originating state transition: notifications MUST be enqueued asynchronously (Outbox pattern) so a state transition (including acceptance, rejection, supersede, promotion) succeeds even if the email subsystem is unavailable.
- **FR-041b**: System MUST retry failed email deliveries with bounded backoff and MUST record any final failure as an entry in the proposal activity timeline (without altering the proposal state).
- **FR-042**: System MUST record every state transition and notification event in a per-proposal activity timeline.

#### Authorization & Multi-Tenancy

- **FR-043**: System MUST isolate proposals strictly by organization: users from one organization MUST NOT see, list, or affect proposals of another organization.
- **FR-044**: System MUST enforce the following authorization matrix:

  | Action | Owner | Manager | Agent | Receptionist | Prospector |
  |---|---|---|---|---|---|
  | Create | Yes | Yes | Yes (own properties) | No | No |
  | List all (org) | Yes | Yes | No | Read-only | No |
  | List own | — | — | Yes | — | — |
  | Update (non-terminal) | Yes | Yes | Yes (own) | No | No |
  | Send | Yes | Yes | Yes (own) | No | No |
  | Accept / Reject / Counter | Yes | Yes | Yes (own) | No | No |
  | Cancel (soft-delete) | Yes | Yes | No | No | No |
  | Attach documents | Yes | Yes | Yes (own) | No | No |
  | View queue | Yes | Yes | Yes | Read-only | No |

- **FR-045**: System MUST forbid an agent from creating or modifying a proposal on a property they are not assigned to.
- **FR-046**: System MUST apply soft deletion for cancellation (records remain queryable for audit but are excluded from active listings unless explicitly requested).
- **FR-046a**: When a property is archived or withdrawn from the market (e.g., its `active` flag becomes false), the system MUST automatically cancel all of that property's non-terminal proposals (Draft, Queued, Sent, Negotiation) with cancellation reason "Property withdrawn from market" and notify each affected agent via email and timeline entry. Terminal proposals (Accepted, Rejected, Expired, Cancelled) MUST remain untouched.

#### Validation & Resilience

- **FR-047**: System MUST validate every input against a schema and return clear, structured validation errors.
- **FR-048**: System MUST never leak the existence of records from other organizations (return generic "not found" responses for unauthorized access).

### Key Entities *(include if feature involves data)*

- **Proposal**: The core entity. Represents an offer made on a property, with an organization-unique code, monetary value, currency, type (sale/lease), validity date, current state, optional description, optional rejection/cancellation reason, send/acceptance/rejection dates, queue position, active flag, and audit fields. Belongs to exactly one property, one client, one responsible agent, one organization. Optionally linked to a parent proposal (counter-proposal chain), a superseding proposal (winner that cancelled this one), and a lead (origin or auto-created).
- **Property**: Pre-existing entity (managed by another feature). A proposal is always tied to one. Each property at any time has at most one active proposal and zero-or-more queued proposals.
- **Client**: A person or company identified by document (CPF/CNPJ). Reused across proposals when document matches.
- **Agent**: The proposal's responsible party. MUST be assigned to the property at creation time.
- **Lead**: A sales pipeline entity. Either pre-existing (linked) or auto-created with source "proposal" when contact is new.
- **Attachment**: A document file linked to a proposal (name, type, size, owner, upload date).
- **Activity Event**: A timeline entry tied to a proposal recording state changes, notifications, or comments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An agent can register and send a new proposal in under 1 minute (from form open to "Sent" state confirmation).
- **SC-002**: When the active proposal of a property terminates as rejected, expired, or cancelled, the next queued proposal is promoted within 5 seconds (excluding cron-driven expirations, which run daily).
- **SC-003**: Under simultaneous creation attempts on the same empty property by 10 agents in parallel, exactly one proposal becomes active and the other 9 enter the queue with sequential positions — verified across 100 trial runs without any duplicate active proposal.
- **SC-004**: Acceptance of a proposal with N competing proposals (queued or otherwise) causes 100% of the N competitors to be cancelled with proper cancellation reason, back-reference, and notification, in a single atomic operation.
- **SC-005**: Listing of proposals returns the first page of up to 100 records in under 1 second for organizations holding up to 50,000 proposals.
- **SC-006**: Aggregated metrics (total + per-state counts) are served in under 200 milliseconds at the 95th percentile.
- **SC-007**: A new contact's first proposal automatically generates exactly one lead with source "proposal" — verified by a 0% duplication rate across automated test runs.
- **SC-008**: 100% of state transitions are recorded in the activity timeline (no missing entries across the full feature test suite).
- **SC-009**: 0 occurrences of cross-organization data exposure across security tests (a user from organization A receives identical responses for non-existent IDs and IDs belonging to organization B).
- **SC-010**: Daily expiration routine completes in under 5 minutes for organizations with up to 10,000 active proposals.
- **SC-011**: Email notifications for proposal lifecycle events are dispatched within 30 seconds of the triggering action under nominal load.
- **SC-012**: 100% of acceptance scenarios listed in this specification pass automated end-to-end tests before release.

## Assumptions

- The existing property, agent, lead, and client modules expose stable read interfaces (lookup by ID, by document) and enforce their own integrity rules.
- The lead module accepts an extension of its source list to include "proposal" via a controlled migration.
- Acceptance is a final decision within this feature's scope; an explicit "undo acceptance" workflow is out of scope (a future feature may revisit it).
- Counter-proposals replace the active slot of their parent rather than entering the queue (this preserves negotiation continuity).
- Only the buyer/lessee side of a proposal is modelled here; landlord/seller-initiated counter-offers follow the same counter-proposal mechanism.
- Brazilian Portuguese (pt_BR) is the required locale for end-user notifications; multi-language support is out of scope for this feature.
- Document validity is restricted to Brazilian CPF/CNPJ in this feature.
- Currency defaults to BRL; multi-currency support is out of scope.

## Dependencies

- **Property module**: source of property records, agent-property assignments, and organization affiliation.
- **Lead module**: target for auto-creation/linking with source "proposal" — requires a coordinated update to the lead source list.
- **Client (partner) module**: source of identity records resolved by document (CPF/CNPJ).
- **Agent module**: source of agent records and their property assignments.
- **Notification subsystem**: for transactional emails.
- **Authentication & authorization subsystem**: for role-based access control and organization scoping.
- **Activity timeline subsystem**: for recording state changes and events.
- **Background job scheduler**: for the daily expiration routine.

## Out of Scope

- Automatic creation of lease/sale contracts on acceptance (only the next-step action is exposed; the contract feature is separate).
- Undoing an accepted proposal.
- Re-opening cancelled or expired proposals (a "renew" action creates a new draft instead, subject to slot availability).
- Multi-currency proposals.
- Localizations other than pt_BR.
- Mobile-specific UX flows (covered by the consuming frontend features).
- Reporting dashboards beyond the per-state metrics summary.
- Property reservation / hold without a formal proposal.
- Data-retention and PII anonymization policy for terminal proposals (deferred to a future cross-cutting LGPD/retention feature; this feature retains data indefinitely until that policy is enacted).
