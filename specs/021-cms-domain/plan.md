# Implementation Plan: CMS Domain

**Branch**: `021-cms-domain` | **Date**: 2026-05-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/021-cms-domain/spec.md`

## Summary

Headless CMS domain para imobiliárias gerenciarem páginas web. O módulo `thedevkitchen_cms` expõe 25 endpoints REST (4 entidades + rota pública) com máquina de estados 4-fases (draft→pending_review→published→archived), upload de mídia com validação por magic bytes, editor Puck via JSON, SEO completo e isolamento multi-tenancy por company_id. A rota pública serve páginas publicadas usando apenas `@require_jwt` (sem sessão/company) com company_slug na URL. Não inclui agendamento (technical debt).

## Technical Context

**Language/Version**: Python 3.11 / Odoo 18.0  
**Primary Dependencies**: `thedevkitchen_apigateway` (decorators @require_jwt/@require_session/@require_company), `thedevkitchen_observability` (eventos), `python-magic` (MIME validation), `ir.attachment` (storage binário)  
**Storage**: PostgreSQL (6 tabelas: page, page_content, template, template_content, media, settings); Redis (sessões/cache via infraestrutura existente — sem configuração nova)  
**Testing**: Python unittest + unittest.mock (testes unitários em `tests/unit/`), curl/bash em `integration_tests/`, Cypress em `cypress/e2e/`  
**Target Platform**: Linux Docker, Odoo 18.0  
**Project Type**: Módulo único em `18.0/extra-addons/thedevkitchen_cms/`  
**Performance Goals**: rota pública < 200ms p95 @ 500 req/s; listagem de páginas < 300ms @ 10k registros  
**Constraints**: Sem agendamento (ver TECHNICAL_DEBIT.md); sem multilingual; @require_jwt reaproveitado (sem nova infraestrutura de auth); content validation no service layer (não no ORM)  
**Scale/Scope**: Até 10k páginas/imobiliária; 5 entidades; 25 endpoints; 6 testes unitários

## Constitution Check

*GATE: Validado pré-Phase 0 e pós-Phase 1 design. Todos os princípios: PASS.*

| Princípio | Status | Justificativa |
|-----------|--------|---------------|
| **I – Security First** | ✅ PASS | Endpoints internos: triple decorator (ADR-011). Rota pública: @require_jwt apenas (company resolvida via company_slug na URL, sem session/company requerida). Multi-tenancy: company_id em todas as 5 entidades + record rules. CSS injection: 5 patterns de regex. MIME: magic bytes via python-magic. |
| **II – Test Coverage 80%+** | ✅ PASS | 6 arquivos de testes unitários planejados (T013, T014, T019, T023, T030, T040). Testes de integração bash. Testes Cypress para UI Odoo. |
| **III – API-First** | ✅ PASS | 25 endpoints definidos em contracts/api-contracts.md. OpenAPI via api_endpoints.xml (T047). Postman collection (T048). |
| **IV – Multi-Tenancy** | ✅ PASS | company_id em: page, template, media, settings. Record rules em cms_record_rules.xml. Validação cruzada: og_image_id deve ter mesmo company_id da página. |
| **V – ADR Governance** | ✅ PASS | ADR-003 (Git), ADR-004 (naming: thedevkitchen_cms), ADR-005 (Swagger), ADR-007 (testes), ADR-008 (observabilidade), ADR-011 (auth), ADR-015 (hard delete mídia: exceção documentada em constitution v1.7.0), ADR-017 (módulo naming), ADR-018 (JWT), ADR-019 (RBAC). |
| **VI – Headless Architecture** | ✅ PASS | API REST completa para todos os roles. UI Odoo (backend views) apenas para administração interna. Rota pública sem dependência de sessão Odoo. |

**Exceção ADR-015**: Hard delete para `cms.media` — JUSTIFICADO (mesmo padrão da Feature 017, pattern `Hard-Delete Exception` documentado em constitution v1.7.0).

## Project Structure

### Documentation (this feature)

```text
specs/021-cms-domain/
├── plan.md              # Este arquivo (/speckit.plan output)
├── research.md          # Phase 0: 9 itens RES-001→RES-009
├── data-model.md        # Phase 1: ERD, state machine, 6 entidades
├── quickstart.md        # Phase 1: guia de setup para devs
├── contracts/
│   └── api-contracts.md # Phase 1: 25 endpoints, RBAC matrix, error codes
└── tasks.md             # 49 tarefas, 12 fases (pré-existente)
```

### Source Code

```text
18.0/extra-addons/thedevkitchen_cms/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── cms_page.py                    # thedevkitchen.cms.page (mail.thread mixin)
│   ├── cms_page_content.py            # thedevkitchen.cms.page.content (1:1 via UNIQUE)
│   ├── cms_template.py                # thedevkitchen.cms.template
│   ├── cms_template_content.py        # thedevkitchen.cms.template.content
│   ├── cms_media.py                   # thedevkitchen.cms.media (hard delete override)
│   └── cms_settings.py                # thedevkitchen.cms.settings (singleton)
├── controllers/
│   ├── __init__.py
│   ├── cms_page_controller.py         # POST/GET/PUT/DELETE pages + duplicate
│   ├── cms_template_controller.py     # CRUD templates
│   ├── cms_media_controller.py        # upload + CRUD mídia
│   ├── cms_settings_controller.py     # GET/PUT settings
│   └── cms_public_controller.py       # GET /public/cms/:company_slug/pages/:slug
├── services/
│   ├── __init__.py
│   ├── cms_page_service.py            # state machine, validações, duplicate
│   ├── cms_media_service.py           # magic bytes, MIME whitelist, file sanitize
│   ├── cms_settings_service.py        # singleton, CSS injection guard, custom_js RBAC
│   └── cms_error_helpers.py           # _cms_error() FR6.9 envelope
├── views/
│   ├── cms_page_views.xml
│   ├── cms_template_views.xml
│   ├── cms_media_views.xml
│   ├── cms_settings_views.xml
│   └── cms_menus.xml
├── data/
│   └── api_endpoints.xml              # Swagger: thedevkitchen_api_endpoint records
├── security/
│   ├── ir.model.access.csv
│   └── cms_record_rules.xml           # isolamento por company_id
└── tests/
    └── unit/
        ├── __init__.py
        ├── test_cms_page_validations.py   # slug, structured_data, og_image_id cross-company
        ├── test_cms_status_machine.py     # transições válidas e inválidas
        ├── test_cms_media_validations.py  # magic bytes, tamanho, MIME whitelist
        ├── test_cms_public_route.py       # isolamento, 404 para draft/archived
        ├── test_cms_settings_validations.py # CSS injection, company_slug, custom_js RBAC
        └── test_cms_observability.py     # eventos page.published, page.archived

integration_tests/
├── test_us021_cms_page_crud.sh
├── test_us021_cms_media.sh
├── test_us021_cms_public.sh
└── test_us021_rbac_matrix.sh

cypress/e2e/
└── views/
    └── cms.cy.js                       # UI Odoo admin
```

**Structure Decision**: Módulo único Odoo (`thedevkitchen_cms`) com separação em camadas — models (ORM), controllers (HTTP, sem lógica), services (negócio + validação), views (Odoo UI). Padrão consistente com Feature 009 e Feature 017 do projeto.

## Complexity Tracking

| Exceção | Por quê é Necessária | Alternativa Mais Simples Rejeitada Porque |
|---------|---------------------|------------------------------------------|
| Hard delete para mídia (ADR-015) | Binários em ir.attachment devem ser removidos fisicamente; soft delete deixaria storage órfão | Soft delete apenas = orphan ir.attachment records; mesmo padrão adotado em Feature 017 e documentado na constitution v1.7.0 |
| @require_jwt sem @require_session na rota pública | company_slug na URL identifica o contexto; consumidores da rota são apps frontend sem session Odoo | Exigir session impossibilitaria uso headless; nenhuma lógica nova — @require_jwt já valida JWT |
