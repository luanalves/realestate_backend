# ADR-023: MailHog para Testes de Email em Desenvolvimento

## Status
Aceito

## Contexto

O sistema de gestão imobiliária possui funcionalidades críticas que dependem de envio de emails, especialmente o módulo **Feature 009 (User Onboarding & Password Management)** que implementa:

- Convites de usuários com links de ativação
- Recuperação de senha (forgot password)
- Redefinição de senha (reset password)
- Notificações de sistema

Durante o desenvolvimento e testes locais, surgiram os seguintes problemas:

### Problema 1: Timeout com Servidores SMTP Reais (Gmail)

Ao tentar configurar o Gmail SMTP em ambiente Docker local:

```
ERROR: Connection unexpectedly closed: timed out
Traceback: smtp.gmail.com:587 - 60s timeout
```

**Causas identificadas:**
- **Restrições de firewall/DNS:** Ambientes Docker em macOS (especialmente M1/M2) têm limitações de rede que bloqueiam conexões TLS/SSL
- **Requisitos do Gmail:** Exige 2FA + App Password + TLS 1.2+, complexo para configuração de desenvolvimento
- **Rate limits:** Gmail limita envios por hora, inadequado para testes automatizados
- **Segurança:** Expor credenciais reais do Gmail em desenvolvimento viola princípios de segurança

### Problema 2: Risco de Envio Acidental de Emails em Desenvolvimento

Durante testes de API e E2E:
- **162 cenários de teste** do RBAC (18 scenarios × 9 profiles)
- **6 scripts de integração** do Feature 009
- **Testes de Cypress UI**

Usar SMTP real resultaria em:
- ❌ Envio de emails de teste para usuários reais
- ❌ Risco de spam/blacklist do domínio
- ❌ Impossibilidade de inspecionar conteúdo dos emails enviados
- ❌ Logs poluídos com falhas de SMTP

### Problema 3: Necessidade de Validação Visual de Templates

Os templates HTML possuem:
- Inline styles para compatibilidade com clientes de email
- Variáveis dinâmicas (`${object.name}`, `${ctx.get('invite_link')}`)
- Conteúdo em português (pt_BR)
- Branding customizado (TheDevKitchen)

**Requisito:** Validar visualmente o HTML renderizado antes de produção.

---

## Decisão

Adotar **MailHog** como servidor SMTP para **ambiente de desenvolvimento** com as seguintes características:

### Solução Implementada

```yaml
# docker-compose.yml
mailhog:
  image: mailhog/mailhog:latest
  container_name: mailhog
  ports:
    - "1025:1025"  # SMTP server
    - "8025:8025"  # Web UI
  networks:
    - odoo-net
```

### Configuração no Odoo

```ini
# Outgoing Mail Server
SMTP Server: mailhog
SMTP Port: 1025
Connection Security: None
Username: (empty)
Password: (empty)
```

### Fluxo de Funcionamento

```
┌─────────┐     SMTP 1025      ┌─────────┐
│  Odoo   │ ──────────────────▶│ MailHog │
│ Feature │                     │         │
│   009   │                     │ Capture │
└─────────┘                     └─────────┘
                                     │
                                     │ Storage
                                     ▼
                            ┌─────────────────┐
                            │   Web UI :8025  │
                            │ - Visualizar    │
                            │ - Inspecionar   │
                            │ - Validar HTML  │
                            └─────────────────┘
```

### Características do MailHog

**Vantagens:**
1. ✅ **Zero configuração:** Sem credenciais, sem SSL/TLS
2. ✅ **Captura completa:** Captura todos os emails sem enviar
3. ✅ **Interface web:** Visualização instantânea em http://localhost:8025
4. ✅ **Inspeção detalhada:** Headers, HTML source, Plain text, attachments
5. ✅ **API REST:** Permite automação de testes (validar emails enviados)
6. ✅ **Sem persistência:** Emails perdidos ao reiniciar (limpa ambiente automaticamente)
7. ✅ **Leve:** ~10MB de memória, startup instantâneo

**Limitações (aceitáveis para desenvolvimento):**
- ⚠️ Não valida entregabilidade real (SPF/DKIM/DMARC)
- ⚠️ Não simula delays de rede/servidores remotos
- ⚠️ Não suporta webhooks/callbacks de delivery

---

## Consequências

### Positivas

#### 1. Velocidade de Desenvolvimento
- **Antes:** 60s timeout + retry = ~3min por teste de email
- **Depois:** <100ms para enviar + visualização instantânea
- **Ganho:** ~97% redução no tempo de teste

#### 2. Segurança
- ✅ Sem credenciais reais expostas em arquivos de configuração
- ✅ Sem risco de leak de emails para destinatários reais
- ✅ Isolamento completo de ambiente de desenvolvimento

#### 3. Qualidade de Testes
- ✅ Validação visual de templates HTML
- ✅ Inspeção de headers (From, To, Subject, Content-Type)
- ✅ Verificação de variáveis dinâmicas renderizadas
- ✅ Teste de links de ativação/reset password

#### 4. Experiência do Desenvolvedor
```bash
# Teste rápido após cada mudança
curl -X POST http://localhost:8069/api/v1/users/invite \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"email": "test@example.com", ...}'

# Verificar email instantaneamente
open http://localhost:8025
```

#### 5. CI/CD Pronto
MailHog pode rodar em pipelines CI:
```yaml
# .github/workflows/test.yml
services:
  mailhog:
    image: mailhog/mailhog
    ports:
      - 1025:1025
      - 8025:8025
```

### Negativas

#### 1. Dependência Adicional
- **Impacto:** +1 container no `docker-compose.yml`
- **Mitigação:** MailHog é opcional (desenvolvimento local), produção usa SMTP real

#### 2. Divergência Produção vs Desenvolvimento
- **Impacto:** Configuração SMTP diferente entre ambientes
- **Mitigação:** Documentar configuração de produção no README.md (Gmail/SendGrid)

#### 3. Não Valida Compliance Email (SPF/DKIM)
- **Impacto:** Não detecta problemas de deliverabilidade em produção
- **Mitigação:** Usar staging com SMTP real antes de deploy final

---

## Implementação

### Verificação Rápida

```bash
# 1. Start MailHog
docker compose up -d mailhog

# 2. Verificar status
docker compose ps mailhog
# STATUS: Up (healthy)

# 3. Testar conectividade
docker compose exec odoo python3 -c "
import smtplib
smtp = smtplib.SMTP('mailhog', 1025, timeout=5)
print('✅ MailHog conectado')
smtp.quit()
"

# 4. Acessar interface
open http://localhost:8025
```

### Configuração Feature 009

```python
# thedevkitchen_email_link_settings
frontend_base_url = "http://localhost:3000"
invite_link_ttl_hours = 24
reset_link_ttl_hours = 24

# Emails gerados:
# http://localhost:3000/auth/set-password?token={uuid}
# http://localhost:3000/auth/reset-password?token={uuid}
```

---

## Alternativas Consideradas

### 1. Gmail SMTP Direto
- ❌ Rejeitado: Timeout de 60s, requer App Password, limitações de rede Docker
- ❌ Complexidade: 2FA + OAuth + firewall configuration
- ❌ Rate limits: 500 emails/dia (insuficiente para testes)

### 2. Mailtrap
- ✅ Vantagens: Interface profissional, análise de spam score, suporte a múltiplos inboxes
- ❌ Desvantagens: Requer cadastro/API key, limite de 500 emails/mês no free tier
- ❌ Complexidade: Credenciais adicionais, não funciona offline

### 3. FakeSMTP
- ✅ Vantagens: Java standalone, salva emails em arquivos
- ❌ Desvantagens: Interface desktop (não web), Java runtime obrigatório, sem API REST

### 4. smtp4dev (.NET)
- ✅ Vantagens: Similar ao MailHog, interface moderna
- ❌ Desvantagens: Requer .NET runtime, menos adoção (261 stars vs 14k do MailHog)

**Decisão:** MailHog venceu por simplicidade, maturidade e adoção da comunidade.

---

## Migração para Produção

### Configuração Recomendada (Produção)

**Opção 1: Gmail Business/Workspace**
```ini
SMTP Server: smtp.gmail.com
SMTP Port: 587
Connection Security: STARTTLS
Username: noreply@company.com
Password: [App Password]
```

**Opção 2: SendGrid (Recomendado)**
```ini
SMTP Server: smtp.sendgrid.net
SMTP Port: 587
Connection Security: STARTTLS
Username: apikey
Password: [SendGrid API Key]
# Capacidade: 100 emails/dia (free), 40k/dia (paid)
```

**Opção 3: Amazon SES**
```ini
SMTP Server: email-smtp.us-east-1.amazonaws.com
SMTP Port: 587
Connection Security: STARTTLS
Username: [SMTP Username]
Password: [SMTP Password]
# Capacidade: 62k emails/mês (free tier)
```

### Checklist Produção

- [ ] Configurar DNS SPF record: `v=spf1 include:_spf.google.com ~all`
- [ ] Configurar DKIM no provedor de email
- [ ] Testar deliverabilidade com [mail-tester.com](https://www.mail-tester.com/)
- [ ] Configurar limites de rate (evitar blacklist)
- [ ] Monitorar bounce rate e spam complaints
- [ ] Backup de credenciais SMTP em vault seguro (AWS Secrets Manager, Vault)

---

## Referências

- MailHog GitHub: https://github.com/mailhog/MailHog
- Odoo Mail Server Configuration: https://www.odoo.com/documentation/18.0/applications/general/email_communication/email_servers.html
- Feature 009 Specification: `specs/009-user-onboarding-password-management/`
- ADR-011: Controller Security Authentication Storage
- ADR-016: Postman Collection Standards

---

## Histórico

- **2026-02-17:** ADR criado após resolução de timeout SMTP com Gmail
- **Commit:** `e82c443` - feat: Add MailHog service for email testing in development
- **Autor:** TheDevKitchen
- **Contexto:** Feature 009 - User Onboarding & Password Management
