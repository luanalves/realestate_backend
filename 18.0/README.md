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

## References
- Official image: https://hub.docker.com/_/odoo
- Docker source: https://github.com/odoo/docker
- Documentation: https://github.com/docker-library/docs/tree/master/odoo


# Update module
```bash
docker exec odoo18 odoo -d realestate -u quicksol_estate --stop-after-init
```