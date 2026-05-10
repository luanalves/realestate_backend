# Fluxogramas de Property Attachments — Spec 017

Este documento contém os fluxogramas visuais do ciclo de vida de **anexos de propriedades** (`ir.attachment`), cobrindo upload, listagem, download e exclusão. Use estes diagramas para entender quais endpoints chamar, em qual ordem e quais condições de erro tratar.

**Endpoints desta feature:**

| Método | Endpoint | Ação |
|--------|----------|------|
| `POST` | `/api/v1/properties/{id}/attachments` | Upload de arquivo (multipart/form-data) |
| `GET` | `/api/v1/properties/{id}/attachments` | Listar metadados dos anexos |
| `GET` | `/api/v1/properties/{id}/attachments/{attachment_id}/download` | Download do binário |
| `DELETE` | `/api/v1/properties/{id}/attachments/{attachment_id}` | Excluir anexo permanentemente |

---

## Máquina de Estados do Anexo

```mermaid
stateDiagram-v2
    direction LR

    [*] --> stored : POST /api/v1/properties/{id}/attachments\n201 Created

    stored --> listed : GET /api/v1/properties/{id}/attachments\n200 OK (metadados)
    stored --> downloaded : GET /api/v1/properties/{id}/attachments/{att_id}/download\n200 OK (binário)
    stored --> deleted : DELETE /api/v1/properties/{id}/attachments/{att_id}\n204 No Content

    listed --> stored : (stateless — não altera o anexo)
    downloaded --> stored : (stateless — não altera o anexo)

    deleted --> [*]

    state stored {
        direction LR
        [*] --> active : ir.attachment criado\nres_model=real.estate.property
    }
    state deleted {
        direction LR
        [*] --> permanent : 🔒 Irreversível\nbinário removido do filestore
    }
```

---

## J1 — Upload de imagem ou documento

**Endpoint:** `POST /api/v1/properties/{id}/attachments`

```mermaid
flowchart TD
    Start([👤 Owner / Manager / Agent\nprecisa anexar arquivo à propriedade]) --> U1

    U1["**POST /api/v1/properties/{id}/attachments**\n\nHeaders:\n  Authorization: Bearer {token}\n  X-Session-Id: {session_id}\n  Content-Type: multipart/form-data\n\nBody (form-data):\n  file = @fachada.jpg"] --> U1R{Validações do servidor}

    U1R -->|✅ MIME válido + tamanho OK\n+ limite de quantidade OK| U2
    U1R -->|❌ Campo 'file' ausente\n→ 400 Bad Request| ERR1([❌ Incluir campo 'file'\nno form-data])
    U1R -->|❌ MIME não permitido\n→ 415 Unsupported Media Type| ERR2([❌ Apenas imagens e PDFs/Office\nMIME validado via magic bytes\nnão pela extensão do arquivo])
    U1R -->|❌ Arquivo excede limite\n→ 413 Request Entity Too Large| ERR3([❌ Reduzir tamanho ou ajustar\nweb.max_file_upload_size no painel])
    U1R -->|❌ 50 imagens já existem\n→ 422 Unprocessable| ERR4([❌ Excluir imagens antes\nDELETE /attachments/{id}])
    U1R -->|❌ 20 documentos já existem\n→ 422 Unprocessable| ERR5([❌ Excluir documentos antes\nDELETE /attachments/{id}])
    U1R -->|❌ Property sem acesso\n→ 404 Not Found| ERR6([❌ Verificar property_id\ne permissão de acesso])

    U2["**201 Created**\n\n{\n  'status': 'success',\n  'data': {\n    'id': 42,\n    'name': 'fachada.jpg',\n    'mimetype': 'image/jpeg',\n    'size': 204800,\n    'attachment_type': 'image',\n    'uploaded_at': '2026-05-10T21:40:00Z',\n    'links': {\n      'self': '/api/v1/properties/17/attachments/42',\n      'download': '/api/v1/properties/17/attachments/42/download'\n    }\n  }\n}"] --> U3

    U3["Salvar links.download retornado\npara uso futuro"] --> Done([✅ Anexo armazenado])

    note1["⚠️ links.download SEMPRE usa /api/v1/...\nnunca /web/content/{id} — essa rota\nbypassa o API Gateway e a autenticação JWT"]
```

---

## J2 — Listagem de anexos de uma propriedade

**Endpoint:** `GET /api/v1/properties/{id}/attachments`

```mermaid
flowchart TD
    Start([👤 Owner / Manager / Agent\nprecisa ver os anexos da propriedade]) --> L1

    L1["**GET /api/v1/properties/{id}/attachments**\n\nHeaders:\n  Authorization: Bearer {token}\n  X-Openerp-Session-Id: {session_id}\n\nQuery params opcionais:\n  attachment_type=image|document\n  limit=50 (max 100)\n  offset=0"] --> L1R{Resposta}

    L1R -->|200 OK| L2
    L1R -->|401 Unauthorized\nToken inválido| ERR2([❌ Renovar token\nno API Gateway])
    L1R -->|403 Forbidden\nSem permissão| ERR3([❌ Verificar perfil do usuário\nOwner / Manager / Agent])
    L1R -->|404 Not Found\nProperty não encontrada| ERR1([❌ Verificar property_id\ne permissão de acesso])

    L2{Filtrar por tipo?}
    L2 -->|Só imagens| L3a["**GET .../attachments?attachment_type=image**\n→ 200 OK"]
    L2 -->|Só documentos| L3b["**GET .../attachments?attachment_type=document**\n→ 200 OK"]
    L2 -->|Todos| L4

    L3a --> L4
    L3b --> L4

    L4["**200 OK**\n\n{\n  'status': 'success',\n  'data': {\n    'items': [ { id, name, mimetype, size,\n                 attachment_type, uploaded_at,\n                 links: { download } } ],\n    'pagination': {\n      'total': 3, 'limit': 20, 'offset': 0 }\n  }\n}"] --> L5

    L5{pagination.total > items.length?\nHá mais páginas?}
    L5 -->|Sim| L6["**GET .../attachments?limit=20&offset=20**\n→ próxima página"]
    L5 -->|Não| Done([✅ Lista completa obtida\nUsar links.download de cada item para baixar])
```

---

## J3 — Download do conteúdo binário

**Endpoint:** `GET /api/v1/properties/{id}/attachments/{attachment_id}/download`

```mermaid
flowchart TD
    Start([👤 Precisa do arquivo binário\n— exibir imagem ou abrir documento]) --> D0

    D0{Tenho o links.download?}
    D0 -->|Não| D0b["**GET /api/v1/properties/{id}/attachments**\n→ pegar campo links.download do item desejado\n→ J2 Listagem"]
    D0 -->|Sim| D1
    D0b --> D1

    D1["**GET {links.download}**\nEx: GET /api/v1/properties/17/attachments/42/download\n\nHeaders:\n  Authorization: Bearer {token}\n  X-Openerp-Session-Id: {session_id}"] --> D1R{Resposta}

    D1R -->|200 OK\nBinário + headers corretos| D2
    D1R -->|401 Unauthorized| ERR1([❌ Renovar token\nno API Gateway])
    D1R -->|403 Forbidden| ERR2([❌ Sem permissão\npara esta propriedade])
    D1R -->|404 Not Found\nAttachment não pertence à property| ERR3([❌ Verificar que attachment_id\npertence ao property_id informado])

    D2["**200 OK — headers da resposta:**\nContent-Type: image/jpeg (MIME real do arquivo)\nContent-Disposition: attachment; filename='fachada.jpg'\nContent-Length: 204800\n\nCorpo: bytes do arquivo"] --> Done([✅ Arquivo recebido\nExibir ou salvar localmente])

    note1["⚠️ Nunca usar /web/content/{id} diretamente\nSempre usar a rota /api/v1/... retornada\nem links.download — garante autenticação JWT"]
```

---

## J4 — Exclusão de anexo

**Endpoint:** `DELETE /api/v1/properties/{id}/attachments/{attachment_id}`

```mermaid
flowchart TD
    Start([👤 Owner / Manager\nprecisa remover um anexo]) --> Del1

    Del1["**GET /api/v1/properties/{id}/attachments**\n\n→ Confirmar o attachment_id a excluir\n→ J2 Listagem (se não souber o id)"] --> Del2

    Del2["**DELETE /api/v1/properties/{id}/attachments/{attachment_id}**\n\nHeaders:\n  Authorization: Bearer {token}\n  X-Openerp-Session-Id: {session_id}"] --> Del2R{Resposta}

    Del2R -->|204 No Content\nExcluído com sucesso| Done([✅ Anexo removido permanentemente\nOperação irreversível — sem corpo na resposta])
    Del2R -->|401 Unauthorized| ERR3([❌ Renovar token\nno API Gateway])
    Del2R -->|403 Forbidden\nAgent tentou excluir| ERR1([❌ Apenas Owner / Manager / Admin\npodem excluir\nAgent não tem permissão de exclusão])
    Del2R -->|404 Not Found\nAttachment não pertence à property| ERR2([❌ Verificar attachment_id\npertence ao property_id informado])

    note1["⚠️ Exclusão é irreversível\nnão há soft delete — o ir.attachment e o\nbinário são removidos do banco e do filestore"]
```

---

## J5 — Ciclo completo (upload → listar → download → excluir)

**Endpoints:** `POST` → `GET` (list) → `GET` (download) → `DELETE`

```mermaid
flowchart TD
    Start([Ciclo completo de gerenciamento\nde anexos de uma propriedade]) --> C1

    C1["**POST /api/v1/properties/{id}/attachments**\nmultipart: file=@planta.pdf\n\n→ 201 Created\n   { id: 55, links: { self: '...', download: '.../55/download' }, ... }"] --> C2

    C2["**GET /api/v1/properties/{id}/attachments**\n?attachment_type=document\n\n→ 200 OK\n   data: [{ id: 55, name: 'planta.pdf', ... }]"] --> C3

    C3["**GET /api/v1/properties/{id}/attachments/55/download**\n\n→ 200 OK\n   Content-Type: application/pdf\n   binário do arquivo"] --> C4

    C4{Arquivo correto?}
    C4 -->|Sim| Done([✅ Anexo disponível para uso])
    C4 -->|Não, precisa trocar| C5

    C5["**DELETE /api/v1/properties/{id}/attachments/55**\n\n→ 204 No Content"] --> C1

    note1["Não existe PATCH/PUT para substituir binário\nFluxo correto: DELETE + re-upload"]
```

---

## Resumo de Erros por Endpoint

| Endpoint | Código | Causa |
|---|---|---|
| `POST .../attachments` | 400 | Campo `file` ausente no form-data |
| `POST .../attachments` | 401 | Token JWT inválido ou ausente |
| `POST .../attachments` | 403 | Perfil sem permissão de upload (apenas Owner, Manager e Admin) |
| `POST .../attachments` | 404 | Property não encontrada (anti-enumeração) |
| `POST .../attachments` | 413 | Arquivo excede `web.max_file_upload_size` |
| `POST .../attachments` | 415 | MIME type não permitido (validado via magic bytes) |
| `POST .../attachments` | 422 | Limite de 50 imagens ou 20 documentos atingido |
| `GET .../attachments` | 401 | Token JWT inválido |
| `GET .../attachments` | 403 | Sem permissão para a propriedade |
| `GET .../attachments` | 404 | Property não encontrada (anti-enumeração) |
| `GET .../attachments/{id}/download` | 401 | Token JWT inválido |
| `GET .../attachments/{id}/download` | 403 | Sem permissão para a propriedade |
| `GET .../attachments/{id}/download` | 404 | Attachment não pertence à property informada |
| `DELETE .../attachments/{id}` | 401 | Token JWT inválido |
| `DELETE .../attachments/{id}` | 403 | Perfil sem permissão de exclusão (apenas Owner, Manager e Admin) |
| `DELETE .../attachments/{id}` | 404 | Attachment não pertence à property informada |

---

## MIME Types Aceitos

| Categoria | MIME Types |
|---|---|
| **Imagens** | `image/jpeg`, `image/png`, `image/webp` |
| **Documentos** | `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |

> **Validação:** MIME type é detectado via **magic bytes** (conteúdo binário), não pela extensão do arquivo. Um arquivo `.jpg` com conteúdo executável será rejeitado com 415.
