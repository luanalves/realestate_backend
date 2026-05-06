# Tasks: Property Attachments Upload API (017)

**Input**: Design documents from `specs/017-property-attachments-upload-api/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/property-attachments.yaml ✅, quickstart.md ✅
**Branch**: `017-property-attachments-upload-api`

**Organization**: Tasks organized by User Story (US1/US2/US6 → MVP, US3 → Download, US4 → Delete, US5 → Config). Testes NOT included as separate tasks — seguir a estratégia de testes definida em spec.md (unit + E2E integration bash scripts).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (files distintos, sem dependência entre si)
- **[Story]**: User Story mapeado em spec.md
- Caminhos absolutos relativos à raiz do repositório

---

## Phase 1: Setup

**Purpose**: Dependência de sistema (Docker) e registro do controller no módulo

- [X] T001 Adicionar `libmagic1` ao bloco apt-get em `18.0/Dockerfile` (requisito de R002 — python-magic sem essa lib levanta ImportError)
- [X] T002 Registrar `property_attachments_controller` no `18.0/extra-addons/quicksol_estate/controllers/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura partilhada pelo controller antes de qualquer endpoint

**⚠️ CRITICAL**: Nenhum endpoint pode ser implementado antes desta fase

- [X] T003 Criar arquivo `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py` com: imports, constantes (`ALLOWED_IMAGE_MIMETYPES`, `ALLOWED_DOCUMENT_MIMETYPES`, `MAX_IMAGES_PER_PROPERTY`, `MAX_DOCUMENTS_PER_PROPERTY`, `DEFAULT_MAX_FILE_BYTES`, `CONFIG_PARAM_MAX_SIZE`, `TYPE_IMAGE`, `TYPE_DOCUMENT`), helper `_fetch_property_for_company()` e classe `PropertyAttachmentsController(http.Controller)` vazia
- [X] T004 [P] Implementar helper `_get_max_upload_bytes()` no controller (`ir.config_parameter.sudo().get_param(...)` com default 134217728) — R005
- [X] T005 [P] Implementar helper `_detect_mime()` com `magic.from_buffer(content[:2048], mime=True)` — R002
- [X] T006 [P] Implementar helper `_serialize_attachment()` que monta o dict de resposta (id, name, mimetype, size, attachment_type, uploaded_at, links) com `download_url` sempre em `/api/v1/...` — nunca `/web/content/` — R004, FR1.7, data-model.md
- [X] T007 Implementar helper `_fetch_attachment()` com verificação `res_model='real.estate.property'` + `res_id == property_id` — FR2.2, R008

**Checkpoint**: Infraestrutura base pronta — endpoints podem ser implementados

---

## Phase 3: User Story 1 + 2 — Upload de imagens e documentos (Priority: P1) 🎯 MVP

**User Stories**: US1 (imagens) + US2 (documentos)
**Goal**: `POST /api/v1/properties/{id}/attachments` funcionando para imagens e documentos com todas as validações

**Independent Test**:
```bash
# Upload de imagem válida
curl -X POST http://localhost:8069/api/v1/properties/7/attachments \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID" \
  -F "file=@/tmp/test.jpg;type=image/jpeg" -F "attachment_type=image"
# → HTTP 201 com id, download_url iniciando com /api/v1/

# Upload com MIME inválido
curl -X POST ... -F "file=@/tmp/malicious.jpg" -F "attachment_type=image"
# → HTTP 400 (magic bytes rejeitam o script)
```

### Implementation — US1 + US2

- [X] T008 [US1] Implementar `POST /api/v1/properties/{id}/attachments` em `18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py`:
  - Decorators: `@http.route`, `@trace_http_request`, `@require_jwt`, `@require_session`, `@require_company`
  - `_fetch_property_for_company(property_id)` — 404 anti-enumeração
  - Ler `file` e `attachment_type` do form; validar campos obrigatórios (400)
  - Verificar `attachment_type` em `[TYPE_IMAGE, TYPE_DOCUMENT]` (400)
  - Ler bytes: `content = upload.read()`
  - Verificar tamanho via `_get_max_upload_bytes()` → 413 com `max_size_bytes` se exceder
  - Verificar limite de quantidade (`MAX_IMAGES` ou `MAX_DOCUMENTS`) com `search_count` → 422
  - Detectar MIME via `_detect_mime()` e verificar whitelist → 415
  - Verificar que `attachment_type` condiz com o MIME detectado → 400
  - Sanitizar filename: `secure_filename(upload.filename) or 'untitled'`
  - RBAC: Agent retorna 403 (FR3.1 / ADR-019)
  - `ir.attachment.create({...})` com campos definidos em data-model.md
  - Retornar `success_response(_serialize_attachment(...), status_code=201)`

- [X] T009 [P] [US1] Criar arquivo de fixture `seed_image.jpg` (~1 MB JPEG válido) em `18.0/extra-addons/quicksol_estate/tests/fixtures/seed_image.jpg` — Seed Data spec.md
- [X] T010 [P] [US2] Criar arquivo de fixture `seed_document.pdf` (~500 KB PDF válido) em `18.0/extra-addons/quicksol_estate/tests/fixtures/seed_document.pdf`
- [X] T011 [P] [US1] Criar arquivo de fixture `seed_malicious.jpg` (extensão .jpg, magic bytes de script Python/PHP) em `18.0/extra-addons/quicksol_estate/tests/fixtures/seed_malicious.jpg` — test_magic_bytes_mismatch_rejected
- [X] T012 [P] [US1] Criar arquivo de fixture `seed_large.jpg` (acima de 10 MB) em `18.0/extra-addons/quicksol_estate/tests/fixtures/seed_large.jpg` — test_image_size_limit_enforced
- [X] T013 [US1] Criar testes unitários em `18.0/extra-addons/quicksol_estate/tests/unit/test_property_attachments_unit.py`:
  - `test_image_mimetype_allowed()` — jpeg, png, webp aceitos
  - `test_image_mimetype_rejected()` — pdf, html, exe rejeitados para tipo=image
  - `test_magic_bytes_mismatch_rejected()` — seed_malicious.jpg rejeitado
  - `test_image_size_limit_enforced()` — seed_large.jpg retorna 413
  - `test_filename_sanitization()` — `../../../etc/passwd.jpg` → `etc_passwd.jpg`
  - `test_download_url_uses_api_route()` — `_serialize_attachment()` nunca gera `/web/content/`
  - `test_document_mimetype_allowed()` — pdf, docx, xlsx aceitos
  - `test_document_size_limit_enforced()` — limite de documentos aplicado
  - `test_upload_reads_ir_config_param()` — _get_max_upload_bytes() usa ir.config_parameter
  - `test_upload_uses_default_when_param_absent()` — sem parâmetro → 134217728
  - `test_agent_cannot_delete()` — Agent recebe 403 (adiantado aqui para completude unitária)

**Checkpoint**: `POST /api/v1/properties/{id}/attachments` funcional para imagens e documentos, com validações completas e testes unitários

---

## Phase 4: User Story 6 — Listagem paginada (Priority: P1) 🎯 MVP

**User Story**: US6
**Goal**: `GET /api/v1/properties/{id}/attachments` com paginação e filtro por tipo

**Independent Test**:
```bash
# Listar todos
curl -X GET http://localhost:8069/api/v1/properties/7/attachments \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID"
# → HTTP 200 com items[], pagination{total, limit, offset}

# Filtrar por tipo
curl -X GET "http://localhost:8069/api/v1/properties/7/attachments?attachment_type=image&limit=10&offset=0" ...
# → Somente imagens
```

### Implementation — US6

- [X] T014 [US6] Implementar `GET /api/v1/properties/{id}/attachments` em `property_attachments_controller.py`:
  - Triple decorator (`@http.route` GET/POST no mesmo path — usar rota separada) + `@trace_http_request` + `@require_jwt` + `@require_session` + `@require_company`
  - `_fetch_property_for_company(property_id)` → 404
  - Ler `attachment_type`, `limit` (default 50, max 100), `offset` (default 0) dos query params
  - Validar `attachment_type` se presente (400)
  - Construir domain: `[('res_model', '=', 'real.estate.property'), ('res_id', '=', property_id), ('description', 'in', ['image', 'document'])]` + filtro por tipo se informado
  - `ir.attachment.search_count(domain)` para `total`
  - `ir.attachment.search(domain, order='create_date desc', limit=limit, offset=offset)` para `items`
  - Retornar `success_response({'items': [..._serialize_attachment(a)...], 'pagination': {...}})`
- [X] T015 [P] [US6] Adicionar testes unitários em `test_property_attachments_unit.py`:
  - `test_list_download_url_uses_api_route()` — cada item em `items[]` nunca contém `/web/content/`

**Checkpoint**: Upload (US1+US2) + Listagem (US6) compõem o MVP completo

---

## Phase 5: User Story 3 — Download seguro (Priority: P1) 🎯 MVP

**User Story**: US3
**Goal**: `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` com headers de segurança

**Independent Test**:
```bash
# Download autenticado
curl -X GET http://localhost:8069/api/v1/properties/7/attachments/42/download \
  -H "Authorization: Bearer $JWT" -H "Cookie: session_id=$SID" \
  -o /tmp/downloaded.jpg
# → HTTP 200 + binário + headers: Content-Disposition, Content-Security-Policy, X-Content-Type-Options

# Sem autenticação
curl -X GET http://localhost:8069/api/v1/properties/7/attachments/42/download
# → HTTP 401
```

### Implementation — US3

- [X] T016 [US3] Implementar `GET /api/v1/properties/{id}/attachments/<int:attachment_id>/download` em `property_attachments_controller.py`:
  - Triple decorator + `@trace_http_request`
  - `_fetch_property_for_company(property_id)` → 404
  - `_fetch_attachment(attachment_id, property_id)` → 404 se não pertencer à propriedade
  - `content = attachment.raw` (bytes direto do ORM — R004)
  - Retornar `werkzeug.wrappers.Response(content, status=200, headers={...})` com `Content-Type`, `Content-Disposition: attachment; filename="..."`, `Content-Security-Policy: default-src 'none'`, `X-Content-Type-Options: nosniff` — FR2.3
  - NUNCA `redirect('/web/content/...')` — FR2.4
- [X] T017 [P] [US3] Adicionar teste unitário em `test_property_attachments_unit.py`:
  - `test_no_redirect_to_web_content()` — response não contém Location header apontando para /web/content/

**Checkpoint**: Upload + Listagem + Download compõem MVP completo deployável

---

## Phase 6: User Story 4 — Exclusão (Priority: P2)

**User Story**: US4
**Goal**: `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` com RBAC e hard delete

**Independent Test**:
```bash
# Owner deleta
curl -X DELETE http://localhost:8069/api/v1/properties/7/attachments/42 \
  -H "Authorization: Bearer $OWNER_JWT" -H "Cookie: session_id=$SID"
# → HTTP 204 No Content

# Agent tenta deletar
curl -X DELETE ... -H "Authorization: Bearer $AGENT_JWT" ...
# → HTTP 403
```

### Implementation — US4

- [X] T018 [US4] Implementar `DELETE /api/v1/properties/{id}/attachments/<int:attachment_id>` em `property_attachments_controller.py`:
  - Triple decorator + `@trace_http_request`
  - `_fetch_property_for_company(property_id)` → 404
  - RBAC check: perfil do usuário ∈ {Owner, Manager} → senão 403 (FR3.1)
  - `_fetch_attachment(attachment_id, property_id)` → 404
  - `attachment.unlink()` — hard delete (exceção documentada a ADR-015 — FR3.2)
  - Retornar `Response('', status=204)` — FR3.3

**Checkpoint**: CRUD completo (Upload + List + Download + Delete)

---

## Phase 7: User Story 5 — Configuração de limite (Priority: P2)

**User Story**: US5
**Goal**: Garantir que `web.max_file_upload_size` é lido dinamicamente e o controller usa `ir.config_parameter`

> **Nota**: Esta US não tem endpoint novo. É uma garantia de comportamento já implementado em T003/T004 (Phase 2). Esta fase cobre os testes E2E que validam o comportamento dinâmico.

### Implementation — US5

- [X] T019 [US5] Criar script `integration_tests/test_property_attachments_api.sh` com os cenários de configuração dinâmica (US5):
  - `test_upload_rejected_when_over_global_limit()` — configura `web.max_file_upload_size=1048576` via psql → upload de seed_large.jpg → 413
  - `test_upload_accepted_within_global_limit()` — configura `web.max_file_upload_size=134217728` → upload de seed_image.jpg → 201
  - `test_upload_reads_ir_config_param()` — confirma que o parâmetro é alterável sem redeploy

> **Nota M4**: T019 **cria** o arquivo. T020 **extende** o mesmo arquivo adicionando os cenários de US1–US6. T020 depende de T019.

**Checkpoint**: Comportamento de configuração dinâmica de tamanho validado

---

## Phase 8: E2E Integration Tests

**Purpose**: Testes de integração E2E cobrindo todos os user stories e multi-tenancy

- [X] T020 *(depende de T019)* Estender `integration_tests/test_property_attachments_api.sh` com os cenários E2E de US1–US6:
  - **US1**: `test_owner_uploads_image()` — fluxo completo upload → metadados retornados com download_url correto
  - **US1**: `test_multitenancy_isolation_upload()` — upload em propriedade de company_b por usuário de company_a → 404
  - **US1**: `test_max_images_per_property()` — 50+ imagens → 422
  - **US2**: `test_manager_uploads_document()` — upload de PDF → 201
  - **US2**: `test_max_documents_per_property()` — 20+ documentos → 422
  - **US3**: `test_authenticated_download()` — JWT válido → binário + headers corretos
  - **US3**: `test_unauthenticated_download()` — sem JWT → 401
  - **US3**: `test_cross_company_download()` — arquivo company_b por usuário company_a → 404
  - **US3**: `test_attachment_not_on_property()` — attachment_id de outra propriedade → 404
  - **US4**: `test_owner_deletes_attachment()` — Owner deleta → 204 → GET lista não retorna mais
  - **US4**: `test_delete_cross_company()` → 404
  - **US6**: `test_list_attachments_returns_metadata()` — após upload, lista retorna item
  - **US6**: `test_list_filter_by_type()` — `?attachment_type=image` filtra corretamente
  - **US6**: `test_list_pagination()` — `?limit=2&offset=0` e `?limit=2&offset=2` paginam corretamente
  - **US6**: `test_list_cross_company_returns_404()` — outra company → 404

---

## Phase 9: Spec 016 Integration (Phase 4 da spec)

**Purpose**: Migrar `download_url` do serializer legado para `/api/v1/...`

> ⚠️ **Atenção**: Esta fase altera comportamento existente de `serialize_property()`. Coordenar com equipe mobile antes do merge — breaking change nos campos `property_images[].url` e `property_files[].url`.

- [X] T021 ⛔ **BLOCKED — aguarda decisão de PM + alinhamento com equipe mobile (breaking change)** Atualizar `serialize_property_mapping_fields()` em `18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py` (linhas 125–142):
  - Mudar `f'/web/content/real.estate.property.photo/{photo.id}/image?download=true'` para `f'/api/v1/properties/{property_record.id}/attachments/{photo.id}/download'`
  - Mudar `f'/web/content/real.estate.property.document/{document.id}/file?download=true'` para `f'/api/v1/properties/{property_record.id}/attachments/{document.id}/download'`
  - **Importante**: Os IDs de `photo` e `document` aqui são IDs dos custom models (`real.estate.property.photo`, `real.estate.property.document`), NÃO IDs de `ir.attachment`. O endpoint de download deve aceitar ambos — ou este campo deve apontar apenas para `ir.attachment` IDs. Revisar com PM antes de implementar.

---

## Phase 10: Swagger (ADR-005)

**Purpose**: Documentar os 4 novos endpoints no `thedevkitchen_api_endpoint` table via XML data file

> ⚠️ Swagger é gerado **dinamicamente do banco** — nunca editar arquivos estáticos.
> Usar a skill **swagger-updater** para esta fase.

- [X] T022 Adicionar registros para os 4 endpoints no arquivo XML de data do módulo:
  - `POST /api/v1/properties/{id}/attachments`
  - `GET /api/v1/properties/{id}/attachments`
  - `GET /api/v1/properties/{id}/attachments/{attachment_id}/download`
  - `DELETE /api/v1/properties/{id}/attachments/{attachment_id}`
  - Arquivo: `18.0/extra-addons/quicksol_estate/data/` (verificar padrão existente no módulo)
- [X] T023 Upgrade do módulo `quicksol_estate` para sincronizar DB com novos registros de Swagger

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T024 [P] Audit logging: verificar que uploads rejeitados (MIME inválido, size exceeded, 403, 404 cross-company) produzem `_logger.warning()` com contexto suficiente — NFR4
- [X] T025 [P] Lint: rodar `cd 18.0 && bash lint.sh` e corrigir quaisquer erros de ruff/black/isort no novo controller
- [X] T026 [P] Registrar o módulo `quicksol_estate` na fila de update e validar que `odoo -u quicksol_estate --stop-after-init` termina sem erros
- [X] T027 Criar Postman Collection `docs/postman/feature017_property_attachments_v1.0_postman_collection.json` seguindo ADR-016 (usar skill **postman-collection-manager**)

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundation) → Phase 3 (US1+US2) → Phase 4 (US6) → Phase 5 (US3)
                                                             ↘ Phase 6 (US4) ↗
Phase 2 (Foundation) → Phase 7 (US5) [testes apenas — implementação já em T004]
Phase 5 (US3) + Phase 6 (US4) → Phase 8 (E2E)
Phase 5 (US3) → Phase 9 (Spec 016 Integration)
Phase 8 (E2E) → Phase 10 (Swagger) → Phase 11 (Polish)
```

## Parallel Execution Opportunities

| Story Phase | Tasks em Paralelo |
|-------------|-------------------|
| Phase 2 | T004, T005, T006 podem ser escritos simultaneamente (funções independentes) |
| Phase 3 | T009, T010, T011, T012 (fixtures) podem ser criados em paralelo com T008 (implementação) |
| Phase 3 | T015 (teste unitário list URL) após T006 |
| Phase 11 | T024, T025, T026 em paralelo |

## Implementation Strategy

**MVP Scope** (Phases 1–5):
1. Setup (T001, T002) — ~15 min
2. Foundation helpers (T003–T007) — ~45 min
3. POST upload endpoint (T008) + fixtures (T009–T012) + unit tests (T013) — ~2h
4. GET list endpoint (T014) + unit test (T015) — ~30 min
5. GET download endpoint (T016) + unit test (T017) — ~30 min

**MVP estimado**: ~4h desenvolvimento → `POST`, `GET /attachments`, `GET /attachments/{id}/download` funcionais e testados

**Phase 2 increment** (Phases 6–7): `DELETE` + validação de configuração dinâmica (~45 min)

**Phase 3 increment** (Phases 8–11): E2E + Spec 016 serializer migration + Swagger + Postman (~2h)

---

## Task Count Summary

| Phase | Tarefas | User Stories |
|-------|---------|--------------|
| 1 — Setup | 2 | — |
| 2 — Foundation | 5 | — |
| 3 — Upload (US1+US2) | 7 | US1, US2 |
| 4 — List (US6) | 2 | US6 |
| 5 — Download (US3) | 2 | US3 |
| 6 — Delete (US4) | 1 | US4 |
| 7 — Config (US5) | 1 | US5 |
| 8 — E2E | 1 | todos |
| 9 — Spec 016 integration | 1 | — |
| 10 — Swagger | 2 | — |
| 11 — Polish | 4 | — |
| **Total** | **28** | **6 user stories** |

**Parallel opportunities identified**: 8 tarefas marcadas `[P]`
**MVP tasks (Phases 1–5)**: T001–T017 (17 tarefas)
