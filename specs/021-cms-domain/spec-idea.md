# Feature Specification: CMS Domain

**Feature Branch**: `021-cms-domain`
**Created**: 2026-05-20
**Updated**: 2026-05-23
**Status**: Draft
**Solution Type**: Both — API REST headless + Odoo UI (admin)
**ADR References**: ADR-003, ADR-004, ADR-007, ADR-008, ADR-009, ADR-011, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-021, ADR-022

## Executive Summary

Implementar o domínio CMS headless da plataforma, permitindo que imobiliárias criem, gerenciem e publiquem páginas web usando o editor **Puck** (`@measured/puck`), cujo conteúdo é armazenado como árvore JSON e renderizado exclusivamente no frontend React. A feature é **multicanal**: expõe **API REST headless** para os roles da imobiliária (owner/director/manager/agent via frontend Next.js) e **interface Odoo UI** para o usuário `admin` da plataforma gerenciar conteúdo diretamente.

O módulo `thedevkitchen_cms` introduz 4 entidades (Page, Template, Media, Settings), **25 endpoints REST** (24 autenticados + 1 público), views Odoo 18.0, **publicação agendada via Celery** com fila dedicada (`celery_cms_worker`), **campos SEO avançados** (Open Graph, canonical URL, robots meta, JSON-LD), e integra-se ao sistema de capabilities (Feature 020) e observabilidade existentes.

**URL pública de página**: identificada por `company_slug` (em `cms.settings`) + `page_slug` (em `cms.page`). O Odoo resolve a company diretamente — Kong atua apenas como proxy de roteamento, sem conhecimento de regras de negócio.

---

## Slugs e Identificação de URL

### Slug de Página (`cms_page.slug`)
- Identifica a página **dentro** de uma imobiliária
- Regex: `^[a-z0-9]+(?:-[a-z0-9]+)*$` (lowercase, números e hífens — URL-safe)
- Único por company: constraint `UNIQUE(slug, company_id)` no PostgreSQL
- Chave natural composta para acesso público: `(company_slug, page_slug)`

### Slug de Company (`cms_settings.company_slug`)
- Identifica a imobiliária **na plataforma**
- Mesmo padrão de validação do page slug
- Único **globalmente** (platform-wide): constraint `UNIQUE(company_slug)` em settings
- Usado na URL pública: `GET /api/v1/public/cms/:company_slug/pages/:page_slug`
- O controller Odoo resolve `company_slug → company_id → page`

---

## Status State Machine de Páginas

```
                ┌──────────┐
         ┌─────►│  draft   │◄──────────────────────────────────┐
         │      └────┬─────┘                                    │
    reject│           │ submit_review / schedule / publish       │ cancel_schedule / reactivate
         │      ┌────▼──────────┐                               │
         │      │pending_review │──approve+publish──►┌─────────┴──────┐
         │      └────┬──────────┘                    │   published    │
         │           │ approve+schedule               └────────┬───────┘
         │      ┌────▼──────────┐                             │ archive
         └──────│   scheduled   │──(Celery ETA)──►            │
                └───────────────┘              ┌──────────────▼──┐
                                               │    archived     │
                                               └─────────────────┘
```

| Transição | Endpoint | Roles | Trigger |
|-----------|----------|-------|---------|
| draft → pending_review | `/submit-review` | owner/director/manager | manual |
| draft → scheduled | `/schedule` | owner/director/manager | manual |
| draft → published | `/publish` | owner/director/manager | manual |
| pending_review → draft | `/reject` | owner/director/manager | manual |
| pending_review → published | `/approve` (sem `publish_at`) | owner/director/manager | manual |
| pending_review → scheduled | `/approve` (com `publish_at`) | owner/director/manager | manual |
| scheduled → published | automático | sistema (Celery) | `publish_at` alcançado |
| scheduled → draft | `/cancel-schedule` | owner/director/manager | manual |
| published → archived | `/archive` | owner/director/manager | manual |
| archived → draft | `/reactivate` | owner/director/manager | manual |

---

## User Scenarios & Testing

### User Story 1: Criar e publicar uma página CMS com SEO (Priority: P1) 🎯 MVP

**As a** owner, director ou manager de uma imobiliária
**I want to** criar uma nova página com conteúdo Puck JSON, campos SEO e publicá-la
**So that** o conteúdo fique disponível no website com otimização de mecanismos de busca

**Acceptance Criteria**:
- [ ] Dado JWT+session+company válidos, quando `POST /api/v1/cms/pages` com `name`, `slug`, `content` e campos SEO, então página criada com `status=draft` e retorna 201 com HATEOAS links
- [ ] Dado página em draft, quando `POST /api/v1/cms/pages/:id/publish`, então `status=published`, `published_at` preenchido, retorna 200
- [ ] Dado `slug` com caracteres inválidos (uppercase, espaços, `/`, `..`), quando `POST`, então retorna 422 `{"error": "slug_invalid"}`
- [ ] Dado `content` JSON > 512KB, quando `POST` ou `PUT`, então retorna 422 `{"error": "content_too_large", "max_size_bytes": 524288, "received_size": N}`
- [ ] Dado `content` que não é JSON válido, então retorna 422 `{"error": "content_invalid_json"}`
- [ ] Dado slug já existente na mesma company, então retorna 409 `{"error": "slug_conflict", "field": "slug"}`
- [ ] Dado `robots_meta=noindex,nofollow`, quando `GET /api/v1/public/cms/:company_slug/pages/:page_slug`, então resposta inclui `robots_meta`
- [ ] Dado `og_title`, `og_description`, `og_image_id` preenchidos, quando endpoint público, então resposta inclui campos OG
- [ ] Dado `structured_data` com JSON-LD inválido, quando `POST` ou `PUT`, então retorna 422 `{"error": "structured_data_invalid_json"}`
- [ ] Dado página da company B, quando autenticado como company A, então retorna 404

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_slug_valid_formats()` | `my-page`, `page-1` → aceitos | ⚠️ Required |
| Unit | `test_slug_invalid_uppercase()` | `My-Page` → ValidationError | ⚠️ Required |
| Unit | `test_slug_invalid_spaces()` | `my page` → ValidationError | ⚠️ Required |
| Unit | `test_slug_invalid_path_traversal()` | `../etc/passwd` → ValidationError | ⚠️ Required |
| Unit | `test_slug_unique_per_company()` | Duplicado na mesma company → IntegrityError | ⚠️ Required |
| Unit | `test_slug_same_in_different_company()` | Mesmo slug em company diferente → OK | ⚠️ Required |
| Unit | `test_content_json_valid()` | JSON Puck válido aceito | ⚠️ Required |
| Unit | `test_content_json_invalid_string()` | String não-JSON → ValidationError | ⚠️ Required |
| Unit | `test_content_size_limit_exceeded()` | Content > 512KB → ValidationError | ⚠️ Required |
| Unit | `test_publish_sets_published_at()` | `published_at` definido ao publicar | ⚠️ Required |
| Unit | `test_soft_delete_sets_active_false()` | DELETE → `active=False` | ⚠️ Required |
| Unit | `test_structured_data_invalid_json()` | JSON-LD inválido → ValidationError | ⚠️ Required |
| E2E (API) | `test_owner_creates_and_publishes_page()` | Fluxo completo: criar → publicar | ⚠️ Required |
| E2E (API) | `test_agent_view_only_pages()` | Agent: GET ok, POST/PUT/DELETE → 403 | ⚠️ Required |
| E2E (API) | `test_multitenancy_page_isolation()` | Company B não acessa páginas da Company A | ⚠️ Required |
| E2E (API) | `test_seo_fields_returned_in_public_endpoint()` | OG + robots_meta na resposta pública | ⚠️ Required |

---

### User Story 2: Gerenciar biblioteca de mídia (Priority: P1) 🎯 MVP

**As a** owner, director ou manager
**I want to** fazer upload de imagens, documentos e vídeos e referenciá-los em páginas CMS
**So that** a agência tenha assets de mídia gerenciados e organizados

**Acceptance Criteria**:
- [ ] Dado `multipart/form-data` com MIME permitido e tamanho dentro do limite, quando `POST /api/v1/cms/media/upload`, então arquivo armazenado em `ir.attachment`, metadados salvos, retorna 201 com `id`, `url`, `mime_type`
- [ ] Dado MIME não permitido (ex: `text/html`, `application/javascript`), quando upload, então retorna 415 `{"error": "unsupported_mime", "received": "text/html"}`
- [ ] Dado extensão `.jpg` mas conteúdo real é PDF (magic bytes), quando upload, então retorna 415 `{"error": "mime_mismatch"}`
- [ ] Dado imagem > 10MB, quando upload, então retorna 413 `{"error": "file_too_large", "max_size_bytes": 10485760}`
- [ ] Dado vídeo > 100MB, quando upload, então retorna 413 `{"error": "file_too_large", "max_size_bytes": 104857600}`
- [ ] Dado `DELETE /api/v1/cms/media/:id`, então `ir.attachment.unlink()` é chamado (hard delete — ADR-015 exception) e retorna 200
- [ ] Dado mídia da company B, quando autenticado como company A, então retorna 404

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_mime_whitelist_jpeg()` | `image/jpeg` aceito | ⚠️ Required |
| Unit | `test_mime_whitelist_mp4()` | `video/mp4` aceito | ⚠️ Required |
| Unit | `test_mime_blacklist_html()` | `text/html` → 415 | ⚠️ Required |
| Unit | `test_mime_mismatch_detection()` | Magic bytes divergem da extensão → 415 | ⚠️ Required |
| Unit | `test_image_size_limit_exceeded()` | Imagem > 10MB → 413 | ⚠️ Required |
| Unit | `test_secure_filename_path_traversal()` | `../../etc/passwd.jpg` sanitizado | ⚠️ Required |
| E2E (API) | `test_owner_uploads_image()` | Upload completo retorna URL acessível | ⚠️ Required |
| E2E (API) | `test_multitenancy_media_isolation()` | Isolamento de mídia por company | ⚠️ Required |

---

### User Story 3: Criar página a partir de template (Priority: P2)

**As a** owner ou manager
**I want to** criar uma página pré-populada a partir de um template existente
**So that** eu possa iniciar com um layout conhecido sem partir do zero

**Acceptance Criteria**:
- [ ] Dado `POST /api/v1/cms/pages` com `template_id` válido da mesma company, então nova página criada com `content` copiado do template, `status=draft`
- [ ] Dado `template_id` de company diferente, então retorna 422 `{"error": "template_not_found"}`
- [ ] Dado `POST /api/v1/cms/pages/:id/duplicate`, então nova página criada com `name + " (Cópia)"` e `slug + "-copy"`, `status=draft`

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_create_page_from_template_copies_content()` | Content copiado do template | ⚠️ Required |
| Unit | `test_create_page_from_template_wrong_company()` | Template de outra company → 422 | ⚠️ Required |
| Unit | `test_duplicate_page_slug_suffix()` | Slug recebe sufixo `-copy` | ⚠️ Required |
| E2E (API) | `test_owner_creates_page_from_template()` | Fluxo completo | ⚠️ Required |

---

### User Story 4: Website público carrega página por slug (Priority: P2)

**As a** visitante do website da agência (sem autenticação)
**I want to** acessar `GET /api/v1/public/cms/:company_slug/pages/:page_slug`
**So that** o frontend Next.js renderize a página com o Puck JSON + metadados SEO

**Acceptance Criteria**:
- [ ] Dado `company_slug` válido e `page_slug` com `status=published`, quando acesso público, então retorna 200 com `content` (Puck JSON) + campos SEO (title, meta_description, og_*, robots_meta, structured_data) — **sem** `custom_css` ou `custom_js`
- [ ] Dado `company_slug` inexistente, então retorna 404 genérico
- [ ] Dado página com `status≠published` ou `active=False`, então retorna 404 genérico (prevenção de enumeração)
- [ ] Endpoint não requer autenticação (`auth='none'`)
- [ ] Resposta nunca inclui `custom_js` ou `custom_css`

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_public_endpoint_published_page_returns_seo()` | OG + robots_meta na resposta | ⚠️ Required |
| Unit | `test_public_endpoint_draft_returns_404()` | Draft → 404 | ⚠️ Required |
| Unit | `test_public_endpoint_scheduled_returns_404()` | Scheduled (não publicado ainda) → 404 | ⚠️ Required |
| Unit | `test_public_endpoint_no_custom_js_in_response()` | custom_js ausente da resposta | ⚠️ Required |
| Unit | `test_public_endpoint_invalid_company_slug()` | company_slug inexistente → 404 | ⚠️ Required |
| E2E (API) | `test_public_page_accessible_without_auth()` | Nenhum token necessário | ⚠️ Required |
| E2E (API) | `test_company_slug_isolates_pages()` | company_slug da company A não retorna páginas da B | ⚠️ Required |

---

### User Story 5: Owner configura CMS settings (CSS e JavaScript) (Priority: P3)

**As a** owner da imobiliária
**I want to** configurar CSS customizado, JavaScript customizado e o slug da company no website
**So that** eu possa personalizar aparência e comportamento da marca

**Acceptance Criteria**:
- [ ] Dado `company_slug` com formato inválido, quando `PUT /api/v1/cms/settings`, então retorna 422 `{"error": "company_slug_invalid"}`
- [ ] Dado `company_slug` já em uso por outra company, então retorna 409 `{"error": "company_slug_conflict"}`
- [ ] Dado `custom_css` contendo padrão proibido (`expression()`, `behavior:`, `url(javascript:)`), então retorna 422 `{"error": "css_injection_detected"}`
- [ ] Dado `custom_js` no body por `director` ou `manager`, então retorna 403
- [ ] Dado `custom_js` no body por `owner`, então salvo com `custom_js_last_modified_by` e `custom_js_last_modified_at` atualizados
- [ ] `GET /api/v1/cms/settings`: campo `custom_js` omitido da resposta para non-owner

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_company_slug_validation()` | Slug inválido → 422 | ⚠️ Required |
| Unit | `test_company_slug_unique_platform_wide()` | Slug duplicado → 409 | ⚠️ Required |
| Unit | `test_css_injection_expression()` | `expression()` → 422 | ⚠️ Required |
| Unit | `test_custom_js_restricted_to_owner()` | Director/manager → 403 | ⚠️ Required |
| Unit | `test_custom_js_audit_fields_updated()` | Campos de auditoria atualizados | ⚠️ Required |
| Unit | `test_settings_singleton_auto_created()` | Settings criadas automaticamente | ⚠️ Required |
| E2E (API) | `test_owner_updates_custom_js_with_audit()` | Fluxo completo com auditoria | ⚠️ Required |

---

### User Story 6: Agendar publicação de página (Priority: P2) 🎯 MVP

**As a** owner ou manager
**I want to** agendar a publicação de uma página para uma data/hora futura
**So that** o conteúdo seja publicado automaticamente no momento correto, sem intervenção manual

**Acceptance Criteria**:
- [ ] Dado `POST /api/v1/cms/pages/:id/schedule` com `publish_at` válido no futuro, então `status=scheduled`, `scheduled_publish_at` salvo, task Celery enfileirada com ETA, `celery_task_id` salvo, retorna 200
- [ ] Dado `publish_at` no passado, então retorna 422 `{"error": "publish_at_must_be_future"}`
- [ ] Dado `publish_at` sem timezone, então retorna 422 `{"error": "publish_at_must_include_timezone"}`
- [ ] Dado `POST /api/v1/cms/pages/:id/cancel-schedule`, então task Celery revogada, `status=draft`, `celery_task_id` limpo, retorna 200
- [ ] Dado task Celery executada no ETA, quando página ainda em `status=scheduled`, então `status=published`, `published_at` definido, evento `cms.page.published` emitido para observabilidade
- [ ] Dado task Celery executada mas página foi deletada (soft delete), então task abortada graciosamente, erro logado em observabilidade
- [ ] Dado task Celery executada mas página foi manualmente publicada antes do ETA, então task detecta status≠scheduled e aborta sem erro
- [ ] Endpoint `/approve` com body `{"publish_at": "..."}` equivale a `approve + schedule` (transição `pending_review → scheduled`)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_schedule_publish_at_future()` | Datetime futuro → OK | ⚠️ Required |
| Unit | `test_schedule_publish_at_past()` | Datetime passado → 422 | ⚠️ Required |
| Unit | `test_schedule_publish_at_no_timezone()` | Sem TZ → 422 | ⚠️ Required |
| Unit | `test_schedule_saves_celery_task_id()` | `celery_task_id` preenchido após schedule | ⚠️ Required |
| Unit | `test_cancel_schedule_revokes_task()` | Task revogada e `celery_task_id` limpo | ⚠️ Required |
| Unit | `test_celery_task_publishes_page()` | Task executa e publica página corretamente | ⚠️ Required |
| Unit | `test_celery_task_page_already_published()` | Page já publicada → task aborta sem erro | ⚠️ Required |
| Unit | `test_celery_task_page_soft_deleted()` | Page deletada → task aborta, erro logado | ⚠️ Required |
| E2E (API) | `test_owner_schedules_and_page_auto_publishes()` | Fluxo completo com Celery real | ⚠️ Required |
| E2E (API) | `test_owner_cancels_schedule()` | Cancelamento revoga task | ⚠️ Required |

---

### User Story 7: Admin gerencia CMS pela interface Odoo (Priority: P2)

**As a** administrador da plataforma (usuário `admin`)
**I want to** gerenciar páginas, templates, mídia e configurações CMS diretamente pela interface Odoo
**So that** operações de suporte e administração possam ser feitas sem depender do frontend headless

> ⚠️ **Acesso Model**: Este user story aplica-se **exclusivamente** ao usuário `admin` do Odoo.

**Acceptance Criteria**:
- [ ] Menu "CMS" carrega sem diálogo "Oops!" e sem erros no console
- [ ] List view de páginas exibe `status` com badges coloridos por estado, colunas opcionais com `optional="show"`
- [ ] Form view de página exibe statusbar com todos os 5 status, campos SEO em aba dedicada
- [ ] Form view de configurações exibe campo `company_slug` e seção "Código Customizado (Avançado)" separada
- [ ] Zero erros JavaScript no DevTools console (Chrome + Firefox)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (UI) | `cypress: test_cms_menu_loads_without_errors()` | Menu sem "Oops!" | ⚠️ Required |
| E2E (UI) | `cypress: test_cms_page_list_view()` | List view renderiza sem erros | ⚠️ Required |
| E2E (UI) | `cypress: test_cms_page_form_view()` | Form view com statusbar abre sem erros | ⚠️ Required |
| E2E (UI) | `cypress: test_cms_template_list_view()` | Templates list sem erros | ⚠️ Required |
| E2E (UI) | `cypress: test_cms_media_list_view()` | Mídia list sem erros | ⚠️ Required |
| E2E (UI) | `cypress: test_cms_settings_form_view()` | Settings form sem erros | ⚠️ Required |

---

### User Story 8: Observabilidade do domínio CMS (Priority: P3)

**As a** engenheiro de plataforma
**I want to** monitorar operações CMS (publicações, uploads, agendamentos) via Grafana/Loki/Prometheus
**So that** problemas (falhas de publicação agendada, picos de upload, erros de CSS injection) sejam detectáveis proativamente

**Acceptance Criteria**:
- [ ] Dado publicação de página, quando `POST /publish`, então evento `cms.page.published` logado estruturalmente em Loki com `company_id`, `page_id`, `slug`, `author_id`
- [ ] Dado falha de task Celery de publicação agendada, então evento `cms.scheduled_publish_failed` logado com `page_id`, `scheduled_publish_at`, `error`
- [ ] Dado upload de mídia, então contador Prometheus `cms_media_uploads_total` incrementado com labels `company_id`, `mime_type`, `type`
- [ ] Dado tentativa de CSS injection bloqueada, então evento `cms.css_injection_blocked` logado com `company_id`, `field`
- [ ] Dado `GET /api/v1/cms/pages` com latência > 500ms, então span OpenTelemetry registra tempo de resposta
- [ ] Métricas `cms_pages_by_status` (gauge) e `cms_scheduled_tasks_total` (counter) disponíveis em `/metrics`

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_publish_emits_observability_event()` | Evento logado na publicação | ⚠️ Required |
| Unit | `test_css_injection_emits_security_event()` | Evento logado no bloqueio | ⚠️ Required |
| Unit | `test_scheduled_fail_emits_error_event()` | Falha de Celery logada | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Gestão de Páginas CMS**
- FR1.1: CRUD completo para `thedevkitchen.cms.page` com multi-tenancy (ADR-008)
- FR1.2: Campo `content` armazena JSON Puck (Text field), validado com `json.loads()` e limite de 512KB
- FR1.3: Campo `slug` validado com regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`, único por company via `UNIQUE(slug, company_id)`
- FR1.4: State machine: `draft` → `pending_review` → `scheduled` → `published` → `archived` (com rollbacks)
- FR1.5: `published_at` preenchido automaticamente ao publicar (manual ou via Celery)
- FR1.6: Soft delete via `active=False` (ADR-015); páginas inativas não aparecem em listagens
- FR1.7: Duplicação cria cópia com nome sufixado e slug com `-copy`
- FR1.8: Criação suporta `template_id` opcional para pré-popular `content`

**FR2: Gestão de Mídia**
- FR2.1: Upload `multipart/form-data` com validação de MIME via magic bytes (`python-magic`)
- FR2.2: MIME whitelist: `image/jpeg`, `image/png`, `image/webp`, `image/gif`, `application/pdf`, `video/mp4`
- FR2.3: Limites: imagens/docs ≤ 10MB, vídeos ≤ 100MB (constantes no módulo)
- FR2.4: Filename sanitizado com `secure_filename`
- FR2.5: Armazenamento via `ir.attachment` com `res_model='thedevkitchen.cms.media'`
- FR2.6: Hard delete via `ir.attachment.unlink()` (ADR-015 exception)
- FR2.7: Campo `url` derivado do attachment Odoo

**FR3: Gestão de Templates**
- FR3.1: CRUD completo, acesso somente owner/director/manager
- FR3.2: Templates isolados por company (company-scoped)
- FR3.3: Campo `category` livre; soft delete via `active=False`

**FR4: Configurações CMS**
- FR4.1: Singleton `thedevkitchen.cms.settings` por company (criado automaticamente no primeiro acesso)
- FR4.2: Campo `company_slug` único na plataforma — usado no endpoint público para resolução de company
- FR4.3: `custom_css` validado server-side contra: `expression()`, `behavior:`, `url(javascript:)`
- FR4.4: `custom_js` write somente por role `owner` (restrição no service layer)
- FR4.5: Campos de auditoria `custom_js_last_modified_by` + `custom_js_last_modified_at`
- FR4.6: `GET /api/v1/cms/settings` omite `custom_js` da resposta para non-owner

**FR5: Endpoint Público**
- FR5.1: `GET /api/v1/public/cms/:company_slug/pages/:page_slug` — `auth='none'`, `# public endpoint`
- FR5.2: Odoo resolve `company_slug → company_id → page`; Kong apenas roteia
- FR5.3: Retorna apenas páginas `status=published` e `active=True`; qualquer outro caso → 404 genérico
- FR5.4: Resposta inclui: Puck JSON + campos SEO (title, meta_description, meta_keywords, og_*, canonical_url, robots_meta, structured_data)
- FR5.5: Resposta **nunca** inclui `custom_js` ou `custom_css`

**FR6: Capabilities RBAC Update**
- FR6.1: Adicionar `CMSTemplate` e `CMSSettings` em `ALLOWED_SUBJECTS` de `capability_service.py`
- FR6.2: Atualizar `ROLE_RULES` para owner/director/manager/agent
- FR6.3: Atualizar enum em `data/api_endpoints.xml`

**FR7: Odoo UI**
- FR7.1: Menu "CMS" sem `groups`; submenus: Páginas, Templates, Mídia, Configurações
- FR7.2: Views Odoo 18.0: `<list>`, sem `attrs`, `optional="show"` para colunas, sem `column_invisible` com Python
- FR7.3: Form view de página com statusbar de 5 estados e aba SEO dedicada
- FR7.4: Cypress E2E para todos os menus e views

**FR8: Publicação Agendada (Celery)**
- FR8.1: Campo `scheduled_publish_at` (Datetime) e `celery_task_id` (Char 255) em `cms_page`
- FR8.2: Endpoint `POST /api/v1/cms/pages/:id/schedule` enfileira task com `apply_async(eta=scheduled_publish_at)`
- FR8.3: Endpoint `POST /api/v1/cms/pages/:id/cancel-schedule` revoga task via `AsyncResult(task_id).revoke(terminate=True)`
- FR8.4: Task `publish_cms_page_task(page_id)` verifica `status=scheduled` antes de publicar (idempotente)
- FR8.5: Falha da task loga evento de erro em observabilidade e não altera status da página
- FR8.6: Novo worker: `celery_cms_worker` na fila `cms_events`, concurrency=2

**FR9: SEO Avançado**
- FR9.1: Campos Open Graph em `cms_page`: `og_title`, `og_description`, `og_image_id` (FK para cms.media)
- FR9.2: `canonical_url` (Char 500) — URL canônica da página para evitar conteúdo duplicado
- FR9.3: `robots_meta` (Selection) — `index,follow` (default), `noindex,nofollow`, `noindex,follow`, `index,nofollow`
- FR9.4: `structured_data` (Text) — JSON-LD livre, validado como JSON válido antes de persistir

**FR10: Observabilidade**
- FR10.1: Eventos estruturados logados (Loki): `cms.page.created`, `cms.page.status_changed`, `cms.page.published`, `cms.scheduled_publish_failed`, `cms.css_injection_blocked`, `cms.media.uploaded`
- FR10.2: Métricas Prometheus: `cms_pages_by_status` (gauge), `cms_scheduled_tasks_total` (counter), `cms_media_uploads_total` (counter com labels)
- FR10.3: Spans OpenTelemetry nos controllers CMS (via `thedevkitchen_observability`)

---

### Data Model (per ADR-004, knowledge_base/09-database-best-practices.md)

#### Entity: `thedevkitchen.cms.page`
- **Model Name**: `thedevkitchen.cms.page`
- **Table Name**: `thedevkitchen_cms_page`
- **Mixin**: `mail.thread` para audit trail de transições de status

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(200) | required | Título interno da página |
| `slug` | Char(200) | required, validated | URL slug — regex `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| `title` | Char(200) | optional | SEO title tag |
| `meta_description` | Text | optional | SEO meta description |
| `meta_keywords` | Char(500) | optional | SEO keywords |
| `og_title` | Char(200) | optional | Open Graph title |
| `og_description` | Text | optional | Open Graph description |
| `og_image_id` | Many2one | optional | `thedevkitchen.cms.media` — imagem OG |
| `canonical_url` | Char(500) | optional | URL canônica (evita conteúdo duplicado) |
| `robots_meta` | Selection | default=`index,follow` | `index,follow`, `noindex,nofollow`, `noindex,follow`, `index,nofollow` |
| `structured_data` | Text | optional | JSON-LD livre (validado como JSON) |
| `status` | Selection | required, default=`draft` | `draft`, `pending_review`, `scheduled`, `published`, `archived` |
| `content` | Text | optional | Puck JSON (max 512KB) |
| `template_id` | Many2one | optional | `thedevkitchen.cms.template` — usado na criação |
| `author_id` | Many2one | required | `res.users` |
| `company_id` | Many2one | required | `res.company` — multi-tenancy |
| `published_at` | Datetime | auto | Definido ao publicar |
| `scheduled_publish_at` | Datetime | optional | Datetime alvo para publicação agendada |
| `celery_task_id` | Char(255) | optional | ID da task Celery ativa (para revogação) |
| `active` | Boolean | default=True | Soft delete (ADR-015) |
| `create_date` | Datetime | auto | Audit |
| `write_date` | Datetime | auto | Audit |

**SQL Constraints**:
```python
_sql_constraints = [
    ('slug_company_uniq', 'unique(slug, company_id)',
     'O slug deve ser único por imobiliária.'),
]
```

**Python Constraints**:
```python
import re, json
SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
MAX_CONTENT_BYTES = 512 * 1024  # 512KB

@api.constrains('slug')
def _check_slug_format(self):
    for record in self:
        if not SLUG_PATTERN.match(record.slug):
            raise ValidationError('Slug deve conter apenas letras minúsculas, números e hífens.')

@api.constrains('content')
def _check_content_json(self):
    for record in self:
        if record.content:
            if len(record.content.encode('utf-8')) > MAX_CONTENT_BYTES:
                raise ValidationError('Content excede o limite de 512KB.')
            try:
                json.loads(record.content)
            except (ValueError, TypeError) as e:
                raise ValidationError('Content deve ser JSON válido.') from e

@api.constrains('structured_data')
def _check_structured_data_json(self):
    for record in self:
        if record.structured_data:
            try:
                json.loads(record.structured_data)
            except (ValueError, TypeError) as e:
                raise ValidationError('structured_data deve ser JSON válido (JSON-LD).') from e

@api.constrains('scheduled_publish_at')
def _check_scheduled_publish_at(self):
    from odoo.tools import datetime as dt_tools
    for record in self:
        if record.scheduled_publish_at and record.status == 'scheduled':
            if record.scheduled_publish_at <= fields.Datetime.now():
                raise ValidationError('scheduled_publish_at deve ser uma data futura.')
```

**Record Rules** (per ADR-019):
```xml
<record id="rule_cms_page_company" model="ir.rule">
    <field name="name">CMS Page: company isolation</field>
    <field name="model_id" ref="model_thedevkitchen_cms_page"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

---

#### Entity: `thedevkitchen.cms.template`
- **Model Name**: `thedevkitchen.cms.template`
- **Table Name**: `thedevkitchen_cms_template`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(200) | required | Nome do template |
| `category` | Char(100) | optional | Categoria livre (`landing`, `property`, `about`) |
| `content` | Text | optional | Puck JSON do template |
| `thumbnail` | Binary | optional | Preview em base64 |
| `thumbnail_mime` | Char(50) | optional | MIME do thumbnail |
| `company_id` | Many2one | required | `res.company` |
| `active` | Boolean | default=True | Soft delete |

---

#### Entity: `thedevkitchen.cms.media`
- **Model Name**: `thedevkitchen.cms.media`
- **Table Name**: `thedevkitchen_cms_media`
- **Nota**: Sem campo `active` — hard delete via `ir.attachment.unlink()` (ADR-015 exception)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `name` | Char(200) | required | Nome do arquivo (sanitizado) |
| `type` | Selection | required | `image`, `video`, `document` |
| `mime_type` | Char(100) | required | MIME detectado por magic bytes |
| `file_size` | Integer | required | Tamanho em bytes |
| `url` | Char(500) | computed | URL de acesso via ir.attachment |
| `alt_text` | Char(300) | optional | Texto alternativo (acessibilidade) |
| `attachment_id` | Many2one | required, ondelete=cascade | `ir.attachment` |
| `company_id` | Many2one | required | `res.company` |

---

#### Entity: `thedevkitchen.cms.settings`
- **Model Name**: `thedevkitchen.cms.settings`
- **Table Name**: `thedevkitchen_cms_settings`
- **Padrão**: Singleton por company — criado automaticamente no primeiro acesso

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto | Primary key |
| `company_id` | Many2one | required, unique | `res.company` |
| `company_slug` | Char(200) | required, validated, unique | Slug da company na URL pública — `^[a-z0-9]+(?:-[a-z0-9]+)*$` |
| `default_meta_title_suffix` | Char(200) | optional | Sufixo para title tags (ex: `\| Minha Imobiliária`) |
| `default_meta_description` | Text | optional | Meta description padrão do site |
| `max_image_width` | Integer | default=1920 | Limite de largura |
| `max_image_height` | Integer | default=1080 | Limite de altura |
| `max_image_size_bytes` | Integer | default=10485760 | Limite de tamanho imagem (10MB) |
| `custom_css` | Text | optional | CSS customizado (validado contra injection) |
| `custom_js` | Text | optional | JavaScript (risco alto — somente owner) |
| `custom_js_last_modified_by` | Many2one | optional | `res.users` |
| `custom_js_last_modified_at` | Datetime | optional | Timestamp da última alteração de `custom_js` |

**SQL Constraints**:
```python
_sql_constraints = [
    ('company_uniq', 'unique(company_id)',
     'Só pode existir uma configuração CMS por imobiliária.'),
    ('company_slug_platform_uniq', 'unique(company_slug)',
     'O slug da company deve ser único na plataforma.'),
]
```

---

### Celery Worker — `celery_cms_worker`

**ADR Reference**: ADR-021 (Async Processing Architecture)

```python
# 18.0/celery_worker/cms_tasks.py

from celery import Celery
from datetime import datetime

app = Celery('cms_tasks')

@app.task(bind=True, name='cms.publish_page', max_retries=3,
          default_retry_delay=60)
def publish_cms_page_task(self, page_id: int):
    """
    Publica uma página CMS agendada.
    Idempotente: verifica status antes de publicar.
    Loga falha em observabilidade sem alterar status da página.
    """
    try:
        with odoo_env() as env:
            page = env['thedevkitchen.cms.page'].browse(page_id)
            if not page.exists():
                log_cms_event('cms.scheduled_publish_failed',
                              page_id=page_id, error='page_not_found')
                return
            if page.status != 'scheduled':
                # Já publicado manualmente ou cancelado — abortar silenciosamente
                return
            page.write({
                'status': 'published',
                'published_at': datetime.utcnow(),
                'celery_task_id': False,
            })
            log_cms_event('cms.page.published', page_id=page_id,
                          company_id=page.company_id.id, slug=page.slug,
                          trigger='scheduled')
    except Exception as exc:
        log_cms_event('cms.scheduled_publish_failed',
                      page_id=page_id, error=str(exc))
        raise self.retry(exc=exc)
```

**Configuração Docker** (atualizar `docker-compose.yml`):
```yaml
celery_cms_worker:
  build: ./celery_worker
  command: celery -A cms_tasks worker --queues=cms_events --concurrency=2 --loglevel=info
  environment:
    - CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672/
    - CELERY_RESULT_BACKEND=redis://redis:6379/2
  depends_on:
    - rabbitmq
    - redis
    - odoo
```

---

### Capability Service Update (Feature 020 — `capability_service.py`)

**Arquivo**: `18.0/extra-addons/quicksol_estate/services/capability_service.py`

**Novos subjects em `ALLOWED_SUBJECTS`**:
```python
"CMSTemplate",
"CMSSettings",
```

**Atualização de `ROLE_RULES`**:

```python
# owner — acesso total CMS
("view",   "MenuCMS"),
("view",   "CMSPage"),    ("create", "CMSPage"),
("update", "CMSPage"),    ("delete", "CMSPage"),
("view",   "CMSMedia"),   ("create", "CMSMedia"),   ("delete", "CMSMedia"),
("view",   "CMSTemplate"),("create", "CMSTemplate"),
("update", "CMSTemplate"),("delete", "CMSTemplate"),
("view",   "CMSSettings"),("update", "CMSSettings"),

# director — acesso total CMS (igual owner para este domínio)

# manager — acesso total CMS (igual owner para este domínio)

# agent — view-only em páginas e mídia
("view",   "MenuCMS"),
("view",   "CMSPage"),
("view",   "CMSMedia"),
```

> **Nota de segurança**: `custom_js` write é restrito a `owner` no **service layer** — o RBAC marca `("update", "CMSSettings")` para os três roles, mas o controller rejeita `custom_js` para non-owners.

---

### API Endpoints (per ADR-007, ADR-009, ADR-011)

**Total: 25 endpoints** (24 autenticados + 1 público)

#### Pages (12 endpoints)

| Método | Rota | Roles | Descrição |
|--------|------|-------|-----------|
| GET | `/api/v1/cms/pages` | owner/director/manager/agent | Lista páginas (`?status=&search=&limit=&offset=`) |
| POST | `/api/v1/cms/pages` | owner/director/manager | Cria página |
| GET | `/api/v1/cms/pages/:id` | owner/director/manager/agent | Retorna página completa |
| PUT | `/api/v1/cms/pages/:id` | owner/director/manager | Atualiza campos |
| DELETE | `/api/v1/cms/pages/:id` | owner/director/manager | Soft delete |
| POST | `/api/v1/cms/pages/:id/publish` | owner/director/manager | `draft/pending_review → published` |
| POST | `/api/v1/cms/pages/:id/archive` | owner/director/manager | `published → archived` |
| POST | `/api/v1/cms/pages/:id/reactivate` | owner/director/manager | `archived → draft` |
| POST | `/api/v1/cms/pages/:id/duplicate` | owner/director/manager | Cria cópia com slug `-copy` |
| POST | `/api/v1/cms/pages/:id/submit-review` | owner/director/manager | `draft → pending_review` |
| POST | `/api/v1/cms/pages/:id/approve` | owner/director/manager | `pending_review → published/scheduled` |
| POST | `/api/v1/cms/pages/:id/reject` | owner/director/manager | `pending_review → draft` |
| POST | `/api/v1/cms/pages/:id/schedule` | owner/director/manager | `draft → scheduled` + Celery ETA |
| POST | `/api/v1/cms/pages/:id/cancel-schedule` | owner/director/manager | `scheduled → draft` + revoke task |

#### Templates (5 endpoints)

| Método | Rota | Roles |
|--------|------|-------|
| GET | `/api/v1/cms/templates` | owner/director/manager |
| POST | `/api/v1/cms/templates` | owner/director/manager |
| GET | `/api/v1/cms/templates/:id` | owner/director/manager |
| PUT | `/api/v1/cms/templates/:id` | owner/director/manager |
| DELETE | `/api/v1/cms/templates/:id` | owner/director/manager |

#### Media (4 endpoints)

| Método | Rota | Roles |
|--------|------|-------|
| GET | `/api/v1/cms/media` | owner/director/manager/agent |
| POST | `/api/v1/cms/media/upload` | owner/director/manager |
| GET | `/api/v1/cms/media/:id` | owner/director/manager/agent |
| DELETE | `/api/v1/cms/media/:id` | owner/director/manager |

#### Settings (2 endpoints)

| Método | Rota | Roles |
|--------|------|-------|
| GET | `/api/v1/cms/settings` | owner/director/manager/agent |
| PUT | `/api/v1/cms/settings` | owner/director/manager |

#### Public (1 endpoint)

```python
# public endpoint
@http.route('/api/v1/public/cms/<string:company_slug>/pages/<string:page_slug>',
            type='http', auth='none', methods=['GET'], csrf=False, cors='*')
def get_public_page(self, company_slug, page_slug, **kwargs):
    # 1. Resolve company_slug → company_id via thedevkitchen.cms.settings
    # 2. Busca page por (slug=page_slug, company_id=..., status=published, active=True)
    # 3. Retorna JSON com conteúdo + SEO, sem custom_js/css
    ...
```

**Response 200**:
```json
{
  "slug": "home",
  "title": "Página Inicial",
  "meta_description": "Bem-vindo à imobiliária...",
  "meta_keywords": "imóveis, venda, aluguel",
  "og_title": "Encontre seu imóvel ideal",
  "og_description": "A maior seleção de imóveis...",
  "og_image_url": "/api/v1/cms/media/5/download",
  "canonical_url": "https://www.minhaagencia.com/home",
  "robots_meta": "index,follow",
  "structured_data": "{\"@context\": \"https://schema.org\", \"@type\": \"RealEstateAgent\"}",
  "content": "{...puck json...}",
  "published_at": "2026-05-23T10:00:00Z"
}
```

---

#### Endpoint: `POST /api/v1/cms/pages/:id/schedule`

**Request Body**:
```json
{
  "publish_at": "2026-06-01T08:00:00-03:00"
}
```

**Validações**:
- `publish_at` obrigatório
- Deve incluir timezone (offset ou `Z`) — `{"error": "publish_at_must_include_timezone"}`
- Deve ser futuro — `{"error": "publish_at_must_be_future"}`

**Response 200**:
```json
{
  "id": 1,
  "status": "scheduled",
  "scheduled_publish_at": "2026-06-01T11:00:00Z",
  "links": [
    {"href": "/api/v1/cms/pages/1/cancel-schedule", "rel": "cancel_schedule", "type": "POST"}
  ]
}
```

---

#### Endpoint: `POST /api/v1/cms/pages/:id/approve`

**Request Body**:
```json
{
  "publish_at": "2026-06-01T08:00:00-03:00"
}
```

> Se `publish_at` omitido → `pending_review → published` imediatamente.
> Se `publish_at` presente → `pending_review → scheduled` + Celery ETA.

---

### Views Odoo (per ADR-001, knowledge_base/10-frontend-views-odoo18.md)

| View | Type | Destaques |
|------|------|-----------|
| `cms.page.list` | `<list>` | `status` com badge colorido; `published_at`, `scheduled_publish_at` com `optional="show"` |
| `cms.page.form` | form | Statusbar com 5 estados; aba "Conteúdo" (Puck JSON); aba "SEO" (title, meta, OG, canonical, robots, structured_data); aba "Agendamento" |
| `cms.template.list` | `<list>` | `name`, `category`, `company_id` |
| `cms.template.form` | form | Todos os campos |
| `cms.media.list` | `<list>` | `name`, `type`, `mime_type`, `file_size` (optional), `url` (optional) |
| `cms.settings.form` | form | Seção "URL Pública" (`company_slug`); seção "SEO Padrão"; seção "Código Customizado (Avançado)" (`custom_css`, `custom_js`) |

**Regras mandatórias Odoo 18.0**:
```xml
<!-- ✅ CORRETO -->
<list>...</list>
<field name="published_at" optional="show"/>
<field name="canonical_url" invisible="not canonical_url"/>

<!-- ❌ PROIBIDO -->
<tree>...</tree>
<field name="published_at" column_invisible="status != 'published'"/>
<field name="canonical_url" attrs="{'invisible': [('canonical_url', '=', False)]}"/>
```

**Menus (sem `groups`)**:
```xml
<menuitem id="menu_cms_root"      name="CMS"            sequence="50"/>
<menuitem id="menu_cms_pages"     name="Páginas"        parent="menu_cms_root" action="action_cms_page_list"/>
<menuitem id="menu_cms_templates" name="Templates"      parent="menu_cms_root" action="action_cms_template_list"/>
<menuitem id="menu_cms_media"     name="Mídia"          parent="menu_cms_root" action="action_cms_media_list"/>
<menuitem id="menu_cms_settings"  name="Configurações"  parent="menu_cms_root" action="action_cms_settings"/>
```

---

### Seed Data (MANDATORY)

```python
# Companies
company_a = env['res.company'].create({'name': 'Imobiliária Seed A'})
company_b = env['res.company'].create({'name': 'Imobiliária Seed B'})

# Users
users = {
    'seed_owner_a':      {'login': 'seed_cms_owner@test.com',    'group': 'group_real_estate_owner',       'company': company_a},
    'seed_director_a':   {'login': 'seed_cms_director@test.com', 'group': 'group_real_estate_director',    'company': company_a},
    'seed_manager_a':    {'login': 'seed_cms_manager@test.com',  'group': 'group_real_estate_manager',     'company': company_a},
    'seed_agent_a':      {'login': 'seed_cms_agent@test.com',    'group': 'group_real_estate_agent',       'company': company_a},
    'seed_receptionist': {'login': 'seed_cms_recept@test.com',   'group': 'group_real_estate_receptionist','company': company_a},
    'seed_owner_b':      {'login': 'seed_cms_owner_b@test.com',  'group': 'group_real_estate_owner',       'company': company_b},
}

# Settings (com company_slug)
env['thedevkitchen.cms.settings'].create({
    'company_id': company_a.id,
    'company_slug': 'seed-imobiliaria-a',
    'default_meta_title_suffix': ' | Seed Imobiliária A',
})
env['thedevkitchen.cms.settings'].create({
    'company_id': company_b.id,
    'company_slug': 'seed-imobiliaria-b',
})

# Templates
env['thedevkitchen.cms.template'].create({'name': 'Seed Template Landing',  'category': 'landing',  'content': '{"content":[],"root":{"props":{}}}', 'company_id': company_a.id})
env['thedevkitchen.cms.template'].create({'name': 'Seed Template Property', 'category': 'property', 'content': '{"content":[],"root":{"props":{}}}', 'company_id': company_a.id})

# Pages (todos os status)
puck_json = '{"content":[{"type":"HeadingBlock","props":{"children":"Seed"}}],"root":{"props":{}}}'
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Draft',         'slug': 'seed-page-draft',         'status': 'draft',          'content': puck_json, 'company_id': company_a.id, 'author_id': seed_owner_a.id})
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Pending',       'slug': 'seed-page-pending',       'status': 'pending_review', 'content': puck_json, 'company_id': company_a.id, 'author_id': seed_owner_a.id})
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Scheduled',     'slug': 'seed-page-scheduled',     'status': 'scheduled',      'content': puck_json, 'company_id': company_a.id, 'author_id': seed_owner_a.id, 'scheduled_publish_at': '2099-12-31 23:59:59'})
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Published',     'slug': 'seed-page-published',     'status': 'published',      'content': puck_json, 'published_at': fields.Datetime.now(), 'company_id': company_a.id, 'author_id': seed_owner_a.id, 'robots_meta': 'index,follow'})
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Archived',      'slug': 'seed-page-archived',      'status': 'archived',       'content': puck_json, 'company_id': company_a.id, 'author_id': seed_owner_a.id})
# Isolamento company B
env['thedevkitchen.cms.page'].create({'name': 'Seed Page Company B',     'slug': 'seed-page-company-b',     'status': 'published',      'content': puck_json, 'published_at': fields.Datetime.now(), 'company_id': company_b.id, 'author_id': seed_owner_b.id})
```

> **Regras**: prefixo `seed_` em logins; `seed-` em slugs; idempotente; cobre todos os 5 status + 2 companies para isolamento.

---

### Non-Functional Requirements

**NFR1: Security** (per ADR-008, ADR-011, ADR-017, ADR-019)
- Triple decorator em todos os 24 endpoints autenticados
- Isolamento multi-tenant via `company_id` + record rules
- `custom_js` write bloqueado no service layer para non-owner
- Endpoint público nunca expõe `custom_js` ou `custom_css`
- Slug validado contra path traversal; CSS validado contra injection

**NFR2: Performance**
- Listas paginadas: < 200ms para 100 itens
- Upload: streaming para arquivos grandes (não buffer em memória)
- Índices em `(slug, company_id)`, `status`, `company_id`

**NFR3: Quality** (per ADR-022)
- Pylint ≥ 8.0, `black`, `isort`, `flake8`
- 100% cobertura em constraints e validações

**NFR4: Data Integrity**
- `UNIQUE(slug, company_id)` em `cms_page`
- `UNIQUE(company_id)` e `UNIQUE(company_slug)` em `cms_settings`
- `ir.attachment` com `ondelete=cascade` em `cms.media.attachment_id`

**NFR5: Frontend Compatibility** (per KB-10)
- `<list>`, sem `attrs`, `optional="show"` para colunas
- Cypress E2E + manual DevTools check

**NFR6: Observabilidade** (per `thedevkitchen_observability`)
- Eventos estruturados no padrão existente da plataforma
- Métricas Prometheus disponíveis em `/metrics`
- Alertas configuráveis para falhas de publicação agendada

**NFR7: Celery Reliability** (per ADR-021)
- Tasks com `max_retries=3` e `default_retry_delay=60`
- Idempotência: task verifica `status=scheduled` antes de executar
- `celery_task_id` armazenado para permitir revogação explícita

---

## Technical Constraints

### Must Follow

| Source | Requirement | Applied To |
|--------|-------------|------------|
| ADR-001 | `<list>`, sem `attrs`, sem `groups` em menus | Views/Menus |
| ADR-003 | 100% cobertura em validações | Constraints |
| ADR-004 | Prefix `thedevkitchen_cms`, models `thedevkitchen.cms.*` | Module, models |
| ADR-007 | HATEOAS links em todas as respostas autenticadas | Endpoints |
| ADR-008 | `company_id` + record rules | Todas as entidades |
| ADR-011 | Triple decorator obrigatório | 24 controllers autenticados |
| ADR-015 | Soft delete (Page/Template); hard delete documentado (Media) | Deleção |
| ADR-018 | Validação: slug, content JSON, CSS injection, MIME, publish_at | Input validation |
| ADR-019 | RBAC; `capability_service.py` atualizado | Authorization |
| ADR-021 | Celery `apply_async(eta=...)` para publicação agendada | Celery worker |
| ADR-022 | Linting obrigatório | Todo código Python |
| Feature 017 | `python-magic` + `secure_filename` | Upload de mídia |
| Feature 020 | Atualizar `capability_service.py` | ROLE_RULES + ALLOWED_SUBJECTS |
| Constitution | `# public endpoint` marker | Endpoint público |
| KB-10 | `optional="show"` para colunas; Cypress E2E | List views |

### Estrutura do Módulo

```
18.0/extra-addons/thedevkitchen_cms/
├── __manifest__.py               # depends: ['quicksol_estate', 'thedevkitchen_apigateway', 'thedevkitchen_observability']
├── __init__.py
├── models/
│   ├── cms_page.py
│   ├── cms_template.py
│   ├── cms_media.py
│   └── cms_settings.py
├── controllers/
│   ├── cms_pages_controller.py
│   ├── cms_templates_controller.py
│   ├── cms_media_controller.py
│   ├── cms_settings_controller.py
│   └── cms_public_controller.py         # auth='none'
├── services/
│   ├── cms_sanitizer.py                 # validação JSON + CSS injection
│   └── cms_scheduler.py                 # lógica de enfileiramento Celery
├── tasks/
│   └── cms_tasks.py                     # Celery task: publish_cms_page_task
├── schemas/
│   ├── page_schema.py
│   └── settings_schema.py
├── views/
│   ├── cms_page_views.xml
│   ├── cms_template_views.xml
│   ├── cms_media_views.xml
│   ├── cms_settings_views.xml
│   └── cms_menus.xml
├── data/
│   └── api_endpoints.xml
└── security/
    ├── security.xml
    └── ir.model.access.csv
```

**Arquivos externos a atualizar**:
```
18.0/extra-addons/quicksol_estate/services/capability_service.py
18.0/extra-addons/quicksol_estate/data/api_endpoints.xml
18.0/docker-compose.yml   ← adicionar celery_cms_worker
```

---

## Success Criteria

### Backend
- [ ] Todos os user stories (US1–US8) implementados e testados
- [ ] 100% cobertura em constraints e validações (ADR-003)
- [ ] State machine testado: todas as transições + transições inválidas
- [ ] Agendamento Celery: schedule, cancel, execução no ETA, idempotência
- [ ] Isolamento multi-company: 2 companies, slugs separados
- [ ] `capability_service.py` atualizado (ROLE_RULES + ALLOWED_SUBJECTS)
- [ ] Endpoint público: `company_slug` resolve corretamente; sem custom_js/css
- [ ] Pylint ≥ 8.0, `./lint.sh thedevkitchen_cms` passando (ADR-022)

### Frontend (Odoo UI — admin)
- [ ] Views Odoo 18.0: `<list>`, sem `attrs`, sem `column_invisible` com Python expr
- [ ] Nenhum `groups` em `<menuitem>`
- [ ] Form view de página: statusbar com 5 estados + aba SEO
- [ ] Cypress E2E: 6 tests passando (`cypress/e2e/views/cms.cy.js`)
- [ ] Zero erros JavaScript no console (Chrome + Firefox)

### Celery & Observabilidade
- [ ] `celery_cms_worker` configurado em `docker-compose.yml`
- [ ] Task `publish_cms_page_task` com `max_retries=3`, idempotente
- [ ] Eventos estruturados: criação, publicação, agendamento, falha, CSS injection
- [ ] Métricas Prometheus disponíveis: `cms_pages_by_status`, `cms_media_uploads_total`

### Seeds
- [ ] Prefixo `seed_` em logins; `seed-` em slugs
- [ ] 5 páginas (1 por status: draft/pending/scheduled/published/archived) + 1 em company_b
- [ ] 2 companies com `company_slug` configurado em settings
- [ ] Seed idempotente

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Description | Constitution Section | Priority |
|---------|-------------|---------------------|----------|
| **Company Slug Resolution** | URL pública inclui `company_slug` resolvido pelo Odoo (não pelo Kong) — separação de responsabilidades | New: CMS/Content Patterns | High |
| **Celery ETA Scheduling** | `apply_async(eta=datetime)` para publicação futura precisa + revogação via `task_id` | New: Async Patterns | High |
| **CSS Injection Validation** | Regex server-side contra `expression()`, `behavior:`, `url(javascript:)` | Security Requirements | High |
| **Role-level Field Restriction** | Service layer bloqueia campo específico (`custom_js`) para non-owner | Security Requirements | High |
| **Composite Slug Key** | `UNIQUE(slug, company_id)` como chave natural de acesso público | Database Best Practices | Medium |
| **Observability Integration CMS** | Eventos estruturados por domínio funcional (não apenas erros globais) | Observability Patterns | Medium |
| **5-State Page Lifecycle** | `draft → pending_review → scheduled → published → archived` com rollbacks | New: CMS/Content Patterns | Medium |

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: v1.8.0 (MINOR)
- **Sections to Update**:
  - [ ] Security Requirements: CSS injection, custom_js role restriction
  - [ ] Async Patterns: Celery ETA scheduling + task revocation
  - [ ] Reference Implementations: Feature 021 CMS Domain
  - [ ] Nova Seção: CMS/Content Patterns (Puck JSON, company slug, 5-state lifecycle)

---

## Assumptions & Dependencies

**Assumptions**:
- `python-magic` disponível no Docker (Feature 017)
- `secure_filename` via `werkzeug.utils` (Odoo)
- RabbitMQ já em execução (ADR-021 — arquitetura Celery existente)
- Frontend usa `@measured/puck` para renderização — backend é agnóstico à estrutura interna do JSON
- Rate limiting no Kong (sem lógica de negócio de routing)

**Dependencies**:
- `quicksol_estate` — RBAC groups, `capability_service.py`
- `thedevkitchen_apigateway` — `@require_jwt`, `@require_session`, `@require_company`
- `thedevkitchen_observability` — logging estruturado, Prometheus, OpenTelemetry
- `ir.attachment` — armazenamento binário de mídia
- `mail.thread` — audit trail em `cms_page`
- Feature 020 — capabilities API funcional

---

## Implementation Phases

### Phase 1: Foundation
- Módulo `thedevkitchen_cms` + `__manifest__.py`
- Models + constraints + `cms_sanitizer.py`
- `security.xml` + `ir.model.access.csv`
- Unit tests para todas as constraints

### Phase 2: API Layer — Pages & Templates
- Controllers de pages (14 endpoints) + templates (5 endpoints)
- Endpoint público com resolução por `company_slug`
- Schemas de validação (ADR-018)
- E2E API tests

### Phase 3: API Layer — Media & Settings
- Upload com `python-magic`; settings com `custom_js` e `company_slug`
- E2E API tests

### Phase 4: Agendamento Celery
- `cms_tasks.py` + `cms_scheduler.py`
- Configuração `celery_cms_worker` em `docker-compose.yml`
- Endpoints `/schedule` e `/cancel-schedule`
- Testes de agendamento (unit + E2E)

### Phase 5: Odoo UI — Views & Menus
- Views XML (Odoo 18.0), menus sem `groups`
- Cypress E2E: `cypress/e2e/views/cms.cy.js`

### Phase 6: Observabilidade
- Eventos + métricas no padrão `thedevkitchen_observability`
- Testes de eventos

### Phase 7: RBAC Integration
- `capability_service.py` + `api_endpoints.xml`
- Testes da matriz RBAC completa

### Phase 8: Testing & Quality
- `./lint.sh thedevkitchen_cms`; Pylint ≥ 8.0
- Suite completa

### Phase 9: Documentation *(pós-implementação)*
- Constitution v1.8.0
- Swagger (ADR-005) + Postman (ADR-016)
