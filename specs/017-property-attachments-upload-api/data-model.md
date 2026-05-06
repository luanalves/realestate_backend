# Data Model: Property Attachments Upload API (017)

**Phase**: 1 | **Feature**: 017 | **Date**: 2026-05-06

## Overview

Feature 017 não introduz novos modelos Odoo. Usa `ir.attachment` nativo com `res_model='real.estate.property'`.

## Entities

### Primary Entity: ir.attachment (nativo Odoo)

Nenhuma alteração ao modelo — apenas criação de registros com fields específicos.

| Campo | Tipo | Valor/Comportamento | Descrição |
|-------|------|---------------------|-----------|
| `name` | `Char` | `secure_filename(upload.filename)` | Nome sanitizado do arquivo |
| `datas` | `Binary` (computed) | `base64.b64encode(raw_bytes)` | Write: salva binário no filestore + store_fname no DB; Read: retorna base64 do disco |
| `raw` | `Binary` (computed) | `bytes` | Odoo 14+ — retorna bytes do disco diretamente (sem encode) |
| `res_model` | `Char` | `'real.estate.property'` | Modelo vinculado |
| `res_id` | `Integer` | `property.id` | ID da propriedade |
| `mimetype` | `Char` | `magic.from_buffer(content[:2048], mime=True)` | MIME detectado via magic bytes |
| `description` | `Char` | `'image'` ou `'document'` | **Discriminador de tipo** |
| `company_id` | `Many2one` | `request.env.company.id` | Multi-tenancy |
| `file_size` | `Integer` | calculado pelo ORM no create | Tamanho em bytes |
| `store_fname` | `Char` | `{2-char-prefix}/{sha1_hash}` | Referência ao arquivo em disco (relativa ao filestore) |
| `checksum` | `Char` | SHA1 do binário | Deduplicação automática pelo Odoo |
| `create_date` | `Datetime` | auto | Timestamp de upload |

### Campos NÃO usados da spec legacy

Os seguintes campos existem no ORM mas NÃO são usados nesta feature:
- `url`: reservado para attachments que são links, não arquivos
- `type`: `'binary'` (default) para arquivos; não alterar
- `res_field`: vinculo a campo específico — não usar; vinculamos via `res_model/res_id`

## Constants (controller-level)

```python
# Quantidade máxima por tipo por propriedade
MAX_IMAGES_PER_PROPERTY = 50
MAX_DOCUMENTS_PER_PROPERTY = 20

# Discriminador de tipo (ir.attachment.description)
TYPE_IMAGE = 'image'
TYPE_DOCUMENT = 'document'

# MIME whitelist (validação por magic bytes)
ALLOWED_IMAGE_MIMETYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
    # image/gif excluído: sem caso de uso em real estate; risco XSS em metadata
})

ALLOWED_DOCUMENT_MIMETYPES = frozenset({
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
})

ALLOWED_MIMETYPES = ALLOWED_IMAGE_MIMETYPES | ALLOWED_DOCUMENT_MIMETYPES

# Tamanho máximo (lido de ir.config_parameter no runtime)
DEFAULT_MAX_FILE_BYTES = 134_217_728  # 128 MB
CONFIG_PARAM_MAX_SIZE = 'web.max_file_upload_size'
```

## Queries de Leitura

### Lista de attachments de uma propriedade

```python
attachments = request.env['ir.attachment'].search([
    ('res_model', '=', 'real.estate.property'),
    ('res_id', '=', property_id),
    ('description', 'in', ['image', 'document']),
], order='create_date desc', limit=limit, offset=offset)
```

### Filtro por tipo

```python
# Com filtro de tipo (parâmetro attachment_type)
domain = [
    ('res_model', '=', 'real.estate.property'),
    ('res_id', '=', property_id),
    ('description', '=', attachment_type),  # 'image' ou 'document'
]
```

### Contagem para verificar limite

```python
count = request.env['ir.attachment'].search_count([
    ('res_model', '=', 'real.estate.property'),
    ('res_id', '=', property_id),
    ('description', '=', attachment_type),
])
```

### Fetch de attachment com verificação de pertencimento

```python
def _fetch_attachment(attachment_id, property_id):
    """Busca attachment verificando pertencimento à propriedade da company."""
    att = request.env['ir.attachment'].browse(attachment_id)
    if not att.exists():
        return None
    if att.res_model != 'real.estate.property' or att.res_id != property_id:
        return None
    return att
```

## Serialização de Resposta

### Upload Response (201 Created)

```json
{
  "status": "success",
  "data": {
    "id": 42,
    "name": "planta-baixa.pdf",
    "mimetype": "application/pdf",
    "size": 204800,
    "attachment_type": "document",
    "uploaded_at": "2026-05-06T14:23:11Z",
    "links": {
      "self": "/api/v1/properties/7/attachments/42",
      "download": "/api/v1/properties/7/attachments/42/download"
    }
  }
}
```

### List Response (200 OK)

```json
{
  "status": "success",
  "data": {
    "items": [
      {
        "id": 42,
        "name": "fachada.jpg",
        "mimetype": "image/jpeg",
        "size": 512000,
        "attachment_type": "image",
        "uploaded_at": "2026-05-06T14:23:11Z",
        "links": {
          "download": "/api/v1/properties/7/attachments/42/download"
        }
      }
    ],
    "pagination": {
      "total": 8,
      "limit": 50,
      "offset": 0
    }
  }
}
```

## Modelos Existentes (Paralelos — Sem Alteração)

### real.estate.property.photo

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | `Char` | required |
| `image` | `Binary` | `attachment=True` → Odoo cria ir.attachment internamente vinculado ao `PropertyPhoto`, não à propriedade |
| `image_medium` | `Binary` | computed, 512x512 thumbnail |
| `image_small` | `Binary` | computed, 256x256 thumbnail |
| `is_main` | `Boolean` | uniqueness enforced via `write()` hook |
| `property_id` | `Many2one` | `ondelete='cascade'` |
| `sequence` | `Integer` | ordering |

### real.estate.property.document

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | `Char` | required |
| `file` | `Binary` | `attachment=True` |
| `document_type` | `Selection` | 13 tipos (matricula, iptu, etc.) |
| `is_confidential` | `Boolean` | |
| `property_id` | `Many2one` | `ondelete='cascade'` |

**Nota**: Esses modelos **não são alterados** por esta feature. O serializer `serialize_property_mapping_fields` continuará iterando sobre `photo_ids`/`document_ids`, mas os `download_url`s serão atualizados (Phase 4) para apontar para `/api/v1/properties/{property_id}/attachments/{id}/download`.

## Dockerfile Change

```dockerfile
# Adicionar ao bloco de apt-get existente (18.0/Dockerfile):
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*
```

## Nenhuma Migration Necessária

- Sem novos modelos Odoo
- Sem alteração de campos existentes
- `ir.attachment` já existe
- Constantes e controllers não requerem migration de schema
