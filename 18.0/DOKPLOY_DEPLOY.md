# 🚀 Dokploy Deployment Guide

**Versão:** 1.0  
**Data:** 2026-03-24  
**Stack:** Odoo 18.0 + PostgreSQL + Redis + RabbitMQ + Celery + Grafana + OpenTelemetry

---

## 📋 Pré-requisitos

- [ ] Conta no Dokploy configurada
- [ ] Domínio DNS configurado (ex: `app.seudominio.com`)
- [ ] Acesso ao repositório Git (GitHub, GitLab, Bitbucket)
- [ ] Arquivo `.env.production` editado com senhas fortes

---

## 🔐 1. Preparar Variáveis de Ambiente

### 1.1 Gerar Senhas Fortes

Execute no terminal para gerar todas as senhas necessárias:

```bash
cd 18.0

# Gerar senhas e salvar em arquivo temporário (NÃO COMMITAR!)
echo "# Senhas geradas em $(date)" > .env.secrets
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets
echo "RABBITMQ_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets
echo "ODOO_ADMIN_PASSWD=$(openssl rand -base64 48)" >> .env.secrets
echo "ODOO_NEW_ADMIN_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets
echo "JWT_SECRET=$(openssl rand -base64 48)" >> .env.secrets
echo "FLOWER_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 32)" >> .env.secrets

# Exibir senhas geradas
cat .env.secrets
```

**⚠️ IMPORTANTE:** Copie essas senhas para um gerenciador de senhas (1Password, Bitwarden) ANTES de continuar!

### 1.2 Editar .env.production

Abra o arquivo `.env.production` e substitua todos os valores `YOUR_*_HERE`:

```bash
# Editar arquivo
nano .env.production
# ou
code .env.production
```

**Atalho:** Você pode copiar/colar as senhas do arquivo `.env.secrets` gerado acima.

**Atenção especial às URLs:**
- `CELERY_BROKER_URL`: Deve conter `RABBITMQ_PASSWORD`
- `CELERY_RESULT_BACKEND`: Deve conter `REDIS_PASSWORD`
- `JWT_ISSUER`: Seu domínio real (ex: `https://app.seudominio.com`)
- `GRAFANA_ROOT_URL`: Subdomínio Grafana (ex: `https://grafana.seudominio.com`)

### 1.3 Validar Arquivo

**Verificar se todas as senhas foram substituídas:**

```bash
# Deve retornar 0 (zero)
grep -c "YOUR_.*_HERE" .env.production
```

Se retornar número > 0, ainda há valores não substituídos!

**Verificar sincronização de senhas:**

```bash
# POSTGRES_PASSWORD deve aparecer 2x (POSTGRES_PASSWORD e DB_PASSWORD)
grep POSTGRES_PASSWORD .env.production | wc -l

# REDIS_PASSWORD deve aparecer 2x (REDIS_PASSWORD e CELERY_RESULT_BACKEND)
grep REDIS_PASSWORD .env.production | wc -l

# RABBITMQ_PASSWORD deve aparecer 2x (RABBITMQ_PASSWORD e CELERY_BROKER_URL)
grep RABBITMQ_PASSWORD .env.production | wc -l
```

---

## 🌐 2. Deploy no Dokploy

### 2.1 Criar Novo Projeto

1. Acesse o Dokploy: `https://dokploy.seudominio.com`
2. Faça login com suas credenciais
3. Clique em **"New Project"**
4. Preencha:
   - **Project Name:** `odoo-production`
   - **Description:** `Odoo 18.0 Real Estate Management System`
   - **Repository URL:** `https://github.com/seu-usuario/odoo-docker.git`
   - **Branch:** `master` (ou `main`)
   - **Docker Compose File:** `18.0/docker-compose.yml`

### 2.2 Configurar Build Settings

1. Vá em **"Settings"** → **"Build"**
2. Configure:
   - **Build Context:** `18.0/`
   - **Dockerfile:** `18.0/Dockerfile` (se aplicável)
   - **Docker Compose:** ✅ Enabled

### 2.3 Upload de Variáveis de Ambiente (CRÍTICO)

#### Método 1: Upload de Arquivo (RECOMENDADO)

1. Vá em **"Settings"** → **"Environment Variables"**
2. Clique em **"Import from file"**
3. Selecione o arquivo `.env.production` editado
4. ✅ **HABILITE** o checkbox **"Create Environment File"**
   - Isso cria o arquivo `.env` dentro do container
   - Necessário para `docker-compose` ler as variáveis corretamente
5. Clique em **"Save"**

#### Método 2: Colar Conteúdo Manualmente

1. Vá em **"Settings"** → **"Environment Variables"**
2. Clique em **"Add from text"**
3. Copie todo o conteúdo do `.env.production`
4. Cole no campo de texto
5. ✅ **HABILITE** o checkbox **"Create Environment File"**
6. Clique em **"Save"**

#### Método 3: Adicionar Individualmente (NÃO RECOMENDADO)

Use apenas se os métodos acima falharem:

1. Vá em **"Settings"** → **"Environment Variables"**
2. Para cada variável, clique em **"Add Variable"**
3. Preencha **Key** e **Value**
4. Repita para todas as 30+ variáveis (trabalhoso)
5. ✅ **HABILITE** o checkbox **"Create Environment File"**

**⚠️ ATENÇÃO:**  
- **SEMPRE** habilite **"Create Environment File"**
- Caso contrário, `docker-compose` não conseguirá ler as variáveis
- Variáveis devem estar disponíveis tanto no build quanto no runtime

### 2.4 Configurar Domínios

1. Vá em **"Settings"** → **"Domains"**
2. Adicione os domínios/subdomínios:

| Service | Domain | Port | SSL |
|---------|--------|------|-----|
| odoo | `app.seudominio.com` | 8069 | ✅ |
| grafana | `grafana.seudominio.com` | 3000 | ✅ |
| flower | `flower.seudominio.com` | 5555 | ✅ |

3. Para cada domínio:
   - Clique em **"Add Domain"**
   - Preencha **Domain Name**
   - Preencha **Port** do serviço
   - ✅ Habilite **"SSL/TLS"** (Let's Encrypt automático)
   - Clique em **"Save"**

### 2.5 Configurar Volumes (Opcional mas RECOMENDADO)

Para persistir dados fora do container:

1. Vá em **"Settings"** → **"Volumes"**
2. Configure volumes persistentes:

| Volume Name | Mount Path | Description |
|-------------|------------|-------------|
| `odoo18-data` | `/var/lib/odoo` | Dados Odoo (filestore, sessions) |
| `odoo18-pg-data` | `/var/lib/postgresql/data` | Database PostgreSQL |
| `odoo18-redis` | `/data` | Cache Redis |

**⚠️ NOTA:** Se usar volumes nomeados do Docker Compose (default), Dokploy os gerencia automaticamente.

---

## 🚀 3. Deploy e Validação

### 3.1 Fazer Deploy

1. No dashboard do projeto, clique em **"Deploy"**
2. Aguarde o build completar (5-10 minutos na primeira vez)
3. Acompanhe os logs em tempo real:
   - **"Logs"** → Selecione o serviço (odoo, db, redis, etc.)

### 3.2 Verificar Status dos Serviços

Todos os serviços devem estar **Running** (verde):

```
✅ db (PostgreSQL)
✅ redis (Redis)
✅ rabbitmq (RabbitMQ)
✅ odoo (Odoo Web)
✅ celery_commission_worker
✅ celery_audit_worker
✅ celery_notification_worker
✅ flower (Celery Monitor)
✅ tempo (OpenTelemetry)
✅ grafana (Observability)
```

Se algum estiver **Unhealthy** ou **Exited**, verifique os logs.

### 3.3 Testar Acesso

**Odoo Web:**
```
https://app.seudominio.com
```
- Login: `admin`
- Senha: Valor de `ODOO_NEW_ADMIN_PASSWORD`

**Grafana:**
```
https://grafana.seudominio.com
```
- Login: `admin`
- Senha: Valor de `GRAFANA_ADMIN_PASSWORD`

**Flower (Celery Monitor):**
```
https://flower.seudominio.com
```
- Login: `admin`
- Senha: Valor de `FLOWER_PASSWORD`

### 3.4 Validar Database Connection

Execute no terminal do container `odoo`:

```bash
# Dentro do Dokploy, vá em "Terminal" → Selecione serviço "odoo"

# Testar conexão PostgreSQL
psql -h db -U odoo_prod_user -d odoo_production -c "SELECT version();"

# Testar conexão Redis
redis-cli -h redis -p 6379 -a $REDIS_PASSWORD ping
# Deve retornar: PONG
```

### 3.5 Validar Celery Workers

Acesse Flower (`https://flower.seudominio.com`) e verifique:
- [ ] 3 workers online (commission, audit, notification)
- [ ] Status: **Online** (verde)
- [ ] Tasks processadas com sucesso

Ou via terminal:

```bash
# Listar workers ativos
docker exec celery_commission_worker celery -A odoo inspect active_queues
```

### 3.6 Validar OpenTelemetry (APM)

Acesse Grafana (`https://grafana.seudominio.com`):

1. Vá em **"Explore"** → Selecione **"Tempo"**
2. Pesquise traces:
   ```
   {service.name="odoo-production"}
   ```
3. Deve exibir traces recentes de requisições HTTP

Ou acesse o dashboard pré-configurado:
```
https://grafana.seudominio.com/d/distributed-tracing/distributed-tracing-apm
```

---

## 🔧 4. Troubleshooting

### Problema: Serviço não inicia (Exited)

**Diagnóstico:**
```bash
# Ver logs do serviço
docker logs odoo
docker logs db
docker logs redis
```

**Soluções comuns:**
- **Database:** Senha incorreta → Verifique `POSTGRES_PASSWORD` e `DB_PASSWORD` (devem ser iguais)
- **Redis:** Senha incorreta → Verifique `REDIS_PASSWORD` no `CELERY_RESULT_BACKEND`
- **RabbitMQ:** Senha incorreta → Verifique `RABBITMQ_PASSWORD` no `CELERY_BROKER_URL`
- **Odoo:** Falta variável obrigatória → Verifique logs para identificar qual

### Problema: "Create Environment File" não funcionou

**Diagnóstico:**
```bash
# Acessar terminal do container odoo
docker exec -it odoo bash

# Verificar se .env existe
ls -la /.env
cat /.env
```

**Solução:**
- Volte em "Environment Variables" no Dokploy
- ✅ Certifique-se que **"Create Environment File"** está habilitado
- Clique em "Save" novamente
- Faça **Redeploy**

### Problema: CELERY_BROKER_URL ou CELERY_RESULT_BACKEND com senha errada

**Sintomas:**
- Celery workers não conectam
- Flower dashboard vazio
- Logs: `amqp.exceptions.AccessRefused` ou `redis.exceptions.AuthenticationError`

**Solução:**
```bash
# Verificar se senha no URL está correta
echo $CELERY_BROKER_URL
# Deve ser: amqp://odoo_mq_user:SUA_SENHA@rabbitmq:5672//odoo_production

echo $CELERY_RESULT_BACKEND
# Deve ser: redis://:SUA_SENHA@redis:6379/2
```

**Corrigir:**
1. Edite `.env.production` com as senhas corretas
2. Re-upload no Dokploy
3. **Redeploy** o projeto

### Problema: Odoo acessível mas sem CSS/JS

**Causa:** `ODOO_PROXY_MODE` não configurado ou SSL redirect incorreto

**Solução:**
```bash
# Verificar se variável está correta
echo $ODOO_PROXY_MODE
# Deve ser: True

# Verificar configuração do Traefik/Nginx no Dokploy
# HTTP Headers corretos:
#   X-Forwarded-For
#   X-Forwarded-Proto
#   X-Forwarded-Host
```

### Problema: High memory usage

**Causa:** `ODOO_WORKERS` ou `CELERY_WORKER_CONCURRENCY` muito alto para recursos disponíveis

**Solução:**
```bash
# Ajustar no .env.production:
ODOO_WORKERS=2                    # Reduzir de 4 para 2
CELERY_WORKER_CONCURRENCY=2       # Reduzir de 4 para 2

# Limites de memória (se necessário):
ODOO_LIMIT_MEMORY_HARD=2147483648     # 2GB
ODOO_LIMIT_MEMORY_SOFT=1610612736     # 1.5GB
```

---

## 🔒 5. Segurança Pós-Deploy

### 5.1 Alterar Senha Padrão do Admin

**Primeiro login:**
1. Acesse `https://app.seudominio.com`
2. Login: `admin`
3. Senha: `ODOO_NEW_ADMIN_PASSWORD`
4. Vá em **Configurações** → **Usuários** → **Administrator**
5. Clique em **"Alterar Senha"**
6. Defina nova senha forte (32+ caracteres)
7. Atualize `ODOO_PASSWORD` no `.env.production` (para Celery continuar funcionando)
8. Re-upload variáveis no Dokploy
9. **Redeploy** Celery workers

### 5.2 Configurar Backup Automático

**Dokploy tem backup nativo:**
1. Vá em **"Settings"** → **"Backups"**
2. Configure:
   - **Frequency:** Daily (diário)
   - **Time:** 02:00 AM (horário de baixa carga)
   - **Retention:** 7 days (últimos 7 dias)
   - **Include Volumes:** ✅ Todos os volumes persistentes

**Backup manual via script:**
```bash
# Criar script de backup
# Ver: 18.0/PRODUCTION_SETUP.md seção "Backup Strategy"
```

### 5.3 Configurar Monitoramento/Alertas

**Dokploy:**
1. Vá em **"Settings"** → **"Monitoring"**
2. Configure alertas:
   - CPU > 80%
   - Memory > 90%
   - Disk > 85%
   - Service down/unhealthy

**Grafana:**
1. Acesse `https://grafana.seudominio.com`
2. Vá em **"Alerting"** → **"Alert rules"**
3. Configure alertas:
   - HTTP 5xx errors > 10/min
   - Response time > 2s
   - Database connection errors
   - Celery worker offline

### 5.4 Firewall / Network Isolation

**Dokploy gerencia automaticamente, mas verifique:**
- [ ] Apenas portas 80, 443 expostas publicamente
- [ ] PostgreSQL, Redis, RabbitMQ **NÃO** expostos externamente (só rede Docker interna)
- [ ] SSH key-based auth (não senha)
- [ ] Fail2ban habilitado (proteção brute-force)

---

## 📚 6. Recursos Adicionais

**Documentação:**
- [Dokploy Docs](https://docs.dokploy.com/)
- [Odoo 18 Deployment](https://www.odoo.com/documentation/18.0/administration/on_premise/deploy.html)
- [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md) - Hardening detalhado
- [ADR-025](../docs/adr/ADR-025-opentelemetry-distributed-tracing.md) - Observabilidade

**Suporte:**
- Dokploy Community: https://discord.gg/dokploy
- Odoo Community: https://www.odoo.com/forum

---

## ✅ Checklist Final

Antes de marcar como **produção ativa**:

- [ ] Todos os serviços estão **Running** (verde)
- [ ] Odoo acessível via HTTPS com SSL válido
- [ ] Login admin funciona com senha forte
- [ ] Database connection OK (teste via psql)
- [ ] Redis connection OK (teste via redis-cli ping)
- [ ] 3 Celery workers **Online** no Flower
- [ ] Grafana acessível e exibindo traces (OpenTelemetry)
- [ ] Backup automático configurado
- [ ] Monitoramento/alertas configurados
- [ ] Senhas armazenadas em gerenciador seguro (1Password, Bitwarden)
- [ ] Equipe treinada em operação básica
- [ ] Plano de rollback definido
- [ ] Janela de manutenção agendada (para futuras atualizações)

---

**Status:** ✅ Deploy Completo  
**Data:** _____________  
**Responsável:** _____________
