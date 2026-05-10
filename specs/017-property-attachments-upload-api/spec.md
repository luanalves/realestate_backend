# Feature Specification: Property Attachments Upload API

**Feature Branch**: `017-property-attachments-upload-api`
**Created**: 2026-05-05
**Status**: Draft
**Continuação de**: Spec 016 — Property Mapping Fields API Completion
**Input**: Property Attachments Upload API — upload, download seguro e exclusão de imagens e documentos de propriedades via API headless com magic bytes validation e limite global via ir.config_parameter
**ADR References**: ADR-003, ADR-007, ADR-008, ADR-009, ADR-011, ADR-015, ADR-018, ADR-019, ADR-022

---

## Executive Summary

Complementa a Spec 016 entregando o ciclo completo de gerenciamento de arquivos (imagens e documentos) de propriedades via API headless. Implementa upload (multipart/form-data), download seguro (rota `/api/v1/...` obrigatória, passando pelo API Gateway) e exclusão de anexos, com limites dinâmicos configuráveis pelo painel Odoo — evitando deploys para ajustar quotas. Segurança é camada central: MIME validation via magic bytes, isolamento por empresa no `ir.attachment`, e download nunca expõe `/web/content/{id}` que bypassa o API Gateway.

---

## Arquitetura de Acesso

```
React Native App (CSR)
        │
        │ Requisições sem token
        ▼
   API Gateway
        │ Injeta JWT automaticamente em todas as rotas /api/v1/...
        ▼
   Odoo Backend
        │ @require_jwt + @require_session + @require_company
        ▼
   ir.attachment / real.estate.property
```

**Implicações para esta feature:**

- O frontend React Native **não gerencia tokens** — o API Gateway injeta o JWT em cada requisição antes de chegar ao Odoo
- O `download_url` retornado pela API **DEVE ser uma rota `/api/v1/...`** para garantir que o Gateway injete o JWT; nunca `/web/content/{id}` que bypassa o Gateway e portanto bypassa autenticação
- O endpoint de download próprio (`GET /api/v1/properties/{id}/attachments/{attachment_id}`) é obrigatório precisamente porque é a única rota que passa pelo Gateway com o JWT injetado

---

## Contexto: Lacuna da Spec 016

A Spec 016 (D007) documentou conscientemente que:
> *"Binary upload format is not defined. Returning metadata satisfies the read contract."*

Esta spec fecha essa lacuna. Os campos `property_images` e `property_files` passam de **somente leitura de metadados** para um **ciclo completo: upload → listagem → download → exclusão**.

---

## User Scenarios & Testing

### User Story 1 — Upload de imagem de propriedade (Priority: P1) 🎯 MVP

**As a** Manager ou Owner autenticado
**I want to** enviar imagens de um imóvel via API
**So that** o app React Native possa exibir fotos da propriedade

**Acceptance Criteria**:
- [ ] `POST /api/v1/properties/{id}/attachments` com `attachment_type=image` e arquivo JPEG/PNG/WebP aceita e persiste o arquivo
- [ ] Arquivo acima do limite configurado retorna `413 Payload Too Large` com `max_size_bytes` e `received_size` no erro
- [ ] MIME type não permitido retorna `415 Unsupported Media Type` com o tipo rejeitado
- [ ] Magic bytes do arquivo divergindo do MIME declarado retorna `415 Unsupported Media Type`
- [ ] Resposta inclui `id`, `name`, `mimetype`, `size`, `attachment_type`, `download_url` e `links` HATEOAS
- [ ] O campo `download_url` SEMPRE aponta para `/api/v1/properties/{id}/attachments/{attachment_id}` (nunca `/web/content/{id}`)
- [ ] Anexo criado é isolado à empresa da propriedade (multi-tenancy)
- [ ] Upload em propriedade de outra empresa retorna `404` (anti-enumeração)

**Test Coverage** (per ADR-003):

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_image_mimetype_allowed()` | image/jpeg, image/png, image/webp aceitos | ⚠️ Required |
| Unit | `test_image_mimetype_rejected()` | application/pdf, text/html, etc. rejeitados | ⚠️ Required |
| Unit | `test_magic_bytes_mismatch_rejected()` | Arquivo .jpg com conteúdo script rejeitado | ⚠️ Required |
| Unit | `test_image_size_limit_enforced()` | Arquivo acima do limite retorna 413 | ⚠️ Required |
| Unit | `test_filename_sanitization()` | Filename com `../`, `<script>`, etc. sanitizado | ⚠️ Required |
| Unit | `test_download_url_uses_api_route()` | download_url nunca contém /web/content/ | ⚠️ Required |
| E2E (API) | `test_owner_uploads_image()` | Fluxo completo: upload → metadados retornados | ⚠️ Required |
| E2E (API) | `test_multitenancy_isolation_upload()` | Upload em propriedade de outra empresa retorna 404 | ⚠️ Required |
| E2E (API) | `test_max_images_per_property()` | Limite de imagens por propriedade respeitado | ⚠️ Required |

---

### User Story 2 — Upload de documento (Priority: P1) 🎯 MVP

**As a** Manager ou Owner autenticado
**I want to** enviar documentos legais (escritura, laudo, contrato) de um imóvel
**So that** o app possa listar e baixar documentos sem acessar o Odoo UI

**Acceptance Criteria**:
- [ ] `POST /api/v1/properties/{id}/attachments` com `attachment_type=document` e arquivo PDF/DOC/DOCX/XLS/XLSX aceita
- [ ] Limite de documentos por propriedade (configurável) é respeitado
- [ ] Resposta segue o mesmo schema de metadados que imagens, com `attachment_type=document`
- [ ] O campo `download_url` aponta para `/api/v1/properties/{id}/attachments/{attachment_id}`

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_document_mimetype_allowed()` | PDF, DOCX, XLSX aceitos | ⚠️ Required |
| Unit | `test_document_size_limit_enforced()` | Limite de documentos aplicado | ⚠️ Required |
| E2E (API) | `test_manager_uploads_document()` | Upload de PDF completo | ⚠️ Required |
| E2E (API) | `test_max_documents_per_property()` | Limite por propriedade respeitado | ⚠️ Required |

---

### User Story 3 — Download seguro de arquivo (Priority: P1) 🎯 MVP

**As a** usuário do app React Native com acesso à propriedade
**I want to** baixar um arquivo da propriedade via rota `/api/v1/...`
**So that** o API Gateway injete o JWT corretamente e o acesso seja autenticado

**Acceptance Criteria**:
- [ ] `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` retorna stream do arquivo com `Content-Type` e `Content-Disposition` corretos
- [ ] Requisição sem JWT (que chegaria apenas se houvesse bypass do Gateway) retorna `401`
- [ ] Acesso a arquivo de outra empresa retorna `404` (anti-enumeração)
- [ ] Acesso a `attachment_id` que não pertence à propriedade `{id}` retorna `404`
- [ ] Header `Content-Security-Policy: default-src 'none'` na resposta de download
- [ ] Header `X-Content-Type-Options: nosniff` na resposta de download
- [ ] O endpoint NUNCA redireciona para `/web/content/{id}`

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_authenticated_download()` | JWT válido retorna stream do arquivo | ⚠️ Required |
| E2E (API) | `test_unauthenticated_download()` | Sem JWT retorna 401 | ⚠️ Required |
| E2E (API) | `test_cross_company_download()` | Arquivo de outra empresa retorna 404 | ⚠️ Required |
| E2E (API) | `test_attachment_not_on_property()` | attachment_id de outra propriedade retorna 404 | ⚠️ Required |
| Unit | `test_no_redirect_to_web_content()` | Controller nunca emite redirect para /web/content/ | ⚠️ Required |

---

### User Story 4 — Exclusão de arquivo (Priority: P2)

**As a** Manager ou Owner
**I want to** remover um arquivo de uma propriedade
**So that** imagens desatualizadas ou documentos incorretos não fiquem expostos

**Acceptance Criteria**:
- [ ] `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` remove o anexo e retorna `204 No Content`
- [ ] Agent não pode excluir (apenas Manager/Owner) → `403 Forbidden`
- [ ] Arquivo de outra empresa retorna `404`
- [ ] Exclusão bem-sucedida não é reversível (hard delete de `ir.attachment`, diferente do soft-delete ADR-015 que se aplica a entidades de domínio)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_agent_cannot_delete()` | Agent recebe 403 | ⚠️ Required |
| E2E (API) | `test_owner_deletes_attachment()` | Owner deleta, retorna 204 | ⚠️ Required |
| E2E (API) | `test_delete_cross_company()` | Arquivo de outra empresa retorna 404 | ⚠️ Required |

---

### User Story 6 — Listagem de anexos de uma propriedade (Priority: P1) 🎯 MVP

**As a** Manager, Owner ou Agent autenticado
**I want to** listar todos os anexos de um imóvel via API
**So that** o app React Native possa exibir thumbnails e documentos disponíveis sem ter que parsear o payload completo da propriedade

**Acceptance Criteria**:
- [ ] `GET /api/v1/properties/{id}/attachments` retorna lista paginada de metadados de anexos
- [ ] Resposta inclui `id`, `name`, `mimetype`, `size`, `attachment_type`, `download_url` e `uploaded_at` por item
- [ ] Suporte a filtro por `attachment_type=image|document` via query param
- [ ] Paginação via `offset` e `limit` (default: `limit=50`)
- [ ] Acesso a propriedade de outra empresa retorna `404` (anti-enumeração)
- [ ] Agent com acesso à propriedade pode listar (somente leitura)

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| E2E (API) | `test_list_attachments_returns_metadata()` | Lista retorna metadados corretos após upload | ⚠️ Required |
| E2E (API) | `test_list_filter_by_type()` | Filtro `?attachment_type=image` retorna apenas imagens | ⚠️ Required |
| E2E (API) | `test_list_pagination()` | `offset` e `limit` funcionam corretamente | ⚠️ Required |
| E2E (API) | `test_list_cross_company_returns_404()` | Outra empresa retorna 404 | ⚠️ Required |
| Unit | `test_list_download_url_uses_api_route()` | `download_url` em cada item nunca contém `/web/content/` | ⚠️ Required |

---

### User Story 5 — Configuração global de limite de tamanho (Priority: P2)

**As a** administrador do sistema (admin Odoo)
**I want to** configurar o limite máximo de tamanho de arquivo via Parâmetros do Sistema do Odoo
**So that** posso ajustar a quota sem deploy de código

**Como configurar no Odoo UI**:
> Configurações → Técnico → Parâmetros do Sistema → chave `web.max_file_upload_size`
> - Valor em **bytes** (ex: `10485760` = 10 MB, `20971520` = 20 MB)
> - Default Odoo: `128 MB` se o parâmetro não existir
> - Escopo: **global** (afeta todos os uploads do servidor)

**Acceptance Criteria**:
- [ ] Controller lê `web.max_file_upload_size` via `env['ir.config_parameter'].sudo().get_param(...)` a cada upload
- [ ] Upload acima do limite retorna `413` com `max_size_bytes` e `received_size` no body
- [ ] Sem o parâmetro configurado, o default de 128 MB é aplicado
- [ ] A documentação da spec indica o caminho exato no Odoo UI para alterar o limite

**Test Coverage**:

| Type | Test Name | Description | Status |
|------|-----------|-------------|--------|
| Unit | `test_upload_reads_ir_config_param()` | Controller lê `web.max_file_upload_size`, não constante hardcoded | ⚠️ Required |
| Unit | `test_upload_uses_default_when_param_absent()` | Sem parâmetro configurado → default 128 MB aplicado | ⚠️ Required |
| E2E (API) | `test_upload_rejected_when_over_global_limit()` | Configura param a 1 MB → arquivo 2 MB retorna 413 | ⚠️ Required |
| E2E (API) | `test_upload_accepted_within_global_limit()` | Arquivo dentro do limite configurado é aceito | ⚠️ Required |

---

## Requirements

### Functional Requirements

**FR1: Upload de Arquivos**
- FR1.1: `POST /api/v1/properties/{id}/attachments` aceita `multipart/form-data` com campos `file` (required) e `attachment_type=image|document` (required)
- FR1.1a: Campos obrigatórios ausentes ou inválidos retornam `400 Bad Request` com os seguintes bodies: campo `file` ausente → `{"error": "missing_file", "detail": "A file is required."}`. Campo `attachment_type` ausente → `{"error": "missing_attachment_type", "detail": "attachment_type is required (image or document)."}`. Valor de `attachment_type` inválido → `{"error": "invalid_attachment_type", "detail": "Invalid attachment_type '<received>'. Allowed values: image, document."}`.
- FR1.2: O sistema valida MIME type por magic bytes do conteúdo, não apenas pelo header Content-Type ou extensão do arquivo
- FR1.3: Tamanho máximo é lido do parâmetro global `web.max_file_upload_size` via `env['ir.config_parameter'].sudo().get_param('web.max_file_upload_size', default=128*1024*1024)`. Nenhum modelo customizado de settings é necessário. Quando excedido, retorna `413 Payload Too Large` com body: `{"error": "file_too_large", "detail": "File size exceeds the configured limit.", "max_size_bytes": <limite>, "received_size": <tamanho_recebido>}`
- FR1.4: Quantidade máxima de arquivos por propriedade é controlada por constantes no controller: `MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20` (hardcoded — não há requisito de configurabilidade para quantidade). Quando excedido, retorna `422 Unprocessable Entity` com body: `{"error": "attachment_limit_exceeded", "detail": "Maximum number of <type> attachments has been reached for this property.", "attachment_type": "<image|document>", "limit": <constante>, "current": <quantidade_atual>}`
- FR1.5: Filename é sanitizado com `werkzeug.utils.secure_filename()` antes do armazenamento. Se o resultado da sanitização for uma string vazia (filename ausente ou composto apenas de caracteres inválidos), o controller retorna `400 Bad Request` com `{"error": "missing_filename", "detail": "A valid filename is required."}`.
- FR1.5a: Upload com conteúdo de arquivo zero-byte (campo `file` presente mas vazio) retorna `400 Bad Request` com `{"error": "empty_file", "detail": "File content cannot be empty."}`. A validação ocorre antes da magic bytes detection.
- FR1.6: O sistema armazena o arquivo como `ir.attachment` com `res_model='real.estate.property'` e `res_id=property.id`
- FR1.7: A resposta inclui metadados completos: `id`, `name`, `mimetype`, `size`, `attachment_type`, `download_url` (rota `/api/v1/...`), `uploaded_at`, `links`

**FR2: Download de Arquivos**
- FR2.1: `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` exige JWT válido e sessão Odoo (injetados pelo API Gateway)
- FR2.2: O controller valida que `attachment.res_id == property.id` e `property.company_id == request.env.company`
- FR2.3: A resposta é construída via `attachment.raw` (bytes completos via ORM) e retornada como `werkzeug.wrappers.Response` com `Content-Type` correto, `Content-Disposition: attachment; filename="..."`, `Content-Security-Policy: default-src 'none'` e `X-Content-Type-Options: nosniff`
- FR2.4: O controller NUNCA emite redirect para `/web/content/{id}` — esse endpoint bypassa o API Gateway e portanto bypassa autenticação
- FR2.5: O tamanho máximo dos arquivos servidos pelo endpoint de download é limitado implicitamente pelo parâmetro configurável `web.max_file_upload_size` — apenas arquivos que passaram pela validação de upload existem no storage. Não há limite adicional para download além deste.

**FR3: Exclusão de Arquivos**
- FR3.1: `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` exige perfil Manager ou Owner
- FR3.2: Exclusão é permanente (hard delete de `ir.attachment`)
- FR3.3: Retorna `204 No Content` em caso de sucesso

**FR4: Configuração de Limite de Tamanho (nativo Odoo)**
- FR4.1: O limite de tamanho de arquivo é configurado via Parâmetros do Sistema do Odoo — **não há modelo customizado**
  - **Caminho no Odoo UI**: Configurações → Técnico → Parâmetros do Sistema
  - **Chave**: `web.max_file_upload_size`
  - **Valor**: tamanho máximo em bytes (ex: `10485760` = 10 MB)
  - **Default**: 128 MB quando o parâmetro não existe
- FR4.2: O controller lê o parâmetro dinamicamente a cada requisição: `env['ir.config_parameter'].sudo().get_param('web.max_file_upload_size', default=134217728)`
- FR4.3: Nenhuma view, menu ou model adicional é necessário para configuração de limites

**FR1.8: Visibilidade no Odoo UI (sem alteração necessária)**
- FR1.8.1: Como os arquivos são armazenados como `ir.attachment` com `res_model='real.estate.property'` e `res_id=property.id`, eles aparecem automaticamente no chatter e painel de anexos do registro da propriedade no Odoo, sem qualquer customização adicional
- FR1.8.2: O admin Odoo pode visualizar, baixar e deletar esses anexos diretamente pelo Odoo UI usando o sistema nativo de attachments

**FR7: Listagem de Arquivos**
- FR7.1: `GET /api/v1/properties/{id}/attachments` retorna lista paginada dos metadados de `ir.attachment` vinculados à propriedade
- FR7.2: Query params suportados: `attachment_type=image|document` (filtro opcional), `limit` (default 50, max 100), `offset` (default 0)
- FR7.3: Cada item retorna: `id`, `name`, `mimetype`, `size`, `attachment_type`, `download_url` (rota `/api/v1/...`), `uploaded_at`, `links` (apenas `links.download` — sem `links.self`)
- FR7.4: Multi-tenancy: apenas anexos da empresa do usuário autenticado são retornados. O campo `total` na resposta reflete **exclusivamente** a contagem dos anexos visíveis ao usuário (resultado da mesma query filtrada por empresa) — nunca uma contagem global.
- FR7.5: Perfis Agent, Manager e Owner têm acesso de leitura à listagem

**FR5: Multi-tenancy**
- FR5.1: O controller de upload verifica que a propriedade pertence à empresa do usuário antes de criar o anexo
- FR5.2: O controller de download verifica propriedade → empresa antes de servir o arquivo
- FR5.3: `ir.attachment` records recebem `company_id` para rastreamento e isolamento

**FR6: Segurança**
- FR6.1: Whitelist de MIME types por categoria (ver seção Data Model)
- FR6.2: Validação de magic bytes com `python-magic` — falha explícita se `libmagic1` não estiver instalado no sistema (T001 garante disponibilidade via Dockerfile)
- FR6.3: Nenhum conteúdo binário retornado em respostas JSON — apenas metadados
- FR6.4: Filename sanitizado antes de qualquer operação de storage
- FR6.5: Logs de audit para uploads rejeitados (tipo inválido, tamanho excedido, acesso negado) em nível `WARNING`. Apenas rejeições são logadas (uploads bem-sucedidos não geram entrada de audit). Campos mínimos obrigatórios por entrada: `timestamp`, `user_id`, `company_id`, `property_id`, `rejection_code` (código do campo `error` do body), `attachment_type`, `file_size_bytes`.
- FR6.6: `download_url` nos metadados SEMPRE aponta para rota `/api/v1/...`, garantindo passagem pelo API Gateway
- FR6.7: O body do erro `415 Unsupported Media Type` segue o formato: `{"error": "unsupported_mime", "detail": "MIME type <detected> is not allowed for attachment_type=<type>"}`. O campo `detail` inclui o MIME type detectado por magic bytes para facilitar debug pelo cliente da API. Para mismatch entre magic bytes e MIME declarado: `{"error": "mime_mismatch", "detail": "Declared MIME type <declared> does not match detected content type <detected>"}`. 
- FR6.8: Respostas de erro NUNCA incluem stack traces, paths internos do servidor, mensagens de exceção do ORM/banco de dados, ou IDs de registros pertencentes a outras empresas. Em caso de erro interno não tratado, o controller retorna `500 Internal Server Error` com body genérico: `{"error": "internal_error", "detail": "An unexpected error occurred."}`.
- FR6.9: Todas as respostas de erro da API seguem o envelope obrigatório `{"error": "<code>", "detail": "<mensagem_legível>", ...campos_extras}`. O campo `error` é um código string em `snake_case`. O campo `detail` é uma string descritiva em inglês voltada para o desenvolvedor cliente. Campos extras são permitidos para informações contextuais (ex: `max_size_bytes`, `limit`, `current`).

---

### Data Model

**Configuração de Limite de Tamanho — Parâmetro Nativo do Odoo**

O Odoo 18.0 possui um parâmetro de sistema nativo para controle de tamanho de upload:

| Atributo | Valor |
|----------|-------|
| **Chave** | `web.max_file_upload_size` |
| **Onde configurar** | Odoo UI: Configurações → Técnico → Parâmetros do Sistema |
| **Formato** | Inteiro em **bytes** (ex: `10485760` = 10 MB, `134217728` = 128 MB) |
| **Default** | `134217728` (128 MB) quando parâmetro não existe |
| **Escopo** | Global — afeta todos os uploads do servidor |

> **Esta feature NÃO cria nenhum modelo customizado de settings.** O `web.max_file_upload_size` é a fonte única de verdade para o limite de tamanho de arquivo.

**Constantes de quantidade no controller** (hardcoded — não há requisito de configurabilidade):
```python
MAX_IMAGES_PER_PROPERTY = 50
MAX_DOCUMENTS_PER_PROPERTY = 20
```

---

**Armazenamento de Arquivos: `ir.attachment` (nativo Odoo, sem nova tabela)**

| Campo | Valor fixado pelo controller | Notas |
|-------|----------------------------|-------|
| `res_model` | `'real.estate.property'` | Vincula ao imóvel |
| `res_id` | `property.id` | ID da propriedade |
| `mimetype` | Detectado por magic bytes | Não o declarado pelo cliente |
| `name` | `secure_filename(original)` | Sanitizado |
| `company_id` | `request.env.company.id` | Multi-tenancy tracking |
| `description` | `"image"` ou `"document"` | Discriminador de tipo |

> **Nota sobre `description`**: Como `ir.attachment` não possui campo nativo `attachment_type`, usamos o campo `description` com valores `"image"` ou `"document"` para distinguir os tipos sem necessidade de herança do modelo.

> **Visibilidade no Odoo UI**: Por usar `res_model='real.estate.property'` e `res_id=property.id`, **todos os arquivos enviados via API aparecem automaticamente** no chatter e painel de anexos do registro da propriedade no Odoo. Nenhuma customização adicional é necessária — este é o comportamento nativo do `ir.attachment`.

**MIME Types permitidos por categoria**:

```python
ALLOWED_IMAGE_MIMETYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    # image/gif excluído: sem caso de uso em apps imobiliários e risco de XSS em metadados
}

ALLOWED_DOCUMENT_MIMETYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
```

---

### RBAC Authorization Matrix

| Endpoint | Owner | Manager | Agent |
|---|---|---|---|
| `POST /api/v1/properties/{id}/attachments` (upload) | ✅ | ✅ | ❌ 403 |
| `GET /api/v1/properties/{id}/attachments` (list) | ✅ | ✅ | ✅ |
| `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` | ✅ | ✅ | ✅ |
| `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` | ✅ | ✅ | ❌ 403 |

**Regras de precedência**:
- A verificação de empresa ocorre **antes** da verificação de perfil: propriedade não encontrada na empresa ativa → `404` (anti-enumeração), independentemente do perfil do usuário.
- A verificação de perfil ocorre **somente** após confirmar que a propriedade pertence à empresa ativa do usuário.
- Uma propriedade pertence a exatamente uma empresa — um usuário que pertença a múltiplas empresas só pode acessar propriedades da **empresa ativa** no momento da requisição.

---

### API Endpoints

#### `POST /api/v1/properties/{id}/attachments` — Upload de arquivo

| Atributo | Valor |
|----------|-------|
| **Method** | POST |
| **Path** | `/api/v1/properties/{id}/attachments` |
| **Content-Type** | `multipart/form-data` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` (ADR-011) — JWT injetado pelo API Gateway |
| **Authorization** | Owner, Manager (Agents: somente leitura) |

**Form Fields**:
```
file            (required) — binário do arquivo
attachment_type (required) — enum: "image" | "document"
```

**Response Success (201)**:
```json
{
  "id": 42,
  "name": "fachada_principal.jpg",
  "mimetype": "image/jpeg",
  "size": 1048576,
  "attachment_type": "image",
  "download_url": "/api/v1/properties/7/attachments/42/download",
  "uploaded_at": "2026-05-05T14:00:00Z",
  "links": {
    "self": "/api/v1/properties/7/attachments/42",
    "download": "/api/v1/properties/7/attachments/42/download"
  }
}
```

> ⚠️ **Invariante de segurança**: `download_url` SEMPRE usa rota `/api/v1/...`. Rota `/web/content/{id}` nunca deve aparecer em nenhuma resposta desta feature — ela bypassa o API Gateway.

**Error Responses**:

| Code | Condição |
|------|----------|
| 400 | `attachment_type` ausente ou inválido |
| 415 | MIME type não permitido para a categoria |
| 415 | Magic bytes divergem do MIME declarado |
| 400 | Nenhum arquivo enviado |
| 403 | Perfil sem permissão de upload (Agent) |
| 404 | Propriedade não encontrada ou de outra empresa (anti-enumeração) |
| 413 | Arquivo excede o limite configurado — body: `{"error": "file_too_large", "max_size_bytes": <limite>, "received_size": <recebido>}` |
| 422 | Limite de quantidade atingido — body: `{"error": "attachment_limit_exceeded", "attachment_type": "<type>", "limit": <n>, "current": <n>}` |

---

#### `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` — Download

| Atributo | Valor |
|----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/properties/{id}/attachments/{attachment_id}/download` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` — JWT injetado pelo API Gateway |
| **Authorization** | Todos os perfis com acesso à propriedade |

**Response Success (200)**:
```
Content-Type: image/jpeg
Content-Disposition: attachment; filename="fachada_principal.jpg"
Content-Security-Policy: default-src 'none'
X-Content-Type-Options: nosniff

[binary stream]
```

> O controller lê o binário do filestore do Odoo via `ir.attachment` e faz streaming direto — sem redirect para `/web/content/{id}`.

**Error Responses**:

| Code | Condição |
|------|----------|
| 401 | JWT ausente ou inválido (requisição chegou sem passar pelo Gateway) |
| 404 | Propriedade não encontrada, attachment não encontrado, ou pertence a outra empresa |

---

#### `GET /api/v1/properties/{id}/attachments` — Listagem paginada

| Atributo | Valor |
|----------|-------|
| **Method** | GET |
| **Path** | `/api/v1/properties/{id}/attachments` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner, Manager, Agent (todos os perfis com acesso à propriedade) |

**Query Parameters**:
```
attachment_type  (optional) — enum: "image" | "document" — filtra por tipo
limit            (optional) — inteiro, default 50, max 100
offset           (optional) — inteiro, default 0
```

**Response Success (200)**:
```json
{
  "total": 12,
  "offset": 0,
  "limit": 50,
  "items": [
    {
      "id": 42,
      "name": "fachada_principal.jpg",
      "mimetype": "image/jpeg",
      "size": 1048576,
      "attachment_type": "image",
      "download_url": "/api/v1/properties/7/attachments/42/download",
      "uploaded_at": "2026-05-05T14:00:00Z"
    }
  ]
}
```

**Error Responses**:

| Code | Condição |
|------|----------|
| 400 | `attachment_type` inválido (não é `image` nem `document`) |
| 404 | Propriedade não encontrada ou de outra empresa |

---

#### `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` — Exclusão

| Atributo | Valor |
|----------|-------|
| **Method** | DELETE |
| **Path** | `/api/v1/properties/{id}/attachments/{attachment_id}` |
| **Authentication** | `@require_jwt` + `@require_session` + `@require_company` |
| **Authorization** | Owner, Manager only |

**Response Success (204)**: `No Content`

**Error Responses**:

| Code | Condição |
|------|----------|
| 403 | Perfil Agent tentando deletar |
| 404 | Propriedade ou attachment não encontrado, ou de outra empresa |

---

### Seed Data (MANDATORY)

**Seed: Companies**
```python
company_a = env['res.company'].create({'name': 'Imobiliária Alpha (Seed)'})
company_b = env['res.company'].create({'name': 'Imobiliária Beta (Seed)'})
```

**Seed: Users por Perfil**
```python
users = {
    'seed_owner_a':   {'login': 'seed_owner_a@test.com',   'company': company_a, 'group': 'group_real_estate_owner'},
    'seed_manager_a': {'login': 'seed_manager_a@test.com', 'company': company_a, 'group': 'group_real_estate_manager'},
    'seed_agent_a':   {'login': 'seed_agent_a@test.com',   'company': company_a, 'group': 'group_real_estate_agent'},
    'seed_owner_b':   {'login': 'seed_owner_b@test.com',   'company': company_b, 'group': 'group_real_estate_owner'},
}
```

**Seed: Propriedades**
```python
property_a = env['real.estate.property'].create({
    'name': 'Seed Property Alpha - Attachments',
    'company_id': company_a.id,
})

property_b = env['real.estate.property'].create({
    'name': 'Seed Property Beta - Attachments',
    'company_id': company_b.id,
})
```

**Seed: Parâmetro de sistema para testes de limite**
```python
# Para E2E tests que validam rejeição por tamanho, usar ir.config_parameter:
env['ir.config_parameter'].sudo().set_param(
    'web.max_file_upload_size',
    str(1 * 1024 * 1024)  # 1 MB — para testar rejeição de seed_large.jpg
)
# IMPORTANTE: restaurar ao valor default após o teste (tearDown)
```

**Seed: Arquivos de Teste** (fixtures na pasta `tests/fixtures/`)
- `seed_image.jpg` — JPEG válido ~1 MB (happy path de upload de imagem)
- `seed_document.pdf` — PDF válido ~500 KB (happy path de upload de documento)
- `seed_malicious.jpg` — Arquivo com extensão .jpg mas magic bytes de script (teste de rejeição por magic bytes)
- `seed_large.jpg` — Arquivo acima de 10 MB (teste de 413)

> Todos os seeds usam prefixo `seed_` para evitar conflito com dados de produção. Seeds são idempotentes.

---

### Non-Functional Requirements

**NFR1: Security** (ADR-008, ADR-011, ADR-017, ADR-019)
- Magic bytes validation impede upload de scripts disfarçados (ZIP bombs, SVG com XSS, PHP mascarado como JPEG)
- Filename sanitization impede path traversal (`../../etc/passwd`)
- Download NUNCA redireciona para `/web/content/{id}` — qualquer redirect bypassaria o API Gateway e portanto a autenticação
- `Content-Security-Policy: default-src 'none'` em downloads previne execução de scripts em eventuais visualizações inline
- `X-Content-Type-Options: nosniff` previne MIME sniffing
- Todos os endpoints protegidos por triple decorator: JWT (injetado pelo Gateway) + sessão Odoo + empresa

**NFR2: Performance**
- `web.max_file_upload_size` lido via `ir.config_parameter` a cada request (custo mínimo — é uma query simples por chave indexada)
- Download implementado via `attachment.raw` (ORM Odoo 14+) retornado como `werkzeug.wrappers.Response` — simples e idiomático; aceito para arquivos até 128 MB (limite configurado)
- Limite de payload validado via `Content-Length` header antes de ler body completo quando possível

**NFR3: Quality** (ADR-022)
- `python-magic` declarado como dependência explícita no ambiente Docker
- **`libmagic1` (biblioteca C) obrigatória no Dockerfile**: `RUN apt-get install -y libmagic1` — `python-magic` (pip) sozinho não funciona sem esta dependência de sistema
- Sem fallback: ausência de `libmagic1` levanta erro explícito — validação silenciosa fraca seria uma vulnerabilidade de segurança (R002)
- Pylint ≥ 8.0, black + isort passando

**NFR4: Observabilidade**
- Decorator `@trace_http_request` em todos os novos endpoints (seguindo padrão de `proposal_controller.py`)
- Logs de audit para: uploads rejeitados por MIME inválido, size exceeded, acesso negado cross-company

---

## Technical Constraints

### Must Follow

| Source | Requisito | Aplicado A |
|--------|-----------|------------|
| **Arquitetura** | `download_url` SEMPRE rota `/api/v1/...` — nunca `/web/content/{id}` | Todos os serializers desta feature |
| **Arquitetura** | Frontend CSR (React Native) não gerencia tokens — API Gateway injeta JWT | Contexto de todos os endpoints |
| ADR-011 | Triple decorators em todos os endpoints | `property_attachments_controller.py` |
| ADR-007 | HATEOAS links na resposta de upload | Response 201 |
| ADR-008 | Company isolation | Upload + Download + Delete |
| ADR-018 | Structured validation errors | 400/413/422 responses |
| ADR-019 | RBAC: upload/delete = Owner+Manager; download = todos os perfis com acesso | Authorization checks |
| ADR-015 | **Exceção**: `ir.attachment` usa hard delete — não é entidade de domínio | DELETE endpoint |
| Odoo nativo | Limite de tamanho via `web.max_file_upload_size` (ir.config_parameter) — sem model customizado | Controller de upload |

### Architecture Decisions

**D001 — Endpoint único `POST /api/v1/properties/{id}/attachments` com `attachment_type` como discriminador**
- Evita duplicação de lógica de upload
- `attachment_type` obrigatório: `image` | `document`
- Cada tipo tem whitelist de MIMEs e limite de tamanho independentes

**D002 — `ir.attachment.description` como discriminador de tipo**
- `description="image"` ou `description="document"`
- Não requer herança de modelo nem campo customizado
- Retrocompatível com Odoo nativo
- ⚠️ `ir.attachment.description` é **exclusivamente um discriminador interno** — NÃO deve ser exposto como campo de texto livre ao usuário; não aparece na API request nem na API response

**D003 — Validação de magic bytes com `python-magic`**
- Detecta conteúdo real independente de extensão/header declarado pelo cliente
- Impede upload de scripts (PHP, Python, JavaScript) mascarados como imagens
- Sem fallback: `libmagic1` é pré-requisito de sistema garantido pelo Dockerfile (T001) — falha explícita é mais segura que validação silenciosa fraca

**D004 — Download via endpoint JWT próprio, streaming direto do filestore**
- Lê binário do `ir.attachment` e entrega em stream HTTP
- NUNCA redireciona para `/web/content/{id}` — esse endpoint não passa pelo API Gateway
- Valida empresa e vínculo com a propriedade antes de servir o arquivo
- Headers de segurança: `Content-Security-Policy`, `X-Content-Type-Options`

**D005 — Limite de tamanho via parâmetro nativo do Odoo, sem model customizado**
- Fonte única de verdade: `web.max_file_upload_size` em `ir.config_parameter`
- Configuração pelo admin: Odoo UI → Configurações → Técnico → Parâmetros do Sistema → `web.max_file_upload_size` (valor em bytes)
- Nenhum modelo customizado criado — simplifica implementação, manutenção e testes
- Constantes de quantidade hardcoded no controller (`MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`)

**D006 — Sem alteração no Odoo para exibição no UI**
- O comportamento nativo de `ir.attachment` com `res_model + res_id` já exibe os arquivos no chatter e painel de anexos da propriedade no Odoo
- Nenhuma view, menu ou ação adicional é necessária para a visibilidade no Odoo — funciona out-of-the-box

**D007 — Fluxo técnico de upload: multipart/form-data → bytes → base64 → filestore do Odoo**

O cliente envia o arquivo como **binário bruto em `multipart/form-data`** (não base64). O fluxo interno é:

```
Cliente (React Native)
    │  multipart/form-data
    │  campo: file=<binary bytes>  (← não é base64)
    │  campo: attachment_type=image|document
    ▼
API Gateway → injeta JWT
    ▼
Controller (Odoo)
    │  upload = request.httprequest.files.get('file')  ← Werkzeug parseia o multipart
    │  content = upload.read()                         ← bytes crus em memória
    │  [validações: size, magic bytes, MIME whitelist]
    │  base64.b64encode(content)                       ← conversão interna p/ ORM
    ▼
ir.attachment.create({'datas': base64_content, ...})
    ▼
Odoo Filestore (disco do container)
    /filestore/{db_name}/{2-char-prefix}/{hash}
    (← gerenciado 100% pelo ORM, não há diretório público intermediário)
```

**Implicações**:
- O cliente **nunca envia base64** — envia binário bruto via multipart
- A conversão `base64.b64encode()` é **interna ao controller**, necessária porque o campo `ir.attachment.datas` do ORM do Odoo armazena em base64
- **Não há diretório público intermediário** — `ir.attachment.create()` salva diretamente no filestore do Odoo
- **Não há cópia entre diretórios** — o filestore é o destino final
- Para download, o controller lê `attachment.raw` (bytes) via ORM e faz streaming direto — sem expor o caminho do filestore

---

## Success Criteria

### Backend
- [ ] Upload de imagem (JPEG, PNG, WebP) funciona via `POST /api/v1/properties/{id}/attachments`
- [ ] Upload de documento (PDF, DOCX, XLSX) funciona via `POST /api/v1/properties/{id}/attachments`
- [ ] Magic bytes validation rejeita scripts mascarados como imagens
- [ ] Download via `GET /api/v1/properties/{id}/attachments/{attachment_id}/download` retorna stream com headers de segurança
- [ ] `download_url` nos metadados SEMPRE aponta para rota `/api/v1/...` — nunca `/web/content/{id}`
- [ ] DELETE funciona para Owner/Manager, retorna 403 para Agent
- [ ] Multi-tenancy: acesso cross-company retorna 404 em todos os endpoints
- [ ] Limite de tamanho lido corretamente de `web.max_file_upload_size` (ir.config_parameter); default 128 MB aplicado quando parâmetro ausente
- [ ] Documentação da spec indica caminho exato: Configurações → Técnico → Parâmetros do Sistema → `web.max_file_upload_size`
- [ ] 100% unit test coverage em validações de segurança e negócio (ADR-003)
- [ ] Pylint ≥ 8.0, black + isort (ADR-022)

### Frontend (Odoo UI — somente admin)
- [ ] Não há views ou menus customizados nesta feature — configuração é via Parâmetros do Sistema nativos do Odoo
- [ ] Admin confirma que `web.max_file_upload_size` está acessível em Configurações → Técnico → Parâmetros do Sistema

### Seeds
- [ ] Prefixo `seed_` em todas as entidades
- [ ] Arquivos de fixture incluídos (seed_image.jpg, seed_document.pdf, seed_malicious.jpg, seed_large.jpg)
- [ ] `ir.config_parameter` configurado no setUp dos E2E tests que validam limite de tamanho e restaurado no tearDown
- [ ] Seeds são idempotentes

### Integração com Spec 016
- [ ] `serialize_property()` atualizado para gerar `download_url` usando rota `/api/v1/...`
- [ ] Metadados de `property_images` e `property_files` incluem `attachment_type` no payload

---

## Constitution Feedback

### New Patterns Introduced

| Pattern | Descrição | Seção na Constitution | Prioridade |
|---------|-----------|----------------------|------------|
| **File Upload Sub-resource Pattern** | Uploads via `POST /resource/{id}/attachments` multipart/form-data, separado do CRUD JSON principal | Architectural Patterns | High |
| **Magic Bytes Validation** | Validação de conteúdo real do arquivo via `python-magic`, independente do MIME declarado pelo cliente | Security Requirements | High |
| **Secure Download Endpoint** | Download JWT-autenticado com streaming e headers de segurança; NUNCA redirect para `/web/content/{id}` | Security Requirements | High |
| **Gateway-Aware URL Generation** | `download_url` e links HATEOAS SEMPRE usam rotas `/api/v1/...` para garantir passagem pelo API Gateway | Architectural Patterns | High |
| **Global File Size via ir.config_parameter** | Limite de tamanho lido de `web.max_file_upload_size` (Odoo nativo) sem model customizado | Architectural Patterns | Medium |

### Architectural Clarification Documented

Durante esta spec, foi confirmado e documentado o modelo real de acesso:

```
React Native App (CSR) → API Gateway (injeta JWT) → Odoo Backend
```

- Frontend React Native (CSR) — não gerencia tokens
- API Gateway — injeta JWT em todas as rotas `/api/v1/...`
- Consequência: qualquer rota que bypass o Gateway (`/web/content/`, `/web/login`, etc.) chega ao Odoo sem JWT → sem autenticação

**Esta arquitetura deve ser documentada na Constitution como restrição de segurança explícita.**

### Constitution Update Recommendation

- **Update Required**: Yes
- **Suggested Version Bump**: MINOR (1.6.0 → 1.7.0)
- **Sections to Update**:
  - [ ] Security Requirements: Magic bytes validation pattern
  - [ ] Security Requirements: Secure download endpoint pattern + Gateway bypass risk
  - [ ] Architectural Patterns: File Upload Sub-resource Pattern
  - [ ] Architectural Patterns: Gateway-Aware URL Generation (download_url invariant)
  - [ ] Core Principles — VI (Headless Architecture): detalhar modelo CSR React Native + API Gateway
  - [ ] Reference Implementations: Feature 017 entry

---

## Assumptions & Dependencies

**Assumptions**:
- `python-magic` pode ser adicionado como dependência no ambiente Docker
- `libmagic1` está disponível via `apt-get` na imagem base do Odoo (Debian Bookworm)
- `ir.attachment` com `res_model='real.estate.property'` funciona corretamente (padrão confirmado em propostas com `res_model='real.estate.proposal'`)
- O campo `description` de `ir.attachment` é seguro para uso como discriminador sem conflito com uso nativo do Odoo
- O API Gateway já está configurado para injetar JWT em todas as rotas `/api/v1/...`
- Rotas fora de `/api/v1/...` (como `/web/content/`) não passam pelo Gateway — essa é a razão pela qual o endpoint de download próprio é obrigatório
- O Odoo remove `ir.attachment` automaticamente via cascade quando o registro vinculado (`res_id`) é deletado — nenhum código de cascade precisa ser implementado nesta feature

**Dependencies**:
- Spec 016: modelo `real.estate.property` com relations `photo_ids` e `document_ids` já existentes no serializer
- `python-magic` (pip package) para magic bytes detection
- `libmagic1` (apt package) — dependência de sistema obrigatória para `python-magic`; adicionar `RUN apt-get install -y libmagic1` ao Dockerfile do Odoo
- `werkzeug.utils.secure_filename` (já disponível no Odoo) para sanitização de filename

---

## Implementation Phases

### Phase 1: Upload Endpoint
- `controllers/property_attachments_controller.py`: `POST /api/v1/properties/{id}/attachments`
- Magic bytes validation + filename sanitization
- MIME whitelist por `attachment_type`
- Size limit lido de `web.max_file_upload_size` via `ir.config_parameter`; quantity limits como constantes (`MAX_IMAGES_PER_PROPERTY = 50`, `MAX_DOCUMENTS_PER_PROPERTY = 20`)
- E2E API tests (incluindo teste de limite via `ir.config_parameter`)

### Phase 2: List + Download Endpoints
- `GET /api/v1/properties/{id}/attachments` com paginação e filtro por `attachment_type`
- `GET /api/v1/properties/{id}/attachments/{attachment_id}` com streaming e headers de segurança
- Validação empresa + vínculo com propriedade
- E2E API tests de isolamento, paginação e acesso não autenticado

### Phase 3: Delete Endpoint
- `DELETE /api/v1/properties/{id}/attachments/{attachment_id}` com RBAC
- E2E API tests

### Phase 4: Integração com Spec 016
- Atualizar `serialize_property()` para gerar `download_url` usando rota `/api/v1/...`
- Atualizar metadados de `property_images` e `property_files` no serializer

### Phase 5: Docs & Artifacts (pós-implementação)
- Swagger/OpenAPI via `thedevkitchen_api_endpoint` table (ADR-005)
- Postman collection (ADR-016)
- Constitution update (v1.7.0)

---

## Validation Checklist

### Backend Validation
- [ ] ADR-011: Triple decorators em todos os 4 endpoints (list, upload, download, delete)
- [ ] ADR-007: HATEOAS links na resposta 201 do upload
- [ ] ADR-008: Company isolation verificada em upload + download + delete
- [ ] ADR-018: Structured validation errors (400, 413, 422)
- [ ] ADR-019: RBAC correto (upload/delete: Owner+Manager; download: todos os perfis com acesso)
- [ ] ADR-003: Unit tests para todas as validações de segurança
- [ ] ADR-022: Linting Python
- [ ] **Invariante arquitetural**: `download_url` NUNCA contém `/web/content/`
- [ ] `web.max_file_upload_size` lido corretamente via `ir.config_parameter`; E2E test valida rejeição quando parâmetro configurado abaixo do tamanho do arquivo

### Frontend Validation
- [ ] Nenhuma view ou menu customizado nesta feature — sem validação de UI necessária
- [ ] Admin pode acessar `web.max_file_upload_size` em Configurações → Técnico → Parâmetros do Sistema

---

## Clarifications

### Session 2026-05-06

- Q: O ciclo completo inclui um endpoint dedicado de listagem (`GET /api/v1/properties/{id}/attachments`) ou a listagem fica embedded no payload do GET da propriedade via `serialize_property()`? → A: Novo endpoint dedicado `GET /api/v1/properties/{id}/attachments` com paginação — escopo adicional desta feature
- Q: Como a dependência `python-magic` deve ser provisionada no Docker? → A: `RUN apt-get install -y libmagic1` no Dockerfile do Odoo — `python-magic` (pip) requer `libmagic` como biblioteca C de sistema
- Q: O que acontece com os `ir.attachment` quando a propriedade vinculada é deletada? → A: Cascade delete via comportamento nativo do Odoo — attachments são removidos automaticamente, nenhum código adicional necessário nesta feature
- Q: `image/gif` deve ser incluído na whitelist de MIME types para imagens? → A: Não — removido da whitelist; sem caso de uso em apps imobiliários e GIFs podem carregar XSS em metadados; whitelist final: JPEG, PNG, WebP
- Q: Como implementar o download do arquivo (streaming vs. bytes em memória)? → A: `attachment.raw` (ORM, bytes completos em memória) + `werkzeug.wrappers.Response` — idiomático no Odoo, aceito para arquivos até 128 MB
