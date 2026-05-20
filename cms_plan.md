# Plano de Implementação — Domínio CMS

## Contexto técnico

O CMS usa o **Puck editor** (`@measured/puck`). O conteúdo **não é armazenado como HTML** — é armazenado como **JSON** representando uma árvore de componentes React:

```json
{
  "content": [
    { "type": "HeadingBlock", "props": { "children": "Título", "level": "h1" } },
    { "type": "TextBlock",    "props": { "content": "Texto..." } }
  ],
  "root": { "props": {} }
}
```

A renderização HTML acontece **exclusivamente no frontend** via `<Render config={puckConfig} data={...} />`. O backend apenas persiste e devolve esse JSON.

O risco real de HTML/código fica nos campos **Custom CSS** e **Custom JavaScript** do `CmsSettings`.

---

## Endpoints necessários

### 1. Páginas CMS — `/api/v1/cms/pages`

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| `GET` | `/api/v1/cms/pages` | Lista páginas (filtros: `status`, `search`, `limit`, `offset`) | `@require_jwt` + `@require_session` + `@require_company` |
| `POST` | `/api/v1/cms/pages` | Cria nova página | idem |
| `GET` | `/api/v1/cms/pages/:id` | Retorna página por ID | idem |
| `PUT` | `/api/v1/cms/pages/:id` | Atualiza página + conteúdo Puck | idem |
| `DELETE` | `/api/v1/cms/pages/:id` | Deleta página | idem |
| `POST` | `/api/v1/cms/pages/:id/publish` | Publica página (status → published) | idem |
| `POST` | `/api/v1/cms/pages/:id/archive` | Arquiva página | idem |
| `POST` | `/api/v1/cms/pages/:id/duplicate` | Duplica página (nova com status draft) | idem |
| `GET` | `/api/v1/public/cms/pages/:slug` | Retorna página publicada por slug | **public endpoint** (`auth='none'`) |

### 2. Templates — `/api/v1/cms/templates`

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/cms/templates` | Lista templates (filtro: `category`) |
| `POST` | `/api/v1/cms/templates` | Cria template |
| `GET` | `/api/v1/cms/templates/:id` | Retorna template |
| `PUT` | `/api/v1/cms/templates/:id` | Atualiza template |
| `DELETE` | `/api/v1/cms/templates/:id` | Deleta template |

### 3. Mídia — `/api/v1/cms/media`

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/cms/media` | Lista arquivos (filtro: `type`, `search`) |
| `POST` | `/api/v1/cms/media/upload` | Upload (`multipart/form-data`) |
| `GET` | `/api/v1/cms/media/:id` | Metadados do arquivo |
| `DELETE` | `/api/v1/cms/media/:id` | Deleta arquivo |

### 4. Configurações — `/api/v1/cms/settings`

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/cms/settings` | Retorna config da empresa atual |
| `PUT` | `/api/v1/cms/settings` | Atualiza config |

---

## Modelos Odoo necessários

```
thedevkitchen.cms.page      → título, slug, content (Text/JSON), status, SEO, company_id, author_id
thedevkitchen.cms.template  → nome, category, content (Text/JSON), thumbnail, company_id
thedevkitchen.cms.media     → nome, type, mime_type, file_size, url, alt_text, ir.attachment, company_id
thedevkitchen.cms.settings  → company_id (unique), SEO defaults, image config, custom_css, custom_js
```

---

## Segurança — Pontos críticos

### Conteúdo Puck (JSON) — risco baixo
- Armazenar em campo `Text` no Odoo
- Validar que é JSON válido antes de persistir (`json.loads()` no controller)
- Validar tamanho máximo (ex: 512KB) para prevenir DoS
- **Não executar** nem interpretar o conteúdo server-side

### Custom CSS — risco médio
- Armazenar como texto puro
- Acesso restrito a `@require_role('admin')` ou grupo específico no `@require_company`
- No frontend, injetar apenas dentro de `<style scoped>` — nunca via `innerHTML`
- Adicionar `Content-Security-Policy` no header de resposta das páginas públicas
- Recusar se contiver `expression()`, `behavior:`, `url(javascript:)` — validação regex server-side

### Custom JavaScript — risco alto
- Acesso restrito a **admin da agência** (grupo mais elevado)
- Armazenar como texto puro, **nunca executar server-side**
- Endpoint separado ou campo com validação de role mais estrita
- Log de auditoria em toda escrita (quem alterou, quando)
- Campo `last_modified_by` + `last_modified_at` específico para este campo

### Slugs — prevenir path traversal
```python
import re
SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
if not SLUG_PATTERN.match(slug):
    return error_response(400, 'slug_invalid', 'Slug must be lowercase alphanumeric with hyphens only')
```

### Upload de mídia — validação obrigatória
- Validar MIME type real (não só extensão) via `python-magic`
- Whitelist: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `application/pdf`, `video/mp4`
- Limite server-side de tamanho (ex: 10MB para imagens, 100MB para vídeo)
- Sanitizar nome do arquivo (`secure_filename`)
- Armazenar em `ir.attachment` com `res_model='thedevkitchen.cms.media'`

### Endpoint público `/api/v1/public/cms/pages/:slug`
- Apenas páginas com `status = 'published'` são acessíveis
- Retornar 404 genérico para páginas não publicadas (prevenir enumeração)
- Nunca retornar `custom_js` ou `custom_css` neste endpoint
- Rate limiting no Kong

---

## Estrutura do addon `thedevkitchen_cms`

```
thedevkitchen_cms/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── cms_page.py
│   ├── cms_template.py
│   ├── cms_media.py
│   └── cms_settings.py
├── controllers/
│   ├── __init__.py
│   ├── cms_pages_controller.py
│   ├── cms_templates_controller.py
│   ├── cms_media_controller.py
│   ├── cms_settings_controller.py
│   └── cms_public_controller.py   ← auth='none', public endpoint
├── services/
│   ├── __init__.py
│   └── cms_sanitizer.py           ← validação JSON + CSS/JS
├── schemas/
│   ├── __init__.py
│   ├── page_schema.py
│   └── settings_schema.py
└── security/
    ├── security.xml
    └── ir.model.access.csv
```
