# Feature Specification: CMS Domain

**Feature Branch**: `021-cms-domain`
**Created**: 2026-05-23
**Status**: Draft
**Solution Type**: Both — API REST headless + Odoo UI (admin)
**Input**: CMS Domain com Puck editor, SEO avançado, biblioteca de mídia, company slug multi-tenant, observabilidade

## Clarifications

### Session 2026-05-24

- Q: O token de integração da rota pública é um mecanismo novo (ex: campo em cms.settings) ou reutiliza a autenticação existente da plataforma? → A: Reutiliza o JWT existente da aplicação (`@require_jwt`). A rota pública NÃO é anônima e NÃO cria nova infraestrutura de token. A company é resolvida pelo `company_slug` na URL em vez de via sessão.
- Q: O conteúdo do template (`content` Puck JSON) deve ficar na própria tabela ou em tabela separada como as páginas? → A: Tabela separada (`thedevkitchen.cms.template.content`) — mesmo padrão das páginas para consistência e performance em listagens.
- Q: Páginas CMS precisam suportar múltiplos idiomas (locale por página, traduções vinculadas)? → A: Não — idioma único por página, sem suporte multilingual neste escopo. Pode ser adicionado como extensão futura sem quebrar o modelo atual.
- Q: O registro em `cms.page.content` é criado imediatamente no `POST` (com `content=null`) ou de forma lazy no primeiro `PUT` com conteúdo? → A: Imediatamente no `POST` com `content=null` — join sempre garantido, sem lógica condicional no service layer.
- Q: O `agent` acessa metadados apenas ou metadados + `content` completo de páginas publicadas via rota interna? → A: Metadados + `content` completo — mesma resposta que owner/director/manager para páginas `published`. O mesmo conteúdo já está disponível via rota pública com JWT.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar e publicar uma página CMS com SEO (Priority: P1)

Proprietários, diretores e gerentes de imobiliárias precisam criar páginas web com conteúdo visual rico e metadados SEO completos (Open Graph, canonical URL, robots meta e JSON-LD para rich results no Google), publicando-as imediatamente no website da agência via editor visual baseado em componentes.

> **Por que JSON-LD?** JSON-LD (`structured_data`) permite que o Google extraia informações estruturadas da página e exiba rich results nas buscas (ex: card de imobiliária com estrelas, endereço e telefone). Para imobiliárias, isso aumenta visibilidade orgânica de imóveis e da empresa sem mudanças no HTML. É a forma padrão recomendada pelo Google para structured data (schema.org).

**Why this priority**: É o fluxo fundamental do CMS — sem criação e publicação de páginas, nenhuma outra funcionalidade tem valor. Entrega visibilidade digital imediata para a agência.

**Independent Test**: Pode ser testado criando uma página via `POST /api/v1/cms/pages`, publicando-a via `PUT /api/v1/cms/pages/:id` com `{"status": "published"}`, e verificando que `GET /api/v1/cms/pages/:page_slug` (rota interna) retorna o conteúdo com todos os campos SEO.

**Acceptance Scenarios**:

1. **Given** um owner/director/manager autenticado com JWT+session+company válidos, **When** `POST /api/v1/cms/pages` com `name`, `slug` URL-safe, `content` JSON Puck válido e campos SEO, **Then** página criada com `status=draft`, `created_at` e `updated_at` preenchidos, retorna 201 com HATEOAS links.

2. **Given** uma página em `status=draft`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "published"}`, **Then** `status=published`, `published_at` preenchido, `updated_at` atualizado, retorna 200.

3. **Given** um `slug` com caracteres inválidos (uppercase, espaços, `/`, `..`), **When** `POST /api/v1/cms/pages`, **Then** retorna 422 `{"error": "slug_invalid"}` — path traversal prevenido.

4. **Given** `content` maior que 512KB, **When** `POST` ou `PUT`, **Then** retorna 422 `{"error": "content_too_large", "max_size_bytes": 524288, "received_size": N}`.

5. **Given** `content` que não é JSON válido, **When** `POST` ou `PUT`, **Then** retorna 422 `{"error": "content_invalid_json"}`.

6. **Given** slug já existente na mesma imobiliária, **When** `POST /api/v1/cms/pages`, **Then** retorna 409 `{"error": "slug_conflict", "field": "slug"}`.

7. **Given** `structured_data` com JSON-LD inválido, **When** `POST` ou `PUT`, **Then** retorna 422 `{"error": "structured_data_invalid_json"}`.

8. **Given** `robots_meta=noindex,nofollow` configurado, **When** `GET /api/v1/cms/pages/:page_slug`, **Then** resposta inclui `robots_meta` com o valor correto.

9. **Given** role `agent`, **When** `POST /api/v1/cms/pages` ou `PUT /api/v1/cms/pages/:id`, **Then** retorna 403 — agents são view-only.

10. **Given** roles `receptionist`, `prospector`, `property_owner` ou `portal`, **When** qualquer endpoint CMS autenticado, **Then** retorna 403.

11. **Given** página da imobiliária B, **When** autenticado como imobiliária A, **Then** retorna 404 — isolamento multi-tenant garantido.

---

### User Story 2 - Gerenciar biblioteca de mídia (Priority: P1)

Equipes editoriais precisam fazer upload e organizar imagens, vídeos e documentos para uso nas páginas CMS. Uploads mal formados ou arquivos maliciosos devem ser rejeitados antes de chegar ao armazenamento.

**Why this priority**: Sem mídia, as páginas ficam sem conteúdo visual. É a base para carrosséis de imagens, banners e thumbnails de imóveis nos componentes Puck.

**Independent Test**: Pode ser testado fazendo upload de uma imagem via `POST /api/v1/cms/media/upload` e verificando que o arquivo está acessível via a URL retornada.

**Acceptance Scenarios**:

1. **Given** um arquivo com MIME type permitido e tamanho dentro do limite, **When** `POST /api/v1/cms/media/upload` (multipart/form-data), **Then** arquivo armazenado, metadados salvos, retorna 201 com `id`, `url`, `mime_type`.

2. **Given** arquivo com MIME não permitido (ex: `text/html`, `application/javascript`), **When** upload, **Then** retorna 415 `{"error": "unsupported_mime", "received": "..."}`.

3. **Given** extensão `.jpg` mas conteúdo real detectado como PDF (magic bytes), **When** upload, **Then** retorna 415 `{"error": "mime_mismatch"}` — validação por conteúdo, não por extensão.

4. **Given** imagem maior que 10MB, **When** upload, **Then** retorna 413 `{"error": "file_too_large", "max_size_bytes": 10485760}`.

5. **Given** vídeo maior que 100MB, **When** upload, **Then** retorna 413 `{"error": "file_too_large", "max_size_bytes": 104857600}`.

6. **Given** nome de arquivo com path traversal (ex: `../../etc/passwd.jpg`), **When** upload, **Then** filename sanitizado antes de armazenar.

7. **Given** `DELETE /api/v1/cms/media/:id`, **When** executado por owner/director/manager da imobiliária correta, **Then** arquivo binário removido definitivamente do armazenamento (hard delete), retorna 200.

8. **Given** mídia da imobiliária B, **When** autenticado como imobiliária A, **Then** retorna 404.

---

### User Story 3 - Consultar páginas CMS: rota interna e rota pública (Priority: P1)

O sistema precisa expor dois pontos de acesso distintos para leitura de páginas: um para integrantes autenticados da imobiliária (que podem ver páginas em qualquer status) e outro para o frontend público (Next.js SSR), que deve carregar apenas páginas publicadas. Ambas as rotas reutilizam o JWT existente da aplicação — sem criar novo mecanismo de autenticação. A diferença está nos dados retornados e em como a company é identificada.

**Why this priority**: A separação de rotas é crítica para segurança: a rota interna expõe campos operacionais (`status`, `created_at`, `updated_at`) que não devem aparecer no website público; a rota pública identifica a company pelo `company_slug` na URL em vez de via sessão, e retorna apenas páginas publicadas sem dados operacionais internos.

**Independent Test**: Pode ser testado chamando a rota interna com JWT+session+company e a rota pública com JWT (sem session/company), verificando que cada uma retorna apenas os campos adequados ao seu contexto.

**Acceptance Scenarios**:

**Rota Interna (integrantes da imobiliária)**

1. **Given** owner/director/manager autenticado com JWT+session+company, **When** `GET /api/v1/cms/pages` (listagem), **Then** retorna todas as páginas da imobiliária em qualquer status, com campos operacionais (`status`, `created_at`, `updated_at`), paginado.

2. **Given** owner/director/manager autenticado, **When** `GET /api/v1/cms/pages/:id`, **Then** retorna metadados + conteúdo completo da página incluindo campos SEO e operacionais.

3. **Given** role `agent` autenticado, **When** `GET /api/v1/cms/pages`, **Then** retorna apenas páginas com `status=published` — agents têm acesso somente leitura de páginas publicadas, incluindo metadados e `content` completo.

4. **Given** autenticado na imobiliária A, **When** `GET /api/v1/cms/pages/:id` de página pertencente à imobiliária B, **Then** retorna 404.

**Rota Pública (frontend / Next.js SSR)**

5. **Given** chamada com JWT válido da aplicação, **When** `GET /api/v1/public/cms/:company_slug/pages/:page_slug`, **Then** retorna 200 com Puck JSON + campos SEO completos (title, meta_description, og_*, canonical_url, robots_meta, structured_data) — somente se `status=published` e `active=True`.

6. **Given** chamada sem JWT ou com JWT inválido, **When** `GET /api/v1/public/cms/:company_slug/pages/:page_slug`, **Then** retorna 401 — rota pública não é anônima, reutiliza `@require_jwt` existente.

7. **Given** `company_slug` inexistente na plataforma, **When** acesso com token válido, **Then** retorna 404 genérico — sem revelar existência ou não de companies (prevenção de enumeração).

8. **Given** página com `status=draft`, `pending_review` ou `archived`, **When** acesso pela rota pública, **Then** retorna 404 genérico.

9. **Given** página com `active=False` (soft-deleted), **When** acesso pela rota pública, **Then** retorna 404.

10. **Given** resposta 200 da rota pública, **When** inspecionado o payload, **Then** campos `custom_js`, `custom_css`, `status`, `created_at` e `updated_at` estão ausentes — dados operacionais nunca expostos ao frontend.

11. **Given** o mesmo `page_slug` existente em duas imobiliárias, **When** acesso com `company_slug` da imobiliária A, **Then** retorna somente a página da imobiliária A.

---

### User Story 4 - Gerenciar ciclo de vida da página via PUT (Priority: P1)

Equipes editoriais precisam submeter páginas para revisão e aprovação via uma única interface de atualização — sem endpoints de ação separados por transição. Toda mudança de status é um `PUT` no recurso da página, e o sistema valida se a transição é permitida pelo estado atual.

**Why this priority**: Um endpoint único de atualização (`PUT`) simplifica o contrato da API, é mais previsível para integrações e deixa a tabela de páginas com `updated_at` sempre atualizado como registro de auditoria natural de qualquer mudança.

**Independent Test**: Pode ser testado fazendo o fluxo completo draft → pending_review → published → archived usando apenas `PUT /api/v1/cms/pages/:id` com diferentes valores de `status`, verificando as transições.

**Acceptance Scenarios**:

1. **Given** página em `draft`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "pending_review"}`, **Then** `status=pending_review`, `updated_at` atualizado, retorna 200.

2. **Given** página em `pending_review`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "published"}` por owner/director/manager, **Then** `status=published`, `published_at` e `updated_at` definidos, retorna 200.

3. **Given** página em `pending_review`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "draft"}` (rejeição), **Then** `status=draft`, `updated_at` atualizado, retorna 200.

4. **Given** página em `published`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "archived"}`, **Then** `status=archived`, `updated_at` atualizado, retorna 200.

5. **Given** página em `archived`, **When** `PUT /api/v1/cms/pages/:id` com `{"status": "draft"}` (reativação), **Then** `status=draft`, `updated_at` atualizado, retorna 200.

6. **Given** transição inválida (ex: `draft → archived` diretamente), **When** `PUT /api/v1/cms/pages/:id` com `{"status": "archived"}`, **Then** retorna 422 `{"error": "invalid_status_transition", "from": "draft", "to": "archived", "allowed": ["pending_review", "published"]}`.

7. **Given** role `agent`, **When** `PUT /api/v1/cms/pages/:id` com qualquer mudança de `status`, **Then** retorna 403.

8. **Given** `PUT /api/v1/cms/pages/:id` com campos de metadados (name, SEO) sem campo `status`, **When** executado, **Then** metadados atualizados, `updated_at` atualizado, status não muda.

---

### User Story 5 - Criar e gerenciar templates (Priority: P2)

Owners e managers precisam criar layouts padrão reutilizáveis (landing pages de imóvel, páginas sobre, páginas de contato) para que a equipe editorial possa iniciar novas páginas com estrutura pré-definida.

**Why this priority**: Templates aceleram a criação de conteúdo e mantêm consistência visual entre páginas da mesma imobiliária.

**Independent Test**: Pode ser testado criando um template e depois criando uma página a partir dele, verificando que o `content` é copiado corretamente.

**Acceptance Scenarios**:

1. **Given** owner/director/manager autenticado, **When** `POST /api/v1/cms/templates` com `name`, `category` e `content` Puck JSON, **Then** template criado isolado à imobiliária atual, retorna 201.

2. **Given** `POST /api/v1/cms/pages` com `template_id` válido da mesma imobiliária, **When** criado, **Then** nova página com `content` copiado do template, `status=draft`.

3. **Given** `template_id` pertencente a imobiliária diferente, **When** `POST /api/v1/cms/pages`, **Then** retorna 422 `{"error": "template_not_found"}`.

4. **Given** `POST /api/v1/cms/pages/:id/duplicate`, **When** executado, **Then** nova página criada com `name + " (Cópia)"`, `slug + "-copy"`, `status=draft`, `created_at` e `updated_at` preenchidos com o momento da duplicação.

5. **Given** role `agent`, **When** `GET /api/v1/cms/templates`, **Then** retorna 403 — gestão de templates restrita a owner/director/manager.

---

### User Story 6 - Configurar CMS da imobiliária (Priority: P3)

O owner da imobiliária precisa configurar o slug público da empresa (que aparece na URL do website), CSS customizado para estilização da marca e, com controle restrito, JavaScript customizado para comportamentos avançados.

**Why this priority**: Configurações são pré-requisito para o endpoint público funcionar (sem `company_slug`, a URL pública não resolve). CSS e JS são secundários mas necessários para personalização da marca.

**Independent Test**: Pode ser testado configurando o `company_slug` e verificando que o endpoint público resolve corretamente a imobiliária.

**Acceptance Scenarios**:

1. **Given** settings ainda não existem para a imobiliária, **When** `GET /api/v1/cms/settings`, **Then** settings criadas automaticamente (singleton), retorna 200 com valores padrão.

2. **Given** `PUT /api/v1/cms/settings` com `company_slug` no formato correto (lowercase, hífens), **When** executado por owner/director/manager, **Then** salvo, retorna 200.

3. **Given** `company_slug` com formato inválido (uppercase, espaços, caracteres especiais), **When** `PUT /api/v1/cms/settings`, **Then** retorna 422 `{"error": "company_slug_invalid"}`.

4. **Given** `company_slug` já em uso por outra imobiliária na plataforma, **When** `PUT /api/v1/cms/settings`, **Then** retorna 409 `{"error": "company_slug_conflict"}`.

5. **Given** `custom_css` contendo padrão de injeção (`expression()`, `behavior:`, `url(javascript:)`), **When** `PUT /api/v1/cms/settings`, **Then** retorna 422 `{"error": "css_injection_detected"}`.

6. **Given** `custom_js` no body enviado por `director` ou `manager`, **When** `PUT /api/v1/cms/settings`, **Then** retorna 403 `{"error": "forbidden", "detail": "custom_js can only be modified by owner"}`.

7. **Given** `custom_js` enviado por `owner`, **When** salvo, **Then** campos `custom_js_last_modified_by` e `custom_js_last_modified_at` atualizados para auditoria.

8. **Given** `GET /api/v1/cms/settings` por `director` ou `manager`, **When** retornado, **Then** campo `custom_js` ausente da resposta.

---

### User Story 7 - Admin gerencia CMS pela interface Odoo (Priority: P2)

O administrador da plataforma precisa gerenciar páginas, templates, mídia e configurações CMS diretamente pela interface Odoo para operações de suporte, auditoria e administração de emergência.

> ⚠️ **Acesso exclusivo ao `admin` Odoo** — todos os demais roles acessam o CMS exclusivamente via API headless.

**Why this priority**: Operações de suporte (corrigir slug errado, forçar publicação, limpar mídia) precisam de acesso direto sem depender do frontend Next.js estar disponível.

**Independent Test**: Pode ser testado navegando pelo menu "CMS" no Odoo como usuário admin e verificando que todas as views carregam sem erros.

**Acceptance Scenarios**:

1. **Given** usuário `admin` logado no Odoo, **When** navega para o menu "CMS", **Then** carrega sem diálogo "Oops!" e sem erros JavaScript no console.

2. **Given** list view de páginas aberta, **When** visualizada, **Then** exibe `status` com badge colorido por estado (4 estados), `created_at` e `updated_at` como colunas opcionais com `optional="show"`.

3. **Given** form view de página aberta, **When** visualizada, **Then** exibe statusbar com todos os 4 status, aba "SEO" dedicada com campos Open Graph, canonical e robots.

4. **Given** form view de configurações aberta, **When** visualizada, **Then** campo `company_slug` visível e `custom_js` em seção separada "Código Customizado (Avançado)".

5. **Given** DevTools aberto durante navegação, **When** todas as views são carregadas, **Then** zero erros JavaScript no console em Chrome e Firefox.

---

### User Story 8 - Observabilidade do domínio CMS (Priority: P3)

Engenheiros de plataforma precisam monitorar operações CMS (publicações, uploads, tentativas de injeção, mudanças de status) via Grafana/Loki/Prometheus para detectar proativamente falhas críticas.

**Why this priority**: Mudanças de status de páginas são operações críticas de negócio — uma publicação que falha silenciosamente impacta diretamente o website público da imobiliária.

**Independent Test**: Pode ser testado publicando uma página e verificando que o evento `cms.page.published` aparece no Loki com os campos corretos.

**Acceptance Scenarios**:

1. **Given** mudança de status de página (qualquer transição), **When** executada com sucesso, **Then** evento `cms.page.status_changed` logado com `company_id`, `page_id`, `slug`, `from_status`, `to_status`, `author_id`.

2. **Given** publicação de página (status → published), **When** executada, **Then** evento específico `cms.page.published` logado adicionalmente com `published_at`.

3. **Given** upload de mídia bem-sucedido, **When** executado, **Then** contador `cms_media_uploads_total` incrementado com labels `company_id`, `mime_type`, `type`.

4. **Given** tentativa de CSS injection bloqueada, **When** detectada, **Then** evento de segurança `cms.css_injection_blocked` logado com `company_id` e `field`.

5. **Given** métricas disponíveis, **When** acessadas em `/metrics`, **Then** `cms_pages_by_status` (gauge por status, 4 valores) presente e correto.

---

### Edge Cases

- Dois usuários fazem `PUT` de status na mesma página simultaneamente → A última escrita vence (lock otimista do Odoo ORM); ambas operações registradas em `mail.thread` com `updated_at` do vencedor.
- `duplicate` gera slug já existente (ex: `home-copy` já existe) → Sufixo incrementado automaticamente: `home-copy-2`, `home-copy-3`.
- Imobiliária não configurou `company_slug` e alguém acessa o endpoint público → Retorna 404 genérico.
- `og_image_id` referencia mídia de outra imobiliária → Validação de constraint rejeita antes de persistir.
- `custom_css` maior que 64KB → Retorna 422 `{"error": "css_too_large"}`.
- `page_slug` com path traversal (`../admin`) → Validação regex bloqueia antes de qualquer operação de banco.
- JWT expirado ou inválido na rota pública → Retorna 401 via `@require_jwt` existente — rota pública não é degradada para anônima.
- `PUT` com `status` inválido (ex: `{"status": "deleted"}`) → Retorna 422 `{"error": "invalid_status_value", "allowed": ["draft", "pending_review", "published", "archived"]}`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE suportar ciclo de vida de páginas CMS com 4 estados (`draft → pending_review → published → archived`), com transições controladas e rollback para `draft`. Mudanças de status são realizadas exclusivamente via `PUT /api/v1/cms/pages/:id` com o campo `status` no body.

- **FR-002**: O sistema DEVE validar que `slug` de página contém apenas caracteres URL-safe (`^[a-z0-9]+(?:-[a-z0-9]+)*$`) e que é único por imobiliária — constraint composta no banco.

- **FR-003**: O sistema DEVE validar que `content` é JSON válido e não excede 512KB; rejeitar com erro explicativo antes de persistir.

- **FR-004**: O sistema DEVE expor duas rotas de leitura distintas, ambas autenticadas via `@require_jwt` existente: (1) rota interna (`GET /api/v1/cms/pages`) — com `@require_session` + `@require_company`, retorna páginas em qualquer status com campos operacionais; (2) rota pública (`GET /api/v1/public/cms/:company_slug/pages/:page_slug`) — somente `@require_jwt`, company resolvida pelo `company_slug` na URL, retorna apenas páginas publicadas sem campos operacionais. Nenhum novo mecanismo de autenticação é criado.

- **FR-005**: O sistema DEVE identificar imobiliárias no endpoint público via `company_slug` configurado nas settings — único na plataforma, resolução feita pelo servidor de aplicação.

- **FR-006**: O sistema DEVE validar arquivos de mídia por conteúdo real (magic bytes), não por extensão, rejeitando MIMEs fora da whitelist e tipos divergentes entre extensão e conteúdo real.

- **FR-007**: O sistema DEVE restringir escrita do campo `custom_js` ao role `owner` no service layer, com auditoria de quem alterou e quando.

- **FR-008**: O sistema DEVE validar `custom_css` contra padrões de injeção (`expression()`, `behavior:`, `url(javascript:)`) antes de persistir.

- **FR-009**: A rota pública NUNCA deve retornar `custom_js`, `custom_css`, `status`, `created_at` ou `updated_at` em sua resposta.

- **FR-010**: O sistema DEVE emitir eventos estruturados para mudanças de status, publicações, CSS injection bloqueada e upload de mídia, consumíveis pela stack de observabilidade existente.

- **FR-011**: O sistema DEVE fornecer interface administrativa Odoo com todos os 4 estados visíveis, aba SEO dedicada e seção de código customizado separada.

- **FR-012**: O sistema DEVE atualizar o módulo de capabilities RBAC para conceder acesso CMS a owner/director/manager (criação, edição, publicação) e agent (somente leitura de páginas publicadas).

- **FR-013**: O carrossel de imagens é tratado como componente frontend — o backend armazena as referências de mídia no JSON da página sem modelo de dados adicional.

- **FR-014**: O sistema DEVE suportar duplicação de páginas, gerando automaticamente um slug não conflitante com sufixo incremental.

- **FR-015**: Deleção de mídia é permanente (hard delete) — exceção explícita ao padrão de soft delete da plataforma, documentada no modelo.

- **FR-016**: A tabela de páginas DEVE registrar `created_at` e `updated_at` automaticamente, com `updated_at` atualizado em toda operação `PUT`.

### Key Entities

- **CMS Page** (`thedevkitchen.cms.page`): Metadados da página — `name`, `slug`, `status` (4 estados), campos SEO (`title`, `og_*`, `canonical_url`, `robots_meta`), `published_at`, `created_at`, `updated_at`, `company_id`. O campo `content` reside em tabela separada. Chave natural composta: `(slug, company_id)`. Suporta `mail.thread` para auditoria de transições de status.

- **CMS Page Content** (`thedevkitchen.cms.page.content`): Armazena o corpo da página em coluna `TEXT`. Relacionada à página via `page_id` (1:1, `ondelete='cascade'`). Registro criado automaticamente junto com a página (no `POST`), com `content=null` até o primeiro `PUT` com conteúdo. Tabela separada para evitar impacto de performance nas consultas de listagem.

- **CMS Template** (`thedevkitchen.cms.template`): Layout reutilizável com conteúdo Puck JSON pré-definido por categoria (`landing`, `property`, `about`). Escopo por imobiliária. O conteúdo reside obrigatoriamente em tabela separada `thedevkitchen.cms.template.content` (mesmo padrão de `cms.page.content`) — listagens de templates não carregam o JSON completo.

- **CMS Media** (`thedevkitchen.cms.media`): Arquivo binário com MIME type validado por conteúdo, tamanho limitado por tipo, vinculado a `ir.attachment`. Deleção permanente — exceção documentada ao soft delete padrão.

- **CMS Settings** (`thedevkitchen.cms.settings`): Singleton por imobiliária (criado automaticamente on-demand). Contém `company_slug`, configurações de SEO padrão, `custom_css` (validado contra injection), `custom_js` (acesso restrito ao role `owner` com campos de auditoria `custom_js_last_modified_by`, `custom_js_last_modified_at`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editores completam o fluxo completo (criar → preencher SEO → publicar) em menos de 5 minutos sem documentação adicional — medido em testes de usabilidade com 5 usuários reais.

- **SC-002**: 100% das tentativas de upload com MIME proibido ou divergente são rejeitadas antes de chegar ao armazenamento — verificado por suite de testes com 15+ tipos de arquivo.

- **SC-003**: A rota pública `GET /api/v1/public/cms/:company_slug/pages/:page_slug` responde em menos de 200ms para 95% das requisições com até 500 req/s concorrentes — medido em teste de carga.

- **SC-004**: A rota de listagem interna `GET /api/v1/cms/pages` retorna em menos de 300ms com dataset de 10.000 páginas, sem carregar o campo `content` na listagem — verificado por teste de performance com dados sintéticos.

- **SC-005**: Zero erros JavaScript no console Odoo ao navegar por todas as views administrativas em Chrome e Firefox — verificado por testes Cypress automatizados.

- **SC-006**: Isolamento multi-tenant: 100% das tentativas de acesso cross-company retornam 404 — verificado por matriz de testes com pelo menos 2 imobiliárias distintas.

- **SC-007**: Campos `custom_js`, `custom_css`, `status`, `created_at` e `updated_at` ausentes em 100% das respostas da rota pública — verificado por asserção nos testes de integração.

- **SC-008**: Todas as transições de estado inválidas são rejeitadas com erro explícito contendo `from`, `to` e `allowed` — verificado por testes unitários de state machine.

- **SC-009**: Rota pública retorna 401 em 100% das chamadas sem JWT válido — zero acesso anônimo à rota pública, validado pelo `@require_jwt` existente.

---

## Assumptions & Dependencies

### Assumptions

- `python-magic` disponível na imagem Docker (Feature 017 introduziu a dependência)
- Feature 020 (RBAC Capabilities API) implementada e funcional
- O frontend Next.js usa `@measured/puck` para renderização — o backend não valida a estrutura interna do JSON Puck, apenas que é JSON válido dentro do limite de tamanho
- Rate limiting no gateway é configurado externamente ao módulo Odoo
- `thedevkitchen_observability` módulo funcional e integrado na versão 18.0
- A rota pública reutiliza `@require_jwt` da plataforma — sem nova infraestrutura de token. A company é resolvida pelo `company_slug` da URL.

### Out of Scope (Technical Debt)

- Agendamento de publicação e demais operações CRUD agendadas — movido para débito técnico (ver `TECHNICAL_DEBIT.md`)
- Suporte multilingual (múltiplos idiomas por página) — fora do escopo; modelo atual suporta extensão futura sem quebra de schema

### Module Dependencies

- `quicksol_estate` — RBAC groups, `capability_service.py`
- `thedevkitchen_apigateway` — `@require_jwt`, `@require_session`, `@require_company`
- `thedevkitchen_observability` — logging estruturado, Prometheus counters/gauges, OpenTelemetry spans
- `ir.attachment` — armazenamento binário de mídia
- `mail.thread` — audit trail de transições de status das páginas
