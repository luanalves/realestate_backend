# Capítulo 3: Ambientes

URLs e configurações dos ambientes deployados do sistema Realestate.

---

## 🌍 Visão Geral

O sistema Realestate possui três ambientes:

1. **Desenvolvimento (dev)** - Ambiente para testes de desenvolvimento
2. **Homologação (homol)** - Ambiente para testes de qualidade e UAT
3. **Produção (prod)** - Ambiente de produção para usuários finais

Cada ambiente possui sua própria stack completa de serviços.

---

## 🚀 Produção

### URLs dos Serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Odoo** | https://torque-backoffice.thedevkitchen.com.br | Aplicação principal |
| **Grafana** | https://grafana.torque-backoffice.thedevkitchen.com.br | Dashboards de monitoramento |
| **Flower** | https://flower.torque-backoffice.thedevkitchen.com.br | Monitoramento Celery |
| **MailHog** | https://mail.torque-backoffice.thedevkitchen.com.br | Captura de emails (dev) |
| **RabbitMQ** | https://rabbitmq.torque-backoffice.thedevkitchen.com.br | Management UI |
| **Swagger** | https://torque-backoffice.thedevkitchen.com.br/api/docs | Documentação da API |

### Características
- SSL/TLS configurado (certificado válido)
- Backup automático diário
- Alta disponibilidade
- Monitoramento 24/7
- Rate limiting configurado
- WAF (Web Application Firewall)

### Configurações especiais
```yaml
Workers: 8
Max Cron Threads: 4
Database Pool Size: 20
Redis Max Memory: 1GB
Log Level: WARNING
```

### Acesso
- Credenciais fornecidas apenas para administradores
- MFA (Multi-Factor Authentication) obrigatório
- VPN necessária para acesso ao banco de dados

---

## 🧪 Homologação

### URLs dos Serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Odoo** | https://homol.torque-backoffice.thedevkitchen.com.br | Aplicação principal |
| **Grafana** | https://grafana.homol.torque-backoffice.thedevkitchen.com.br | Dashboards de monitoramento |
| **Flower** | https://flower.homol.torque-backoffice.thedevkitchen.com.br | Monitoramento Celery |
| **MailHog** | https://mail.homol.torque-backoffice.thedevkitchen.com.br | Captura de emails |
| **RabbitMQ** | https://rabbitmq.homol.torque-backoffice.thedevkitchen.com.br | Management UI |
| **Swagger** | https://homol.torque-backoffice.thedevkitchen.com.br/api/docs | Documentação da API |

### Características
- Espelho da produção
- Dados de teste (não reais)
- Deploy automático após aprovação em code review
- Refresh semanal do banco (cópia sanitizada da produção)

### Configurações
```yaml
Workers: 4
Max Cron Threads: 2
Database Pool Size: 10
Redis Max Memory: 512MB
Log Level: INFO
```

### Acesso
- Disponível para QA, desenvolvedores e stakeholders
- Credenciais de teste disponíveis no wiki interno
- Sem MFA (facilitar testes)

### Casos de uso
- User Acceptance Testing (UAT)
- Testes de integração end-to-end
- Validação de features antes da produção
- Demo para clientes

---

## 💻 Desenvolvimento

### URLs dos Serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Odoo** | https://dev.torque-backoffice.thedevkitchen.com.br | Aplicação principal |
| **Grafana** | https://grafana.dev.torque-backoffice.thedevkitchen.com.br | Dashboards de monitoramento |
| **Flower** | https://flower.dev.torque-backoffice.thedevkitchen.com.br | Monitoramento Celery |
| **MailHog** | https://mail.dev.torque-backoffice.thedevkitchen.com.br | Captura de emails |
| **RabbitMQ** | https://rabbitmq.dev.torque-backoffice.thedevkitchen.com.br | Management UI |
| **Swagger** | https://dev.torque-backoffice.thedevkitchen.com.br/api/docs | Documentação da API |

### Características
- Deploy automático a cada push na branch `develop`
- Dados voláteis (podem ser resetados a qualquer momento)
- Logs verbosos para debug
- Developer mode ativado

### Configurações
```yaml
Workers: 2
Max Cron Threads: 1
Database Pool Size: 5
Redis Max Memory: 256MB
Log Level: DEBUG
Dev Mode: reload
```

### Acesso
- Aberto para toda a equipe de desenvolvimento
- Credenciais simples (admin/admin)
- Sem restrições de acesso

### Casos de uso
- Testes de desenvolvimento
- Integração contínua (CI)
- Validação rápida de features
- Experimentos

---

## 🏠 Local (Desenvolvimento Local)

### URLs dos Serviços

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Odoo** | http://localhost:8069 | Aplicação principal |
| **PostgreSQL** | localhost:5432 | Banco de dados |
| **Redis** | localhost:6379 | Cache |
| **RabbitMQ** | http://localhost:15672 | Management UI |
| **Flower** | http://localhost:5555 | Monitoramento Celery |
| **MailHog** | http://localhost:8025 | Captura de emails |

### Características
- Execução via Docker Compose
- Dados locais (isolados)
- Hot reload ativado
- Sem SSL (HTTP apenas)

### Credenciais padrão
```yaml
Odoo:
  username: admin
  password: admin

PostgreSQL:
  username: odoo
  password: odoo
  database: realestate

RabbitMQ:
  username: odoo
  password: odoo_rabbitmq_secret_2026

Flower:
  username: admin
  password: flower_admin_2026
```

### Como subir
```bash
cd 18.0
docker compose up -d
```

Ver [Capítulo 1: Quick Start](01-quick-start.md) para detalhes.

---

## 🔄 Pipeline de Deploy

```
┌─────────────┐
│    Local    │ git push
│ Development │────────────┐
└─────────────┘            │
                           ▼
                    ┌────────────┐
                    │  GitHub    │
                    │ Repository │
                    └──────┬─────┘
                           │ PR merged
                           ▼
                    ┌─────────────┐
                    │  CI/CD      │
                    │  Pipeline   │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │   Dev    │    │  Homol   │    │   Prod   │
    │  (auto)  │    │ (manual) │    │ (manual) │
    └──────────┘    └──────────┘    └──────────┘
```

### Fluxo de trabalho

1. **Desenvolvimento local** → `git push` → branch `develop`
2. **Deploy automático** → Ambiente **Dev**
3. **Code review & PR** → branch `main`
4. **Deploy manual** → Ambiente **Homol** (após aprovação)
5. **QA & UAT** → Testes em Homologação
6. **Deploy manual** → Ambiente **Prod** (após aprovação final)

---

## 🔐 Matriz de Permissões

| Ambiente | Desenvolvedores | QA | DevOps | Stakeholders |
|----------|----------------|-----|---------|--------------|
| **Local** | ✅ Full | - | - | - |
| **Dev** | ✅ Full | ✅ Read | ✅ Full | - |
| **Homol** | ✅ Read | ✅ Full | ✅ Full | ✅ Read |
| **Prod** | ❌ None | ❌ None | ✅ Admin | ✅ Read |

---

## 📊 Monitoramento

Todos os ambientes possuem:

### Métricas coletadas
- Uptime/Downtime
- Response time
- Error rate
- Database queries
- Memory usage
- CPU usage
- Disk I/O

### Alertas configurados
- Downtime > 1 minuto
- Response time > 2 segundos
- Error rate > 1%
- Disk usage > 80%
- Memory usage > 90%

### Dashboards Grafana
- **Overview:** Métricas gerais do sistema
- **Database:** Performance do PostgreSQL
- **Cache:** Estatísticas do Redis
- **Queue:** Status das filas Celery
- **API:** Métricas dos endpoints REST

---

## 🆘 Contatos de Suporte

### Produção (Urgente)
- **Slack:** #realestate-prod-alerts
- **Email:** devops@thedevkitchen.com.br
- **Telefone:** +55 11 99999-9999 (plantão 24/7)

### Homologação/Dev
- **Slack:** #realestate-dev
- **Email:** dev@thedevkitchen.com.br

---

## 📚 Próximos Passos

- [Capítulo 4: Documentação da API](04-api-documentation.md) - Explore a API REST
- [Capítulo 5: Deployment](05-deployment.md) - Guias de deploy
- [Voltar ao Índice](00-index.md)

---

*Última atualização: 27 de março de 2026*
