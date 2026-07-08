# Testing Strategy and QA

> Sources: `docs/adr/ADR-002` (Cypress + curl for E2E/API), `ADR-003` (Mandatory Test Coverage), `ADR-022` (Code Quality/Linting), `18.0/.flake8`, `scripts/validate_coverage.sh`, `scripts/validate_openapi_sync.sh`, `cypress.config.js`, `integration_tests/`, per-module `tests/` directories, `.coderabbit.yaml`.

## Testing Stack

| Layer | Tooling | Notes |
|---|---|---|
| Python unit/integration tests | Odoo's `odoo.tests.common` (`TransactionCase`, and `HttpCase` where applicable) | Standard Odoo test discovery, run per-module (`--test-enable -i <module> -d <db>` pattern implied by `scripts/validate_coverage.sh`). |
| Coverage | `pytest-cov`-style invocation (`--cov-fail-under=80`) inside `scripts/validate_coverage.sh` | Enforces the **80% minimum coverage** mandated by ADR-003 / project "Constitution Principle II." |
| API/E2E (REST) | **curl-based test scripts** (`integration_tests/*.sh`, `integration_tests/lib/get_oauth2_token.sh`, `get_session.sh`, `get_token.sh`, `get_auth_headers.sh`) | Chosen deliberately over Odoo's `HttpCase` because `HttpCase` runs requests inside **read-only transactions**, which fails on any endpoint that needs to persist data (e.g., OAuth token creation) — a documented, load-bearing limitation (ADR-002/ADR-003). |
| UI E2E | **Cypress** ^15.10.0 (`cypress/e2e/*.cy.js`, 41 spec files found) | Full browser-driven flows: RBAC (owner setup/onboarding, prospector commission, manager oversight, agent property access), leads pipeline/Kanban, lease/sale management, OAuth application management, tenant management, admin cross-company access, services admin, etc. Credentials loaded from `18.0/.env` at `cypress.config.js` runtime (never hardcoded). |
| Static analysis / linting (Python) | `black` (formatter), `isort` (import order), `flake8` (max line length 88, `E203/E501/W503/E402` ignored, per `18.0/.flake8`), `pylint`, `mypy` (gradual typing) | All pinned versions installed directly in the Odoo Docker image (`Dockerfile`), per ADR-022. |
| Static analysis (XML/views) | Custom `18.0/lint_xml.py` / `lint_xml.sh` | Detects Odoo-18-specific view errors: deprecated `<tree>` (use `<list>`), deprecated `attrs`, `column_invisible` with Python expressions (causes `OwlError`), `ref()` misuse in action context. |
| PR review automation | **CodeRabbit** (`.coderabbit.yaml`) | AI-assisted review bot configuration at the repo root. |
| API-contract drift check | `scripts/validate_openapi_sync.sh` | Diffs routes declared in `docs/openapi/proposals.yaml` against routes actually registered in `proposal_controller.py`; fails if either side has an entry the other lacks. Currently scoped only to the proposals module. |

## Test Coverage by Module (test files found under `tests/`)

| Module | Test files |
|---|---|
| `quicksol_estate` | 72 |
| `thedevkitchen_apigateway` | 24 |
| `thedevkitchen_cms` | 7 |
| `thedevkitchen_user_onboarding` | 4 |
| `thedevkitchen_estate_credit_check` | 3 |
| `auditlog` (OCA vendor) | 2 |
| `thedevkitchen_estate_goals` | 1 |
| `thedevkitchen_observability` | 1 |

`ADR-003` mandates test coverage for **all** modules (project-wide "Constitution Principle II — Test Coverage Mandatory, NON-NEGOTIABLE"), enforced via `scripts/validate_coverage.sh` with an 80% minimum threshold and an HTML coverage report (`htmlcov/`).

## E2E / Integration Test Infrastructure (`integration_tests/`)

A large collection of standalone bash/python scripts drives real, persistent-data test runs against a live Odoo instance (not the ORM test-transaction sandbox):
- `run_all_tests.sh`, plus feature-specific runners (`run_feature010_tests.sh`, `run_feature014_tests.sh`, `run_feature019_tests.sh`, `run_feature021_tests.sh`, `run_proposal_tests.sh`, `run_us7_tests.sh`).
- Shared auth helpers in `integration_tests/lib/`: `get_oauth2_token.sh` (OAuth2 `client_credentials`, the **preferred** method per ADR-003), `get_session.sh`, `get_token.sh`, `get_auth_headers.sh`. `POST /api/v1/users/login` (JSON-RPC/legacy) is explicitly discouraged in favor of the OAuth2 token endpoint for test automation.
- Cleanup/debug utilities (`cleanup_test_data.sh`, `cleanup_us7_data.sh`, `debug_invite.sh`, `debug_profile_creation.sh`, `fix_cpf.py`) and dedicated `seeds/` and `test_logs/` directories.
- Security-focused test scripts specifically validating multi-tenancy boundaries: `test_admin_api_block.sh`, `test_admin_invite_block.sh`, `test_business_user_isolation.sh` — directly testing the ADR-029 admin-channel-separation guarantees.

## API Documentation as a Testing Artifact

- Postman collections (`docs/postman/`) are versioned in lockstep with API changes (31+ historical collection versions found, latest `quicksol_api_v1.31_postman_collection.json`, "55+ endpoints" per `docs/postman/README.md`), governed by **ADR-016** (Postman Collection Standards).
- OpenAPI specs also exist as standalone YAML files for specific features (`docs/openapi/009-user-onboarding.yaml`, `docs/openapi/proposals.yaml`), in addition to the dynamically-generated spec served at `/api/v1/openapi.json`.

## Discrepancies / Findings

- No CI workflow file was found to confirm that `scripts/validate_coverage.sh`, `lint.sh`, `lint_xml.sh`, or `scripts/validate_openapi_sync.sh` are actually **run automatically** on push/PR — see [infrastructure.md](infrastructure.md) for the broader CI/CD gap. Their existence strongly suggests they are intended to run in CI, but this could not be verified from the repository alone.
- `scripts/validate_openapi_sync.sh` only covers the `proposal_controller.py` ↔ `docs/openapi/proposals.yaml` pair — there is no equivalent drift check for the other ~170 REST endpoints documented dynamically via `/api/v1/openapi.json`; consistency there instead relies on the endpoint-registry pattern (`thedevkitchen.api.endpoint` records) being kept in sync manually by developers per ADR-005.
- Coverage numbers (test-file counts above) reflect file counts, not verified line/branch coverage percentages — actual coverage percentages per module were not available without executing the suite, which is out of scope for this documentation task.
