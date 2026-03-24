# 🚀 Production Setup - Security & Best Practices

**Versão:** 1.0  
**Data:** 2026-03-24  
**Ambiente:** Dokploy + Docker Swarm  

## 📋 Índice

1. [Checklist Geral](#checklist-geral)
2. [PostgreSQL](#1-postgresql)
3. [Redis](#2-redis)
4. [RabbitMQ](#3-rabbitmq)
5. [Odoo](#4-odoo)
6. [Celery Worker](#5-celery-worker)
7. [Traefik / Reverse Proxy](#6-traefik--reverse-proxy)
8. [Variáveis de Ambiente](#variáveis-de-ambiente)
9. [Monitoramento](#monitoramento)
10. [Backup Strategy](#backup-strategy)

---

## ✅ Checklist Geral

### Antes do Deploy
- [ ] Todas as senhas são **fortes** (mínimo 32 caracteres aleatórios)
- [ ] Nenhuma credencial está **hardcoded** no código
- [ ] `.env` está no `.gitignore`
- [ ] `.env.example` documenta todas as variáveis (sem valores reais)
- [ ] Secrets estão configurados no Dokploy UI
- [ ] "Create Environment File" está **habilitado** no Dokploy
- [ ] SSL/TLS está configurado (certificado válido)
- [ ] Firewall está configurado (só portas necessárias expostas)

### Após Deploy
- [ ] Testar acesso aos serviços
- [ ] Verificar logs de todos os containers
- [ ] Confirmar que credenciais padrão foram alteradas
- [ ] Testar backup e restore
- [ ] Configurar monitoramento/alertas
- [ ] Documentar credenciais em gerenciador de senhas (1Password, Bitwarden, etc.)

---

## 1. PostgreSQL

### 🔒 Boas Práticas de Segurança

#### ❌ **NUNCA em Produção:**
```yaml
POSTGRES_USER=postgres          # ❌ Usuário padrão
POSTGRES_PASSWORD=postgres      # ❌ Senha padrão
POSTGRES_PASSWORD=admin         # ❌ Senha fraca
POSTGRES_PASSWORD=123456        # ❌ Senha fraca
```

#### ✅ **Configuração Segura:**
```yaml
# Variáveis de Ambiente
POSTGRES_DB=odoo_production                    # Nome específico do ambiente
POSTGRES_USER=odoo_prod_user                   # Usuário customizado
POSTGRES_PASSWORD=<GERAR_SENHA_FORTE_32_CHARS> # Senha forte aleatória
POSTGRES_HOST_AUTH_METHOD=scram-sha-256        # Autenticação forte (não md5)
```

#### 📝 Configurações Adicionais

**postgresql.conf** (via volume mount ou POSTGRES_INITDB_ARGS):
```ini
# Connections
max_connections = 200
shared_buffers = 2GB              # 25% da RAM disponível
effective_cache_size = 6GB        # 75% da RAM disponível
work_mem = 10MB
maintenance_work_mem = 512MB

# Security
ssl = on                          # Forçar SSL/TLS
password_encryption = scram-sha-256

# Logging (importante para auditoria)
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_statement = 'ddl'             # Log DDL statements
log_min_duration_statement = 1000 # Log queries > 1s

# Performance
checkpoint_completion_target = 0.9
wal_buffers = 16MB
random_page_cost = 1.1            # Para SSD

# Autovacuum (importante para Odoo)
autovacuum = on
autovacuum_analyze_scale_factor = 0.05
```

**pg_hba.conf** (controle de acesso):
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all            postgres                                peer
host    all            all             127.0.0.1/32            scram-sha-256
host    all            all             ::1/128                 scram-sha-256
host    odoo_production odoo_prod_user  172.16.0.0/12          scram-sha-256  # Rede Docker
```

#### 🔐 Hardening Checklist
- [ ] Usuário customizado (não `postgres`)
- [ ] Senha forte (32+ caracteres)
- [ ] Autenticação `scram-sha-256` (não `md5` ou `trust`)
- [ ] SSL/TLS habilitado
- [ ] Acesso restrito por IP (rede Docker interna)
- [ ] Porta 5432 **NÃO** exposta publicamente (só dentro da rede Docker)
- [ ] Logs habilitados

#### 🎯 Comando para Gerar Senha Forte
```bash
# Gerar senha de 32 caracteres
openssl rand -base64 32
# ou
pwgen -s 32 1
```

---

## 2. Redis

### 🔒 Boas Práticas de Segurança

#### ❌ **NUNCA em Produção:**
```yaml
# ❌ Redis sem senha (acesso aberto)
command: redis-server

# ❌ Redis com senha fraca
command: redis-server --requirepass admin
```

#### ✅ **Configuração Segura:**
```yaml
# Variáveis de Ambiente
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<GERAR_SENHA_FORTE_32_CHARS>
REDIS_DB=1                        # DB index para Odoo sessions
REDIS_MAXMEMORY=256mb             # Limite de memória
REDIS_MAXMEMORY_POLICY=allkeys-lru # Eviction policy

# Command
command: >
  redis-server
  --requirepass ${REDIS_PASSWORD}
  --appendonly yes
  --maxmemory 256mb
  --maxmemory-policy allkeys-lru
  --bind 0.0.0.0                  # Bind em rede Docker (não expor para fora)
  --protected-mode yes
  --timeout 300
  --tcp-keepalive 60
```

#### 📝 Configurações Adicionais

**redis.conf** (via volume mount):
```ini
# Security
requirepass <SENHA_FORTE>
protected-mode yes
bind 0.0.0.0                      # Só acessível dentro da rede Docker

# Performance
maxmemory 256mb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 60

# Persistence
appendonly yes
appendfsync everysec
save 900 1                        # Snapshot a cada 15min se houver 1 mudança
save 300 10                       # Snapshot a cada 5min se houver 10 mudanças

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security - Renomear comandos perigosos
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
rename-command SHUTDOWN ""
rename-command DEBUG ""
```

#### 🔐 Hardening Checklist
- [ ] `requirepass` configurado com senha forte
- [ ] `protected-mode yes`
- [ ] Comandos perigosos renomeados/desabilitados (FLUSHDB, FLUSHALL, CONFIG)
- [ ] Porta 6379 **NÃO** exposta publicamente
- [ ] `maxmemory` configurado (evitar OOM)
- [ ] Persistence habilitada (appendonly + save)
- [ ] Timeout configurado (fechar conexões idle)

---

## 3. RabbitMQ

### 🔒 Boas Práticas de Segurança

#### ❌ **NUNCA em Produção:**
```yaml
RABBITMQ_DEFAULT_USER=guest       # ❌ Usuário padrão
RABBITMQ_DEFAULT_PASS=guest       # ❌ Senha padrão
```

#### ✅ **Configuração Segura:**
```yaml
# Variáveis de Ambiente
RABBITMQ_DEFAULT_USER=odoo_mq_user
RABBITMQ_DEFAULT_PASS=<GERAR_SENHA_FORTE_32_CHARS>
RABBITMQ_DEFAULT_VHOST=/odoo_production
RABBITMQ_NODENAME=rabbit@rabbitmq

# Management UI (deve estar atrás de autenticação)
RABBITMQ_MANAGEMENT_ALLOW_WEB_ACCESS=true
```

#### 📝 Configurações Adicionais

**rabbitmq.conf**:
```ini
# Security
loopback_users.guest = false      # Desabilitar usuário guest
default_vhost = /odoo_production
default_user = odoo_mq_user
default_pass = <SENHA_FORTE>

# Performance
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 2GB
heartbeat = 60

# Management Plugin
management.tcp.port = 15672
management.ssl.port = 15671
management.load_definitions = /etc/rabbitmq/definitions.json

# Clustering (se necessário)
# cluster_formation.peer_discovery_backend = classic_config
```

**definitions.json** (usuários e permissões):
```json
{
  "users": [
    {
      "name": "odoo_mq_user",
      "password_hash": "<HASH_BCRYPT>",
      "tags": "administrator"
    }
  ],
  "vhosts": [
    {
      "name": "/odoo_production"
    }
  ],
  "permissions": [
    {
      "user": "odoo_mq_user",
      "vhost": "/odoo_production",
      "configure": ".*",
      "write": ".*",
      "read": ".*"
    }
  ],
  "policies": [
    {
      "vhost": "/odoo_production",
      "name": "ha-all",
      "pattern": ".*",
      "definition": {
        "ha-mode": "all"
      }
    }
  ]
}
```

#### 🔐 Hardening Checklist
- [ ] Usuário padrão `guest` desabilitado
- [ ] Usuário customizado com senha forte
- [ ] VHost customizado (não `/`)
- [ ] Management UI protegido (autenticação + HTTPS)
- [ ] Porta 5672 (AMQP) **NÃO** exposta publicamente
- [ ] Porta 15672 (Management) protegida por reverse proxy ou VPN
- [ ] Limites de memória e disco configurados
- [ ] TLS/SSL habilitado para conexões

#### 🔑 Gerar Hash de Senha para RabbitMQ
```bash
# Instalar rabbitmqctl localmente ou usar container
docker run -it --rm rabbitmq:3-management rabbitmqctl hash_password "SUA_SENHA_FORTE_AQUI"
```

---

## 4. Odoo

### 🔒 Boas Práticas de Segurança

#### ❌ **NUNCA em Produção:**
```yaml
# ❌ Credenciais padrão
admin_passwd = admin              # Senha do master password
# Sem admin_passwd = acesso TOTAL ao banco via interface

# ❌ Database management habilitado
list_db = True                    # Lista todos os databases
db_maxconn_gevent = unlimited     # Sem limite de conexões
```

#### ✅ **Configuração Segura:**

**Variáveis de Ambiente Críticas:**
```yaml
# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=odoo_production
DB_USER=odoo_prod_user
DB_PASSWORD=<SENHA_POSTGRES>
DB_MAXCONN=64
DB_TEMPLATE=template0

# Master Password (CRÍTICO!)
ODOO_ADMIN_PASSWD=<GERAR_SENHA_FORTE_64_CHARS>  # Master password para gerenciar DBs

# Database Management (DESABILITAR)
ODOO_LIST_DB=False                               # Não listar databases
ODOO_DB_FILTER=^odoo_production$                 # Aceitar só este DB

# Security
ODOO_PROXY_MODE=True                             # Atrás de reverse proxy
ODOO_LIMIT_TIME_CPU=600                          # Timeout CPU (10 min)
ODOO_LIMIT_TIME_REAL=1200                        # Timeout Real (20 min)
ODOO_LIMIT_REQUEST=8192                          # Tamanho máximo request
ODOO_LIMIT_MEMORY_HARD=2684354560                # 2.5GB limite hard
ODOO_LIMIT_MEMORY_SOFT=2147483648                # 2GB limite soft

# Workers (para produção)
ODOO_WORKERS=4                                   # (CPUs * 2) + 1
ODOO_MAX_CRON_THREADS=2
ODOO_DB_MAXCONN=64

# Redis (Cache & Sessions)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<SENHA_REDIS>
REDIS_DBINDEX=1

# JWT (Authentication)
JWT_SECRET=<GERAR_SECRET_FORTE_64_CHARS>
JWT_ISSUER=https://seudominio.com
JWT_EXPIRATION=3600                              # 1 hora

# Logs
ODOO_LOG_LEVEL=info                              # warn em produção
ODOO_LOG_HANDLER=:INFO,werkzeug:WARN            # Reduzir verbosidade

# Data Dir
ODOO_DATA_DIR=/var/lib/odoo                      # Deve estar em volume persistente
```

#### 📝 odoo.conf (Completo)

```ini
[options]
# Database
db_host = db
db_port = 5432
db_user = odoo_prod_user
db_password = <SENHA_POSTGRES>
db_name = odoo_production
db_maxconn = 64
db_template = template0

# Master Password (CRÍTICO - protege acesso ao database manager)
admin_passwd = <SENHA_MASTER_64_CHARS>

# Database Management
list_db = False                   # Não mostrar lista de DBs
dbfilter = ^odoo_production$      # Aceitar só este DB

# Server
xmlrpc_interface = 0.0.0.0
xmlrpc_port = 8069
longpolling_port = 8072
proxy_mode = True                 # Atrás de reverse proxy (Traefik)

# Workers (Produção)
workers = 4                       # (2 CPUs * 2) + 1 = 5 (usar 4 para folga)
max_cron_threads = 2
limit_time_cpu = 600              # 10 min
limit_time_real = 1200            # 20 min
limit_request = 8192
limit_memory_hard = 2684354560    # 2.5GB
limit_memory_soft = 2147483648    # 2GB

# Logs
logfile = False                   # Log para stdout (Docker)
log_level = info                  # warn em prod
log_handler = :INFO,werkzeug:WARN
log_db = False                    # Não logar no database

# Data Directory
data_dir = /var/lib/odoo
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons

# Security
server_wide_modules = base,web
unaccent = True

# Performance - Redis Cache & Sessions
enable_redis = True
redis_host = redis
redis_port = 6379
redis_dbindex = 1
redis_pass = <SENHA_REDIS>

# Email (se usar SMTP externo)
# email_from = noreply@seudominio.com
# smtp_server = smtp.gmail.com
# smtp_port = 587
# smtp_ssl = False
# smtp_user = seu-email@gmail.com
# smtp_password = <SENHA_APP>
```

#### 🔐 Hardening Checklist - Odoo

- [ ] **Master Password** (`admin_passwd`) configurado e **FORTE** (64+ chars)
- [ ] `list_db = False` (não mostrar databases)
- [ ] `dbfilter` configurado (aceitar só DB específico)
- [ ] `proxy_mode = True` (atrás de Traefik)
- [ ] Workers configurados (`workers > 0` para produção)
- [ ] Limites de CPU, memória e tempo configurados
- [ ] Redis habilitado para sessions e cache
- [ ] Data directory em volume persistente
- [ ] Logs configurados (stdout para Docker)
- [ ] Porta 8069 **NÃO** exposta publicamente (só via Traefik)
- [ ] Longpolling (8072) **NÃO** exposto publicamente
- [ ] Usuário inicial `admin` teve senha alterada no primeiro acesso

#### ⚠️ **CRÍTICO: Alterar Senha do Usuário Admin**

**Método 1: Via Interface (primeiro acesso)**
```
1. Acessar http://seudominio.com
2. Login: admin / admin
3. Ir em Settings → Users → Administrator
4. Change Password
5. Nova senha FORTE (32+ caracteres)
```

**Método 2: Via Script Python (antes do primeiro acesso)**

Criar `scripts/change_admin_password.py`:
```python
#!/usr/bin/env python3
import os
import xmlrpc.client

ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.getenv('DB_NAME', 'odoo_production')
ADMIN_PASSWORD = os.getenv('ODOO_INITIAL_ADMIN_PASSWORD', 'admin')
NEW_PASSWORD = os.getenv('ODOO_NEW_ADMIN_PASSWORD')

if not NEW_PASSWORD:
    raise ValueError("ODOO_NEW_ADMIN_PASSWORD não definida!")

common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
uid = common.authenticate(ODOO_DB, 'admin', ADMIN_PASSWORD, {})

if uid:
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
    models.execute_kw(
        ODOO_DB, uid, ADMIN_PASSWORD,
        'res.users', 'write',
        [[uid], {'password': NEW_PASSWORD}]
    )
    print("✅ Senha do admin alterada com sucesso!")
else:
    print("❌ Falha na autenticação!")
```

**Método 3: Forçar via entrypoint.sh**

Modificar `entrypoint.sh`:
```bash
#!/bin/bash
set -e

# Esperar PostgreSQL
python3 /usr/local/bin/wait-for-psql.py

# Se é primeira inicialização E tem senha customizada
if [ ! -f /var/lib/odoo/.initialized ] && [ -n "$ODOO_NEW_ADMIN_PASSWORD" ]; then
    echo "🔒 Primeira inicialização: configurando senha do admin..."
    
    # Iniciar Odoo em background
    odoo --stop-after-init --database=$DB_NAME --init=base --without-demo=all &
    ODOO_PID=$!
    
    # Esperar inicialização
    sleep 30
    
    # Alterar senha via SQL (mais seguro)
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
        "UPDATE res_users SET password='$ODOO_NEW_ADMIN_PASSWORD' WHERE login='admin';"
    
    # Marcar como inicializado
    touch /var/lib/odoo/.initialized
    
    echo "✅ Senha do admin alterada!"
    
    # Matar processo background
    kill $ODOO_PID
    wait $ODOO_PID
fi

# Iniciar Odoo normalmente
exec odoo "$@"
```

---

## 5. Celery Worker

### 🔒 Boas Práticas de Segurança

#### ✅ **Configuração Segura:**
```yaml
# Variáveis de Ambiente
CELERY_BROKER_URL=amqp://odoo_mq_user:<SENHA_RABBITMQ>@rabbitmq:5672//odoo_production
CELERY_RESULT_BACKEND=redis://:SENHA_REDIS>@redis:6379/2
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=json,application/json
CELERY_TIMEZONE=America/Sao_Paulo
CELERY_ENABLE_UTC=True

# Workers
CELERY_WORKER_CONCURRENCY=4       # Número de workers paralelos
CELERY_WORKER_PREFETCH_MULTIPLIER=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000  # Reiniciar worker após N tasks
CELERY_WORKER_LOG_LEVEL=INFO

# Timeouts
CELERY_TASK_TIME_LIMIT=3600        # Hard timeout (1 hora)
CELERY_TASK_SOFT_TIME_LIMIT=3300   # Soft timeout (55 min)
```

#### 🔐 Hardening Checklist
- [ ] Broker URL com credenciais corretas (não guest/guest)
- [ ] Result backend com senha Redis
- [ ] Serializer definido (JSON é mais seguro que pickle)
- [ ] Timeouts configurados (evitar tasks infinitas)
- [ ] Max tasks per child (evitar memory leaks)
- [ ] Logs adequados
- [ ] Não expor portas publicamente

---

## 6. Traefik / Reverse Proxy

### 🔒 Boas Práticas de Segurança

#### ✅ **Configuração Mínima Segura:**

**docker-compose.yml** (labels no serviço Odoo):
```yaml
odoo:
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.odoo.rule=Host(`seudominio.com`)"
    - "traefik.http.routers.odoo.entrypoints=websecure"
    - "traefik.http.routers.odoo.tls=true"
    - "traefik.http.routers.odoo.tls.certresolver=letsencrypt"
    - "traefik.http.services.odoo.loadbalancer.server.port=8069"
    
    # Security Headers
    - "traefik.http.middlewares.security-headers.headers.stsSeconds=31536000"
    - "traefik.http.middlewares.security-headers.headers.stsIncludeSubdomains=true"
    - "traefik.http.middlewares.security-headers.headers.stsPreload=true"
    - "traefik.http.middlewares.security-headers.headers.forceSTSHeader=true"
    - "traefik.http.middlewares.security-headers.headers.contentTypeNosniff=true"
    - "traefik.http.middlewares.security-headers.headers.browserXssFilter=true"
    - "traefik.http.middlewares.security-headers.headers.frameDeny=true"
    
    # Rate Limiting
    - "traefik.http.middlewares.rate-limit.ratelimit.average=100"
    - "traefik.http.middlewares.rate-limit.ratelimit.burst=50"
    
    # Apply middlewares
    - "traefik.http.routers.odoo.middlewares=security-headers,rate-limit"
```

#### 🔐 Hardening Checklist - Traefik
- [ ] HTTPS forçado (redirect HTTP → HTTPS)
- [ ] Certificado SSL válido (Let's Encrypt)
- [ ] HSTS habilitado
- [ ] Security headers configurados
- [ ] Rate limiting configurado
- [ ] Logs de acesso habilitados
- [ ] Dashboard protegido ou desabilitado
- [ ] TLS 1.2+ apenas (desabilitar TLS 1.0 e 1.1)

---

## 📝 Variáveis de Ambiente

### Template Completo para Dokploy UI

**COPIAR E COLAR no Dokploy → Environment Settings:**

```bash
# =============================================================================
# ENVIRONMENT: PRODUCTION
# Created: 2026-03-24
# =============================================================================

# -----------------------------------------------------------------------------
# PostgreSQL
# -----------------------------------------------------------------------------
POSTGRES_DB=odoo_production
POSTGRES_USER=odoo_prod_user
POSTGRES_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS
DB_HOST=db
DB_PORT=5432
DB_NAME=odoo_production
DB_USER=odoo_prod_user
DB_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS
REDIS_DBINDEX=1

# -----------------------------------------------------------------------------
# RabbitMQ
# -----------------------------------------------------------------------------
RABBITMQ_USER=odoo_mq_user
RABBITMQ_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS
RABBIT MQ_DEFAULT_VHOST=/odoo_production
CELERY_BROKER_URL=amqp://odoo_mq_user:TROCAR_POR_SENHA_FORTE_32_CHARS@rabbitmq:5672//odoo_production
CELERY_RESULT_BACKEND=redis://:TROCAR_POR_SENHA_FORTE_32_CHARS@redis:6379/2

# -----------------------------------------------------------------------------
# Odoo Security
# -----------------------------------------------------------------------------
ODOO_ADMIN_PASSWD=TROCAR_POR_SENHA_FORTE_64_CHARS     # Master password
ODOO_NEW_ADMIN_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS  # Senha do usuário admin
ODOO_LIST_DB=False
ODOO_DB_FILTER=^odoo_production$

# -----------------------------------------------------------------------------
# Odoo Configuration
# -----------------------------------------------------------------------------
ODOO_WORKERS=4
ODOO_MAX_CRON_THREADS=2
ODOO_PROXY_MODE=True
ODOO_LOG_LEVEL=info

# -----------------------------------------------------------------------------
# JWT Authentication
# -----------------------------------------------------------------------------
JWT_SECRET=TROCAR_POR_SECRET_FORTE_64_CHARS
JWT_ISSUER=https://seudominio.com
JWT_EXPIRATION=3600

# -----------------------------------------------------------------------------
# Aplicação
# -----------------------------------------------------------------------------
ENVIRONMENT=production
TZ=America/Sao_Paulo
```

### 🔑 Gerar Todas as Senhas de Uma Vez

```bash
#!/bin/bash
echo "# Senhas Geradas - $(date)"
echo ""
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo "RABBITMQ_PASSWORD=$(openssl rand -base64 32)"
echo "ODOO_ADMIN_PASSWD=$(openssl rand -base64 48)"
echo "ODOO_NEW_ADMIN_PASSWORD=$(openssl rand -base64 32)"
echo "JWT_SECRET=$(openssl rand -base64 48)"
```

---

## 📊 Observabilidade & Monitoramento

### 🎯 Stack Recomendada: Grafana Observability Stack

**Componentes:**
- **Grafana** - Dashboards e visualização
- **Prometheus** - Métricas (CPU, memória, requests/s)
- **Loki** - Logs agregados
- **Tempo** - Distributed tracing (APM)
- **Node Exporter** - Métricas do host
- **cAdvisor** - Métricas dos containers

**Alternativa All-in-One:** SigNoz (OpenTelemetry-native, mais simples)

---

### 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     Grafana (Port 3000)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Prometheus  │  │     Loki     │  │    Tempo     │     │
│  │  (métricas)  │  │    (logs)    │  │   (traces)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
         ▲                  ▲                  ▲
         │                  │                  │
    ┌────┴─────┬───────────┴┬──────────┬──────┴────┐
    │          │            │          │           │
┌───┴──┐  ┌───┴───┐  ┌────┴────┐  ┌──┴───┐  ┌────┴─────┐
│ Odoo │  │ Redis │  │PostgreSQL│  │ MQ   │  │  Celery  │
└──────┘  └───────┘  └─────────┘  └──────┘  └──────────┘
```

---

### 📦 Docker Compose - Observabilidade

**Criar arquivo separado:** `18.0/docker-compose.observability.yml`

```yaml
version: '3.8'

services:
  # ============================================================================
  # PROMETHEUS - Coleta de Métricas
  # ============================================================================
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    networks:
      - odoo-net

  # ============================================================================
  # NODE EXPORTER - Métricas do Host
  # ============================================================================
  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    ports:
      - "9100:9100"
    networks:
      - odoo-net

  # ============================================================================
  # cADVISOR - Métricas dos Containers
  # ============================================================================
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "8080:8080"
    networks:
      - odoo-net

  # ============================================================================
  # LOKI - Agregação de Logs
  # ============================================================================
  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: unless-stopped
    volumes:
      - ./observability/loki-config.yml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    ports:
      - "3100:3100"
    networks:
      - odoo-net

  # ============================================================================
  # PROMTAIL - Coleta de Logs (Docker)
  # ============================================================================
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    restart: unless-stopped
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./observability/promtail-config.yml:/etc/promtail/config.yml:ro
    command: -config.file=/etc/promtail/config.yml
    networks:
      - odoo-net

  # ============================================================================
  # TEMPO - Distributed Tracing (APM)
  # ============================================================================
  tempo:
    image: grafana/tempo:latest
    container_name: tempo
    restart: unless-stopped
    volumes:
      - ./observability/tempo-config.yml:/etc/tempo/tempo.yaml:ro
      - tempo-data:/var/tempo
    command: -config.file=/etc/tempo/tempo.yaml
    ports:
      - "3200:3200"   # Tempo HTTP
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    networks:
      - odoo-net

  # ============================================================================
  # GRAFANA - Dashboards & Visualização
  # ============================================================================
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-TROCAR_SENHA_FORTE}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.seudominio.com
      - GF_INSTALL_PLUGINS=redis-datasource,grafana-piechart-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./observability/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
      - loki
      - tempo
    networks:
      - odoo-net

  # ============================================================================
  # POSTGRES EXPORTER - Métricas do PostgreSQL
  # ============================================================================
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: postgres-exporter
    restart: unless-stopped
    environment:
      DATA_SOURCE_NAME: "postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}?sslmode=disable"
    ports:
      - "9187:9187"
    networks:
      - odoo-net

  # ============================================================================
  # REDIS EXPORTER - Métricas do Redis
  # ============================================================================
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: redis-exporter
    restart: unless-stopped
    environment:
      REDIS_ADDR: redis:6379
      REDIS_PASSWORD: ${REDIS_PASSWORD}
    ports:
      - "9121:9121"
    networks:
      - odoo-net

volumes:
  prometheus-data:
  loki-data:
  tempo-data:
  grafana-data:

networks:
  odoo-net:
    external: true
```

---

### ⚙️ Configurações

#### 1. Prometheus (`observability/prometheus.yml`)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'odoo-production'
    environment: 'production'

# Alertmanager (opcional)
# alerting:
#   alertmanagers:
#     - static_configs:
#         - targets: ['alertmanager:9093']

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (métricas do host)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # cAdvisor (métricas dos containers)
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # PostgreSQL Exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis Exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Odoo (se expuser métricas - ver abaixo)
  # - job_name: 'odoo'
  #   static_configs:
  #     - targets: ['odoo:8069']
  #   metrics_path: '/metrics'
```

#### 2. Loki (`observability/loki-config.yml`)

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h
  retention_period: 744h  # 31 dias

chunk_store_config:
  max_look_back_period: 744h

table_manager:
  retention_deletes_enabled: true
  retention_period: 744h
```

#### 3. Promtail (`observability/promtail-config.yml`)

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Logs dos containers Docker
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'
    pipeline_stages:
      - docker: {}
      - json:
          expressions:
            level: level
            message: message
      - labels:
          level:
```

#### 4. Tempo (`observability/tempo-config.yml`)

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

ingester:
  trace_idle_period: 10s
  max_block_bytes: 1_000_000
  max_block_duration: 5m

compactor:
  compaction:
    compaction_window: 1h
    max_block_bytes: 100_000_000
    block_retention: 744h  # 31 dias
    compacted_block_retention: 1h

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal
    pool:
      max_workers: 100
      queue_depth: 10000
```

#### 5. Grafana Data Sources (`observability/grafana/provisioning/datasources/datasources.yml`)

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    editable: false
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['trace_id']
      nodeGraph:
        enabled: true
```

---

### 📈 Dashboards Essenciais

**Criar em:** `observability/grafana/dashboards/`

1. **`odoo-overview.json`** - Overview geral do sistema
2. **`postgres-performance.json`** - Database performance
3. **`redis-monitoring.json`** - Redis cache hit rate
4. **`rabbitmq-queues.json`** - Filas do RabbitMQ
5. **`celery-tasks.json`** - Tasks do Celery
6. **`container-resources.json`** - CPU/RAM dos containers

**Dashboards prontos para importar:**
- Node Exporter: ID 1860
- PostgreSQL: ID 9628
- Redis: ID 11835
- Docker Containers: ID 193
- Traefik: ID 11462

---

### 🔧 Instrumentação do Odoo para APM

**✅ MÓDULO PRONTO:** O módulo `thedevkitchen_observability` já está implementado e disponível em `extra-addons/thedevkitchen_observability/`

**Características:**
- OpenTelemetry SDK 1.22+ integrado
- Decorador `@trace_http_request` para controllers
- Injeção automática de trace_id/span_id nos logs
- Exportador OTLP (gRPC) para Tempo configurado
- W3C Trace Context propagation
- Sampling configurável (production-ready)

**Quick Start:**

1. **Instalar dependências:**
```bash
pip install -r extra-addons/thedevkitchen_observability/requirements.txt
```

2. **Configurar variáveis de ambiente (já adicionadas em `.env.example`):**
```bash
OTEL_ENABLED=true
OTEL_SERVICE_NAME=odoo-production
OTEL_EXPORTER_OTLP_ENDPOINT=tempo:4317
OTEL_TRACES_SAMPLER=always_on  # Use traceidratio:0.1 para 10% em produção
```

3. **Instalar o módulo via Odoo UI ou CLI:**
```bash
docker compose exec odoo odoo -u thedevkitchen_observability -d realestate --stop-after-init
```

4. **Usar o decorador nos controllers:**
```python
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

@http.route('/api/v1/properties', type='http', auth='none', methods=['GET'])
@require_jwt
@require_session
@require_company
@trace_http_request  # 👈 Adicione este decorador
def list_properties(self, **kwargs):
    # Span automático com HTTP semantics
    # trace_id nos logs para correlação com Tempo/Loki
    return request.make_json_response({'properties': [...]})
```

**Documentação completa:**
- [README.md](extra-addons/thedevkitchen_observability/README.md)
- [INSTRUMENTATION_EXAMPLE.md](extra-addons/thedevkitchen_observability/INSTRUMENTATION_EXAMPLE.md)

**Exemplo anterior (manual, não use mais):**

1. **Instalar OpenTelemetry:**
```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

2. **Criar `extra-addons/thedevkitchen_observability/__init__.py`:**
```python
from . import models
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configurar tracer
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
```

3. **Decorar controllers com tracing:**
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@http.route('/api/v1/properties', type='http', auth='none', methods=['GET'])
@require_jwt
@require_session
@require_company
def list_properties(self, **kwargs):
    with tracer.start_as_current_span("list_properties"):
        # Seu código aqui
        pass
```

---

### 🚨 Alertas Críticos

**Configurar em:** `observability/prometheus/alerts.yml`

```yaml
groups:
  - name: system
    interval: 30s
    rules:
      # Uso de disco
      - alert: HighDiskUsage
        expr: (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100) < 20
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disco quase cheio (< 20% livre)"

      # Uso de memória
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Memória alta (> 90%)"

  - name: containers
    interval: 30s
    rules:
      # Container down
      - alert: ContainerDown
        expr: up{job=~"postgres|redis|odoo"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.job }} está down"

  - name: database
    interval: 30s
    rules:
      # Conexões PostgreSQL
      - alert: PostgreSQLTooManyConnections
        expr: sum(pg_stat_activity_count) > 180
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Muitas conexões no PostgreSQL (> 180)"

      # Slow queries
      - alert: PostgreSQLSlowQueries
        expr: rate(pg_stat_statements_mean_time_seconds[5m]) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Queries lentas detectadas (> 1s)"

  - name: redis
    interval: 30s
    rules:
      # Cache hit rate
      - alert: RedisLowHitRate
        expr: (redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) < 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Redis cache hit rate baixo (< 80%)"
```

---

### 🏃 Como Usar

#### 1. Subir Stack de Observabilidade

```bash
cd 18.0

# Criar diretórios
mkdir -p observability/grafana/{provisioning/datasources,dashboards}

# Criar arquivos de configuração (prometheus.yml, loki-config.yml, etc.)
# (usar conteúdos acima)

# Subir observabilidade
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d

# Verificar
docker compose ps
```

#### 2. Acessar Interfaces

- **Grafana:** http://localhost:3000 (admin/TROCAR_SENHA_FORTE)
- **Prometheus:** http://localhost:9090
- **Loki:** http://localhost:3100/ready

#### 3. Importar Dashboards

```bash
# Via Grafana UI
Grafana → Dashboards → Import → Digite ID → Load

# Ou via API
curl -X POST http://admin:SENHA@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @observability/grafana/dashboards/odoo-overview.json
```

---

### 🔐 Segurança - Observabilidade

#### Checklist
- [ ] Grafana admin password alterado
- [ ] Prometheus sem acesso público (só interna)
- [ ] Loki sem auth (só rede interna)
- [ ] Grafana atrás de Traefik + HTTPS
- [ ] Dashboards com controle de acesso
- [ ] Alertas configurados
- [ ] Retenção de dados configurada (30 dias)

#### Variáveis de Ambiente

```bash
# Adicionar ao .env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=TROCAR_POR_SENHA_FORTE_32_CHARS
```

---

### 📊 Métricas-Chave a Monitorar

#### 1. Sistema (Node Exporter)
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Disk I/O
- Network I/O

#### 2. Containers (cAdvisor)
- Container CPU (%)
- Container Memory (MB)
- Container restarts
- Container uptime

#### 3. PostgreSQL
- Conexões ativas
- Slow queries (> 1s)
- Cache hit rate
- Transaction rate
- Deadlocks

#### 4. Redis
- Cache hit rate
- Memory usage
- Evicted keys
- Connected clients
- Commands/s

#### 5. Odoo
- Requests/s
- Response time (p50, p95, p99)
- Error rate (%)
- Active sessions
- Cron jobs duration

#### 6. RabbitMQ
- Queue depth
- Message rate
- Consumer lag
- Memory usage

#### 7. Celery
- Tasks/s
- Task success/failure rate
- Task duration
- Active workers

---

### 🎯 Alertas Críticos (Atualizado)

- [ ] Database down
- [ ] Redis down
- [ ] RabbitMQ down
- [ ] Odoo down
- [ ] Uso de disco > 80%
- [ ] Uso de memória > 90%
- [ ] Taxa de erro > 5%
- [ ] **PostgreSQL conexões > 180**
- [ ] **Redis cache hit rate < 80%**
- [ ] **Slow queries > 1s (média 5min)**
- [ ] **RabbitMQ queue depth > 10000**
- [ ] **Celery task lag > 5min**
- [ ] **Container restarts > 3/hora**
- [ ] **Response time p95 > 2s**

---

### 🆚 Alternativa: SigNoz (All-in-One)

**Mais simples, menos componentes:**

```yaml
# docker-compose.signoz.yml
services:
  signoz:
    image: signoz/signoz:latest
    ports:
      - "3301:3301"  # Frontend
      - "4317:4317"  # OTLP gRPC
    environment:
      - SIGNOZ_ADMIN_USER=admin
      - SIGNOZ_ADMIN_PASSWORD=TROCAR_SENHA_FORTE
    volumes:
      - signoz-data:/var/lib/signoz
```

**Vantagens:** Setup mais rápido, all-in-one  
**Desvantagens:** Menos flexível, comunidade menor

---

## 💾 Backup Strategy

### O que fazer backup

1. **PostgreSQL (CRÍTICO)**
```bash
# Backup diário
docker exec db pg_dump -U odoo_prod_user odoo_production | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip < backup_20260324.sql.gz | docker exec -i db psql -U odoo_prod_user odoo_production
```

2. **Filestore (CRÍTICO)**
```bash
# Backup do volume
docker run --rm -v odoo18-data:/data -v $(pwd):/backup alpine tar czf /backup/filestore_$(date +%Y%m%d).tar.gz /data
```

3. **Redis (OPCIONAL - dados efêmeros)**
```bash
# Backup RDB
docker exec redis redis-cli --pass <SENHA> BGSAVE
docker cp redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### Frequência Recomendada
- **Diário**: PostgreSQL + Filestore
- **Semanal**: Full com teste de restore
- **Mensal**: Arquivar offsite (S3, Google Cloud Storage)

---

## 🎯 Checklist Final antes do Go-Live

### Segurança
- [ ] Todas as senhas alteradas
- [ ] Usuário admin do Odoo alterado
- [ ] Master password forte configurado
- [ ] SSL/TLS configurado
- [ ] Firewall configurado
- [ ] Portas internas não expostas

### Configuração
- [ ] Variáveis de ambiente validadas
- [ ] Workers configurados (Odoo)
- [ ] Redis conectando
- [ ] RabbitMQ conectando
- [ ] Celery funcionando
- [ ] Logs funcionando

### Performance
- [ ] Limites de memória configurados
- [ ] Timeouts configurados
- [ ] Connection pools configurados
- [ ] Cache (Redis) funcionando

### Backup
- [ ] Backup automático configurado
- [ ] Testado restore
- [ ] Backup offsite configurado

### Monitoramento
- [ ] Healthchecks configurados
- [ ] Alertas configurados
- [ ] Dashboard funcionando

---

## 📚 Referências

- [Odoo Production Deployment](https://www.odoo.com/documentation/18.0/administration/install/deploy.html)
- [PostgreSQL Security Checklist](https://www.postgresql.org/docs/current/security.html)
- [Redis Security](https://redis.io/topics/security)
- [RabbitMQ Access Control](https://www.rabbitmq.com/access-control.html)
- [Dokploy Documentation](https://docs.dokploy.com/)
- [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)

---

**Próximos Passos:**
1. [ ] Adaptar `docker-compose.yml` para usar variáveis
2. [ ] Criar `.env.example`
3. [ ] Modificar `entrypoint.sh` para segurança
4. [ ] Configurar variáveis no Dokploy
5. [ ] Deploy e validação
