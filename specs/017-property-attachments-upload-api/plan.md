# Implementation Plan: Property Attachments Upload API (017)

**Branch**: `017-property-attachments-upload-api` | **Date**: 2026-05-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/017-property-attachments-upload-api/spec.md`

## Summary

Entrega 4 endpoints REST dedicados a upload/listagem/download/exclusão de arquivos de propriedades (imagens e documentos) via API headless. O cliente envia `multipart/form-data`; o controller valida com `python-magic` (magic bytes), sanitiza o filename, verifica o limite de tamanho lido de `web.max_file_upload_size` via `ir.config_parameter`, e persiste como `ir.attachment` vinculado diretamente à `real.estate.property`. Download é feito via rota `/api/v1/...` com `attachment.raw`, nunca `/web/content/`. Phase 4 migra os `download_url`s de `serialize_property()` dos modelos legados (`real.estate.property.photo`, `real.estate.property.document`) para a nova rota autenticada.

## Technical Context

**Language/Version**: Python 3.11 (Odoo 18.0)
**Primary Dependencies**: Odoo 18.0 ORM, Werkzeug (multipart parsing via `request.httprequest.files`), `python-magic` (magic bytes — pip), `libmagic1` (apt — C library required by python-magic), `werkzeug.utils.secure_filename`
**Storage**: PostgreSQL (`ir_attachment` — metadados + `store_fname`); Odoo Filestore em disco (`/filestore/{db}/{2-char}/{hash}`)
**Testing**: Odoo `TransactionTestCase` (unit), shell E2E scripts (API integration)
**Target Platform**: Linux Docker container (Debian Bookworm, imagem base Odoo oficial)
**Project Type**: Single Odoo module (`quicksol_estate`)
**Performance Goals**: Upload aceito até 128 MB (limite lido de `ir.config_parameter`); download em memória via `attachment.raw` (aceitável para o limite configurado)
**Constraints**: `download_url` NUNCA usa `/web/content/`; `libmagic1` requer `apt-get install` explícito no Dockerfile; limites de quantidade hardcoded (`MAX_IMAGES_PER_PROPERTY=50`, `MAX_DOCUMENTS_PER_PROPERTY=20`); discriminador de tipo: `ir.attachment.description` com valor `"image"` ou `"document"`
**Scale/Scope**: 4 novos endpoints REST; 1 novo controller (`property_attachments_controller.py`); 1 atualização em `serialize_property_mapping_fields` (serializer); 1 linha nova no Dockerfile

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Gate | Status | Notes |
|---|------|--------|-------|
| G1 | Triple decorator em todos os endpoints (`@require_jwt` + `@require_session` + `@require_company`) | ✅ PASS | Todos os 4 endpoints têm `auth='none'` + triple decorator — ADR-011 |
| G2 | HATEOAS: POST 201 retorna `links.self` + `links.download` | ✅ PASS | Especificado em FR1.5 |
| G3 | Company isolation em todos os endpoints | ✅ PASS | `require_company` garante; filtro explícito `property_id.company_id = company_id` |
| G4 | Unit + E2E tests planejados | ✅ PASS | `test_property_attachments_unit.py` + E2E bash scripts — ADR-003 |
| G5 | Hard delete em `ir.attachment` documentado como exceção a ADR-015 | ✅ PASS | `ir.attachment` não é entidade de domínio; sem histórico de auditoria requerido |
| G6 | Naming convention: controller em módulo `quicksol_estate` | ✅ PASS | Módulo existente; novo arquivo `property_attachments_controller.py` — ADR-004 |
| G7 | OpenAPI documentation via `thedevkitchen_api_endpoint` table | ✅ PASS | Swagger via DB (ADR-005); NUNCA arquivo estático |
| G8 | `download_url` usa rota `/api/v1/...` (via Gateway) | ✅ PASS | Invariante crítico; `/web/content/` proibido — FR1.5, FR2.1 |
| G9 | `@trace_http_request` em todos os métodos do controller | ✅ PASS | Pattern ADR-017/Feature 013 |

**Post-Design Re-check**: Nenhuma violação identificada. Complexidade extra justificada por requisito de segurança (magic bytes) e invariante arquitetural (download via Gateway).

## Project Structure

### Documentation (this feature)

```text
specs/017-property-attachments-upload-api/
├── plan.md              # Este arquivo (saída do /speckit.plan)
├── research.md          # Fase 0 — decisões arquiteturais
├── data-model.md        # Fase 1 — modelo de dados
├── quickstart.md        # Fase 1 — setup local
├── contracts/
│   └── property-attachments.yaml   # OpenAPI 3.0 — Fase 1
└── tasks.md             # Fase 2 (saída do /speckit.tasks — não criado por /speckit.plan)
```

### Source Code (repository root)

```text
18.0/extra-addons/quicksol_estate/
├── controllers/
│   ├── property_attachments_controller.py   # NOVO — 4 endpoints
│   ├── property_api.py                      # LER (serialize_property_mapping_fields)
│   └── utils/
│       └── serializers.py                   # ATUALIZAR — download_url fotos/documentos legados
├── models/
│   └── property_media.py                    # LER — PropertyPhoto, PropertyDocument existentes
├── tests/
│   └── unit/
│       └── test_property_attachments_unit.py  # NOVO — testes unitários
└── 18.0/Dockerfile                             # ATUALIZAR — adicionar libmagic1
integration_tests/
└── test_property_attachments_api.sh           # NOVO — E2E integration (pasta raiz do repositório)
```

**Structure Decision**: Single Odoo module (`quicksol_estate`). Novo controller separado (SRP). Sem novo modelo — usa `ir.attachment` nativo com discriminador via `description` field. Sistemas `ir.attachment` e custom models (`PropertyPhoto`/`PropertyDocument`) são paralelos intencionalmente.

## Complexity Tracking

Nenhuma violação a ADRs detectada. Decisões de design:

| Decisão | Justificativa |
|---------|---------------|
| `ir.attachment` direto (não custom model) | `PropertyPhoto`/`PropertyDocument` têm thumbnails, is_main, sequence — funcionalidades UI. A nova API serve dados brutos ao cliente mobile. Sistemas paralelos intencionais. |
| Discriminador via `ir.attachment.description` | Campo existente; sem migration. Alternativa (inferir via mimetype) menos explícita. |
| Sem fallback a `mimetypes.guess_type()` | Segurança em critical path; fallback silencioso cria false sense of security. |
