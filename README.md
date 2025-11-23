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
