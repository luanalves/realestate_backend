# Tasks: CMS Domain

**Feature Branch**: `021-cms-domain`
**Input**: [spec.md](spec.md)
**Module path**: `18.0/extra-addons/thedevkitchen_cms/`

---

## Phase 1: Setup — Estrutura do Módulo

**Purpose**: Criar a estrutura base do módulo Odoo antes de qualquer implementação

- [ ] T001 Criar estrutura de diretórios do módulo `thedevkitchen_cms/` com `__init__.py`, `__manifest__.py`, `models/`, `controllers/`, `services/`, `views/`, `data/`, `security/`, `tests/unit/`
- [ ] T002 [P] Preencher `__manifest__.py` com nome, versão, dependências (`quicksol_estate`, `thedevkitchen_apigateway`, `thedevkitchen_observability`) e lista de arquivos data/security/views
- [ ] T003 [P] Criar `security/ir.model.access.csv` com as ACLs iniciais para os 5 modelos CMS (leitura para todos os grupos autenticados, escrita restrita)

**Checkpoint**: Módulo instalável no Odoo sem erros de manifesto

---

## Phase 2: Foundational — Modelos e Banco de Dados

**Purpose**: Modelos de dados que bloqueiam toda implementação posterior

- [ ] T004 Criar modelo `thedevkitchen.cms.settings` em `models/cms_settings.py` com campos: `company_slug` (Char, unique), `og_default_title`, `og_default_description`, `custom_css` (Text), `custom_js` (Text), `custom_js_last_modified_by` (Many2one res.users), `custom_js_last_modified_at` (Datetime), `company_id` (Many2one res.company, required). Adicionar `_sql_constraints` para `UNIQUE(company_slug)` e `UNIQUE(company_id)` (singleton).

- [ ] T005 [P] Criar modelo `thedevkitchen.cms.page` em `models/cms_page.py` com campos: `name` (Char, required), `slug` (Char, required), `status` (Selection: draft/pending_review/published/archived), `title` (Char — SEO), `meta_description` (Text), `og_title` (Char), `og_description` (Text), `og_image_id` (Many2one cms.media), `canonical_url` (Char), `robots_meta` (Selection), `structured_data` (Text — JSON-LD), `published_at` (Datetime), `company_id` (Many2one res.company). Herdar `mail.thread`. Adicionar `_sql_constraints` para `UNIQUE(slug, company_id)`.

- [ ] T006 [P] Criar modelo `thedevkitchen.cms.page.content` em `models/cms_page_content.py` com campos: `page_id` (Many2one cms.page, required, ondelete='cascade'), `content` (Text — JSON Puck). Constraint `UNIQUE(page_id)`.

- [ ] T007 [P] Criar modelo `thedevkitchen.cms.template` em `models/cms_template.py` com campos: `name` (Char), `category` (Selection: landing/property/about), `company_id` (Many2one res.company). Constraint `UNIQUE(name, company_id)`.

- [ ] T008 [P] Criar modelo `thedevkitchen.cms.template.content` em `models/cms_template_content.py` com campos: `template_id` (Many2one cms.template, required, ondelete='cascade'), `content` (Text — JSON Puck). Constraint `UNIQUE(template_id)`.

- [ ] T009 [P] Criar modelo `thedevkitchen.cms.media` em `models/cms_media.py` com campos: `name` (Char), `mime_type` (Char), `url` (Char), `file_size` (Integer), `attachment_id` (Many2one ir.attachment), `company_id` (Many2one res.company). Documentar que `unlink()` é hard delete (override explícito).

- [ ] T010 Adicionar `@api.constrains` em `cms_page.py`: validação de `slug` via regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`; validação de `structured_data` como JSON válido; validação de `og_image_id.company_id == self.company_id`.

- [ ] T011 Adicionar `@api.constrains` em `cms_settings.py`: validação de `company_slug` via regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`; validação de `custom_css` contra padrões de injection (`expression(`, `behavior:`, `url(javascript:`).

- [ ] T012 Atualizar `capability_service.py` em `quicksol_estate/services/` adicionando `CMSTemplate` e `CMSSettings` a `ALLOWED_SUBJECTS` e regras CMS nas `ROLE_RULES`: owner/director/manager = full access; agent = somente leitura de `CMSPage` e `CMSMedia`.

**Checkpoint**: `docker compose exec odoo bash -c "odoo -d realestate -u thedevkitchen_cms"` instala sem erros; tabelas criadas no banco

---

## Phase 3: US1 + US4 — CRUD de Páginas e Ciclo de Vida (Priority: P1)

**Goal**: Criar, editar e publicar páginas via API. Toda mudança de status por `PUT /api/v1/cms/pages/:id`

**Independent Test**: `POST /api/v1/cms/pages` → `PUT` com `{"status": "published"}` → `GET /api/v1/cms/pages/:id` retorna `status=published`

### Testes para US1 + US4

- [ ] T013 [P] Criar testes unitários `tests/unit/test_cms_page_validations.py`: slug inválido → ValidationError; conteúdo > 512KB → ValidationError; slug duplicado → IntegrityError; JSON-LD inválido → ValidationError; transições de estado inválidas → ValidationError
- [ ] T014 [P] Criar testes unitários `tests/unit/test_cms_status_machine.py`: testar todas as transições válidas (draft→pending_review, pending_review→published, pending_review→draft, published→archived, archived→draft) e inválidas (draft→archived, archived→published) usando mock do ORM
- [ ] T015 [P] Criar testes E2E `integration_tests/test_us021_cms_page_crud.sh`: POST criar página, PUT atualizar metadados, PUT mudar status (fluxo completo), GET por ID, DELETE, isolamento multi-tenant (página de outra imobiliária retorna 404)

### Implementação de US1 + US4

- [ ] T016 Criar `services/cms_page_service.py` com métodos: `create_page()`, `update_page()` (valida conteúdo ≤ 512KB e JSON válido antes de persistir em tabela separada), `change_status()` (valida transição via state machine), `duplicate_page()` (gera slug com sufixo incremental)
- [ ] T017 Criar `controllers/cms_page_controller.py` com endpoints:
  - `POST /api/v1/cms/pages` — criar página (status=draft)
  - `GET /api/v1/cms/pages` — listar páginas da imobiliária (sem campo `content`, paginado)
  - `GET /api/v1/cms/pages/:id` — detalhes completos (inclui conteúdo via join)
  - `PUT /api/v1/cms/pages/:id` — atualizar metadados e/ou status
  - `DELETE /api/v1/cms/pages/:id` — soft delete (`active=False`)
  - `POST /api/v1/cms/pages/:id/duplicate` — duplicar página
  Aplicar decoradores `@require_jwt`, `@require_session`, `@require_company` em todos.
- [ ] T018 Implementar state machine em `cms_page_service.py`: mapa de transições permitidas; lançar `{"error": "invalid_status_transition", "from": ..., "to": ..., "allowed": [...]}` para transições inválidas; atualizar `published_at` quando `status → published`

**Checkpoint**: US1 e US4 funcionais e testados de forma independente

---

## Phase 4: US2 — Biblioteca de Mídia (Priority: P1)

**Goal**: Upload seguro de arquivos com validação por conteúdo real (magic bytes)

**Independent Test**: Upload de `.jpg` com conteúdo PDF retorna 415; upload válido retorna 201 com URL

### Testes para US2

- [ ] T019 [P] Criar testes unitários `tests/unit/test_cms_media_validations.py`: MIME proibido → erro; magic bytes divergentes → erro; arquivo maior que limite → erro; path traversal no filename → sanitizado
- [ ] T020 [P] Criar testes E2E `integration_tests/test_us021_cms_media.sh`: upload válido (jpg, png, mp4, pdf), upload com MIME inválido, upload com magic bytes divergentes, upload acima do limite, DELETE (verificar remoção do ir.attachment), isolamento multi-tenant

### Implementação de US2

- [ ] T021 Criar `services/cms_media_service.py` com: validação de MIME via `python-magic` (magic bytes, não extensão); whitelist de MIMEs permitidos por tipo; limites por tipo (imagem: 10MB, vídeo: 100MB, documento: 20MB); sanitização de filename (strip path traversal, normalize unicode)
- [ ] T022 Criar `controllers/cms_media_controller.py` com endpoints:
  - `POST /api/v1/cms/media/upload` — upload via multipart/form-data
  - `GET /api/v1/cms/media` — listar mídia da imobiliária
  - `GET /api/v1/cms/media/:id` — detalhes de um arquivo
  - `DELETE /api/v1/cms/media/:id` — hard delete (override de `unlink()` para remover `ir.attachment`)
  Aplicar decoradores `@require_jwt`, `@require_session`, `@require_company` em todos.

**Checkpoint**: US2 funcional — uploads maliciosos rejeitados, uploads válidos acessíveis via URL

---

## Phase 5: US3 — Rotas Interna e Pública de Consulta (Priority: P1)

**Goal**: Rota interna com JWT para integrantes; rota pública com token de integração para Next.js SSR

**Independent Test**: Rota pública sem token retorna 401; com token válido e página publicada retorna 200 sem campos operacionais

### Testes para US3

- [ ] T023 [P] Criar testes unitários `tests/unit/test_cms_public_route.py`: acesso sem token → 401; token inválido → 401; página não publicada → 404; company_slug não existe → 404; campos `status`, `created_at`, `updated_at`, `custom_js`, `custom_css` ausentes na resposta pública
- [ ] T024 [P] Criar testes E2E `integration_tests/test_us021_cms_public.sh`: GET rota pública com token válido, GET sem token, GET com página em draft, GET com company_slug inexistente, isolamento entre imobiliárias, validar campos ausentes no payload

### Implementação de US3

- [ ] T025 Criar `controllers/cms_public_controller.py` com endpoint:
  - `GET /api/v1/public/cms/:company_slug/pages/:page_slug` — autenticado via `@require_jwt` existente (sem `@require_session` nem `@require_company`)
  Lógica: validar JWT via decorador padrão; resolver `company_slug → company_id` via `cms.settings`; buscar página com `status=published` e `active=True`; retornar Puck JSON + campos SEO; **nunca retornar** `custom_js`, `custom_css`, `status`, `created_at`, `updated_at`.
  Marcar como `# public endpoint` com `auth='none'` + aplicar `@require_jwt` manualmente (padrão para rotas que precisam de JWT mas não de sessão).

**Checkpoint**: US3 funcional — rota interna (JWT+session+company) e rota pública (JWT only) operando corretamente

---

## Phase 6: US5 — Templates (Priority: P2)

**Goal**: Criar templates reutilizáveis e criar páginas a partir deles

**Independent Test**: Criar template → criar página com `template_id` → conteúdo da página igual ao do template

### Testes para US5

- [ ] T027 [P] Criar testes E2E `integration_tests/test_us021_cms_templates.sh`: criar template, listar templates, criar página a partir de template, criar página com template de outra imobiliária (422), role agent em GET templates (403)

### Implementação de US5

- [ ] T028 Criar `controllers/cms_template_controller.py` com endpoints:
  - `POST /api/v1/cms/templates` — criar template
  - `GET /api/v1/cms/templates` — listar templates da imobiliária
  - `GET /api/v1/cms/templates/:id` — detalhes do template
  - `PUT /api/v1/cms/templates/:id` — atualizar template
  - `DELETE /api/v1/cms/templates/:id` — remover template
  Aplicar decoradores `@require_jwt`, `@require_session`, `@require_company` em todos.
- [ ] T029 Atualizar `cms_page_service.create_page()` para aceitar `template_id`: copiar `content` do template para `thedevkitchen.cms.page.content`; validar que `template_id.company_id == company_id` antes de copiar

**Checkpoint**: US5 funcional — templates criados e páginas instanciadas a partir deles

---

## Phase 7: US6 — Configurações CMS (Priority: P3)

**Goal**: Configurar `company_slug`, CSS e JS customizados por imobiliária

**Independent Test**: Configurar `company_slug` → acessar rota pública com o slug → resolução correta da imobiliária

### Testes para US7

- [ ] T030 [P] Criar testes unitários `tests/unit/test_cms_settings_validations.py`: company_slug inválido → ValidationError; CSS injection → ValidationError; custom_js por director/manager → 403
- [ ] T031 [P] Criar testes E2E `integration_tests/test_us021_cms_settings.sh`: GET settings (auto-criação singleton), PUT company_slug válido, PUT company_slug duplicado (409), PUT CSS injection (422), PUT custom_js por manager (403), PUT custom_js por owner (200 + auditoria), GET por manager sem custom_js na resposta

### Implementação de US6

- [ ] T032 Criar `controllers/cms_settings_controller.py` com endpoints:
  - `GET /api/v1/cms/settings` — obter settings da imobiliária (auto-cria singleton se não existe)
  - `PUT /api/v1/cms/settings` — atualizar settings
  Aplicar decoradores `@require_jwt`, `@require_session`, `@require_company` em todos.
- [ ] T033 Criar `services/cms_settings_service.py` com: lógica de singleton (get-or-create por `company_id`); validação de `custom_js` restrita ao role `owner` com preenchimento de campos de auditoria; exclusão de `custom_js` da resposta para roles não-owner

**Checkpoint**: US6 funcional — company_slug resolve na rota pública; custom_js auditado

---

## Phase 8: US7 — Interface Administrativa Odoo (Priority: P2)

**Goal**: Menus e views Odoo para administração direta do CMS pelo usuário `admin`

**Independent Test**: Navegar para menu "CMS" no Odoo como admin → todas as views carregam sem erros no console

### Testes para US7

- [ ] T034 Criar testes Cypress `cypress/e2e/views/cms.cy.js` com 6 testes:
  - Menu CMS carrega sem "Oops!"
  - List view de páginas exibe status badge com 4 estados e colunas `created_at`/`updated_at`
  - Form view de página exibe statusbar com 4 status e aba "SEO"
  - Form view de template carrega sem erro
  - Form view de settings exibe `company_slug` e seção "Código Customizado"
  - Zero erros JavaScript no console durante toda a navegação

### Implementação de US7

- [ ] T035 [P] Criar `views/cms_page_views.xml`: list view com `status` badge colorido (4 estados), colunas `created_at`/`updated_at` com `optional="show"`, search filters por status; form view com statusbar, campos SEO em aba dedicada "SEO", campo `content` em aba "Conteúdo"
- [ ] T036 [P] Criar `views/cms_template_views.xml`: list view e form view de templates com campo `category`
- [ ] T037 [P] Criar `views/cms_media_views.xml`: list view de arquivos com `mime_type`, `file_size`, URL
- [ ] T038 [P] Criar `views/cms_settings_views.xml`: form view com `company_slug`, seção "Código Customizado (Avançado)" separada para `custom_js`
- [ ] T039 Criar `views/cms_menus.xml`: menu principal "CMS" com submenus "Páginas", "Templates", "Mídia", "Configurações" (sem atributo `groups` — acesso via RBAC da API)

**Checkpoint**: Navegação Odoo admin sem erros; 6 testes Cypress passando

---

## Phase 9: US8 — Observabilidade (Priority: P3)

**Goal**: Eventos estruturados e métricas Prometheus para todas as operações críticas do CMS

**Independent Test**: Publicar uma página → evento `cms.page.published` aparece no Loki com campos corretos

### Testes para US8

- [ ] T040 Criar testes unitários `tests/unit/test_cms_observability.py`: verificar que `cms_page_service.change_status()` emite evento `cms.page.status_changed` com campos corretos usando mock do módulo de observabilidade; verificar que `cms_media_service` incrementa counter `cms_media_uploads_total`; verificar que CSS injection emite evento `cms.css_injection_blocked`

### Implementação de US8

- [ ] T041 Adicionar emissão de eventos em `cms_page_service.py`:
  - `cms.page.status_changed` em toda mudança de status (campos: `company_id`, `page_id`, `slug`, `from_status`, `to_status`, `author_id`)
  - `cms.page.published` adicional quando `to_status == published` (campos: `published_at`)
- [ ] T042 [P] Adicionar emissão de eventos em `cms_media_service.py`: counter `cms_media_uploads_total` com labels `company_id`, `mime_type`, `type`
- [ ] T043 [P] Adicionar emissão de evento `cms.css_injection_blocked` em `cms_settings_service.py` com campos `company_id`, `field`
- [ ] T044 [P] Registrar métricas Prometheus: gauge `cms_pages_by_status` (por status, 4 valores: draft/pending_review/published/archived); atualizar no `change_status()`

**Checkpoint**: Eventos visíveis no Loki; métricas em `/metrics`

---

## Phase 10: Validação Final

**Purpose**: Verificação cross-cutting de todos os requisitos de segurança e isolamento

- [ ] T045 Criar testes E2E `integration_tests/test_us021_rbac_matrix.sh`: testar todas as combinações de role × endpoint do CMS (owner/director/manager/agent/outros) verificando 200 ou 403 conforme matriz do spec.md; usar pelo menos 2 imobiliárias distintas para isolamento
- [ ] T046 [P] Criar testes E2E `integration_tests/test_us021_multitenancy.sh`: para cada entidade (page, template, media, settings), verificar que acesso cross-company retorna 404; verificar que `company_slug` duplicado retorna 409; verificar que `og_image_id` de outra imobiliária é rejeitado

**Checkpoint**: Matriz RBAC 100% correta; isolamento multi-tenant verificado

---

## Phase 11: Swagger (após todas as atividades desenvolvidas e validadas)

**Purpose**: Documentar todos os endpoints do módulo CMS no Swagger UI

- [ ] T047 Criar `data/api_endpoints.xml` usando a skill `swagger-updater` com todos os endpoints do módulo (25 endpoints: 7 pages + 1 public + 5 templates + 4 media + 2 settings + 1 duplicate):
  - Cada endpoint com `name`, `path`, `method`, `summary`, `description`, `tags`, `protected`, `request_schema`, `response_schema`
  - Endpoints autenticados: `protected=True`, tag `CMS`
  - Endpoint público: `protected=False`, tag `CMS Public`
  - Não duplicar exemplos em `description` quando `request_schema`/`response_schema` presentes
- [ ] T048 Fazer upgrade do módulo e validar todos os endpoints em `/api/v1/openapi.json` e `/api/docs`:
  ```bash
  docker compose exec odoo bash -c "odoo -d realestate -u thedevkitchen_cms"
  ```

**Checkpoint**: Todos os 25 endpoints do CMS visíveis e documentados no Swagger UI

---

## Phase 12: Flowcharts (após todas as atividades desenvolvidas e validadas)

**Purpose**: Documentar visualmente as jornadas de usuário com os endpoints envolvidos

- [ ] T049 Criar `specs/021-cms-domain/flowcharts.md` com diagramas Mermaid para cada jornada da spec:
  - **Fluxo 1 — Criar e publicar página**: POST /pages → PUT /pages/:id (status=published) → GET /public/:company_slug/pages/:page_slug
  - **Fluxo 2 — Upload de mídia**: POST /media/upload → GET /media/:id
  - **Fluxo 3 — Rota interna vs pública**: comparação de autenticação e campos retornados
  - **Fluxo 4 — State machine de páginas**: diagrama de estados (draft/pending_review/published/archived) com transições válidas e inválidas
  - **Fluxo 5 — Fluxo editorial com revisão**: POST /pages → PUT (pending_review) → PUT (published/draft)
  - **Fluxo 6 — Criar página a partir de template**: POST /templates → POST /pages com template_id
  - **Fluxo 7 — Configurar company_slug**: PUT /settings → GET /public/:company_slug
  - **Fluxo 8 — RBAC por endpoint**: tabela de role × endpoint com permissões

**Checkpoint**: `flowcharts.md` com todos os 8 diagramas renderizáveis em markdown preview
