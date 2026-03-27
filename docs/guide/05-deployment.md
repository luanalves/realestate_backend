# Capítulo 5: Deployment

Guias de deploy e configuração de produção para o sistema Realestate.

---

## 🎯 Overview

Este capítulo cobre diferentes estratégias de deploy do sistema Realestate:

1. **Dokploy** - Plataforma PaaS (recomendado)
2. **Docker Compose** - Deploy manual em VPS
3. **Kubernetes** - Para ambientes enterprise
4. **CI/CD Pipeline** - Automação de deploys

---

## ☁️ Deploy no Dokploy (Recomendado)

### O que é Dokploy?

Dokploy é uma plataforma PaaS (Platform as a Service) que simplifica o deploy de aplicações Docker.

### Pré-requisitos

- Conta no Dokploy
- Repositório Git configurado
- Dockerfile na raiz do projeto

### Configuração do Projeto

#### 1. Build Type

⚠️ **IMPORTANTE:** Use **Dockerfile**, NÃO Nixpacks!

- **Build Type:** `Dockerfile`
- **Dockerfile Path:** `./Dockerfile`

#### 2. Configurações da Aplicação

```yaml
Name: realestate-backend
Port: 8069
Health Check Path: /web/health
Restart Policy: always
```

#### 3. Variáveis de Ambiente

Configure as seguintes variáveis:

```bash
# Database
POSTGRES_USER=odoo
POSTGRES_PASSWORD=<strong_password>
POSTGRES_DB=realestate
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Odoo
ODOO_DB_NAME=realestate
ODOO_ADMIN_PASSWORD=<strong_admin_password>
ODOO_WORKERS=4
ODOO_MAX_CRON_THREADS=2

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1

# RabbitMQ
RABBITMQ_USER=odoo
RABBITMQ_PASSWORD=<strong_rabbitmq_password>
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

# Security
JWT_SECRET_KEY=<generate_strong_secret>
SESSION_SECRET=<generate_strong_secret>

# Email (Production)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid_api_key>
SMTP_FROM=noreply@thedevkitchen.com.br

# Environment
ENVIRONMENT=production
LOG_LEVEL=WARNING
```

#### 4. Volumes Persistentes

Configure volumes para dados persistentes:

```yaml
/var/lib/odoo -> /data/odoo (filestore)
/var/lib/postgresql/data -> /data/postgres (database)
```

#### 5. Deploy

1. Conecte o repositório Git ao Dokploy
2. Configure as variáveis de ambiente
3. Clique em **"Deploy"**
4. Aguarde o build e deploy (5-10 minutos)
5. Acesse a URL fornecida pelo Dokploy

### Comandos Úteis no Dokploy

```bash
# Ver logs da aplicação
dokploy logs realestate-backend

# Reiniciar aplicação
dokploy restart realestate-backend

# Escalar workers
dokploy scale realestate-backend --replicas=3

# Ver métricas
dokploy metrics realestate-backend
```

---

## 🐳 Deploy com Docker Compose (VPS)

Para deploy manual em VPS (DigitalOcean, AWS EC2, etc.).

### Pré-requisitos

- VPS com Ubuntu 20.04+ ou Debian 11+
- Docker e Docker Compose instalados
- Domínio configurado apontando para o IP do VPS
- SSL/TLS certificate (Let's Encrypt recomendado)

### Passo a Passo

#### 1. Preparar o Servidor

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin -y

# Criar usuário para deploy
sudo useradd -m -s /bin/bash odoo-deploy
sudo usermod -aG docker odoo-deploy
```

#### 2. Clonar Repositório

```bash
# Login como odoo-deploy
sudo su - odoo-deploy

# Clonar repo
git clone https://github.com/thedevkitchen/realestate-backend.git
cd realestate-backend/18.0
```

#### 3. Configurar Variáveis de Ambiente

```bash
# Copiar exemplo
cp .env.example .env

# Editar variáveis
nano .env
```

Preencha com valores de produção (ver seção Variáveis de Ambiente acima).

#### 4. Configurar Nginx Reverse Proxy

```bash
# Instalar Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Criar configuração
sudo nano /etc/nginx/sites-available/realestate
```

```nginx
server {
    listen 80;
    server_name torque-backoffice.thedevkitchen.com.br;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name torque-backoffice.thedevkitchen.com.br;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/torque-backoffice.thedevkitchen.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/torque-backoffice.thedevkitchen.com.br/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Increase upload limit
    client_max_body_size 100M;
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/realestate /etc/nginx/sites-enabled/

# Obter certificado SSL
sudo certbot --nginx -d torque-backoffice.thedevkitchen.com.br

# Testar configuração
sudo nginx -t

# Reiniciar Nginx
sudo systemctl restart nginx
```

#### 5. Subir a Aplicação

```bash
# Usar docker-compose de produção
docker compose -f docker-compose-production.yml up -d

# Ver logs
docker compose logs -f odoo

# Verificar status
docker compose ps
```

#### 6. Configurar Backup Automático

```bash
# Criar script de backup
nano ~/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup do banco de dados
docker compose exec -T db pg_dump -U odoo realestate > "$BACKUP_DIR/db_$DATE.sql"

# Backup do filestore
tar -czf "$BACKUP_DIR/filestore_$DATE.tar.gz" ./filestore

# Manter apenas últimos 7 dias
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Dar permissão
chmod +x ~/backup.sh

# Adicionar ao cron (backup diário às 2h)
crontab -e
0 2 * * * /home/odoo-deploy/backup.sh >> /var/log/backup.log 2>&1
```

#### 7. Monitoramento

```bash
# Instalar monitoring stack
cd observability
docker compose up -d

# Acessar Grafana
# https://grafana.torque-backoffice.thedevkitchen.com.br
```

---

## 🚀 CI/CD Pipeline (GitHub Actions)

### Workflow Automático

Crie `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.7.0
        with:
          ssh-private-key: ${{ secrets.SSH_PRIVATE_KEY }}
      
      - name: Deploy to server
        run: |
          ssh -o StrictHostKeyChecking=no odoo-deploy@${{ secrets.SERVER_IP }} << 'EOF'
            cd realestate-backend
            git pull origin main
            cd 18.0
            docker compose -f docker-compose-production.yml down
            docker compose -f docker-compose-production.yml up -d --build
            docker compose -f docker-compose-production.yml exec -T odoo odoo-bin -u all -d realestate --stop-after-init
          EOF
      
      - name: Verify deployment
        run: |
          curl -f https://torque-backoffice.thedevkitchen.com.br/web/health || exit 1
      
      - name: Notify success
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deploy to production completed successfully!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Secrets Necessários

Configure no GitHub:
- `SSH_PRIVATE_KEY` - Chave SSH para acessar o servidor
- `SERVER_IP` - IP do servidor de produção
- `SLACK_WEBHOOK` - Webhook do Slack para notificações

---

## 🔒 Checklist de Segurança

Antes de ir para produção:

### Aplicação
- [ ] Alterar senha padrão do admin
- [ ] Configurar JWT_SECRET_KEY forte
- [ ] Configurar SESSION_SECRET forte
- [ ] Desabilitar modo debug (`debug = False`)
- [ ] Configurar rate limiting
- [ ] Ativar HTTPS/SSL
- [ ] Configurar CORS adequadamente

### Database
- [ ] Alterar senha do PostgreSQL
- [ ] Desabilitar acesso externo (apenas localhost)
- [ ] Configurar backup automático
- [ ] Limitar connections
- [ ] Configurar SSL para conexões

### Redis
- [ ] Configurar senha (requirepass)
- [ ] Limitar max memory
- [ ] Configurar persistência (AOF or RDB)
- [ ] Desabilitar comandos perigosos

### RabbitMQ
- [ ] Alterar senha padrão
- [ ] Configurar vhosts separados
- [ ] Limitar connections
- [ ] Ativar SSL/TLS

### Servidor
- [ ] Configurar firewall (UFW)
- [ ] Desabilitar senha SSH (apenas key)
- [ ] Configurar fail2ban
- [ ] Atualizar sistema regularmente
- [ ] Configurar monitoramento

---

## 📊 Monitoramento em Produção

### Métricas Importantes

1. **Application Metrics**
   - Response time (p50, p95, p99)
   - Error rate
   - Request rate
   - Active sessions

2. **Database Metrics**
   - Query time
   - Connection pool usage
   - Cache hit ratio
   - Disk usage

3. **Infrastructure Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network traffic

### Alertas Recomendados

```yaml
# Grafana Alerts
- name: High Error Rate
  condition: error_rate > 5%
  for: 5m
  severity: critical

- name: High Response Time
  condition: response_time_p95 > 2s
  for: 5m
  severity: warning

- name: Database Connection Pool Full
  condition: db_connections > 90%
  for: 1m
  severity: critical

- name: Disk Usage High
  condition: disk_usage > 80%
  for: 10m
  severity: warning
```

---

## 🆘 Troubleshooting

### Aplicação não inicia

```bash
# Ver logs
docker compose logs -f odoo

# Verificar configuração
docker compose config

# Verificar recursos
docker stats
```

### Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
docker compose ps db

# Testar conexão
docker compose exec db psql -U odoo -d realestate

# Ver logs do PostgreSQL
docker compose logs -f db
```

### Performance lenta

```bash
# Ver queries lentas
docker compose exec db psql -U odoo -d realestate -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Verificar cache hit ratio
docker compose exec redis redis-cli INFO stats | grep hit

# Ver workers Celery
docker compose exec flower flower
```

### Restaurar Backup

```bash
# Parar aplicação
docker compose down

# Restaurar banco
cat backup.sql | docker compose exec -T db psql -U odoo -d realestate

# Restaurar filestore
tar -xzf filestore_backup.tar.gz -C ./filestore

# Subir aplicação
docker compose up -d
```

---

## 📚 Recursos Adicionais

### Documentação Oficial
- [Odoo Deployment](https://www.odoo.com/documentation/18.0/administration/deploy.html)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)

### Guias Internos
- [Production Setup Guide](../../18.0/PRODUCTION_SETUP.md)
- [Dokploy Deploy Guide](../../18.0/DOKPLOY_DEPLOY.md)

### Suporte
- **Slack:** #realestate-devops
- **Email:** devops@thedevkitchen.com.br

---

## 📚 Próximos Passos

- [Capítulo 1: Quick Start](01-quick-start.md) - Desenvolvimento local
- [Capítulo 3: Ambientes](03-environments.md) - URLs dos ambientes
- [Voltar ao Índice](00-index.md)

---

*Última atualização: 27 de março de 2026*
