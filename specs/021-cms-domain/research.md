# Research: CMS Domain (021)

**Date**: 2026-05-24
**Branch**: `021-cms-domain`

---

## RES-001 — `@require_jwt` sem session/company na rota pública

**Contexto**: A rota pública `GET /api/v1/public/cms/:company_slug/pages/:page_slug` deve reutilizar o JWT existente mas sem exigir sessão de usuário nem company via cabeçalho — a company é resolvida pelo `company_slug` na URL.

**Investigação**: Analisado `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`.

`@require_jwt` valida o token Bearer contra `thedevkitchen.oauth.token`, seta `request.jwt_token` e `request.jwt_application`, e retorna 401 se inválido/expirado/revogado. Ele **não depende de sessão de usuário** — funciona com tokens de aplicação (Client Credentials). `@require_session` e `@require_company` são decoradores separados e independentes.

**Decisão**: Usar somente `@require_jwt` na rota pública. A company é resolvida dentro do controller via `env['thedevkitchen.cms.settings'].sudo().search([('company_slug', '=', company_slug)], limit=1)`. O endpoint tem `auth='none'` no `@http.route` (padrão do projeto para rotas que gerenciam auth manualmente).

**Rationale**: Sem reinventar a roda. O mecanismo de token já existe e já valida expiração, revogação e tipo. Usar `auth='none'` + `@require_jwt` é o padrão estabelecido para todos os endpoints do projeto.

**Alternatives considered**: (1) Endpoint completamente anônimo sem token → rejeitado (spec SC-009 exige 401 sem JWT). (2) Criar novo mecanismo de "integration token" → rejeitado pelo usuário na sessão speckit.clarify.

---

## RES-002 — `created_at` / `updated_at` no Odoo ORM

**Contexto**: A spec exige `created_at` e `updated_at` na tabela de páginas.

**Investigação**: Odoo ORM fornece automaticamente em **todos** os modelos:
- `create_date` (Datetime, read-only) — preenchido na criação
- `write_date` (Datetime, read-only) — atualizado em todo `write()`

Confirmado em uso no projeto: `lead.create_date`, `lead.write_date` em `quicksol_estate/controllers/lead_api.py` e `att.create_date` em `property_attachments_controller.py`.

**Decisão**: **Não criar campos customizados** `created_at`/`updated_at`. Usar os campos nativos do Odoo e expô-los na resposta da API com os nomes `created_at` e `updated_at`:
```python
"created_at": page.create_date.strftime("%Y-%m-%dT%H:%M:%SZ") if page.create_date else None,
"updated_at": page.write_date.strftime("%Y-%m-%dT%H:%M:%SZ") if page.write_date else None,
```

**Rationale**: Zero overhead no schema do banco. Consistência com o padrão já usado em lead_api.py e property_attachments_controller.py.

**Alternatives considered**: Campos customizados `created_at` / `updated_at` com `default=fields.Datetime.now` → rejeitado por ser redundante com campos nativos do Odoo.

---

## RES-003 — Relação 1:1 (Content em tabela separada) no Odoo

**Contexto**: `thedevkitchen.cms.page.content` deve estar em tabela separada com relação 1:1 com `thedevkitchen.cms.page`.

**Investigação**: Odoo não tem campo `One2one` nativo. O padrão estabelecido para relação 1:1 é:

**Opção A (escolhida)**: `One2many` no parent com `limit=1` via computed field:
```python
# Em cms.page:
content_ids = fields.One2many('thedevkitchen.cms.page.content', 'page_id', string='Content')
content_body = fields.Text(related='content_ids.content', string='Content Body')
# Em cms.page.content:
page_id = fields.Many2one('thedevkitchen.cms.page', required=True, ondelete='cascade')
content = fields.Text(string='Content (Puck JSON)')
_sql_constraints = [('unique_page', 'UNIQUE(page_id)', 'One content record per page')]
```

**Criação automática**: Service layer cria o `cms.page.content` imediatamente no `POST` com `content=None` (clarificado em speckit.clarify Q4).

**Acesso no service layer**:
```python
content_record = page.content_ids[:1]  # sempre existe após criação
content_record.write({'content': json_body})
return content_record.content  # pode ser None
```

**Decisão**: Usar `One2many` + `UNIQUE(page_id)` constraint + criação atômica no service layer.

**Rationale**: Padrão Odoo nativo, sem extensões. A constraint SQL garante a invariante 1:1. A criação no `POST` garante que o join sempre funciona sem lógica condicional.

**Alternatives considered**: (1) Lazy creation → rejeitado na clarificação Q4. (2) Campo computed `Text` sem tabela separada → não resolve o problema de performance em listagens.

---

## RES-004 — Validação de CSS Injection

**Contexto**: `custom_css` deve ser validado contra padrões de injeção antes de persistir.

**Investigação**: Padrões de CSS injection relevantes para ambientes web:
- `expression(...)` — IE CSS expressions (execução de JS via CSS)
- `behavior: url(...)` — IE behaviours
- `url(javascript:...)` — JavaScript em valores CSS
- `-moz-binding:` — XBL bindings no Firefox
- `@import url(...)` — carregamento de CSS externo malicioso

**Decisão**: Implementar via regex em `@api.constrains` no modelo e replicar no service layer para 422 antes de persistir:
```python
import re
CSS_INJECTION_PATTERNS = [
    re.compile(r'expression\s*\(', re.IGNORECASE),
    re.compile(r'behavior\s*:', re.IGNORECASE),
    re.compile(r'url\s*\(\s*["\']?\s*javascript:', re.IGNORECASE),
    re.compile(r'-moz-binding\s*:', re.IGNORECASE),
    re.compile(r'@import\b', re.IGNORECASE),
]
```

**Rationale**: Patterns cobrem os vetores conhecidos de CSS injection sem ser over-restrictive para CSS legítimo. Validação em dois lugares (model constraint + service layer) garante que nem bypass via ORM direto funciona.

---

## RES-005 — Validação do Content Puck JSON

**Contexto**: `content` deve ser JSON válido e ≤ 512KB. O backend não valida a estrutura interna do Puck JSON.

**Investigação**: Puck JSON é um objeto estruturado pelo `@measured/puck` frontend. O backend não conhece o schema. A spec define apenas:
1. JSON sintaxe válida
2. Tamanho ≤ 512KB (524.288 bytes)

**Decisão**:
```python
MAX_CONTENT_SIZE = 524_288  # 512KB — product constant, not configurable

def _validate_content(content_str):
    if content_str is None:
        return  # null é permitido (página sem conteúdo ainda)
    size = len(content_str.encode('utf-8'))
    if size > MAX_CONTENT_SIZE:
        raise ValidationError({
            "error": "content_too_large",
            "max_size_bytes": MAX_CONTENT_SIZE,
            "received_size": size,
        })
    try:
        json.loads(content_str)
    except json.JSONDecodeError:
        raise ValidationError({"error": "content_invalid_json"})
```

Usar `len(str.encode('utf-8'))` para contar bytes reais (não caracteres Unicode). Limite como constante de módulo (padrão ADR-017 para limites de produto, não configurável via `ir.config_parameter`).

**Alternatives considered**: Validação via `@api.constrains` no modelo `cms.page.content` → possível, mas melhor no service layer para retornar 422 JSON antes de tocar no ORM.

---

## RES-006 — Módulo Naming e Estrutura (ADR-004)

**Contexto**: ADR-004 define convenções de nomenclatura para módulos e tabelas.

**Decisão**:
- **Módulo**: `thedevkitchen_cms` (em `18.0/extra-addons/thedevkitchen_cms/`)
- **Tabelas** (mapeadas de `_name`):
  - `thedevkitchen.cms.page` → `thedevkitchen_cms_page`
  - `thedevkitchen.cms.page.content` → `thedevkitchen_cms_page_content`
  - `thedevkitchen.cms.template` → `thedevkitchen_cms_template`
  - `thedevkitchen.cms.template.content` → `thedevkitchen_cms_template_content`
  - `thedevkitchen.cms.media` → `thedevkitchen_cms_media`
  - `thedevkitchen.cms.settings` → `thedevkitchen_cms_settings`

---

## RES-007 — Hard Delete de Mídia (ADR-015 Exception)

**Contexto**: `thedevkitchen.cms.media` usa hard delete — exceção ao padrão de soft delete (ADR-015).

**Investigação**: Feature 017 (Property Attachments) já estabeleceu este padrão e está documentado na Constitution v1.7.0:
> "Hard-Delete Exception: `ir.attachment.unlink()` is permissible for binary blobs to reclaim disk. Always document the ADR-015 exception explicitly in the spec/contract."

**Decisão**: Seguir exatamente o padrão da Feature 017. Override de `unlink()` no model para garantir que `ir.attachment` também é deletado:
```python
def unlink(self):
    attachments = self.mapped('attachment_id')
    res = super().unlink()
    attachments.sudo().unlink()
    return res
```

Documentar com comentário `# ADR-015 exception: hard delete for binary blobs (see constitution v1.7.0)`.

---

## RES-008 — python-magic (MIME validation)

**Contexto**: Validação de MIME por conteúdo real (magic bytes) para uploads de mídia.

**Investigação**: Feature 017 já introduziu `python-magic` no Dockerfile. Padrão estabelecido na Constitution v1.7.0:
> "Magic Bytes MIME: Use python-magic to detect MIME from file content (not extension). Separate whitelists per attachment_type."

**Decisão**: Reutilizar exatamente o mesmo padrão da Feature 017. Whitelists por tipo:
```python
MIME_WHITELIST = {
    'image': {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'},
    'video': {'video/mp4', 'video/webm', 'video/ogg'},
    'document': {'application/pdf', 'application/msword',
                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
}
SIZE_LIMITS = {
    'image': 10 * 1024 * 1024,    # 10MB
    'video': 100 * 1024 * 1024,   # 100MB
    'document': 20 * 1024 * 1024, # 20MB
}
```

**Reference**: `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py`

---

## RES-009 — Error Envelope Pattern (FR6.9)

**Contexto**: Todos os erros do CMS devem usar o envelope FR6.9.

**Investigação**: Constitution v1.7.0 documenta:
> "FR6.9 Error Envelope: Always `{'error': '<snake_case>', 'detail': '<string>', ...extras}` — never `message` key."
> "`_att_error()` Pattern: Module-local helper when FR6.9-compliant errors incompatible with shared `error_response()`."

**Decisão**: Implementar helper `_cms_error()` em `services/cms_error_helpers.py`:
```python
def _cms_error(http_status, error_code, detail=None, **extra):
    payload = {"error": error_code}
    if detail:
        payload["detail"] = detail
    payload.update(extra)
    return request.make_response(
        json.dumps(payload),
        headers=[("Content-Type", "application/json")],
        status=http_status,
    )
```
