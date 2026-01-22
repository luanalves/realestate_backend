# Celery Worker

Worker assíncrono para processar tarefas em background do Odoo Real Estate.

## Arquivos

- **Dockerfile** - Imagem Python 3.11 slim (~200MB)
- **requirements.txt** - Dependências: Celery, Redis, Pandas, Requests
- **tasks.py** - Definição das tasks assíncronas

## Como funciona

O Celery Worker se conecta ao Odoo via **XML-RPC** (não precisa do Odoo instalado localmente) e executa tarefas assíncronas enfileiradas pelo RabbitMQ.

### Filas disponíveis

| Fila | Worker | Concurrency | Uso |
|------|--------|-------------|-----|
| `commission_events` | celery_commission_worker | 2 | Cálculo de comissões |
| `audit_events` | celery_audit_worker | 1 | Logs de auditoria |
| `notification_events` | celery_notification_worker | 1 | Envio de notificações |

## Comandos úteis

```bash
# Ver logs de um worker específico
docker compose logs -f celery_commission_worker

# Restartar workers
docker compose restart celery_commission_worker celery_audit_worker celery_notification_worker

# Verificar se workers estão conectados
docker compose exec celery_commission_worker celery -A tasks inspect active

# Acessar shell do worker
docker compose exec celery_commission_worker bash
```

## Monitoramento

- **Flower Dashboard**: http://localhost:5555 (admin/flower_admin_2026)
- **RabbitMQ Management**: http://localhost:15672 (odoo/odoo_rabbitmq_secret_2026)

## Variáveis de ambiente

Configuradas no `.env` e passadas via `docker-compose.yml`:

- `CELERY_BROKER_URL` - RabbitMQ connection
- `CELERY_RESULT_BACKEND` - Redis connection
- `ODOO_URL` - URL do Odoo para XML-RPC
- `ODOO_DB` - Nome do banco de dados
- `ODOO_USER` - Usuário para autenticação
- `ODOO_PASSWORD` - Senha para autenticação

## Documentação adicional

- [PLANO-CELERY-RABBITMQ.md](../../PLANO-CELERY-RABBITMQ.md) - Plano completo de implementação
- [ADR-021](../../docs/adr/ADR-021-async-messaging-rabbitmq-celery.md) - Decisão arquitetural
