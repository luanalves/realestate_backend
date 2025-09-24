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
```

### Development Notes

- All Docker operations should be performed from the `18.0` directory
- The `extra-addons` folder is mounted for custom module development
- Database data persists in Docker volumes
- External database access is available via localhost:5432

When providing assistance, assume the user is working within the 18.0 directory context unless otherwise specified.
