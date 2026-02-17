# Odoo 18.0 + Postgres with Docker

This directory contains instructions to quickly launch an Odoo 18.0 environment with Postgres using Docker, without changing the repository.

## Step by step

### 1. Create Docker network (if needed)
```bash
docker network create odoo-net || true
```

### 2. Create persistent volumes
```bash
docker volume create odoo18-db
docker volume create odoo18-data
```

### 3. Start Postgres
```bash
docker run -d --name db --network odoo-net \
  -e POSTGRES_DB=postgres \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo \
  -v odoo18-db:/var/lib/postgresql/data \
  postgres:16-alpine
```

### 4. Start Odoo 18.0
```bash
docker run -d --name odoo18 --network odoo-net \
  -p 8069:8069 -p 8071:8071 -p 8072:8072 \
  -v odoo18-data:/var/lib/odoo \
  odoo:18.0
```

### 5. Access

#### Odoo Web Application
- **URL:** [http://localhost:8069](http://localhost:8069)
- **Username:** `admin`
- **Password:** `admin`

#### Database Access (DBeaver, pgAdmin, etc.)
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `realestate`
- **Username:** `odoo`
- **Password:** `odoo`

#### Redis Cache
- **Host:** `localhost`
- **Port:** `6379`
- **DB Index:** `1` (configured in odoo.conf)
- **No password required** (local development)
- **CLI Access:** `docker compose exec redis redis-cli`

#### RabbitMQ (Message Broker)
- **Management UI:** [http://localhost:15672](http://localhost:15672)
- **Username:** `odoo`
- **Password:** `odoo`
- **AMQP Port:** `5672` (for application connections)
- **Purpose:** Celery task queue management

#### Flower (Celery Monitoring)
- **URL:** [http://localhost:5555](http://localhost:5555)
- **Purpose:** Real-time monitoring of Celery workers and tasks
- **No authentication required** (development mode)

#### Celery Workers (Background Tasks)
- **Commission Worker:** Processes commission calculations
- **Notification Worker:** Handles email/SMS notifications  
- **Audit Worker:** Logs security and data changes
- **Status:** Check with `docker compose ps` or Flower UI

#### MailHog (Email Testing)
- **SMTP Server:** `mailhog:1025` (for Odoo configuration)
- **Web UI:** [http://localhost:8025](http://localhost:8025)
- **Purpose:** Captures all emails sent by Odoo without actually sending them
- **Usage:** Perfect for testing email flows (invites, password reset, notifications)
- **No authentication required** - zero configuration needed

**How to Configure in Odoo:**
1. Go to: Settings > Technical > Email > Outgoing Mail Servers
2. Click "New" and fill:
   - **Name:** MailHog Development
   - **SMTP Server:** mailhog
   - **SMTP Port:** 1025
   - **Connection Security:** None
   - **Username:** (leave empty)
   - **Password:** (leave empty)
3. Click "Test Connection" - should succeed instantly
4. Save and access [http://localhost:8025](http://localhost:8025) to view captured emails

**Note:** For production, use a real SMTP provider (Gmail, SendGrid, Amazon SES). See [ADR-023](../docs/adr/ADR-023-mailhog-email-testing-development.md) for details.

---

## Extras

### Mount local addons
```bash
mkdir -p ./extra-addons
# Start Odoo mounting the folder:
docker run -d --name odoo18 --network odoo-net \
  -p 8069:8069 -p 8071:8071 -p 8072:8072 \
  -v odoo18-data:/var/lib/odoo \
  -v $(pwd)/extra-addons:/mnt/extra-addons \
  odoo:18.0
```

### Use a custom configuration (odoo.conf)
```bash
# Mount your file at /etc/odoo/odoo.conf
# Example:
docker run -d --name odoo18 --network odoo-net \
  -p 8069:8069 \
  -v odoo18-data:/var/lib/odoo \
  -v $(pwd)/odoo.conf:/etc/odoo/odoo.conf:ro \
  odoo:18.0
```

---

## Useful commands
- View Odoo logs:
```bash
docker logs -f odoo18
```
- Stop services:
```bash
docker stop odoo18 db
```
- Start again:
```bash
docker start db odoo18
```
- Remove containers (keep data):
```bash
docker rm odoo18 db
```
- Full reset (delete volumes):
```bash
docker rm -f odoo18 db
docker volume rm odoo18-data odoo18-db
```

---

## Redis Cache Integration

This setup includes **Redis 7** for session storage and caching, using **Odoo's native Redis support**.

### What Redis is Used For

- **HTTP Session Storage**: Stores user sessions (faster than database)
- **ORM Cache**: Caches database queries and model data
- **Asset Cache**: Caches static assets and compiled resources
- **Message Bus**: Improves longpolling performance

### Redis Configuration

Redis is configured in `odoo.conf` with:
```ini
enable_redis = True
redis_host = redis
redis_port = 6379
redis_dbindex = 1
```

### Monitoring Redis

Check Redis status:
```bash
docker compose exec redis redis-cli ping
# Expected output: PONG
```

Monitor Redis operations:
```bash
docker compose exec redis redis-cli MONITOR
```

View Redis statistics:
```bash
docker compose exec redis redis-cli INFO stats
```

Check memory usage:
```bash
docker compose exec redis redis-cli INFO memory
```

### Redis Data Persistence

- Data is persisted in the `odoo18-redis` Docker volume
- Uses AOF (Append Only File) for durability
- Memory limit: 256MB with LRU eviction policy

---

## 📖 API Documentation (Swagger/OpenAPI)

### Swagger UI (Interactive Interface)
- **URL:** [http://localhost:8069/api/docs](http://localhost:8069/api/docs)
- **Description:** Interactive graphical interface to explore and test API endpoints
- **Authentication:** No authentication required to view (protected endpoints require Bearer token)

### OpenAPI Specification (JSON)
- **URL:** [http://localhost:8069/api/v1/openapi.json](http://localhost:8069/api/v1/openapi.json)
- **Description:** Dynamically generated OpenAPI 3.0 specification in JSON format
- **Usage:** Import into tools like Postman, Insomnia, or code generators

### How to use Swagger documentation

1. **View endpoints:** Access [http://localhost:8069/api/docs](http://localhost:8069/api/docs)
2. **Get authentication token:** Use the `/api/v1/oauth/token` endpoint with your credentials
3. **Authorize:** Click "Authorize" in Swagger UI and enter the token in format `Bearer {your_token}`
4. **Test endpoints:** Click "Try it out" on any endpoint to test directly

---

## Code Quality and Linting

This project uses **Flake8** and other Python linting tools to ensure code quality and adherence to PEP 8 standards.

### Available Linting Tools

The following tools are installed in the Docker container:
- **Flake8** (v7.1.1) - Style guide enforcement
- **Black** (v24.10.0) - Code formatter
- **isort** (v5.13.2) - Import sorting
- **Pylint** (v3.3.1) - Advanced static analysis
- **mypy** (v1.13.0) - Type checking

### Running Flake8

#### From the Host Machine

Check all custom addons:
```bash
docker compose exec odoo flake8 /mnt/extra-addons
```

Check a specific addon:
```bash
docker compose exec odoo flake8 /mnt/extra-addons/quicksol_estate
```

Using the lint script:
```bash
# Check all addons
docker compose exec odoo bash /mnt/extra-addons/../lint.sh

# Check specific addon
docker compose exec odoo bash /mnt/extra-addons/../lint.sh quicksol_estate
```

#### Inside the Container

```bash
# Enter the container
docker compose exec odoo bash

# Run flake8
flake8 /mnt/extra-addons

# Or use the lint script
./lint.sh
./lint.sh quicksol_estate
```

### Configuration

Flake8 configuration is stored in `.flake8` with the following key settings:
- Maximum line length: 88 characters (Black compatible)
- Maximum complexity: 10
- Excludes: migrations, static files, i18n, tests, etc.
- Compatible with Black formatter

### Pre-commit Checklist

Before committing code, ensure:
1. Run `black .` to format code
2. Run `isort .` to sort imports
3. Run `flake8 .` to check style compliance
4. Fix any reported issues

---

## References
- Official image: https://hub.docker.com/_/odoo
- Docker source: https://github.com/odoo/docker
- Documentation: https://github.com/docker-library/docs/tree/master/odoo


# Update module
```bash
docker exec odoo18 odoo -d realestate -u quicksol_estate --stop-after-init
```