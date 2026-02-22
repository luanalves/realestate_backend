# Envio de Emails no Odoo 18 — Guia Definitivo

🎯 **Lições aprendidas com o sistema de envio de emails no Odoo 18.0**

Este documento registra os problemas encontrados e as soluções definitivas para envio de emails programático no Odoo 18, especialmente usando `mail.template` e `mail.mail`.

---

## 📋 Índice

1. [Problema Central](#problema-central)
2. [Como o Odoo 18 Renderiza Templates](#como-o-odoo-18-renderiza-templates)
3. [Armadilhas Comuns](#armadilhas-comuns)
4. [Solução Recomendada: mail.mail.create()](#solução-recomendada-mailmailcreate)
5. [Referência: mail.template.send_mail()](#referência-mailtemplatesend_mail)
6. [Checklist de Troubleshooting](#checklist-de-troubleshooting)

---

## Problema Central

Ao usar `mail.template.send_mail()` no Odoo 18, variáveis como `${object.name}`, `${ctx.get('invite_link')}` podem **não ser renderizadas**, chegando como texto literal no email final.

**Sintoma**: Email é enviado (aparece no MailHog/SMTP), mas o corpo contém `${object.name}` em vez do nome real do usuário.

**Causa raiz**: O Odoo 18 possui dois modos de renderização no engine `inline_template`, e o roteamento entre eles depende do tipo de expressão e das permissões do usuário.

---

## Como o Odoo 18 Renderiza Templates

### Arquivo-chave
```
/usr/lib/python3/dist-packages/odoo/addons/mail/models/mail_render_mixin.py
```

### Os dois modos de renderização

O método `_render_template_inline_template()` (linha ~432) possui dois caminhos:

#### 1. Regex Mode (modo restrito/seguro)
```python
if not self._has_unsafe_expression_template_inline_template(str(template_txt), model):
    return self._render_template_inline_template_regex(str(template_txt), model, res_ids)
```

- **Quando**: Todas as expressões são "seguras" (apenas `object.campo.subcampo`)
- **Como funciona**: Usa `reduce()` para resolver `object.field1.field2` diretamente nos campos do record
- **Limitação**: **NÃO suporta `ctx.get()`**, funções, ou qualquer expressão que não seja `object.X.Y.Z`
- **Não requer** permissões especiais

#### 2. Full Mode (modo completo/unsafe)
```python
if (not self._unrestricted_rendering
    and not self.env.is_admin()
    and not self.env.user.has_group('mail.group_mail_template_editor')):
    raise AccessError(...)
```

- **Quando**: Detecta expressões "unsafe" como `ctx.get()`, chamadas de função, etc.
- **Requisito**: O usuário precisa ser admin **OU** membro do grupo `mail.group_mail_template_editor`
- **Se não tiver permissão**: Levanta `AccessError`
- **Se estiver dentro de try/except**: O erro é **silenciado** e o email é enviado com variáveis literais

### O que é considerado "unsafe"?

O método `_has_unsafe_expression_template_inline_template()` usa `ir.qweb._is_expression_allowed()` para verificar cada expressão. Expressões que **falham** na validação:

| Expressão | Status | Motivo |
|-----------|--------|--------|
| `${object.name}` | ✅ Segura | Acesso direto a campo |
| `${object.company_id.name}` | ✅ Segura | Navegação de campos |
| `${object.company_id.name or 'Default'}` | ❌ Unsafe | Operador `or` |
| `${ctx.get('invite_link')}` | ❌ Unsafe | Chamada de função |
| `${object.email or 'fallback'}` | ❌ Unsafe | Operador `or` |

> **Conclusão**: Qualquer expressão com `or`, `and`, `.get()`, ou chamadas de função é marcada como "unsafe" e requer permissões especiais para renderização.

---

## Armadilhas Comuns

### 1. Campo `lang` no template XML
```xml
<!-- ❌ NÃO FAZER - causa "Invalid language code: ${object.lang}" -->
<field name="lang">${object.lang}</field>

<!-- ✅ SOLUÇÃO - não incluir o campo lang -->
<!-- Simplesmente omita a tag <field name="lang"> -->
```

O campo `lang` é avaliado **antes** da renderização do template pelo Odoo, então `${object.lang}` é passado literalmente como código de idioma, causando erro.

### 2. send_mail() engole erros silenciosamente
```python
# ❌ PERIGOSO - não detecta falha de renderização
template.with_context(ctx).send_mail(
    user.id,
    force_send=False,
    raise_exception=False,  # Erros de renderização são silenciados!
)
```

Mesmo com `raise_exception=False`, o `send_mail()` pode:
- Criar `mail.mail` com variáveis não renderizadas
- Retornar um ID válido (parece ter funcionado)
- Log mostra "email sent" mas conteúdo está errado

### 3. `generate_email()` não existe no Odoo 18
```python
# ❌ NÃO EXISTE no Odoo 18
template.generate_email(user.id, ['body_html', 'subject'])
# AttributeError: 'mail.template' has no attribute 'generate_email'

# ✅ O equivalente no Odoo 18 é:
template._generate_template([user.id], ('body_html', 'subject'))
```

### 4. `complete_name` não existe em `res.groups` no Odoo 18
```python
# ❌ NÃO EXISTE no Odoo 18
groups = user.groups_id.mapped('complete_name')
# KeyError: 'complete_name'

# ✅ full_name também não é campo stored - use IDs
group_ids = user.groups_id.ids
group = self.env.ref('module.xml_id')
if group.id in group_ids:
    ...
```

### 5. Templates com `noupdate="1"` no XML
```xml
<data noupdate="1">
    <record id="email_template_user_invite" model="mail.template">
```

Templates com `noupdate="1"` **não são atualizados** ao fazer `-u module`. Para forçar atualização:

```sql
-- 1. Deletar referências
DELETE FROM ir_model_data 
WHERE module = 'thedevkitchen_user_onboarding' AND model = 'mail.template';

-- 2. Deletar templates
DELETE FROM mail_template WHERE model = 'res.users';

-- 3. Atualizar módulo
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d realestate -u thedevkitchen_user_onboarding --stop-after-init
```

---

## Solução Recomendada: mail.mail.create()

Em vez de usar `mail.template.send_mail()`, construa o HTML em Python e crie `mail.mail` diretamente:

### Exemplo: Envio de Convite
```python
def send_invite_email(self, user, raw_token, expires_hours, frontend_base_url):
    """
    Envia email de convite criando mail.mail diretamente.
    
    Odoo 18's inline_template engine restringe ctx.get() em modo regex
    (usuários não-admin). Contornamos renderizando o HTML em Python.
    """
    try:
        invite_link = f"{frontend_base_url}/set-password?token={raw_token}"
        user_name = user.name or user.login
        company_name = user.company_id.name or 'Sistema Imobiliário'
        company_email = user.company_id.email or 'noreply@thedevkitchen.com'

        subject = f"Convite para Criar Senha - {company_name}"
        body_html = f"""
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #007bff; color: white; padding: 20px; text-align: center;">
        <h2>Bem-vindo(a) ao Sistema</h2>
    </div>
    <div style="padding: 30px; background-color: #f9f9f9;">
        <p>Olá, <strong>{user_name}</strong>!</p>
        <p>Para criar sua senha, clique abaixo:</p>
        <p style="text-align: center;">
            <a href="{invite_link}" style="display: inline-block; padding: 12px 24px; 
               background-color: #28a745; color: white; text-decoration: none; 
               border-radius: 4px;">Criar Minha Senha</a>
        </p>
        <p><strong>⚠️ Este link expira em {expires_hours} horas.</strong></p>
    </div>
</div>
"""
        # Criar e enviar mail.mail diretamente
        mail = self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': company_email,
            'email_to': user.email or user.login,
            'auto_delete': True,
        })
        mail.send()

        _logger.info(f'Invite email sent to {user.email}')
        return True

    except Exception as e:
        _logger.error(f'Failed to send invite email to {user.email}: {e}')
        return False
```

### Por que funciona?
- `mail.mail.create()` não passa pelo engine de renderização de templates
- O HTML já vem com todas as variáveis preenchidas via f-string do Python
- `mail.send()` apenas envia o conteúdo, sem tentar renderizar
- Funciona com qualquer usuário, sem necessidade de permissões especiais

### Quando usar mail.template vs mail.mail?

| Cenário | Recomendação |
|---------|-------------|
| Templates com apenas `${object.campo}` (sem `or`, `get`, etc.) | `mail.template.send_mail()` funciona |
| Templates com `ctx.get()`, `or`, funções | **Usar `mail.mail.create()`** |
| Usuário executando é sempre admin | `mail.template.send_mail()` funciona |
| Usuário executando é não-admin | **Usar `mail.mail.create()`** |
| Precisa de tradução multi-idioma | `mail.template` com expressões simples |
| Email transacional (convite, reset) | **Usar `mail.mail.create()`** |

---

## Referência: mail.template.send_mail()

### Assinatura (Odoo 18)
```python
def send_mail(self, res_id, force_send=False, raise_exception=False, 
              email_values=None, email_layout_xmlid=False):
```

### Parâmetros
| Param | Tipo | Descrição |
|-------|------|-----------|
| `res_id` | int | ID do record para renderizar template |
| `force_send` | bool | Enviar imediatamente (vs. fila) |
| `raise_exception` | bool | Levantar exceção em falha SMTP |
| `email_values` | dict | Sobrescrever valores gerados |
| `email_layout_xmlid` | str | Layout de notificação |

### Pipeline de renderização
```
send_mail()
  └─ send_mail_batch()
       └─ _generate_template()
            └─ _classify_per_lang()
                 └─ _render_field(field, res_ids)
                      └─ _render_template(template[field], model, res_ids)
                           ├─ Se expressões "seguras": _render_template_inline_template_regex()
                           └─ Se expressões "unsafe": _render_template_inline_template()
                                ├─ Se admin/template_editor: renderiza com safe_eval
                                └─ Se não: AccessError (silenciado pelo try/except)
```

---

## Checklist de Troubleshooting

Quando emails não renderizam variáveis:

- [ ] **Verificar logs do Odoo**: `docker compose logs odoo --tail=50 | grep -E "email|mail|ERROR|template|lang"`
- [ ] **Verificar MailHog**: `curl -s 'http://localhost:8025/api/v2/messages'` — procurar por `${` no body
- [ ] **Campo `lang` existe no template?** → Remover `<field name="lang">`
- [ ] **Template usa `ctx.get()` ou `or`?** → Migrar para `mail.mail.create()`
- [ ] **Usuário tem grupo `mail.group_mail_template_editor`?** → Verificar ou usar `sudo()`
- [ ] **Template foi atualizado no banco?** → Deletar e recriar (ver seção `noupdate`)
- [ ] **`raise_exception=False` esconde erros?** → Testar com `raise_exception=True` e verificar logs
- [ ] **body_html armazenado como JSON multilíngue?** → Normal no Odoo 18 (`{"en_US": "..."}`)

---

## Comandos Úteis

```bash
# Ver templates de email no banco
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, name, model, lang FROM mail_template WHERE model = 'res.users';"

# Ver emails pendentes na fila
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, subject, email_to, state FROM mail_mail ORDER BY id DESC LIMIT 10;"

# Verificar MailHog
curl -s 'http://localhost:8025/api/v2/messages' | python3 -m json.tool | head -50

# Forçar envio de emails na fila
docker compose exec db psql -U odoo -d realestate -c \
  "SELECT id, subject, state FROM mail_mail WHERE state = 'outgoing';"

# Deletar templates para recriar
docker compose exec db psql -U odoo -d realestate -c \
  "DELETE FROM ir_model_data WHERE module = 'SEU_MODULO' AND model = 'mail.template';"
docker compose exec db psql -U odoo -d realestate -c \
  "DELETE FROM mail_template WHERE model = 'SEU_MODELO';"
```

---

## Histórico

| Data | Evento |
|------|--------|
| 2026-02-21 | Descoberto que `send_mail()` não renderiza `ctx.get()` para não-admin |
| 2026-02-21 | Tentativas com `email_values`, `force_send`, `generate_email()` — todas falharam |
| 2026-02-22 | Identificada causa raiz: engine `inline_template` com dois modos (regex vs full) |
| 2026-02-22 | Solução: `mail.mail.create()` com HTML pré-renderizado em Python |
| 2026-02-22 | Validado: emails chegam no MailHog com todas as variáveis renderizadas |

---

> **Referência ADR**: Este conhecimento impacta qualquer endpoint que envie emails transacionais.
> Módulos afetados: `thedevkitchen_user_onboarding` (invite, reset-password, forgot-password).
