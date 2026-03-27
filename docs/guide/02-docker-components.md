# Capítulo 2: Componentes Docker

Detalhamento de todos os componentes da stack Docker do sistema Realestate.

---

## 🎨 Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    (React/Next.js)                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                    Odoo Web 18.0                             │
│              (Python/Werkzeug/HTTP)                          │
└─┬────────────────────┬──────────────┬──────────────────────┬┘
  │                    │              │                      │
  │ PostgreSQL         │ Redis        │ RabbitMQ             │ Celery
  ▼                    ▼              ▼                      ▼
┌────────┐        ┌────────┐    ┌──────────┐         ┌──────────┐
│   DB   │        │ Cache  │    │  Queue   │         │ Workers  │
│  16    │        │   7    │    │  3.13    │         │   3x     │
└────────┘        └────────┘    └──────────┘         └──────────┘
                                      │                     │
                                      │                     │
                                      ▼                     ▼
                                ┌──────────┐         ┌──────────┐
                                │  Flower  │         │ MailHog  │
                                │   2.0    │         │  1.0     │
                                └──────────┘         └──────────┘
```

---

## 🌐 Odoo Web Application

### Overview
Aplicação principal Odoo 18.0 rodando em Python com servidor Werkzeug.

### Acesso
- **URL:** http://localhost:8069
- **Usuário padrão:** `admin`
- **Senha padrão:** `admin`

### Configurações
```yaml
Porta: 8069
Workers: 4
Max Cron Threads: 2
Limit Time Real: 3600s
Limit Memory Hard: 2684354560 (2.5GB)
```

### Volumes montados
```yaml
- ./extra-addons:/mnt/extra-addons    # Módulos customizados
- ./filestore:/var/lib/odoo           # Arquivos e anexos
- odoo18-data:/var/lib/odoo           # Dados persistentes
```

### Comandos úteis

```bash
# Acessar shell do container
docker compose exec odoo bash

# Ver modules instalados
docker compose exec odoo odoo-bin --list-modules

# Atualizar módulo
docker compose exec odoo odoo-bin -u thedevkitchen_module_name -d realestate

# Shell Python do Odoo
docker compose exec odoo odoo-bin shell -d realestate
```

---

## 🗄️ PostgreSQL Database

### Overview
Banco de dados relacional PostgreSQL 16 otimizado para Odoo.

### Acesso
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `realestate`
- **Username:** `odoo`
- **Password:** `odoo`

### Ferramentas compatíveis
- DBeaver
- pgAdmin
- psql (CLI)
- DataGrip

### Comandos úteis

```bash
# Conectar via psql
docker compose exec db psql -U odoo -d realestate

# Backup do banco
docker compose exec db pg_dump -U odoo realestate > backup.sql

# Restore do banco
cat backup.sql | docker compose exec -T db psql -U odoo -d realestate

# Listar tabelas
docker compose exec db psql -U odoo -d realestate -c "\dt"

# Ver tamanho do banco
docker compose exec db psql -U odoo -d realestate -c "SELECT pg_size_pretty(pg_database_size('realestate'));"
```

### Configurações de performance

```ini
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
```

### Volume
- **Volume Docker:** `odoo18-db-data`
- **Path interno:** `/var/lib/postgresql/data`

---

## 🚀 Redis Cache

### Overview
Sistema de cache em memória para sessões HTTP, cache ORM e message bus.

### Acesso
- **Host:** `localhost`
- **Port:** `6379`
- **DB Index:** `1` (configurado no odoo.conf)

### Configurações
```yaml
Version: 7-alpine
Memory Limit: 256MB
Eviction Policy: allkeys-lru
Persistence: AOF (Append Only File)
```

### Comandos úteis

```bash
# CLI do Redis
docker compose exec redis redis-cli

# Monitorar operações em tempo real
docker compose exec redis redis-cli MONITOR

# Ver estatísticas
docker compose exec redis redis-cli INFO stats

# Limpar cache (use com cuidado!)
docker compose exec redis redis-cli FLUSHDB
```

### Casos de uso
1. **HTTP Sessions:** Armazenamento de sessões de usuário
2. **ORM Cache:** Cache de queries e resultados
3. **Asset Cache:** Cache de assets estáticos
4. **Message Bus:** Pub/sub para notificações em tempo real

### Volume
- **Volume Docker:** `odoo18-redis`
- **Backup:** AOF file persiste automaticamente

---

## 🐰 RabbitMQ (Message Broker)

### Overview
Message broker para filas Celery de tarefas assíncronas.

### Acesso
- **Management UI:** http://localhost:15672
- **Username:** `odoo`
- **Password:** `odoo_rabbitmq_secret_2026`
- **AMQP Port:** `5672` (para aplicação)

### Funcionalidades
- Gerenciamento de filas Celery
- Dead Letter Queues (DLQ)
- Retry automático com backoff exponencial
- Monitoramento de mensagens

### Queues configuradas
1. **commission_queue** - Cálculos de comissão
2. **notification_queue** - Envio de emails/SMS
3. **audit_queue** - Logs de auditoria

### Comandos úteis

```bash
# Ver filas
docker compose exec rabbitmq rabbitmqctl list_queues

# Ver bindings
docker compose exec rabbitmq rabbitmqctl list_bindings

# Purgar fila (desenvolvimento)
docker compose exec rabbitmq rabbitmqctl purge_queue commission_queue
```

---

## 🌺 Flower (Celery Monitoring)

### Overview
Interface web para monitoramento de workers Celery em tempo real.

### Acesso
- **URL:** http://localhost:5555
- **Username:** `admin`
- **Password:** `flower_admin_2026`

### Funcionalidades
- Visualizar workers ativos
- Monitorar execução de tasks
- Ver filas e mensagens pendentes
- Inspeção de tasks executadas
- Gráficos de performance

### Informações disponíveis
- Taxa de sucesso/falha
- Tempo médio de execução
- Tasks ativas, agendadas e reservadas
- Histórico de execuções

---

## ⚙️ Celery Workers

### Overview
3 workers especializados para processamento assíncrono.

### Workers configurados

#### 1. Commission Worker
```yaml
Nome: commission_worker
Queue: commission_queue
Concurrency: 2
Tarefas:
  - Cálculo de comissões
  - Geração de relatórios financeiros
  - Processamento batch de contratos
```

#### 2. Notification Worker
```yaml
Nome: notification_worker
Queue: notification_queue
Concurrency: 4
Tarefas:
  - Envio de emails
  - Envio de SMS
  - Push notifications
  - Webhooks
```

#### 3. Audit Worker
```yaml
Nome: audit_worker
Queue: audit_queue
Concurrency: 2
Tarefas:
  - Logs de auditoria
  - Rastreamento de alterações
  - Compliance e segurança
```

### Comandos úteis

```bash
# Ver status dos workers
docker compose ps | grep celery

# Ver logs de um worker específico
docker compose logs -f celery-commission

# Reiniciar workers
docker compose restart celery-commission
docker compose restart celery-notification
docker compose restart celery-audit
```

### Configurações

```python
# Retry policy
max_retries = 3
default_retry_delay = 60  # segundos
retry_backoff = True
retry_jitter = True
```

---

## 📧 MailHog (Email Testing)

### Overview
Servidor SMTP fake para capturar emails em desenvolvimento sem enviá-los realmente.

### Acesso
- **SMTP Server:** `mailhog:1025` (interno)
- **Web UI:** http://localhost:8025

### Funcionalidades
- Captura todos os emails enviados
- Interface web para visualização
- Download de emails (.eml)
- API REST para integração
- Busca e filtros

### Configuração no Odoo

```
Settings → Technical → Email → Outgoing Mail Servers

SMTP Server: mailhog
SMTP Port: 1025
Connection Security: None
Username: (deixar vazio)
Password: (deixar vazio)
```

### Casos de uso
- Testar fluxos de convite de usuários
- Testar password reset
- Testar notificações automáticas
- Validar templates de email
- Debug de problemas de email

### Produção
Em produção, use um servidor SMTP real (SendGrid, AWS SES, etc.).

Ver [ADR-023](../adr/ADR-023-mailhog-email-testing-development.md) para detalhes.

---

## 📊 Observabilidade (Opcional)

### Grafana + Prometheus + Jaeger

Para monitoramento avançado, ver [Observability Documentation](../observability.md).

```bash
# Subir stack de observabilidade
cd observability
docker compose up -d
```

Serviços disponíveis:
- **Grafana:** http://localhost:3000
- **Prometheus:** http://localhost:9090
- **Jaeger:** http://localhost:16686

---

## 🔗 Matriz de Conexões

| Serviço | Conecta com | Porta | Protocolo |
|---------|-------------|-------|-----------|
| Odoo | PostgreSQL | 5432 | postgres:// |
| Odoo | Redis | 6379 | redis:// |
| Odoo | RabbitMQ | 5672 | amqp:// |
| Odoo | MailHog | 1025 | smtp:// |
| Celery Workers | RabbitMQ | 5672 | amqp:// |
| Celery Workers | PostgreSQL | 5432 | postgres:// |
| Flower | RabbitMQ | 5672 | amqp:// |

---

## 📚 Próximos Passos

- [Capítulo 1: Quick Start](01-quick-start.md) - Guia de início rápido
- [Capítulo 3: Ambientes](03-environments.md) - URLs dos ambientes deployados
- [Voltar ao Índice](00-index.md)

---

*Última atualização: 27 de março de 2026*
