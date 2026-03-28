---
name: production-server-ssh
description: "**TRIGGER KEYWORDS**: ssh, servidor, server, produção, production, deploy, container, docker, logs, restart, grafana, tempo, odoo, VPS, remoto, remote, acesso, conectar, connect. **COVERS**: SSH access to the production VPS, Docker container management, log inspection, service restart, Grafana/Tempo validation. **USE WHEN**: Diagnosing production issues, validating deployments, inspecting container state, restarting services."
---

# Production Server SSH - Torque Backoffice

## Connection

```bash
ssh root@148.230.76.211
```

- **User**: `root`
- **Host**: `148.230.76.211`
- **Auth**: SSH key (no password)

## Project Location on Server

```bash
# Dokploy manages the stack — files are typically at:
ls /etc/dokploy/compose/  # list deployed stacks
# or search:
find / -name "docker-compose-production.yml" 2>/dev/null
```

## Key Commands

### Check container status
```bash
ssh root@148.230.76.211 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'"
```

### View Grafana logs
```bash
ssh root@148.230.76.211 "docker logs \$(docker ps -qf name=grafana) --tail 50"
```

### View Odoo logs (last 100 lines)
```bash
ssh root@148.230.76.211 "docker logs \$(docker ps -qf name=odoo) --tail 100"
```

### Restart Grafana
```bash
ssh root@148.230.76.211 "docker restart \$(docker ps -qf name=grafana)"
```

### Inspect mounted dashboard files inside Grafana container
```bash
ssh root@148.230.76.211 "docker exec \$(docker ps -qf name=grafana) ls /var/lib/grafana/dashboards/"
ssh root@148.230.76.211 "docker exec \$(docker ps -qf name=grafana) cat /var/lib/grafana/dashboards/distributed-tracing.json | python3 -c \"import json,sys; d=json.load(sys.stdin); print('templating:', [t['name'] for t in d.get('templating',{}).get('list',[])])\""
```

### Check Tempo health
```bash
ssh root@148.230.76.211 "docker exec \$(docker ps -qf name=tempo) wget -qO- http://localhost:3200/ready"
```

### Check OTEL env in Odoo container
```bash
ssh root@148.230.76.211 "docker exec \$(docker ps -qf name=odoo) env | grep OTEL"
```

### Reload provisioned dashboards (Grafana API)
```bash
ssh root@148.230.76.211 "docker exec \$(docker ps -qf name=grafana) wget -qO- --header='Content-Type: application/json' http://admin:admin@localhost:3000/api/admin/provisioning/dashboards/reload"
```

## URLs

| Service | URL |
|---------|-----|
| Odoo | https://torque-backoffice.thedevkitchen.com.br |
| Grafana | https://grafana.torque-backoffice.thedevkitchen.com.br |
| OpenAPI | https://torque-backoffice.thedevkitchen.com.br/api/v1/openapi.json |

## Grafana Admin Credentials (default)

- **User**: `admin`
- **Password**: set via `GRAFANA_ADMIN_PASSWORD` env var (default: `admin`)

## Common Diagnostics Workflow

1. Check containers are running: `docker ps`
2. Check Grafana loaded dashboards: inspect `/var/lib/grafana/dashboards/`
3. Verify OTEL env in Odoo: `env | grep OTEL`
4. Check Tempo is receiving traces: query `http://tempo:3200/api/search`
5. Reload provisioned dashboards via Grafana admin API
