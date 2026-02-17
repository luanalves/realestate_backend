# Realestate Backend - Odoo 18.0

Backend do sistema de gestão imobiliária baseado em Odoo 18.0 com PostgreSQL.

## 🚀 Como subir o ambiente

### Pré-requisitos

- Docker
- Docker Compose

### Comandos principais

```bash
# Navegar para o diretório do Odoo 18.0
cd 18.0

# Subir os containers (Odoo + PostgreSQL)
docker compose up -d

# Parar os containers
docker compose down

# Ver logs do Odoo
docker compose logs -f odoo

# Ver logs do PostgreSQL
docker compose logs -f db

# Reiniciar os serviços
docker compose restart

# Acessar o container do Odoo
docker compose exec odoo bash

# Acessar o PostgreSQL
docker compose exec db psql -U odoo -d realestate
```

### Acessos

- **Odoo Web**: http://localhost:8069
- **PostgreSQL**: localhost:5432
- **Database**: `realestate`
- **Usuário padrão**: `admin`
- **Senha padrão**: `admin`

### Desenvolvimento

Os módulos customizados devem ser adicionados no diretório `18.0/extra-addons/`.

## 📚 Documentação

- Docker source: https://github.com/odoo/docker
- Odoo Documentation: https://www.odoo.com/documentation/18.0

## 🔌 Acessos aos Componentes Docker

### Odoo Web Application
- **URL:** http://localhost:8069
- **Usuário:** `admin`
- **Senha:** `admin`

### PostgreSQL Database
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `realestate`
- **Username:** `odoo`
- **Password:** `odoo`
- **Ferramentas:** DBeaver, pgAdmin, psql

### Redis Cache
- **Host:** `localhost`
- **Port:** `6379`
- **DB Index:** `1` (configurado no odoo.conf)
- **CLI Access:** `docker compose exec redis redis-cli`

### RabbitMQ (Message Broker)
- **Management UI:** http://localhost:15672
- **Username:** `odoo`
- **Password:** `odoo_rabbitmq_secret_2026`
- **AMQP Port:** `5672` (para conexões de aplicação)
- **Purpose:** Gerenciamento de filas Celery

### Flower (Celery Monitoring)
- **URL:** http://localhost:5555
- **Username:** `admin`
- **Password:** `flower_admin_2026`
- **Purpose:** Monitoramento em tempo real dos workers Celery

### Celery Workers (Background Tasks)
- **Commission Worker:** Processa cálculos de comissão
- **Notification Worker:** Gerencia notificações email/SMS
- **Audit Worker:** Registra alterações de segurança e dados
- **Status:** `docker compose ps` ou Flower UI

### MailHog (Email Testing - Development)
- **SMTP Server:** `mailhog:1025` (configurar no Odoo)
- **Web UI:** http://localhost:8025
- **Purpose:** Captura todos os emails enviados sem enviá-los realmente
- **Usage:** Ideal para testar fluxos de email (convites, password reset, notificações)
- **Configuration:** Settings > Technical > Email > Outgoing Mail Servers
  - SMTP Server: `mailhog`
  - SMTP Port: `1025`
  - Connection Security: `None`
  - Username/Password: (deixar vazio)
- **Production:** Ver [ADR-023](docs/adr/ADR-023-mailhog-email-testing-development.md) para configuração SMTP de produção

---

## � Documentação da API (Swagger/OpenAPI)

### Swagger UI (Interface Interativa)
- **URL:** http://localhost:8069/api/docs
- **Descrição:** Interface gráfica interativa para explorar e testar os endpoints da API
- **Autenticação:** Não requer autenticação para visualizar (endpoints protegidos requerem token Bearer)

### OpenAPI Specification (JSON)
- **URL:** http://localhost:8069/api/v1/openapi.json
- **Descrição:** Especificação OpenAPI 3.0 em formato JSON gerada dinamicamente
- **Uso:** Importar em ferramentas como Postman, Insomnia ou geradores de código

### Como usar a documentação Swagger

1. **Visualizar endpoints:** Acesse http://localhost:8069/api/docs
2. **Obter token de autenticação:** Use o endpoint `/api/v1/oauth/token` com suas credenciais
3. **Autorizar:** Clique em "Authorize" no Swagger UI e insira o token no formato `Bearer {seu_token}`
4. **Testar endpoints:** Clique em "Try it out" em qualquer endpoint para testar diretamente

---

## �📡 API Endpoints

### Feature 007: Company & Owner Management

#### Owner API

| Method | Endpoint | Description | Auth | RBAC |
|--------|----------|-------------|------|------|
| `POST` | `/api/v1/owners` | Create Owner (no company) | Bearer | Public (JWT only) |
| `POST` | `/api/v1/owners/{owner_id}/companies` | Link Owner to Company | Bearer + Session | Owner, Admin |
| `DELETE` | `/api/v1/owners/{owner_id}/companies/{company_id}` | Unlink Owner from Company | Bearer + Session | Owner, Admin |

> **Nota:** Operações de consulta, atualização e exclusão de usuários (incluindo owners) são feitas pelos endpoints genéricos:
> - `GET /api/v1/me` — Dados do usuário logado
> - `PATCH /api/v1/users/profile` — Atualizar perfil (name, email, phone, mobile)
> - `POST /api/v1/users/change-password` — Alterar senha

#### Company API

| Method | Endpoint | Description | Auth | RBAC |
|--------|----------|-------------|------|------|
| `POST` | `/api/v1/companies` | Create Company (auto-link creator) | Bearer | Owner, Admin |
| `GET` | `/api/v1/companies` | List Companies (multi-tenancy) | Bearer | All authenticated |
| `GET` | `/api/v1/companies/{id}` | Get Company details | Bearer | All authenticated |
| `PUT` | `/api/v1/companies/{id}` | Update Company | Bearer | Owner, Admin |
| `DELETE` | `/api/v1/companies/{id}` | Archive Company (soft delete) | Bearer | Owner, Admin |
| `GET` | `/api/v1/companies/{id}/properties` | List Company Properties (paginated) | Bearer + Session | Admin, Manager see all; Agent sees assigned |

#### Assignment API

| Method | Endpoint | Description | Auth | RBAC |
|--------|----------|-------------|------|------|
| `POST` | `/api/v1/assignments` | Create Agent-Property Assignment | Bearer + Session | Manager, Owner, Admin |
| `GET` | `/api/v1/assignments` | List Assignments (paginated + filtered) | Bearer + Session | Admin sees all; Manager sees company; Agent sees own |
| `GET` | `/api/v1/assignments/{id}` | Get Assignment details | Bearer + Session | Multi-tenancy enforced |
| `PATCH` | `/api/v1/assignments/{id}` | Update Assignment | Bearer + Session | Manager/Owner: all fields; Agent: notes only |
| `DELETE` | `/api/v1/assignments/{id}` | Deactivate Assignment (soft delete) | Bearer + Session | Manager, Owner, Admin |

> **Multi-tenancy (ADR-008):** Returns 404 (not 403) for inaccessible assignments  
> **Junction Model (ADR-014):** Uses `real.estate.agent.property.assignment` with metadata  
> **Immutable Fields:** `agent_id`, `property_id`, `company_id` — delete and recreate instead


#### Validation Features

- **CNPJ**: Brazilian business tax ID with check digit validation
- **CRECI**: Real estate license (optional) - format validation for SP, RJ, MG states
- **Email**: RFC 5322 compliant email validation using `email-validator`
- **Phone**: Brazilian phone format (10-11 digits)
- **Multi-tenancy**: 404 (not 403) for inaccessible resources
- **Last Owner Protection**: Cannot delete/unlink last active Owner from Company
- **Auto-linkage**: Company creator is automatically linked as Owner

#### Example Requests

```bash
# Get OAuth token
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "owner@test.com",
    "client_secret": "password"
  }' | jq -r '.access_token')

# Create Company
curl -X POST http://localhost:8069/api/v1/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Example Realty",
    "cnpj": "11222333000181",
    "email": "contact@example.com",
    "phone": "11999887766"
  }'

# Create Owner (independent)
curl -X POST http://localhost:8069/api/v1/owners \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@owner.com",
    "password": "secure123",
    "phone": "11888777666"
  }'

# Link Owner to Company
curl -X POST http://localhost:8069/api/v1/owners/10/companies \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"company_id": 5}'

# Unlink Owner from Company
curl -X DELETE http://localhost:8069/api/v1/owners/10/companies/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID"

# List Company Properties (with filters)
curl -X GET "http://localhost:8069/api/v1/companies/63/properties?page=1&page_size=20&property_status=available&for_sale=true&order_by=price" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID"

# Create Assignment (link agent to property)
curl -X POST http://localhost:8069/api/v1/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": 12,
    "property_id": 45,
    "company_id": 63,
    "responsibility_type": "primary",
    "commission_percentage": 6.5
  }'

# List Assignments (with filters)
curl -X GET "http://localhost:8069/api/v1/assignments?page=1&page_size=20&agent_id=12&active_only=true" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID"

# Get Assignment details
curl -X GET http://localhost:8069/api/v1/assignments/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID"

# Update Assignment
curl -X PATCH http://localhost:8069/api/v1/assignments/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "responsibility_type": "secondary",
    "commission_percentage": 4.0,
    "notes": "Assisting primary agent"
  }'

# Deactivate Assignment
curl -X DELETE http://localhost:8069/api/v1/assignments/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Openerp-Session-Id: $SESSION_ID"
```

See [specs/007-company-owner-management/quickstart.md](specs/007-company-owner-management/quickstart.md) for complete API documentation.

---