# odoo-docker Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-15

## Active Technologies
- Python 3.11 (Odoo 18.0 framework) + Odoo 18.0 (ORM, security framework), PostgreSQL 16, existing quicksol_estate module (005-rbac-user-profiles)
- PostgreSQL 16 with multi-tenant isolation via `estate_company_ids` field on users (005-rbac-user-profiles)
- Python 3.11 + Odoo 18.0 (ORM, mail.thread, mail.activity.mixin), PostgreSQL 16+, Redis 7 (006-lead-management)
- PostgreSQL (`realestate` database) for persistent data, Redis (DB 1) for sessions/cache (006-lead-management)
- Python 3.11 (Odoo 18.0 framework) + Odoo 18.0, PostgreSQL 16, Redis 7 (sessions), PyJWT (JWT auth) (007-company-management)
- PostgreSQL (existing table `thedevkitchen_estate_company`, no schema changes) (007-company-management)
- Python 3.10+ (Odoo 18.0) + Odoo 18.0 ORM, thedevkitchen_apigateway (OAuth2/JWT), quicksol_estate (existing module) (007-company-owner-management)
- PostgreSQL 14+ with existing tables (thedevkitchen_estate_company, res_users) (007-company-owner-management)
- Python 3.12 (Ubuntu Noble Docker image) + Odoo 18.0 (ORM, HTTP framework), Redis 7 (sessions) (008-tenant-lease-sale-api)
- PostgreSQL 14+ via Odoo ORM, Redis 7 for HTTP sessions (008-tenant-lease-sale-api)

- Python 3.11 (Odoo 18.0) + Odoo 18.0, PyJWT, Redis 7-alpine, PostgreSQL 16 (001-bearer-token-validation)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11 (Odoo 18.0): Follow standard conventions

## Recent Changes
- 008-tenant-lease-sale-api: Added Python 3.12 (Ubuntu Noble Docker image) + Odoo 18.0 (ORM, HTTP framework), Redis 7 (sessions)
- 008-tenant-lease-sale-api: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 007-company-owner-management: Added Python 3.10+ (Odoo 18.0) + Odoo 18.0 ORM, thedevkitchen_apigateway (OAuth2/JWT), quicksol_estate (existing module)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
