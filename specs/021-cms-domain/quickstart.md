# Quickstart: CMS Domain (021)

**Branch**: `021-cms-domain` | **Module**: `thedevkitchen_cms`

---

## Pré-requisitos

```bash
# Stack rodando
cd 18.0 && docker compose up -d
docker compose ps  # odoo, db, redis devem estar healthy
```

---

## 1. Instalar o módulo

```bash
docker compose exec odoo bash -c "odoo -d realestate -u thedevkitchen_cms --stop-after-init"
# Aguarde: "INFO realestate odoo.modules.loading: Modules loaded."
```

Verificar tabelas criadas:
```bash
docker compose exec db psql -U odoo -d realestate -c "\dt thedevkitchen_cms*"
# Deve listar: page, page_content, template, template_content, media, settings
```

---

## 2. Configurar company_slug (pré-requisito da rota pública)

```bash
# Obter JWT da imobiliária (owner)
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@imob.com","password":"senha"}' | jq -r '.access_token')

SESSION=$(curl -s -X POST http://localhost:8069/api/v1/auth/login \
  -d '...' | jq -r '.session_id')

# Configurar slug
curl -X PUT http://localhost:8069/api/v1/cms/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Company-Id: 2" \
  -d '{"company_slug": "minha-agencia"}'
```

---

## 3. Criar e publicar uma página

```bash
# Criar página
PAGE_ID=$(curl -s -X POST http://localhost:8069/api/v1/cms/pages \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Company-Id: 2" \
  -d '{
    "name": "Home",
    "slug": "home",
    "content": "{\"root\":{\"type\":\"div\",\"props\":{},\"children\":[]}}",
    "title": "Minha Imobiliária | Home",
    "robots_meta": "index,follow"
  }' | jq -r '.id')

echo "Page ID: $PAGE_ID"

# Publicar
curl -X PUT http://localhost:8069/api/v1/cms/pages/$PAGE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Company-Id: 2" \
  -d '{"status": "published"}'
```

---

## 4. Acessar rota pública

```bash
# Qualquer JWT válido da plataforma (pode ser o mesmo token)
curl -X GET http://localhost:8069/api/v1/public/cms/minha-agencia/pages/home \
  -H "Authorization: Bearer $TOKEN"
# Deve retornar: slug, content, title, robots_meta, ...
# NÃO deve conter: status, created_at, updated_at, custom_js, custom_css
```

---

## 5. Upload de mídia

```bash
curl -X POST http://localhost:8069/api/v1/cms/media/upload \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Company-Id: 2" \
  -F "file=@/caminho/para/banner.jpg"
# Retorna: id, url, mime_type, file_size
```

---

## 6. Executar testes

```bash
# Testes unitários
docker compose exec odoo bash -c "
  python -m pytest 18.0/extra-addons/thedevkitchen_cms/tests/unit/ -v
"

# Testes E2E (integração via curl)
cd integration_tests
bash test_us021_cms_page_crud.sh
bash test_us021_cms_media.sh
bash test_us021_cms_public.sh
bash test_us021_rbac_matrix.sh

# Testes Cypress (UI Odoo admin)
cd /opt/homebrew/var/www/realestate/realestate_backend
npx cypress run --spec "cypress/e2e/views/cms.cy.js"
```

---

## 7. Verificar observabilidade

```bash
# Publicar uma página e verificar evento no Loki
# Grafana: http://localhost:3000 → Explore → Loki
# Query: {app="odoo"} |= "cms.page.published"

# Métricas Prometheus
curl http://localhost:8069/metrics | grep cms_
# Esperado: cms_pages_by_status, cms_media_uploads_total
```

---

## Estrutura do módulo

```
18.0/extra-addons/thedevkitchen_cms/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── cms_page.py                    # thedevkitchen.cms.page
│   ├── cms_page_content.py            # thedevkitchen.cms.page.content
│   ├── cms_template.py                # thedevkitchen.cms.template
│   ├── cms_template_content.py        # thedevkitchen.cms.template.content
│   ├── cms_media.py                   # thedevkitchen.cms.media
│   └── cms_settings.py                # thedevkitchen.cms.settings
├── controllers/
│   ├── __init__.py
│   ├── cms_page_controller.py         # CRUD + state machine (PUT)
│   ├── cms_template_controller.py     # CRUD templates
│   ├── cms_media_controller.py        # upload + CRUD mídia
│   ├── cms_settings_controller.py     # GET + PUT settings
│   └── cms_public_controller.py       # rota pública (@require_jwt only)
├── services/
│   ├── __init__.py
│   ├── cms_page_service.py            # create, update, change_status, duplicate
│   ├── cms_media_service.py           # upload validation (magic bytes)
│   ├── cms_settings_service.py        # singleton, CSS validation, custom_js guard
│   └── cms_error_helpers.py           # _cms_error() FR6.9 envelope
├── views/
│   ├── cms_page_views.xml
│   ├── cms_template_views.xml
│   ├── cms_media_views.xml
│   ├── cms_settings_views.xml
│   └── cms_menus.xml
├── data/
│   └── api_endpoints.xml              # Swagger via thedevkitchen_api_endpoint
├── security/
│   ├── ir.model.access.csv
│   └── cms_record_rules.xml
└── tests/
    └── unit/
        ├── __init__.py
        ├── test_cms_page_validations.py
        ├── test_cms_status_machine.py
        ├── test_cms_media_validations.py
        ├── test_cms_public_route.py
        ├── test_cms_settings_validations.py
        └── test_cms_observability.py
```
