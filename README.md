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

- **Odoo Web**: http://odoo.localhost
- **PostgreSQL**: localhost:5432
- **Database**: `realestate`
- **Usuário padrão**: `admin`
- **Senha padrão**: `admin`

> Os subdomínios `*.localhost` funcionam automaticamente em qualquer browser moderno sem editar `/etc/hosts`.

### Desenvolvimento

Os módulos customizados devem ser adicionados no diretório `18.0/extra-addons/`.

## 📚 Documentação

- Docker source: https://github.com/odoo/docker
- Odoo Documentation: https://www.odoo.com/documentation/18.0

## 🔌 Acessos aos Componentes Docker

> **Reverse Proxy:** O ambiente utiliza [Caddy](https://caddyserver.com/) como reverse proxy na porta `80`.
> Todos os subdomínios `*.localhost` resolvem automaticamente para `127.0.0.1` sem necessidade de configurar `/etc/hosts`.

### Caddy (Reverse Proxy)
- **Porta:** `80`
- **Configuração:** `18.0/Caddyfile`
- **Reload sem restart:** `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`

### Odoo Web Application
- **URL:** http://odoo.localhost
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
- **Management UI:** http://rabbitmq.localhost
- **Username:** `odoo`
- **Password:** `odoo_rabbitmq_secret_2026`
- **AMQP Port:** `5672` (mantido para conexões diretas de aplicação)
- **Purpose:** Gerenciamento de filas Celery

### Flower (Celery Monitoring)
- **URL:** http://flower.localhost
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
- **Web UI:** http://mailhog.localhost
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
- **URL:** http://odoo.localhost/api/docs
- **Descrição:** Interface gráfica interativa para explorar e testar os endpoints da API
- **Autenticação:** Não requer autenticação para visualizar (endpoints protegidos requerem token Bearer)

### OpenAPI Specification (JSON)
- **URL:** http://odoo.localhost/api/v1/openapi.json
- **Descrição:** Especificação OpenAPI 3.0 em formato JSON gerada dinamicamente
- **Uso:** Importar em ferramentas como Postman, Insomnia ou geradores de código

### Como usar a documentação Swagger

1. **Visualizar endpoints:** Acesse http://odoo.localhost/api/docs
2. **Obter token de autenticação:** Use o endpoint `/api/v1/oauth/token` com suas credenciais
3. **Autorizar:** Clique em "Authorize" no Swagger UI e insira o token no formato `Bearer {seu_token}`
4. **Testar endpoints:** Clique em "Try it out" em qualquer endpoint para testar diretamente

---
