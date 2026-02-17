Regras rápidas do repositório (Copilot):

- Endpoints expostos com `@http.route` que exigem autenticação devem manter ambos os decoradores `@require_jwt` e `@require_session` antes da definição da função.
- `require_jwt` valida o token JWT; `require_session` garante a identificação/estado do usuário na aplicação (sessão). Esses conceitos são distintos — não substitua `@require_session` por lógica genérica de OAuth ou por tratamento só de token.
- Se um endpoint for intencionalmente público, adicione o comentário `# public endpoint` logo acima do `@http.route` e use `auth='none'`.
- **Public Endpoints** (unauthenticated): Use for password reset, set password, health checks, or any operation that must work without authentication. Always include `# public endpoint` comment for documentation and security audits.
- **Authenticated Endpoints** (require user session): Use triple decorators `@require_jwt` + `@require_session` + `@require_company` for endpoints accessing company-specific data.
- Exemplos curtos: aceitável

```py
# Authenticated endpoint (company-specific data)
@http.route('/api/v1/agents', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
@require_jwt
@require_session
@require_company
def list_agents(self, **kwargs):
    ...

# public endpoint
@http.route('/api/v1/auth/forgot-password', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
def forgot_password(self, **kwargs):
    # Always return 200 (anti-enumeration pattern)
    ...
```

- Exemplos não aceitáveis: remover `@require_session` ou substituí-lo por handling genérico de OAuth sem justificativa clara. Usar `auth='public'` sem comentário `# public endpoint`.

Nota: este arquivo é lido automaticamente pelo GitHub Copilot e agentes compatíveis. Para reforçar a proteção, combine estas instruções com verificações automáticas (CI) e regras de proteção de branch (`CODEOWNERS`, checks obrigatórios).
# Copilot Instructions

## Project Context

This repository contains Docker configurations for running Odoo with PostgreSQL in different versions (16.0, 17.0, and 18.0).

### Current Active Directory: 18.0

The main development and operations are focused on the **18.0** directory, which contains:
- `Dockerfile` - Odoo 18.0 image configuration
- `docker-compose.yml` - Complete orchestration with PostgreSQL
- `entrypoint.sh` - Container startup script
- `odoo.conf` - Odoo configuration file
- `wait-for-psql.py` - Database connection helper
- `README.md` - Setup and usage instructions
- `extra-addons/` - Directory for custom addons

### Database Configuration

- **Database name:** `realestate`
- **Default user:** `admin`
- **Default password:** `admin`
- **PostgreSQL port exposed:** `5432` (for external tools like DBeaver)
- **Odoo web port:** `8069`

### Redis Cache Configuration

- **Redis version:** `7-alpine`
- **Redis port exposed:** `6379` (for monitoring tools)
- **Redis DB index:** `1` (configured in odoo.conf)
- **Memory limit:** 256MB with LRU eviction
- **Persistence:** AOF (Append Only File) enabled
- **Use case:** HTTP sessions, ORM cache, asset cache, message bus

### Key Commands

```bash
# Navigate to working directory
cd 18.0

# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f odoo

# Access Odoo container
docker compose exec odoo bash

# Access database
docker compose exec db psql -U odoo -d realestate

# Access Redis
docker compose exec redis redis-cli

# Monitor Redis operations
docker compose exec redis redis-cli MONITOR
```

### Development Notes

- All Docker operations should be performed from the `18.0` directory
- The `extra-addons` folder is mounted for custom module development
- Database data persists in Docker volumes
- External database access is available via localhost:5432
- **Redis is enabled** for session storage and caching (native Odoo 18.0 support)
- Redis data persists in `odoo18-redis` volume

When providing assistance, assume the user is working within the 18.0 directory context unless otherwise specified.

## Architecture Decision Records (ADRs)

This project follows documented architectural decisions. **Always consult the ADR directory** for guidelines on:
- Development patterns and best practices
- Testing standards and requirements
- Naming conventions
- API documentation standards
- Git workflow and branching strategy

**ADR Directory:** [docs/adr](../docs/adr/)

**Important:** When writing code, creating tests, documenting APIs, naming modules/tables, or making architectural decisions, always check the ADR directory for relevant guidelines. If there's a conflict between a request and an ADR, mention the ADR guideline and ask for clarification.

## Instruction Files

This project uses specialized instruction files that are automatically applied by GitHub Copilot when working with specific types of files:

<instruction>
<file>.github/instructions/controllers.instructions.md</file>
<applyTo>18.0/extra-addons/**/controllers/**/*.py</applyTo>
</instruction>

<instruction>
<file>.github/instructions/test-strategy.instructions.md</file>
<applyTo>18.0/extra-addons/**/tests/**/*.py, cypress/e2e/**/*.cy.js, integration_tests/**/*.sh</applyTo>
</instruction>

When the user is working on these file types, always consult the corresponding instruction file for specific guidelines.

## Key Modules

### thedevkitchen_user_onboarding (Feature 009)

User onboarding and password management module implementing token-based authentication flows for 9 RBAC profiles.

**Key Patterns**:
- **Public Endpoints**: set-password, forgot-password, reset-password use `# public endpoint` marker
- **Authenticated Endpoints**: invite, resend-invite use triple decorators (@require_jwt + @require_session + @require_company)
- **Token Security**: UUID v4 → SHA-256 hashing, raw token sent once in email only
- **Anti-Enumeration**: forgot-password always returns 200, never reveals user existence
- **Authorization Matrix**: Owner→all 9 profiles, Manager→5 operational, Agent→owner+portal
- **Portal Dual Record**: Atomic res.users + real.estate.tenant via partner_id linkage
- **Session Invalidation**: api_session.is_active=False after password reset
- **Email Templates**: mail.template with context variables (Portuguese pt_BR)
- **Configuration**: Singleton thedevkitchen.email.link.settings with TTL validation (1-720h)

**API Endpoints**:
- POST /api/v1/users/invite (authenticated, authorization matrix enforced)
- POST /api/v1/users/{id}/resend-invite (authenticated)
- POST /api/v1/auth/set-password (public)
- POST /api/v1/auth/forgot-password (public, anti-enumeration)
- POST /api/v1/auth/reset-password (public)

**Reference**: See constitution v1.3.0 for security patterns and `.specify/memory/constitution.md` section on Feature 009.
