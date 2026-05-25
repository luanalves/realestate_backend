# CMS Domain — Flowcharts

> Feature 021 — `thedevkitchen_cms` Odoo 18.0 module.
> All flows reflect the implemented service and controller logic.

---

## 1. State Machine: Page Status Transitions

```mermaid
stateDiagram-v2
    [*] --> draft : create_page()

    draft --> pending_review : change_status(pending_review)
    draft --> published : change_status(published)

    pending_review --> published : change_status(published)
    pending_review --> draft : change_status(draft)

    published --> archived : change_status(archived)

    archived --> draft : change_status(draft)

    published --> published : published_at already set\n(no overwrite)
```

---

## 2. Create Page Flow

```mermaid
flowchart TD
    A([POST /api/v1/cms/pages]) --> B{@require_jwt\n@require_session\n@require_company}
    B -- 401/403 --> ERR1([Error Response])
    B -- OK --> C{Role in\nowner/director/manager?}
    C -- No --> ERR2([403 Forbidden])
    C -- Yes --> D[Parse JSON body]
    D --> E{template_id\nprovided?}
    E -- Yes --> F{Template exists\nfor company?}
    F -- No --> ERR3([422 template_not_found])
    F -- Yes --> G[Copy template content]
    E -- No --> H[Use provided content]
    G --> I[Create cms.page record]
    H --> I
    I --> J[Create cms.page.content record]
    J --> K([201 Created — page + content])
```

---

## 3. Media Upload Flow

```mermaid
flowchart TD
    A([POST /api/v1/cms/media/upload\nmultipart/form-data]) --> B{Auth decorators}
    B -- Fail --> ERR1([401/403])
    B -- OK --> C{Role check\nowner/director/manager?}
    C -- No --> ERR2([403 Forbidden])
    C -- Yes --> D[Read file bytes + filename\nfrom multipart]
    D --> E{file present?}
    E -- No --> ERR3([400 no_file])
    E -- Yes --> F[python-magic\ndetect MIME]
    F --> G{MIME in whitelist?}
    G -- No --> ERR4([415 unsupported_mime])
    G -- Yes --> H{claimed MIME\n≠ detected MIME?}
    H -- Mismatch --> ERR5([422 mime_mismatch])
    H -- Match/None --> I{size ≤ limit?}
    I -- No --> ERR6([413 file_too_large])
    I -- Yes --> J[Sanitize filename]
    J --> K[Create ir.attachment\nwith base64 data]
    K --> L[Create cms.media record]
    L --> M[Emit cms_media_uploads_total\nspan event]
    M --> N([201 Created — media metadata])
```

---

## 4. CSS Injection Guard Flow

```mermaid
flowchart TD
    A([PUT /api/v1/cms/settings\nbody: custom_css]) --> B{Auth decorators}
    B -- Fail --> ERR1([401/403])
    B -- OK --> C{Role allows\nsettings update?}
    C -- No --> ERR2([403 Forbidden])
    C -- Yes --> D{custom_js in body\nAND role != owner?}
    D -- Yes --> ERR3([403 Forbidden\ncustom_js restricted])
    D -- No --> E{custom_css\nin body?}
    E -- No --> SKIP[Skip CSS validation]
    E -- Yes --> F[Check 5 CSS injection\npatterns]
    F --> G{Pattern\nmatched?}
    G -- Yes --> H[Emit cms.css_injection_blocked\nOTel span event]
    H --> ERR4([422 css_injection_detected])
    G -- No --> I[Write settings record]
    SKIP --> I
    I --> J{custom_js\nin body?}
    J -- Yes --> K[Write audit fields\nlast_modified_by + at]
    J -- No --> L
    K --> L[serialize_for_role\nomit custom_js if !owner]
    L --> M([200 OK — settings])
```

---

## 5. Public Route Resolution Flow

```mermaid
flowchart TD
    A([GET /api/v1/public/cms\n/:company_slug/pages/:page_slug]) --> B{@require_jwt\nJWT only — no session}
    B -- 401 --> ERR1([401 Unauthorized])
    B -- OK --> C[Lookup cms.settings\nby company_slug]
    C --> D{Settings found?}
    D -- No --> ERR2([404 company_slug_not_found])
    D -- Yes --> E[Extract company_id\nfrom settings]
    E --> F[Search cms.page\nslug=page_slug\ncompany_id=company_id\nstatus=published\nactive=True]
    F --> G{Page found?}
    G -- No --> ERR3([404 page_not_found])
    G -- Yes --> H[Build response\nexclude: status, active, company_id\ncustom_js, custom_css]
    H --> I[Include og_default_*\nfrom settings]
    I --> J([200 OK — public page])
```

---

## 6. Page Duplicate Flow

```mermaid
flowchart TD
    A([POST /api/v1/cms/pages/:id/duplicate]) --> B{Auth + role\nowner/director/manager}
    B -- Fail --> ERR1([401/403])
    B -- OK --> C[Find source page\nby id + company_id]
    C --> D{Found?}
    D -- No --> ERR2([404 page_not_found])
    D -- Yes --> E[Base slug = slug + '-copy']
    E --> F{slug available?}
    F -- No --> G[Append '-2', '-3' ...\nuntil unique]
    G --> F
    F -- Yes --> H[Copy page fields\nstatus = draft]
    H --> I[Copy content from\ncontent_ids[0]]
    I --> J[create_page() atomic]
    J --> K([201 Created — new page])
```

---

## 7. RBAC Permission Matrix

```mermaid
flowchart LR
    subgraph Roles
        O[owner]
        D[director]
        M[manager]
        A[agent]
        R[receptionist\nprospector\nproperty_owner\nportal]
    end

    subgraph CMS_Pages["CMS Pages"]
        PP_W["POST/PUT/DELETE\n(write)"]
        PP_R["GET list/detail\n(read)"]
        PP_DUP["Duplicate"]
    end

    subgraph CMS_Templates["CMS Templates"]
        PT_ALL["ALL endpoints"]
        PT_NONE["ALL endpoints\n(denied)"]
    end

    subgraph CMS_Media["CMS Media"]
        PM_W["POST upload\nDELETE"]
        PM_R["GET list/detail/file"]
    end

    subgraph CMS_Settings["CMS Settings"]
        PS_RW["GET + PUT\n(full)"]
        PS_RWNO["GET + PUT\n(no custom_js)"]
        PS_DENY["ALL denied"]
    end

    O --> PP_W & PP_R & PP_DUP
    D --> PP_W & PP_R & PP_DUP
    M --> PP_W & PP_R & PP_DUP
    A --> PP_R

    O & D & M --> PT_ALL
    A --> PT_NONE

    O & D & M --> PM_W & PM_R
    A --> PM_R

    O --> PS_RW
    D & M --> PS_RWNO
    A & R --> PS_DENY

    R --> ERR["403 Forbidden\n(all CMS endpoints)"]
```

---

## 8. Module Upgrade / Swagger Sync Flow

```mermaid
flowchart TD
    A([Edit data/api_endpoints.xml]) --> B[Run module upgrade]
    B --> C["docker compose exec odoo\nodoo -u thedevkitchen_cms\n-d realestate --stop-after-init"]
    C --> D{Upgrade\nsuccessful?}
    D -- No --> ERR([Check Odoo logs\nFix XML errors])
    D -- Yes --> E[DB: thedevkitchen_api_endpoint\ntable updated]
    E --> F[swagger_controller.py reads\nDB at /api/v1/openapi.json]
    F --> G[Visit /api/docs\nVerify 19 CMS endpoints appear]
    G --> H{All endpoints\nvisible?}
    H -- No --> I[Check active=True\nCheck module_name\nCheck DB orphans]
    H -- Yes --> J([Swagger validated ✓])
```
