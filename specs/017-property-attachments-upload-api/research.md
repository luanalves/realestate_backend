# Research: Property Attachments Upload API (017)

**Phase**: 0 | **Feature**: 017 | **Date**: 2026-05-06

## R001 — Upload Pipeline Técnico

**Decision**: `multipart/form-data` → Werkzeug `FileStorage` → `bytes` em memória → base64 → `ir.attachment.datas`

**Rationale**:
- `request.httprequest.files.get('file')` retorna Werkzeug `FileStorage` — padrão já confirmado em `proposal_controller.py` (linha 627)
- `upload.read()` → bytes crus; `base64.b64encode(content)` → campo ORM `ir.attachment.datas` (computed field que persiste em disco via filestore)
- O cliente envia binário via `multipart/form-data`, NUNCA base64 no body JSON

**Reference implementation**: `proposal_controller.py:621-660` — upload para `ir.attachment` já validado em produção.

**Alternatives considered**:
- JSON body com base64: rejeitado — 33% overhead, browser/mobile APIs usam multipart nativamente
- Stream direto para disco: rejeitado — Odoo ORM não suporta streaming; `attachment.raw` em memória é aceitável até 128 MB

---

## R002 — Validação de MIME: python-magic vs upload.mimetype

**Decision**: `python-magic` com `magic.from_buffer(content[:2048], mime=True)` — sem fallback

**Rationale**:
- `upload.mimetype` (Werkzeug) lê o `Content-Type` enviado pelo cliente — facilmente falsificável (ex: `.exe` com `Content-Type: image/jpeg`)
- `python-magic` inspeciona os primeiros bytes do arquivo (magic bytes), independente do header HTTP
- Sem fallback a `mimetypes.guess_type()`: falha explícita é mais segura que validação silenciosa fraca
- Apenas 2048 bytes precisam ser lidos para magic bytes — eficiente para arquivos grandes

**API pattern**:
```python
import magic

detected_mime = magic.from_buffer(content[:2048], mime=True)
if detected_mime not in ALLOWED_IMAGE_MIMETYPES | ALLOWED_DOCUMENT_MIMETYPES:
    return error_response('VALIDATION_ERROR', 'File type not allowed', 415)
```

**Prerequisites**:
- pip: `python-magic` (já declarado como dependência no módulo)
- apt (Dockerfile): `libmagic1` — biblioteca C obrigatória; sem ela, `import magic` falha silenciosamente ou levanta `ImportError`

**Alternatives considered**:
- `upload.mimetype` (Werkzeug): rejeitado — client-controlled, não é security control
- `mimetypes.guess_type(filename)`: rejeitado — baseado em extensão, facilmente falsificável
- `imghdr` (stdlib): rejeitado — deprecated no Python 3.11+, suporta apenas imagens

---

## R003 — Armazenamento: ir.attachment vs Custom Models

**Decision**: Usar `ir.attachment` diretamente com `res_model='real.estate.property'`; sistemas paralelos intencionais

**Rationale**:
- Modelos existentes `real.estate.property.photo` e `real.estate.property.document` têm funcionalidades UI ricas: thumbnails (`image_medium`, `image_small`), `is_main`, `sequence`, `document_type`, `is_confidential` — esses dados são usados pela interface Odoo e serialize_property no contexto de Spec 016
- A nova API (Spec 017) serve dados brutos ao cliente mobile: upload → `ir.attachment` → download via `/api/v1/...`
- Os dois sistemas coexistem: `photo_ids`/`document_ids` (custom models) continuam sendo retornados pelo `serialize_property` para a lista de propriedades; o novo endpoint `/api/v1/properties/{id}/attachments` retorna apenas `ir.attachment` records
- **Sem migração de dados**: nenhum registro existente é alterado

**ir.attachment fields usados**:
```python
{
    'name': secure_filename(upload.filename),
    'datas': base64.b64encode(content),
    'res_model': 'real.estate.property',
    'res_id': property_id,
    'mimetype': detected_mime,   # de python-magic, não do header HTTP
    'description': 'image' or 'document',  # discriminador de tipo
    'company_id': request.env.company.id,
}
```

**Discriminador de tipo**: `ir.attachment.description` field (`"image"` ou `"document"`). Campo existente no modelo ORM — sem necessidade de migration.

**Cascade delete**: comportamento nativo do Odoo — quando o registro `real.estate.property` é deletado, os `ir.attachment` vinculados são automaticamente removidos (Odoo 18.0 comportamento padrão via `res_id`/`res_model` cleanup). Documentado em FR3.4 da spec.

**Alternatives considered**:
- Escrever nos custom models (`PropertyPhoto`/`PropertyDocument`): rejeitado — esses modelos têm validadores e lógica de thumbnail que interferem com a API; acopla o novo sistema a modelos que podem evoluir independentemente
- Novo modelo customizado: rejeitado — `ir.attachment` já provê tudo necessário; criar novo modelo viola YAGNI

---

## R004 — Download: attachment.raw vs ir.attachment.datas

**Decision**: `attachment.raw` (Odoo 14+ API) retornando `werkzeug.wrappers.Response`

**Rationale**:
- `attachment.raw` retorna `bytes` diretamente do disco sem encode/decode base64 — mais eficiente que `attachment.datas` (que retorna base64)
- `werkzeug.wrappers.Response` com headers corretos: `Content-Type`, `Content-Disposition`, `Content-Security-Policy: default-src 'none'`
- Download URL: `/api/v1/properties/{property_id}/attachments/{attachment_id}/download` — NUNCA `/web/content/{id}` (que bypassa o API Gateway)
- Aceitável para arquivos até 128 MB em memória; streaming seria necessário apenas para limites > 500 MB

**Pattern**:
```python
from werkzeug.wrappers import Response

content = attachment.raw   # bytes
return Response(
    content,
    status=200,
    headers={
        'Content-Type': attachment.mimetype,
        'Content-Disposition': f'attachment; filename="{attachment.name}"',
        'Content-Security-Policy': "default-src 'none'",
        'X-Content-Type-Options': 'nosniff',
    }
)
```

**Alternatives considered**:
- `ir.attachment.datas` (base64): rejeitado — requer decode, overhead de memória ~33%
- `werkzeug.wsgi.wrap_file()` + streaming: rejeitado — complexidade desnecessária para o limite de 128 MB
- `/web/content/{id}` redirect: PROIBIDO — bypassa Gateway, expõe Odoo diretamente

---

## R005 — Limite de Tamanho via ir.config_parameter

**Decision**: Leitura dinâmica de `web.max_file_upload_size` via `ir.config_parameter`; default: 128 MB

**Rationale**:
- Permite configuração por ambiente sem deploy de código
- Chave padrão Odoo, usada pelo próprio frontend Odoo para validação no browser
- Default 134217728 bytes (128 MB) é consistente com Odoo standard

**Pattern**:
```python
IrConfig = request.env['ir.config_parameter'].sudo()
max_bytes = int(IrConfig.get_param('web.max_file_upload_size', default=134217728))
```

**Alternatives considered**:
- Hardcode no controller: rejeitado — impossibilita ajuste por ambiente
- Constante no módulo: rejeitado — requer redeploy para mudança

---

## R006 — Limites de Quantidade por Tipo

**Decision**: Constantes hardcoded no controller: `MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`

**Rationale**:
- Proposta original da spec; nenhum requisito de configurabilidade levantado
- Verificação via contagem de `ir.attachment` records existentes antes de criar novo
- Contagem: `env['ir.attachment'].search_count([('res_model', '=', 'real.estate.property'), ('res_id', '=', property_id), ('description', '=', attachment_type)])`

**Alternatives considered**:
- `ir.config_parameter`: overkill para limites operacionais; nenhum requisito de configurabilidade

---

## R007 — Filename Sanitization

**Decision**: `werkzeug.utils.secure_filename(upload.filename)` + fallback para `untitled`

**Rationale**:
- `secure_filename` remove path traversal characters, espaços, caracteres não-ASCII
- Fallback necessário: `secure_filename` pode retornar string vazia para nomes com apenas caracteres não-ASCII
- Preservar extensão original após sanitização

**Pattern**:
```python
from werkzeug.utils import secure_filename

raw_name = upload.filename or ''
safe_name = secure_filename(raw_name) or 'untitled'
```

---

## R008 — Multi-tenancy: Isolamento por Company

**Decision**: Dupla verificação: `require_company` decorator + query explícita `company_id`

**Rationale**:
- `require_company` garante que `request.env.company` está configurado
- Na busca de `ir.attachment`, sempre filtrar via `res_id` de propriedade que pertence à company do usuário
- Pattern: buscar a propriedade primeiro → verificar `property.company_id == request.env.company` → só então operar nos attachments
- Anti-enumeration: propriedade de outra company retorna 404 (não 403)

**Pattern** (ver Feature 013 reference, `_fetch_proposal()`):
```python
def _fetch_property_for_company(property_id):
    prop = request.env['real.estate.property'].browse(property_id)
    if not prop.exists() or prop.company_id != request.env.company:
        return None  # 404 — sem leakage de informação
    return prop
```

---

## R009 — Estrutura de Arquivos do Módulo

**Decision**: Novo controller `property_attachments_controller.py` em `controllers/` do módulo `quicksol_estate`

**Rationale**:
- Módulo existente; nenhum novo módulo necessário
- Convenção ADR-004: `quicksol_estate` é o módulo de domínio correto para propriedades
- Controller separado mantém SRP; não misturar com CRUD de propriedade em `property_api.py`
- Registrar no `controllers/__init__.py`

**Alternatives considered**:
- Adicionar ao `property_api.py`: rejeitado — SRP; property_api.py já tem ~680 linhas
- Novo módulo `thedevkitchen_property_attachments`: rejeitado — overhead de módulo para 4 endpoints; ADR-004 não requer separação de módulo para funcionalidades do mesmo domínio

---

## R010 — Atualização do serialize_property (Phase 4)

**Decision**: Atualizar `serialize_property_mapping_fields` para retornar `download_url` usando `/api/v1/...`; manter itens `photo_ids`/`document_ids` existentes com nova URL

**Rationale**:
- `serialize_property_mapping_fields` (serializers.py linha 110) atualmente gera URLs `/web/content/real.estate.property.photo/{id}/image?download=true`
- Essas URLs acessam os custom models — não os novos `ir.attachment`
- A atualização muda o formato da URL dos custom models para `/api/v1/properties/{property_id}/attachments/{id}/download` (indicando o tipo e ID correto)
- Isso quebra backward compatibility — Phase 4 deve ser feita com coordenação com a equipe de mobile

**Scope da mudança**: apenas o valor de `download_url` em `property_images` e `property_files` no serializer; estrutura de campos permanece igual.

---

## Resolved Items

| NEEDS CLARIFICATION | Resolução |
|---------------------|-----------|
| API python-magic para magic bytes | `magic.from_buffer(content[:2048], mime=True)` — R002 |
| `attachment.raw` disponível em Odoo 18.0 | Confirmado — API introduzida no Odoo 14.0; estável em 18.0 — R004 |
| Padrão de leitura de `ir.config_parameter` | `IrConfig.get_param('web.max_file_upload_size', default=134217728)` — R005 |
| `werkzeug.utils.secure_filename` behavior | Remove path traversal, retorna empty string para nomes all-unicode — R007 |
| Coexistência com custom models | Sistemas paralelos intencionais; sem migração — R003 |
| Dockerfile change para libmagic1 | `RUN apt-get install -y --no-install-recommends libmagic1` — R002 |
