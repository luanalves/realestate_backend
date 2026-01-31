# Postman Collection - Quicksol Real Estate API

## Overview

Complete Postman collection for Quicksol Real Estate Management System API.

**Version:** 1.4.0  
**Last Updated:** 2026-01-29  
**Spec Coverage:** 006-lead-management (complete)

## Available Collections

### 1. Main API Collection (v1.2) ⭐ RECOMMENDED
**File:** `quicksol_api_v1.2_postman_collection.json`  
**Coverage:** All endpoints with Lead Management integration  
**ADR Compliance:** ADR-016 (complete)

### 2. Legacy API Collection (v1.1)
**File:** `quicksol_api_v1.1_postman_collection.json`  
**Coverage:** Properties, Agents, Assignments, Commissions, RBAC profiles

### 3. Lead Management Collection (Standalone)
**File:** `lead-management-collection.json`  
**Coverage:** Lead CRUD, conversions, statistics, multi-tenancy tests  
**Feature:** 006-lead-management

## Changelog v1.2

✅ Added all 15 Lead Management endpoints (Feature 006)  
✅ Fixed headers per ADR-016 (`X-Openerp-Session-Id` for GET)  
✅ Added test scripts for auto-populating tokens  
✅ Added `refresh_token` variable support  
✅ Reorganized folders by domain  
✅ Added advanced search examples  
✅ Added test scenarios for validation

## Collection Structure

### 1. Authentication
OAuth 2.0 token management endpoints:
- Get OAuth Token
- Refresh Token
- Revoke Token

### 2. User Management
User login, logout, and session management:
- User Login (creates session)
- User Logout
- Get User Context

### 3. Agents
Agent CRUD operations with RBAC:
- List Agents
- Create Agent
- Get Agent Details
- Update Agent
- Delete Agent

### 4. Properties
Property management with multi-tenancy:
- List Properties (filtered by user role)
- Create Property
- Get Property Details
- Update Property
- Delete Property

### 5. Assignments
Property-to-agent assignment management:
- List Assignments
- Create Assignment
- Update Assignment
- Delete Assignment

### 6. Commissions
Commission tracking and management:
- List Commissions
- Calculate Commission
- Update Commission Status

### 7. Performance
Agent performance metrics:
- Agent Sales Metrics
- Commission Reports
- Property Conversion Rates

### 8. Master Data
Reference data endpoints:
- Property Types
- Location Types
- States/Regions

### 9. Leads (NEW - Feature 006) ⭐
Lead management endpoints:
- **CRUD**: List, Create, Get, Update, Archive (soft delete)
- **Actions**: Convert to Sale, Reopen Lost Lead
- **Analytics**: Statistics by state, agent, date range
- **Test Scenarios**: Duplicate prevention, multi-tenancy, state transitions

### 10. Test Journeys (E2E) ⭐

Complete end-to-end test journeys validating RBAC implementation:

#### US1 - Owner Onboarding (3/3 ✅)
- **US1-S1:** Owner Login - Authentication and company creation
- **US1-S2:** Owner CRUD Operations - Full CRUD on properties
- **US1-S3:** Multi-tenancy Isolation - Cross-company access blocked

#### US2 - Manager Team Creation (4/4 ✅)
- **US2-S1:** Manager Creates Agent - Expected restriction (only Owner can create users)
- **US2-S2:** Manager Menu Access - Company data access validated
- **US2-S3:** Manager Assigns Properties - Property-to-agent assignment
- **US2-S4:** Manager Company Isolation - Multi-tenant filtering

#### US3 - Agent Property Management (4/5 ✅ + 1 SKIP)
- **US3-S1:** Agent Assigned Properties - Sees only assigned properties
- **US3-S2:** Agent Auto-Assignment - agent_id auto-set on create
- **US3-S3:** Agent Own Leads - ⏭️ SKIP (requires CRM module)
- **US3-S4:** Agent Cannot Modify Others - Record rule isolation
- **US3-S5:** Agent Company Isolation - Multi-tenant enforcement

#### US4 - Manager Oversight (3/3 ✅)
- **US4-S1:** Manager All Data - Sees all company properties/agents
- **US4-S2:** Manager Reassign Properties - Reassigns between agents
- **US4-S4:** Manager Multi-tenancy - Cross-company isolation

#### US5 - Prospector Property Creation (4/4 ✅)
- **US5-S1:** Prospector Creates Property - prospector_id auto-assigned
- **US5-S2:** Prospector Agent Assignment - Manager assigns selling agent
- **US5-S3:** Prospector Visibility - Sees only own prospected properties
- **US5-S4:** Prospector Restrictions - Cannot access leads/sales

#### US6 - Receptionist Lease Management (2/2 ✅)
- **US6-S1:** Receptionist Lease Management - Full CRUD on leases
- **US6-S2:** Receptionist Restrictions - Read-only on properties (security fix applied)

### 10. RBAC Testing

Additional RBAC validation scenarios:
- Agent - View Own Properties
- Prospector - Create Property
- Receptionist - View Sales (Read-Only)
- Receptionist - Update Sale (Should Fail)
- Financial - View Commissions
- Financial - Update Commission Status
- Legal - View Contracts (Read-Only)
- Portal User - View Own Contracts
- Multi-Tenancy - Company Isolation
- Audit Log - Permission Changes

## Environment Variables

Create a Postman environment with the following variables:

```json
{
  "base_url": "http://localhost:8069",
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "access_token": "",
  "session_id": "",
  "refresh_token": ""
}
```

## Usage

### 1. Get OAuth Token

Run "Get OAuth Token" request first. It will automatically save `access_token` to environment.

### 2. Login as User

Run "User Login" request with credentials:
```json
{
  "db": "realestate",
  "login": "user@company.com",
  "password": "password123"
}
```

This will save `session_id` to environment.

### 3. Run Business Requests

All business endpoints require:
- **Authorization header:** `Bearer {{access_token}}`
- **Session ID:**
  - GET requests: Header `X-Openerp-Session-Id: {{session_id}}`
  - POST/PUT/PATCH: Body property `"session_id": "{{session_id}}"`

### 4. Run Test Journeys

Navigate to **"9. Test Journeys (E2E)"** folder to run complete validation scenarios:

1. **Setup Test Users** (via Odoo UI or admin API):
   - Owner: `owner@company.com`
   - Manager: `manager@company.com`
   - Agent: `agent@company.com`
   - Prospector: `prospector@company.com`
   - Receptionist: `receptionist@company.com`

2. **Run Journey Sequentially**:
   - Each test builds on previous setup
   - Follow US1 → US2 → US3 → US4 → US5 → US6 order

3. **Validate Results**:
   - Check HTTP status codes (200, 201, 403, 404)
   - Verify response data matches expectations
   - Confirm record rules filter correctly

## Test Coverage

**Total E2E Tests:** 21 scenarios  
**Passing:** 20 tests (95.2%)  
**Skipped:** 1 test (US3-S3 - CRM module not implemented)

**User Profiles Validated:**
- ✅ Owner (Real Estate Owner)
- ✅ Director (Company Director) 
- ✅ Manager (Company Manager)
- ✅ User (Company User)
- ✅ Agent (Real Estate Agent)
- ✅ Prospector (Property Prospector)
- ✅ Receptionist (Office Receptionist)
- ✅ Financial (Financial Team)
- ✅ Legal (Legal Team)
- ✅ Portal User (External Portal User)

## Critical Security Fix

**Receptionist Privilege Escalation** (2026-01-26 - Commit 2ce112c)

**Issue:** Receptionist could create properties despite read-only role specification.

**Solution:**
1. Changed Receptionist group inheritance (groups.xml line 51)
2. Removed CREATE permission from User group (ir.model.access.csv line 85)
3. Fixed test to use dynamic group lookup (test_us6_s2)

**Validation:** All 6 restriction checks passing ✅

## Session ID Transmission Rules

⚠️ **CRITICAL - Read Carefully**

### GET Requests (type='http')
```
Header: X-Openerp-Session-Id: {{session_id}}
```

**❌ NEVER send session_id in body for GET requests** - it will be ignored!

### POST/PUT/PATCH (type='json')
```json
{
  "session_id": "{{session_id}}",
  "field1": "value1"
}
```

**✅ Direct property in JSON body** (NOT inside params wrapper)

## JSON Format

**OAuth endpoints:** Direct JSON (no JSONRPC wrapper)
```json
{
  "client_id": "...",
  "client_secret": "...",
  "grant_type": "client_credentials"
}
```

**Business endpoints:** Direct JSON (no JSONRPC wrapper)
```json
{
  "session_id": "...",
  "name": "Property Name",
  "price": 500000
}
```

**❌ DO NOT use:**
```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { ... }
}
```

## Fingerprint Validation

Keep **User-Agent** header consistent during session lifetime:
- Session is bound to IP + User-Agent + Accept-Language
- Changing User-Agent invalidates session
- Use same Postman app for entire session

## Authentication Flow

```
1. GET /api/v1/auth/token
   ↓ (returns access_token)
2. POST /api/v1/users/login (with Bearer token)
   ↓ (returns session_id)
3. Business requests (with Bearer + session_id)
```

## Related Documentation

- [IMPLEMENTATION_VALIDATION.md](../../specs/005-rbac-user-profiles/IMPLEMENTATION_VALIDATION.md) - Complete validation report
- [STATUS.md](../../integration_tests/STATUS.md) - Integration tests status
- [COMPLETION-STATUS.md](../../specs/005-rbac-user-profiles/COMPLETION-STATUS.md) - Final achievement summary
- [spec.md](../../specs/005-rbac-user-profiles/spec.md) - RBAC specification
- [ADR-016](../../docs/adr/ADR-016-api-documentation-standards.md) - API documentation standards

## Standards Compliance

This collection follows:
- **ADR-016:** API Documentation Standards
- **ADR-003:** Mandatory Test Coverage
- **ADR-008:** Testing Best Practices
- **Spec 005:** RBAC User Profiles Implementation

## Import Instructions

1. Open Postman
2. Click "Import" button
3. Select `quicksol_api_v1.1_postman_collection.json`
4. Create environment with required variables
5. Start with "1. Authentication" folder
6. Progress through "9. Test Journeys" for E2E validation

---

**Last Updated:** 2026-01-27  
**Collection Version:** 1.2.0  
**Odoo Version:** 18.0  
**Module:** quicksol_estate
