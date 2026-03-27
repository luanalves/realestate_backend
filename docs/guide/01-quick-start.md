# Capítulo 1: Quick Start

Guia rápido para subir o ambiente de desenvolvimento local.

## 🎯 Pré-requisitos

Antes de começar, certifique-se de ter instalado:

- **Docker** (versão 20.10 ou superior)
- **Docker Compose** (versão 2.0 ou superior)

### Verificando a instalação

```bash
docker --version
docker compose version
```

---

## 🚀 Subindo o ambiente

### 1. Navegar para o diretório correto

```bash
cd 18.0
```

> **Nota:** Todo o desenvolvimento e operação é focado no diretório **18.0**, que contém a versão mais recente do Odoo.

### 2. Subir os containers

```bash
docker compose up -d
```

Este comando irá:
- Baixar as imagens necessárias (primeira execução)
- Criar e iniciar os containers:
  - Odoo 18.0
  - PostgreSQL 16
  - Redis 7
  - RabbitMQ
  - Celery Workers (3 workers)
  - Flower (monitoring)
  - MailHog (email testing)

### 3. Aguardar a inicialização

O Odoo pode levar alguns minutos para inicializar na primeira execução, pois precisa:
- Aguardar o PostgreSQL estar pronto
- Criar o banco de dados `realestate`
- Instalar módulos básicos

Acompanhe os logs:

```bash
docker compose logs -f odoo
```

Quando ver a mensagem `odoo.modules.loading: Modules loaded.`, o sistema está pronto!

---

## 🌐 Primeiro Acesso

### Acessar o Odoo

Abra seu navegador e acesse:

```
http://localhost:8069
```

### Credenciais padrão

- **Usuário:** `admin`
- **Senha:** `admin`

> ⚠️ **Importante:** Altere a senha padrão em ambientes de produção!

---

## 🛠️ Comandos Principais

### Ver logs

```bash
# Logs do Odoo
docker compose logs -f odoo

# Logs do PostgreSQL
docker compose logs -f db

# Logs de todos os serviços
docker compose logs -f
```

### Parar os containers

```bash
docker compose down
```

> **Nota:** Os dados do banco são persistidos em volumes Docker e não serão perdidos.

### Reiniciar os serviços

```bash
# Reiniciar todos os serviços
docker compose restart

# Reiniciar apenas o Odoo
docker compose restart odoo
```

### Acessar o container do Odoo

```bash
docker compose exec odoo bash
```

Útil para:
- Instalar dependências Python
- Executar comandos Odoo CLI
- Debugar problemas

### Acessar o banco de dados

```bash
docker compose exec db psql -U odoo -d realestate
```

---

## 📦 Desenvolvimento de Módulos

### Estrutura de diretórios

```
18.0/
├── extra-addons/          # Seus módulos customizados aqui!
│   ├── thedevkitchen_module1/
│   ├── thedevkitchen_module2/
│   └── ...
├── docker-compose.yml
├── Dockerfile
└── odoo.conf
```

### Adicionar um novo módulo

1. Crie seu módulo em `18.0/extra-addons/`:

```bash
cd 18.0/extra-addons
mkdir thedevkitchen_meu_modulo
```

2. Crie a estrutura básica do módulo:

```
thedevkitchen_meu_modulo/
├── __init__.py
├── __manifest__.py
├── models/
├── views/
└── security/
```

3. Reinicie o Odoo:

```bash
docker compose restart odoo
```

4. Ative o modo desenvolvedor no Odoo:
   - Settings → Activate the developer mode

5. Atualize a lista de aplicativos:
   - Apps → Update Apps List

6. Instale seu módulo:
   - Apps → Pesquise pelo nome → Install

### Hot reload (desenvolvimento)

Para habilitar reload automático ao modificar arquivos Python, adicione ao `odoo.conf`:

```ini
dev_mode = reload
```

---

## 🔍 Verificação de Saúde

### Verificar status dos containers

```bash
docker compose ps
```

Todos os containers devem estar com status `Up`.

### Serviços acessíveis

- ✅ Odoo Web: http://localhost:8069
- ✅ PostgreSQL: localhost:5432
- ✅ Redis: localhost:6379
- ✅ RabbitMQ Management: http://localhost:15672
- ✅ Flower (Celery): http://localhost:5555
- ✅ MailHog Web UI: http://localhost:8025

---

## 🆘 Troubleshooting

### Container não inicia

```bash
# Ver logs de erro
docker compose logs odoo

# Verificar recursos do Docker
docker system df
```

### Banco de dados corrompido

```bash
# Parar containers
docker compose down

# Remover volume do banco (ATENÇÃO: apaga todos os dados!)
docker volume rm 180_odoo18-db-data

# Subir novamente
docker compose up -d
```

### Porta já em uso

Se a porta 8069 já estiver em uso, edite `docker-compose.yml`:

```yaml
services:
  odoo:
    ports:
      - "8070:8069"  # Mude para outra porta
```

---

## 📚 Próximos Passos

- [Capítulo 2: Componentes Docker](02-docker-components.md) - Entenda cada serviço da stack
- [Capítulo 4: Documentação da API](04-api-documentation.md) - Explore a API REST
- [Voltar ao Índice](00-index.md)

---

*Última atualização: 27 de março de 2026*
