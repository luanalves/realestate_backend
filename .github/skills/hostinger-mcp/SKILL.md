---
name: hostinger-mcp
description: 'Manage Hostinger hosting resources via MCP (Model Context Protocol). Use for: deploy, hosting, VPS management, domain configuration, email accounts, database operations, FTP, SSL certificates, metrics monitoring, backup operations, website deployment. 119 tools available for complete hosting infrastructure management.'
argument-hint: 'Optional: specific Hostinger operation (e.g., "list websites", "check VPS status")'
---

# Hostinger MCP Server

Gerencia recursos de hospedagem Hostinger diretamente do VS Code através do protocolo MCP.

## What is Available

**MCP Server:** `hostinger-mcp`
**Total Tools:** 119 ferramentas disponíveis via `mcp_hostinger-mcp_*`
**Status:** ✅ Configurado e funcional

### Categories

- **VPS (Virtual Private Servers)**: Create, manage, monitor VPS instances
- **Domains**: Portfolio management, DNS configuration, nameservers
- **Websites**: List, deploy, configure websites and applications
- **Databases**: MySQL management, backups, users
- **Email**: Account management, quotas, forwarding
- **DNS**: Record management, snapshots, validation
- **Billing**: Subscriptions, invoices, payment methods
- **Hosting**: Static sites, JavaScript apps, WordPress deployments
- **Monitoring**: Metrics, logs, resource usage

## When to Use

### Trigger Keywords
- "hostinger", "hosting", "deploy", "hospedagem"
- "vps", "servidor", "virtual machine"
- "domain", "domínio", "dns"
- "email", "e-mail", "caixa de entrada"
- "database", "banco de dados", "mysql"
- "website", "site", "aplicação web"
- "ssl", "certificado", "https"
- "backup", "restore", "snapshot"
- "metrics", "métricas", "monitoramento"

### Common Use Cases

1. **Deploy Operations**
   - "Deploy a aplicação no Hostinger"
   - "Verificar espaço disponível no servidor"
   - "Checar status do VPS"

2. **Email Management**
   - "Criar conta de e-mail para equipe"
   - "Listar todas as contas de e-mail"
   - "Verificar quota de armazenamento"

3. **Database Operations**
   - "Criar banco de dados MySQL"
   - "Fazer backup do database"
   - "Verificar tamanho dos bancos"

4. **Domain & DNS**
   - "Configurar nameservers"
   - "Adicionar registro DNS"
   - "Verificar status do domínio"

5. **Monitoring**
   - "Checar uso de CPU e RAM"
   - "Ver logs de erro"
   - "Obter métricas de tráfego"

## How to Use

### Discovery

Para ver TODAS as ferramentas disponíveis:

```
Listar todas as ferramentas MCP do servidor Hostinger com descrição
```

Ou buscar ferramentas específicas:

```
Buscar ferramentas Hostinger relacionadas a VPS
Buscar ferramentas Hostinger relacionadas a email
Buscar ferramentas Hostinger relacionadas a DNS
```

### Natural Language

Você não precisa conhecer os nomes exatos das ferramentas. Use linguagem natural:

```
Mostrar todos os meus websites na Hostinger
Criar e-mail contato@example.com
Verificar uso de recursos do VPS
Listar bancos de dados MySQL
```

O agente automaticamente encontrará e usará as ferramentas MCP corretas.

### Tool Pattern

As ferramentas seguem o padrão: `mcp_hostinger-mcp_<category>_<operation>V1`

Exemplos:
- `mcp_hostinger-mcp_VPS_getVirtualMachinesV1`
- `mcp_hostinger-mcp_hosting_listWebsitesV1`
- `mcp_hostinger-mcp_domains_getDomainListV1`
- `mcp_hostinger-mcp_billing_getSubscriptionListV1`

## Configuration Details

**Location:** `.vscode/mcp.json` (gitignored)
**Server:** `hostinger-mcp`
**Command:** `npx hostinger-api-mcp@latest`
**Authentication:** API token via `API_TOKEN` environment variable

**Security:** 
- ⚠️ `.vscode/mcp.json` está no `.gitignore` (contém token)
- ⚠️ Nunca commitar tokens de API
- ✅ Token obtido em: https://hpanel.hostinger.com.br/api-keys

## Resources Available

### Current Hostinger Account

**VPS:**
- 1x KVM 2 (2 CPU, 8GB RAM, 100GB disk, Ubuntu 24.04 + Dokploy)
- IPv4: 148.230.76.211
- Hostname: srv1520050.hstgr.cloud

**Domains:**
- 1 free domain (pending_setup)

**Subscription:**
- KVM 2 plan
- R$ 1,067.88/year
- Active, renews 2027-03-08

## Comprehensive Guide

Para exemplos completos, casos de uso detalhados, troubleshooting e dicas pro, consulte:

📚 [MCP Hostinger Guide](.github/MCP_HOSTINGER_GUIDE.md)

## Troubleshooting

**Ferramentas não aparecem:**
1. Verificar se MCP está ativo: Copilot Chat → procurar por `mcp_hostinger`
2. Reiniciar VS Code completamente (Cmd+Q no macOS)
3. Verificar logs: Command Palette → "Developer: Show Logs" → "GitHub Copilot"

**Erro de autenticação:**
- Token pode estar expirado
- Gerar novo token no painel Hostinger
- Atualizar `.vscode/mcp.json` com novo token

**Servidor não inicia:**
- Verificar Node.js: `node --version` (requer Node.js 18+)
- Verificar npx: `which npx`
- Limpar cache: `npm cache clean --force`

## Examples

### Example 1: Quick Status Check

**Você:** Status atual da infra Hostinger

**Agent:** [usa mcp_hostinger-mcp_VPS_getVirtualMachinesV1 + mcp_hostinger-mcp_domains_getDomainListV1 + mcp_hostinger-mcp_billing_getSubscriptionListV1]

**Response:** 
- VPS: srv1520050.hstgr.cloud (running, 2 CPU, 8GB RAM)
- Domain: 1 pending setup
- Subscription: Active, KVM 2, expires 2027-03-08

### Example 2: Pre-Deploy Check

**Você:** Vou fazer deploy do Odoo. Verificar espaço e recursos disponíveis.

**Agent:** [usa mcp_hostinger-mcp_VPS_getVirtualMachinesV1 + mcp_hostinger-mcp_VPS_getMetricsV1]

**Response:**
- Disk: 45GB used / 100GB total (55GB available)
- RAM: 2.1GB / 8GB (74% available)
- CPU: 15% usage
- ✅ Recursos suficientes para deploy

### Example 3: Email Setup

**Você:** Criar e-mails para equipe: admin@realestate.com.br, vendas@realestate.com.br

**Agent:** [usa mcp_hostinger-mcp_hosting_listWebsitesV1 (verificar domínio) + cria contas]

**Response:**
- ✅ admin@realestate.com.br criado
- ✅ vendas@realestate.com.br criado
- Senhas geradas e enviadas por e-mail

## Best Practices

1. **Combine Operações**: "Deploy, testar, e fazer backup se tudo ok"
2. **Use Contexto**: "Verificar logs do domínio X" vs apenas "Verificar logs"
3. **Automatize Workflows**: Encadeie operações complexas em instruções simples
4. **Monitore Proativamente**: Configure checks regulares de métricas e logs

## Integration with Project

Este skill é particularmente útil para:

- **Feature 009 (User Onboarding)**: Deploy de atualizações, monitoramento de email delivery
- **VPS Management**: Monitorar recursos antes de escalonamento
- **Backup Strategy**: Automatizar backups antes de deploys críticos
- **Email System**: Gerenciar contas de notificação do sistema
- **Domain Setup**: Configurar DNS para ambientes staging/production

## Related Documentation

- [Hostinger API Documentation](https://developers.hostinger.com/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [VS Code MCP Documentation](https://code.visualstudio.com/docs/copilot/copilot-extensibility-overview)
- [Hostinger MCP Server (GitHub)](https://github.com/tomaszstankowski/hostinger-api-mcp)
