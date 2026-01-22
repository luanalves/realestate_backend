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