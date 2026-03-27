# Realestate Backend - Odoo 18.0

Backend do sistema de gestão imobiliária baseado em Odoo 18.0 com PostgreSQL.

## 🚀 Quick Start

```bash
# Navegar para o diretório do Odoo 18.0
cd 18.0

# Subir os containers
docker compose up -d

# Acessar a aplicação
# http://localhost:8069
# Usuário: admin | Senha: admin
```

---

## 📖 Documentação Completa

**[📚 Acesse o Guia Completo →](docs/guide/00-index.md)**

Documentação organizada em capítulos:

| Capítulo | Descrição |
|----------|-----------|
| **[1. Quick Start](docs/guide/01-quick-start.md)** | Como subir o ambiente rapidamente |
| **[2. Componentes Docker](docs/guide/02-docker-components.md)** | Detalhes da stack (Odoo, PostgreSQL, Redis, RabbitMQ, Celery, etc.) |
| **[3. Ambientes](docs/guide/03-environments.md)** | URLs de Produção, Homologação e Desenvolvimento |
| **[4. Documentação da API](docs/guide/04-api-documentation.md)** | Como usar a API REST (Swagger/OpenAPI) |
| **[5. Deployment](docs/guide/05-deployment.md)** | Guias de deploy (Dokploy, Docker Compose, CI/CD) |

---

## 🔗 Links Rápidos

### Desenvolvimento Local
- **Odoo Web:** http://localhost:8069 (admin/admin)
- **Swagger API:** http://localhost:8069/api/docs
- **PostgreSQL:** localhost:5432 (odoo/odoo)
- **Redis:** localhost:6379
- **RabbitMQ:** http://localhost:15672 (odoo/odoo_rabbitmq_secret_2026)
- **Flower:** http://localhost:5555 (admin/flower_admin_2026)
- **MailHog:** http://localhost:8025

### Ambientes Cloud

#### Produção
- **Odoo:** https://torque-backoffice.thedevkitchen.com.br
- **Swagger:** https://torque-backoffice.thedevkitchen.com.br/api/docs
- **Grafana:** https://grafana.torque-backoffice.thedevkitchen.com.br

#### Homologação
- **Odoo:** https://homol.torque-backoffice.thedevkitchen.com.br
- **Swagger:** https://homol.torque-backoffice.thedevkitchen.com.br/api/docs

#### Desenvolvimento
- **Odoo:** https://dev.torque-backoffice.thedevkitchen.com.br
- **Swagger:** https://dev.torque-backoffice.thedevkitchen.com.br/api/docs

---

## 📁 Estrutura do Projeto

```
odoo-docker/
├── 18.0/                    # Odoo 18.0 (diretório principal)
│   ├── extra-addons/        # Módulos customizados
│   ├── docker-compose.yml   # Configuração Docker
│   └── odoo.conf            # Configuração Odoo
├── docs/                    # Documentação
│   ├── guide/               # Guia completo (livro)
│   ├── adr/                 # Architecture Decision Records
│   ├── api/                 # Documentação da API
│   └── architecture/        # Diagramas de arquitetura
├── integration_tests/       # Testes de integração
└── README.md                # Este arquivo
```

---

## 🛠️ Comandos Essenciais

```bash
# Subir ambiente
cd 18.0 && docker compose up -d

# Ver logs
docker compose logs -f odoo

# Parar ambiente
docker compose down

# Reiniciar
docker compose restart

# Acessar container Odoo
docker compose exec odoo bash

# Acessar PostgreSQL
docker compose exec db psql -U odoo -d realestate
```

---

## 📚 Recursos Adicionais

### Documentação Técnica
- [ADRs (Architecture Decision Records)](docs/adr/) - Decisões arquiteturais
- [API Documentation](docs/api/) - Especificações da API
- [OpenAPI Specs](docs/openapi/) - Schemas OpenAPI
- [Postman Collections](docs/postman/) - Collections para testes

### Guias Específicos
- [Production Setup](18.0/PRODUCTION_SETUP.md) - Configuração de produção
- [Dokploy Deploy](18.0/DOKPLOY_DEPLOY.md) - Deploy no Dokploy
- [Observability](docs/observability.md) - Monitoramento e métricas

### Referências Externas
- [Odoo 18.0 Documentation](https://www.odoo.com/documentation/18.0)
- [Docker Documentation](https://docs.docker.com/)

---

## 🆘 Suporte

- **Slack:** #realestate-dev
- **Email:** dev@thedevkitchen.com.br
- **Issues:** [GitHub Issues](https://github.com/thedevkitchen/realestate-backend/issues)

---

*Última atualização: 27 de março de 2026*
