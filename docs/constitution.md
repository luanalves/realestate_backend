# Constitution - Realestate Backend Platform

> **Project Constitution for AI Agents and Development Tools**  
> Last Updated: January 3, 2026

---

## 📋 Project Overview

### Project Identity
- **Name:** Realestate Backend Platform (Kenlo Imóveis Edition)
- **Type:** Multi-tenant SaaS Real Estate Management System
- **Framework:** Odoo 18.0
- **Architecture:** Microservices with API Gateway + Domain Modules
- **License:** LGPL-3
- **Primary Language:** Python 3.11+
- **Database:** PostgreSQL 16
- **Cache Layer:** Redis 7
- **Testing Framework:** Odoo Test Suite + Cypress E2E

### Mission Statement
Build a secure, scalable, and feature-rich real estate management platform for Brazilian market agencies, following Kenlo Imóveis standards. The system provides complete property lifecycle management with OAuth 2.0 secured REST APIs for headless frontend integration.

### Core Values
1. **Security First:** Multi-layered defense-in-depth approach with JWT, session fingerprinting, and company isolation
2. **Test Coverage:** Mandatory testing for all features (ADR-003: minimum 80% coverage)
3. **API-First Design:** RESTful APIs with HATEOAS, OpenAPI 3.0 documentation (ADR-005, ADR-007)
4. **Multi-Tenancy:** Complete data isolation per real estate company (ADR-008)
5. **Brazilian Market Focus:** CEP integration, CPF/CNPJ validation, IPTU, Matrícula, local standards

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│                    (Headless React/Next.js)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API + OAuth 2.0
┌───────────────────────────┴─────────────────────────────────┐
│                  thedevkitchen_apigateway                    │
│  • OAuth 2.0 Server (RFC 6749, 7009, 7662, 9068)           │
│  • JWT Middleware (@require_jwt)                            │
│  • Session Management (@require_session)                    │
│  • Swagger/OpenAPI Documentation                            │
│  • Rate Limiting & Audit Logs                               │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                   quicksol_estate Module                     │
│  • Property Management (CRUD + 13 sections)                 │
│  • Owner/Agent/Tenant Management                            │
│  • Building/Condominium Tracking                            │
│  • Photo Gallery & Document Management                      │
│  • Lease & Sales Contracts                                  │
│  • Key Control & Commission Tracking                        │
│  • Web Publishing (SEO-optimized)                           │
│  • Master Data APIs (8 endpoints)                           │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                  Odoo 18.0 Core Framework                    │
│  • ORM (Object-Relational Mapping)                          │
│  • Security (Users, Groups, Record Rules)                   │
│  • Multi-Company Support                                     │
│  • Mail & Portal Integration                                │
│  • Workflow Engine                                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
    ┌───────────────────────┴──────────────┬──────────────┐
    │                                      │              │
┌───┴─────────┐                  ┌─────────┴────┐   ┌────┴──────┐
│ PostgreSQL  │                  │    Redis     │   │  Filestore│
│  (Port 5432)│                  │  (Port 6379) │   │  (Volumes)│
│  DB: realestate                │  DB Index: 1 │   │           │
└─────────────┘                  └──────────────┘   └───────────┘
```

### Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Container Orchestration** | Docker Compose | 3.x | Service orchestration |
| **Application Server** | Odoo | 18.0 | ERP framework & business logic |
| **Database** | PostgreSQL | 16-alpine | Persistent data storage |
| **Cache/Sessions** | Redis | 7-alpine | HTTP sessions, ORM cache, message bus |
| **Web Server** | Werkzeug (built-in) | Latest | WSGI HTTP server |
| **API Gateway** | Custom (Authlib) | 1.3+ | OAuth 2.0 + JWT authentication |
| **Testing** | Odoo Test + Cypress | - | Unit, Integration, E2E tests |
| **Documentation** | Swagger UI | 3.0 | Interactive API documentation |

### Network & Ports

- **Odoo HTTP:** `8069` (web interface + REST APIs)
- **Odoo XML-RPC:** `8071` (legacy RPC)
- **Odoo Longpolling:** `8072` (WebSocket/notifications)
- **PostgreSQL:** `5432` (exposed for external tools: DBeaver, pgAdmin)
- **Redis:** `6379` (exposed for monitoring: redis-cli)

### Docker Volumes

| Volume | Purpose | Persistence |
|--------|---------|-------------|
| `odoo18-db` | PostgreSQL data | ✅ Production-critical |
| `odoo18-data` | Odoo filestore (attachments) | ✅ Production-critical |
| `odoo18-redis` | Redis AOF persistence | ✅ Session continuity |
| `./extra-addons` | Custom modules (dev mount) | 🔄 Development only |

---

## 🔒 Security Architecture

### Authentication & Authorization

#### 1. OAuth 2.0 (Application Authentication)
- **Grant Type:** Client Credentials
- **Token Type:** JWT (RS256 signed)
- **Standards:** RFC 6749, RFC 7009, RFC 7662, RFC 9068
- **Use Case:** External applications/services consuming APIs
- **Token Endpoint:** `POST /api/v1/auth/token`
- **Refresh Endpoint:** `POST /api/v1/auth/refresh`
- **Revoke Endpoint:** `POST /api/v1/auth/revoke`

#### 2. Session-based (User Authentication)
- **Login Endpoint:** `POST /api/v1/users/login` (email + password)
- **Session Storage:** Redis (DB index 1)
- **Session Token:** JWT with fingerprint (IP + User-Agent + Language)
- **Token Lifetime:** 24 hours (configurable)
- **Fingerprint Components:** 
  - IP Address (configurable on/off)
  - User-Agent (configurable on/off)
  - Language (configurable on/off)
- **Session Hijacking Protection:** JWT signature + fingerprint validation on every request
- **Decorators:** `@require_session`, `@require_jwt`, `@require_company`

### Multi-Tenancy & Company Isolation (ADR-008)

**Status:** Phase 1 In Progress (Phase 0 Security Complete)

#### Phase 0: Authentication & Session Protection ✅ COMPLETE
- [x] User login endpoint with session management
- [x] JWT session token with fingerprint (IP/UA/Lang)
- [x] Session hijacking prevention
- [x] `@require_session` decorator
- [x] Rate limiting (failed login attempts)
- [x] Audit logging (security events)

#### Phase 1: Company Isolation 🚧 IN PROGRESS
- [ ] `@require_company` decorator (filter by `estate_company_ids`)
- [ ] Apply filters to all API endpoints
- [ ] Validation on create/update operations
- [ ] Multi-tenant isolation tests
- [ ] Activate Record Rules (Odoo Web)

**Database Design:**
- `thedevkitchen.estate.company` - Real estate company model
- Many2many relationships: `company_property_rel`, `company_agent_rel`, `company_tenant_rel`, etc.
- User fields: `estate_company_ids` (Many2many), `estate_default_company_id` (Many2one)

**Isolation Strategy:**
- Users see only data from their `estate_company_ids`
- All API queries filtered by company context
- Record Rules enforce isolation in Odoo Web UI
- Creation/update validates company ownership

---

## 📦 Modules

### 1. thedevkitchen_apigateway

**Version:** 18.0.1.1.0  
**Purpose:** Generic OAuth 2.0 API Gateway for Odoo

#### Features
- OAuth 2.0 Server implementation (Client Credentials Grant)
- Token management (access, refresh, revocation)
- JWT authentication middleware
- Session fingerprinting & hijacking prevention
- Swagger/OpenAPI 3.0 documentation
- API endpoint registry
- Access logs & audit trails
- Admin interface for OAuth applications

#### Models (4)
- `oauth.application` - OAuth client credentials
- `oauth.token` - Access/refresh tokens
- `api.endpoint` - Registry of available API endpoints
- `api.access.log` - Audit logs of API calls
- `security.settings` - Session fingerprint configuration

#### Controllers (3)
- `auth_controller.py` - Token/refresh/revoke endpoints
- `swagger_controller.py` - OpenAPI docs & Swagger UI
- `test_controller.py` - Protected endpoint for testing

#### Security Components
- `middleware.py` - JWT validation decorators
- `models/ir_http.py` - Session token injection
- `services/rate_limiter.py` - Brute-force protection
- `services/session_validator.py` - Session validation service
- `services/audit_logger.py` - Security event logging

#### Tests
- **Unit Tests:** 86 tests
- **Integration Tests:** 70 tests
- **E2E Tests (Cypress):** 54 tests
- **Total:** 210 tests ✅ All passing

---

### 2. quicksol_estate

**Version:** 2.0.1  
**Purpose:** Complete Real Estate Management System (Kenlo Imóveis Edition)

#### Features
- **Property Management:** 13-section property form
  1. Owner Data
  2. Structure
  3. Location (CEP integration)
  4. Primary Data (pricing, taxes, status)
  5. Features (rooms, areas, amenities)
  6. Zoning
  7. Tags/Markers
  8. Key Control
  9. Photo Gallery
  10. Web Publishing (SEO)
  11. Signs and Banners
  12. Commissions
  13. Documents

- **Brazilian Market Features:**
  - CEP (postal code) lookup with ViaCEP API
  - CPF/CNPJ validation
  - IPTU (property tax) tracking
  - Matrícula (property deed) management
  - State/city integration (27 Brazilian states)

- **Entity Management:**
  - Owners (CPF/CNPJ, contacts, documents)
  - Agents (commission tracking)
  - Tenants (lease management)
  - Buildings/Condominiums
  - Lease contracts
  - Sales contracts

- **Media & Documents:**
  - Photo gallery with main photo selection
  - Document management (matrícula, IPTU, contracts)
  - Key control & tracking
  - Signs/banners tracking

#### REST API Endpoints (12)

**Property CRUD (4 endpoints)**
- `POST /api/v1/properties` - Create property
- `GET /api/v1/properties/{id}` - Read property
- `PUT /api/v1/properties/{id}` - Update property
- `DELETE /api/v1/properties/{id}` - Delete property

**Master Data API (8 endpoints)**
- `GET /api/v1/property-types` - List property types (15 records)
- `GET /api/v1/location-types` - List location types (5 records)
- `GET /api/v1/states?country_id={id}` - List states (27 Brazilian states)
- `GET /api/v1/agents` - List real estate agents
- `GET /api/v1/owners` - List property owners
- `GET /api/v1/companies` - List real estate companies
- `GET /api/v1/tags` - List property tags (8 records)
- `GET /api/v1/amenities` - List amenities (26 records in Portuguese)

#### Code Structure (OOP Architecture)

```
quicksol_estate/
├── controllers/
│   ├── property_api.py          # Property CRUD (441 lines)
│   ├── master_data_api.py       # Master data endpoints (257 lines)
│   └── utils/                   # Shared utilities
│       ├── auth.py              # @require_jwt decorator
│       ├── response.py          # success_response(), error_response()
│       └── serializers.py       # serialize_property(), validate_property_access()
├── models/                      # Business logic (25+ models)
│   ├── property.py              # Core property model
│   ├── owner.py, agent.py, tenant.py
│   ├── building.py, lease.py, sale.py
│   └── amenity.py, tag.py, ...
├── services/                    # Business services
│   ├── security_service.py      # Company validation & filters
│   └── audit_service.py         # API operation auditing
├── tests/
│   ├── api/
│   │   ├── test_property_api.py      # 53 tests (920 lines)
│   │   ├── test_master_data_api.py   # 22 tests (426 lines)
│   │   └── test_property_api_auth.py # Auth-specific tests
│   └── utils/
│       └── test_utils_unit.py        # 13 unit tests (189 lines)
└── data/
    └── amenity_data.xml         # 26 amenities (Piscina, Academia, etc.)
```

#### Tests
- **Unit Tests:** 13 tests (utils modules)
- **HTTP Integration Tests:** 120 tests (API endpoints)
  - Success scenarios (CRUD operations)
  - Authentication failures (401 Unauthorized)
  - Data validation (required fields, types)
  - Business rules (not found, conflicts)
  - Permissions (admin, manager, agent, user)
  - Edge cases (extreme values, nullables)
- **Total:** 133 tests ✅ All passing

---

### 3. auditlog

**Version:** Latest  
**Purpose:** OCA standard audit logging module  
**Source:** https://github.com/OCA/server-tools

**Features:**
- Automatic change tracking for configured models
- Field-level audit trails
- User/timestamp tracking
- Old/new value comparison

---

## 🧪 Testing Strategy (ADR-002, ADR-003)

### Coverage Requirements (ADR-003)
- **Minimum Coverage:** 80% for all modules
- **Mandatory Tests:** Unit + Integration + E2E for new features
- **Review Requirement:** PRs rejected if coverage drops below 80%

### Test Pyramid

```
       /\
      /E2E\          Cypress (54 tests)
     /______\        - Journey tests (login, property flow)
    /        \       - OAuth lifecycle
   /Integration\     - Session management
  /______________\   
 /                \  Integration (190 tests)
/   Unit Tests     \ - API endpoints (120 tests)
/____________________\ - OAuth flow (70 tests)
                       - Utils (13 tests)

                       Unit Tests (86 tests)
                       - Services, helpers, serializers
```

### Test Categories

#### 1. Unit Tests (86 + 13 = 99 tests)
- **Location:** `tests/test_*.py`, `tests/utils/test_*.py`
- **Scope:** Individual functions, decorators, serializers
- **Isolation:** Mock external dependencies
- **Examples:**
  - `test_utils_unit.py` - JWT decorator, response helpers, serializers
  - API Gateway service tests

#### 2. Integration Tests (190 tests)
- **Location:** `tests/api/test_*.py`
- **Scope:** HTTP endpoints, database interactions
- **Database:** Test database created/destroyed per test class
- **Examples:**
  - `test_property_api.py` - 53 tests (CRUD, auth, permissions, edge cases)
  - `test_master_data_api.py` - 22 tests (all 8 endpoints)
  - API Gateway integration - 70 tests

#### 3. E2E Tests (54 Cypress tests)
- **Location:** `cypress/e2e/*.cy.js`
- **Scope:** Full user journeys, browser automation
- **Environment:** Docker containers running
- **Examples:**
  - `jornada-completa-imoveis.cy.js` - Complete property journey
  - `oauth-applications-actions.cy.js` - OAuth application management
  - `tokens-lifecycle.cy.js` - Token creation/refresh/revoke

### Running Tests

```bash
# Navigate to Odoo 18.0 directory
cd 18.0

# Unit + Integration Tests (Python)
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate --test-enable --stop-after-init --log-level=test

# Specific module tests
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate -u quicksol_estate --test-enable --stop-after-init

# E2E Tests (Cypress)
npm run cypress:run  # Headless
npm run cypress:open # Interactive

# Linting
./lint.sh  # Runs ruff + black
```

---

## 📚 Architecture Decision Records (ADRs)

All architectural decisions are documented in [`docs/adr/`](docs/adr/).

### Active ADRs

| ADR | Title | Status | Impact |
|-----|-------|--------|--------|
| [ADR-001](docs/adr/ADR-001-development-guidelines-for-odoo-screens.md) | Development Guidelines for Odoo Screens | ✅ Active | Code structure, naming, OOP patterns |
| [ADR-002](docs/adr/ADR-002-cypress-end-to-end-testing.md) | Cypress End-to-End Testing | ✅ Active | E2E test standards |
| [ADR-003](docs/adr/ADR-003-mandatory-test-coverage.md) | Mandatory Test Coverage (80%) | ✅ Active | Quality gates, PR requirements |
| [ADR-004](docs/adr/ADR-004-nomenclatura-modulos-tabelas.md) | Module & Table Naming Conventions | ✅ Active | Naming standards (Portuguese) |
| [ADR-005](docs/adr/ADR-005-openapi-30-swagger-documentation.md) | OpenAPI 3.0 Swagger Documentation | ✅ Active | API documentation standards |
| [ADR-006](docs/adr/ADR-006-git-flow-workflow.md) | Git Flow Workflow | ✅ Active | Branching strategy, PR process |
| [ADR-007](docs/adr/ADR-007-hateoas-hypermedia-rest-api.md) | HATEOAS Hypermedia REST API | 🚧 Planned | RESTful API design |
| [ADR-008](docs/adr/ADR-008-api-security-multi-tenancy.md) | API Security & Multi-Tenancy | 🚧 In Progress | Company isolation, RBAC |
| [ADR-009](docs/adr/ADR-009-headless-authentication-user-context.md) | Headless Authentication & User Context | ✅ Active | Session management, JWT |
| [ADR-010](docs/adr/ADR-010-python-virtual-environment.md) | Python Virtual Environment | ✅ Active | Development environment setup |
| [ADR-011](docs/adr/ADR-011-controller-security-authentication-storage.md) | Controller Security & Auth Storage | ✅ Active | Endpoint protection patterns |

### Critical Rules from ADRs

**From ADR-011 (Controller Security):**
- All authenticated endpoints MUST use both `@require_jwt` AND `@require_session`
- `@require_jwt` validates the JWT token
- `@require_session` ensures user identification/state in application
- Public endpoints MUST have `# public endpoint` comment above `@http.route`
- Example:
  ```python
  @http.route('/api/v1/properties', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
  @require_jwt
  @require_session
  @require_company  # Phase 1
  def list_properties(self, **kwargs):
      ...
  ```

**From ADR-003 (Test Coverage):**
- Minimum 80% code coverage for all modules
- Tests MUST be written before PR submission
- Coverage report checked in CI/CD
- PRs rejected if coverage drops

**From ADR-006 (Git Flow):**
- Branch naming: `feature/`, `bugfix/`, `hotfix/`
- PRs require: tests, documentation, CODEOWNERS approval
- Main branches: `main` (production), `develop` (staging)

---

## 🚀 Development Workflow

### Environment Setup

```bash
# Clone repository
git clone <repo-url>
cd odoo-docker/18.0

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Start services
docker compose up -d

# View logs
docker compose logs -f odoo

# Access Odoo shell
docker compose exec odoo bash

# Access database
docker compose exec db psql -U odoo -d realestate

# Access Redis
docker compose exec redis redis-cli
```

### Database Credentials (Development)

| Parameter | Value |
|-----------|-------|
| **Database** | `realestate` |
| **User** | `odoo` |
| **Password** | `odoo` |
| **Host** | `db` (inside Docker) / `localhost` (external) |
| **Port** | `5432` |

### Odoo Default Credentials

| Parameter | Value |
|-----------|-------|
| **URL** | http://localhost:8069 |
| **Email** | `admin` |
| **Password** | `admin` |

### Module Development

**Directory:** `18.0/extra-addons/`

**Creating a new module:**
```bash
docker compose exec odoo bash
cd /mnt/extra-addons
odoo scaffold my_module .
```

**Module structure (follow ADR-001, ADR-004):**
```
my_module/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── my_controller.py
├── models/
│   ├── __init__.py
│   └── my_model.py
├── views/
│   └── my_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── tests/
│   ├── __init__.py
│   ├── test_my_model.py
│   └── api/
│       └── test_my_api.py
└── data/
    └── my_data.xml
```

### Installing/Updating Modules

```bash
# Install module
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate -i my_module

# Update module
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate -u my_module

# Update with tests
docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate -u my_module --test-enable --stop-after-init
```

---

## 📖 API Documentation

### Accessing Swagger UI

**URL:** http://localhost:8069/api/docs

**Features:**
- Interactive API testing
- Request/response schemas
- Authentication support (paste JWT token)
- Try-it-out functionality

### OpenAPI Specification

**URL:** http://localhost:8069/api/openapi.json

**Version:** OpenAPI 3.0.3  
**Format:** JSON

### Authentication Flow

#### For Applications (OAuth 2.0)

```bash
# 1. Get access token
curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "grant_type": "client_credentials"
  }'

# Response:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "Bearer",
#   "expires_in": 3600,
#   "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
# }

# 2. Use token in requests
curl -X GET http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."
```

#### For Users (Session-based)

```bash
# 1. Login
curl -X POST http://localhost:8069/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Response:
# {
#   "success": true,
#   "message": "Login successful",
#   "data": {
#     "user_id": 5,
#     "session_id": "abc123xyz...",
#     "user": {...}
#   }
# }

# 2. Use session_id in requests
curl -X GET http://localhost:8069/api/v1/properties \
  -H "X-Openerp-Session-Id: abc123xyz..."
```

---

## 📊 Current Development Status

### Phase Overview

| Phase | Status | Completion | Description |
|-------|--------|------------|-------------|
| **Phase 0** | ✅ Complete | 100% | Authentication & Session Security |
| **Phase 1** | 🚧 In Progress | 30% | Company Isolation & Multi-Tenancy |
| **Phase 2** | 📋 Planned | 0% | RBAC & Advanced Permissions |
| **Phase 3** | 📋 Planned | 0% | HATEOAS & API Versioning |
| **Phase 4** | 📋 Planned | 0% | Message Queue (Celery + RabbitMQ) |

### Recent Achievements (December 2025)

✅ **Session Hijacking Protection**
- JWT session tokens with fingerprinting (IP/UA/Lang)
- Configurable security settings via admin UI
- 7/7 integration tests passing
- Automatic logout on fingerprint mismatch

✅ **API Gateway Complete**
- OAuth 2.0 server (4 RFCs compliant)
- 210 tests passing (86 unit + 70 integration + 54 E2E)
- Swagger UI with interactive docs
- Rate limiting & audit logging

✅ **Properties REST API**
- 12 endpoints (4 CRUD + 8 master data)
- 133 tests passing (13 unit + 120 integration)
- OOP architecture with service layers
- Complete Brazilian market support

### Known Technical Debt

**From TECHNICAL_DEBIT.md:**

1. 🔄 **UUID for Properties** - Replace sequential IDs with UUIDs for security
2. 🔒 **RBAC E2E Tests** - Create users with different roles and test endpoint access
3. 🔗 **HATEOAS Implementation** - Add hypermedia links to API responses (ADR-007)
4. 📝 **Incremental Swagger Docs** - Document endpoints as they're created
5. 🏢 **Company Integration** - Integrate estate module with Odoo `res.company`
6. 👥 **Admin API Restrictions** - Prevent admin users from accessing end-user APIs
7. 📨 **Message Queue** - Integrate RabbitMQ + Celery for async tasks
8. 🧹 **Duplicate File Cleanup** - Remove duplicated test files in repository
9. 🌐 **Dynamic CORS** - Configure CORS dynamically per endpoint
10. ⚡ **Login Performance** - Replace database queries with Redis cache

---

## 🎯 Roadmap

### Short Term (Q1 2026)

- [ ] Complete Phase 1 (Company Isolation)
  - [ ] `@require_company` decorator
  - [ ] Apply filters to all endpoints
  - [ ] Multi-tenant isolation tests
  - [ ] Activate Record Rules
- [ ] Implement UUID for properties
- [ ] RBAC endpoint tests with multiple user roles
- [ ] Dynamic CORS configuration

### Medium Term (Q2 2026)

- [ ] HATEOAS implementation (ADR-007)
- [ ] API versioning strategy
- [ ] Redis-based session cache (performance)
- [ ] Company integration with `res.company`
- [ ] Advanced audit logging
- [ ] Property search & filtering

### Long Term (Q3-Q4 2026)

- [ ] Message queue integration (RabbitMQ + Celery)
- [ ] Batch operations API
- [ ] Webhook support for events
- [ ] Mobile app API extensions
- [ ] AI-powered property recommendations
- [ ] Integration with external portals (OLX, VivaReal)

---

## 🔧 Configuration Files

### Docker Compose

**File:** `18.0/docker-compose.yml`

**Services:**
- `db` - PostgreSQL 16 Alpine
- `redis` - Redis 7 Alpine (256MB, LRU eviction, AOF persistence)
- `odoo` - Custom Odoo 18.0 image

**Environment Variables (.env):**
```ini
POSTGRES_DB=realestate
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo
DB_HOST=db
DB_PORT=5432
DB_NAME=realestate
JWT_ISSUER=odoo-apigateway
JWT_SECRET=your_secret_key_here
```

### Odoo Configuration

**File:** `18.0/odoo.conf`

**Key Settings:**
```ini
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
admin_passwd = admin
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
http_port = 8069
longpolling_port = 8072

# Redis cache
enable_redis = True
redis_host = redis
redis_port = 6379
redis_dbindex = 1
redis_pass = False
```

---

## 🤝 Contributing

### Pull Request Process (ADR-006)

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Follow coding standards (ADR-001)**
   - OOP principles
   - Self-documenting code
   - No excessive comments
   - Follow naming conventions (ADR-004)

3. **Write tests (ADR-003)**
   - Unit tests for new functions
   - Integration tests for API endpoints
   - E2E tests for user journeys
   - Ensure 80%+ coverage

4. **Run linter**
   ```bash
   ./lint.sh
   ```

5. **Test locally**
   ```bash
   docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d realestate -u my_module --test-enable --stop-after-init
   ```

6. **Create PR**
   - Title: `feat(module): description` or `fix(module): description`
   - Description: What, why, how
   - Link related issues
   - Request review from CODEOWNERS

7. **PR Requirements**
   - ✅ All tests passing
   - ✅ Coverage ≥ 80%
   - ✅ Linter passing
   - ✅ Documentation updated
   - ✅ ADRs followed
   - ✅ CODEOWNERS approval

### Code Review Guidelines

**Reviewers check for:**
- ✅ Adherence to ADRs (especially ADR-001, ADR-011)
- ✅ Test coverage and quality
- ✅ Security best practices (no `.sudo()` abuse, proper decorators)
- ✅ Performance considerations
- ✅ Documentation completeness
- ✅ Code readability and maintainability

---

## 📞 Support & Resources

### Documentation
- **Project Docs:** [`docs/`](docs/)
- **ADRs:** [`docs/adr/`](docs/adr/)
- **Odoo Official:** https://www.odoo.com/documentation/18.0
- **Odoo Docker:** https://github.com/odoo/docker

### Implementation Plans
- [`PLANO_API_REST.md`](PLANO_API_REST.md) - REST API implementation roadmap
- [`MULTI-TENANCY-IMPLMENTATION-PLAN.md`](MULTI-TENANCY-IMPLMENTATION-PLAN.md) - Multi-tenancy strategy
- [`FASE-1-COMPANY-ISOLATION.md`](FASE-1-COMPANY-ISOLATION.md) - Phase 1 detailed plan
- [`PLANO-SECURITY-SESSION-HIJACKING.md`](PLANO-SECURITY-SESSION-HIJACKING.md) - Session security
- [`PLANO-CELERY-RABBITMQ.md`](PLANO-CELERY-RABBITMQ.md) - Message queue plan
- [`TECHNICAL_DEBIT.md`](TECHNICAL_DEBIT.md) - Known issues & improvements

### Testing
- **Cypress Docs:** [`cypress/README.md`](cypress/README.md)
- **E2E Tests:** [`cypress/e2e/`](cypress/e2e/)

### Quick Links
- **Swagger UI:** http://localhost:8069/api/docs
- **OpenAPI JSON:** http://localhost:8069/api/openapi.json
- **Odoo Web:** http://localhost:8069

---

## 📝 Appendix

### Glossary

| Term | Definition |
|------|------------|
| **ADR** | Architecture Decision Record - documented architectural choices |
| **CEP** | Código de Endereçamento Postal (Brazilian postal code) |
| **CNPJ** | Cadastro Nacional da Pessoa Jurídica (Brazilian business tax ID) |
| **CPF** | Cadastro de Pessoas Físicas (Brazilian individual tax ID) |
| **HATEOAS** | Hypermedia as the Engine of Application State |
| **IPTU** | Imposto Predial e Territorial Urbano (Brazilian property tax) |
| **JWT** | JSON Web Token - compact token format for authentication |
| **Matrícula** | Property deed registration number |
| **Multi-Tenancy** | Architecture where multiple customers share same application instance |
| **OCA** | Odoo Community Association - open-source Odoo modules |
| **OAuth 2.0** | Open standard for access delegation |
| **ORM** | Object-Relational Mapping - database abstraction layer |
| **RBAC** | Role-Based Access Control |
| **Record Rules** | Odoo security rules that filter database records |

### Naming Conventions (ADR-004)

**Modules:**
- Pattern: `{company}_{domain}` (lowercase, underscore-separated)
- Examples: `quicksol_estate`, `thedevkitchen_apigateway`

**Models:**
- Pattern: `{company}.{domain}.{entity}` (dot-separated)
- Examples: `thedevkitchen.estate.property`, `oauth.application`

**Database Tables:**
- Pattern: `{company}_{domain}_{entity}` (generated from model name)
- Examples: `thedevkitchen_estate_property`, `oauth_application`

**Controllers:**
- Pattern: `{entity}_api.py` or `{function}_controller.py`
- Examples: `property_api.py`, `auth_controller.py`

**Tests:**
- Pattern: `test_{entity}_{scope}.py`
- Examples: `test_property_api.py`, `test_utils_unit.py`

### File Structure Reference

```
odoo-docker/
├── constitution.md                    # This file
├── README.md                          # Quick start guide
├── LICENSE                            # LGPL-3 license
├── cypress.config.js                  # Cypress configuration
├── 18.0/                              # Active Odoo 18 environment
│   ├── docker-compose.yml             # Service orchestration
│   ├── Dockerfile                     # Custom Odoo image
│   ├── odoo.conf                      # Odoo configuration
│   ├── entrypoint.sh                  # Container startup script
│   ├── .env                           # Environment variables
│   ├── lint.sh                        # Linter script (ruff + black)
│   ├── package.json                   # Node dependencies (Cypress)
│   ├── extra-addons/                  # Custom modules
│   │   ├── thedevkitchen_apigateway/  # OAuth 2.0 gateway
│   │   ├── quicksol_estate/           # Real estate module
│   │   └── auditlog/                  # OCA audit module
│   └── filestore/                     # Odoo attachments
├── docs/                              # Documentation
│   ├── README.md                      # Docs index
│   └── adr/                           # Architecture Decision Records
│       ├── ADR-001-*.md               # Development guidelines
│       ├── ADR-002-*.md               # Cypress testing
│       ├── ADR-003-*.md               # Test coverage
│       └── ...                        # More ADRs
├── cypress/                           # E2E tests
│   ├── e2e/                           # Test specs
│   ├── fixtures/                      # Test data
│   └── support/                       # Custom commands
└── *.md                               # Implementation plans

```

---

## 🔖 Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2026-01-03 | Initial constitution created for Speckit integration |

---

**Last Updated:** January 3, 2026  
**Maintainer:** Development Team  
**License:** LGPL-3

---

*This constitution is a living document and should be updated as the project evolves. Always refer to ADRs for authoritative architectural decisions.*
