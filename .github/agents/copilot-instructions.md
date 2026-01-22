# odoo-docker Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-15

## Active Technologies
- Python 3.11 (Odoo 18.0 framework) + Odoo 18.0 (ORM, security framework), PostgreSQL 16, existing quicksol_estate module (005-rbac-user-profiles)
- PostgreSQL 16 with multi-tenant isolation via `estate_company_ids` field on users (005-rbac-user-profiles)

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
- 005-rbac-user-profiles: Added Python 3.11 (Odoo 18.0 framework) + Odoo 18.0 (ORM, security framework), PostgreSQL 16, existing quicksol_estate module

- 001-bearer-token-validation: Added Python 3.11 (Odoo 18.0) + Odoo 18.0, PyJWT, Redis 7-alpine, PostgreSQL 16

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
