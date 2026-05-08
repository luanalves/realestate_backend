# Security Requirements Checklist: Property Attachments Upload API

**Purpose**: Validate completeness, clarity, consistency, and measurability of security requirements before opening PR
**Created**: 2026-05-08
**Feature**: [spec.md](../spec.md)
**Audience**: Author (auto-revisão pré-PR)
**Depth**: Thorough (gate formal)

---

## Authentication & Authorization Requirements

- [x] CHK001 - Are authentication requirements (triple decorators `@require_jwt + @require_session + @require_company`) specified consistently and explicitly for ALL 4 endpoints (upload, download, list, delete)? [Consistency, Spec §FR2.1, §FR3.1, §FR7]
  > ✅ PASS — Triple decorators explicitados em cada tabela de endpoint da spec.
- [x] CHK002 - Is the Agent-exclusion rule for upload (403 Forbidden) explicitly specified and distinct from the anti-enumeration 404 pattern? When does the controller return 403 vs. 404 for an Agent attempting to upload? [Clarity, Spec §US1-AC]
  > ✅ PASS — Propriedade pertence a exatamente uma empresa. Verificação de empresa (404) precede verificação de perfil (403) por design. Regras de precedência documentadas na Matriz RBAC adicionada à spec.
- [x] CHK003 - Are the RBAC levels (Owner/Manager → upload + delete; Owner/Manager/Agent → read + list) defined without ambiguity for each of the 4 endpoints in a single table or matrix? [Completeness, Gap]
  > ✅ RESOLVIDO — Matriz RBAC consolidada adicionada à spec (§RBAC Authorization Matrix) com regras de precedência explícitas.
- [x] CHK004 - Is the JWT injection responsibility clearly delineated as an API Gateway concern, and are there requirements defining what happens when the JWT is structurally valid but the Odoo session is expired or inactive? [Clarity, Spec §Architecture]
  > ✅ PASS — Tratado pelo framework (`@require_jwt` + `@require_session`). Odoo retorna 401 automaticamente. Não requer requisito explícito na spec.
- [x] CHK005 - Does the spec define the expected behavior when `@require_company` resolves no active company for the authenticated user (missing company context)? [Edge Case, Gap]
  > ✅ PASS — Todo usuário criado via fluxo de convite tem empresa associada. O decorator `require_company` retorna 403 `no_company` via middleware. Não é um cenário de negócio válido — não requer requisito na spec.
- [x] CHK006 - Is the distinction between "no access to property" (404 anti-enumeration) and "access but insufficient role" (403) consistently applied and defined for ALL 4 endpoints? [Consistency, Spec §US1-AC, §US3-AC, §US4-AC]
  > ✅ PASS — Anti-enumeração (404) explícita nos ACs de US1, US3, US4, US6 e em FR5. Regras de precedência documentadas na Matriz RBAC.
- [x] CHK007 - Are requirements defined for the scenario where a user belongs to multiple companies and uploads to a property belonging to a non-active company context? [Edge Case, Gap]
  > ✅ PASS — Uma propriedade pertence a exatamente uma empresa. Se a empresa da propriedade não estiver ativa no contexto do usuário, o filtro `company_id in re_companies.ids` não encontra a propriedade → 404. Regra documentada na Matriz RBAC.

---

## File Validation Requirements

- [x] CHK008 - Are the MIME type whitelists for `image` and `document` categories exhaustively enumerated (no open-ended "etc.") and justified for exclusions (e.g., `image/gif` excluded for XSS risk)? [Completeness, Spec §Data Model]
  > ✅ PASS — Whitelists explícitas no Data Model: 3 tipos de imagem, 5 de documento. Exclusão de `image/gif` documentada com justificativa.
- [x] CHK009 - Is the 415 vs. 400 distinction for file rejection clearly specified: which status code is returned for (a) MIME not in whitelist, (b) magic bytes mismatch with declared MIME, and (c) `attachment_type=image` but sending a PDF? [Clarity, Spec §FR1.2, §US1-AC]
  > ✅ RESOLVIDO — FR6.7 adicionado: dois formatos distintos de body para 415. (a) MIME não na whitelist → `{"error": "unsupported_mime", "detail": "MIME type <detected> is not allowed for attachment_type=<type>"}`. (b) Mismatch magic bytes → `{"error": "mime_mismatch", "detail": "Declared MIME type <declared> does not match detected content type <detected>"}`. (c) `attachment_type=image` com PDF → cobre (a), pois PDF não está em `ALLOWED_IMAGE_MIMETYPES`.
- [x] CHK010 - Is the behavior when `libmagic1` is unavailable at controller runtime (system library missing) specified — hard failure (500), graceful degradation, or startup-time gate? [Edge Case, Spec §FR6.2]
  > ✅ PASS — T001 garante disponibilidade via Dockerfile. FR6.2 especifica "falha explícita" como requisito. Garantia de infraestrutura é suficiente — não requer requisito adicional na spec.
- [x] CHK011 - Is the filename sanitization requirement measurable? Does the spec define which characters are stripped, whether null bytes are handled, and whether a maximum filename length is enforced? [Clarity, Spec §FR1.5]
  > ✅ PASS — `werkzeug.utils.secure_filename()` tem comportamento documentado e determinístico. Testes cobrem `../` e `<script>`. Comprimento máximo sem requisito de negócio.
- [x] CHK012 - Are requirements defined for an empty or missing filename (file sent without a `filename` header in the multipart `Content-Disposition`)? [Edge Case, Gap]
  > ✅ RESOLVIDO — FR1.5 atualizado: `secure_filename()` retornando string vazia → `400` com `{"error": "missing_filename", "detail": "A valid filename is required."}`.
- [x] CHK013 - Does the spec address double-extension attacks (e.g., `malware.pdf.jpg`) — does `secure_filename()` alone cover this, or is there an additional requirement? [Coverage, Gap]
  > ✅ PASS — Coberto implicitamente pela magic bytes validation (FR1.2): extensão é ignorada, conteúdo real é detectado. Não requer requisito adicional.
- [x] CHK014 - Is there a requirement covering zero-byte or truncated file uploads (0-byte `file` field, valid MIME header but empty content)? [Edge Case, Gap]
  > ✅ RESOLVIDO — FR1.5a adicionado: arquivo zero-byte → `400` com `{"error": "empty_file", "detail": "File content cannot be empty."}`. Validação ocorre antes da magic bytes detection.
- [x] CHK015 - Are requirements defined for when `attachment_type` in the form field does not match the magic-bytes-detected MIME category (e.g., `attachment_type=image` submitted with a PDF file)? [Clarity, Gap]
  > ✅ PASS — Coberto pela lógica de whitelist por categoria: PDF não está em `ALLOWED_IMAGE_MIMETYPES` → 415. O discriminador `attachment_type` determina qual whitelist aplicar.

---

## Multi-tenancy & Isolation Requirements

- [x] CHK016 - Is the anti-enumeration pattern (404 instead of 403 for cross-company resources) explicitly required for ALL 4 endpoints without exception? [Completeness, Spec §FR5.1-5.3, §US3-AC]
  > ✅ PASS — Anti-enumeração (404) explícita nos ACs de US1, US3, US4, US6 e em FR5.1–5.2. Cobre todos os 4 endpoints.
- [x] CHK017 - Is the `ir.attachment.company_id` assignment specified as a mandatory field (never null) for all records created by this feature? [Clarity, Spec §Data Model]
  > ✅ PASS — Tabela do Data Model fixa `company_id = request.env.company.id`. Nunca null.
- [x] CHK018 - Are requirements defined for the case where `property.company_id` is null or unset at upload time — is this an error condition (400/500) or should the controller default to the user's active company? [Edge Case, Gap]
  > ✅ PASS — `property.company_id` não pode ser null no modelo. Se a propriedade não for encontrada no filtro da empresa ativa → 404. Cenário impossível na prática.
- [x] CHK019 - Is the cross-company isolation requirement explicitly stated for the LIST endpoint (`GET /api/v1/properties/{id}/attachments`) including that `ir.attachment` records from other companies are never leaked even in `total` count? [Coverage, Spec §FR7.4]
  > ✅ RESOLVIDO — FR7.4 atualizado: campo `total` reflete exclusivamente a contagem dos anexos visíveis ao usuário (mesma query filtrada por empresa), nunca contagem global.
- [x] CHK020 - Does the spec define the behavior for a valid `{attachment_id}` that belongs to a different `{property_id}` within the same company (ownership mismatch within tenant)? [Clarity, Spec §US3-AC, §FR2.2]
  > ✅ PASS — FR2.2 especifica explicitamente: `attachment.res_id == property.id` é validado. Mismatch → 404.
- [x] CHK021 - Are there requirements against timing-based enumeration — i.e., must the controller return 404 responses for cross-company resources in constant time (no differential latency)? [Non-Functional, Gap]
  > ✅ PASS — Fora de escopo. Padrão 404 consistente mitiga enumeração lógica. Constant-time response é impraticável com ORM Odoo e não há requisito de negócio para isso.

---

## Download Security Requirements

- [x] CHK022 - Is the prohibition on `/web/content/{id}` redirect documented as an absolute invariant with an explicit rationale (API Gateway bypass) — not merely a code comment but a stated requirement? [Clarity, Spec §FR2.4]
  > ✅ PASS — FR2.4 é requisito explícito com rationale: bypassa o API Gateway e portanto bypassa autenticação.
- [x] CHK023 - Are the required security response headers (`Content-Security-Policy: default-src 'none'` and `X-Content-Type-Options: nosniff`) specified with exact values, not just referenced by name? [Clarity, Spec §FR2.3, §US3-AC]
  > ✅ PASS — FR2.3 especifica ambos os headers com valores exatos.
- [x] CHK024 - Is `Content-Disposition: attachment` (force download) vs. `inline` (browser rendering) explicitly required, and is the filename encoding standard (RFC 5987 / ASCII fallback) specified? [Clarity, Spec §FR2.3]
  > ✅ PASS — FR2.3 especifica `Content-Disposition: attachment; filename="..."`. Encoding ASCII via werkzeug é suficiente — sem requisito de negócio para filenames não-ASCII.
- [x] CHK025 - Are requirements defined for the maximum file size that `attachment.raw` may load into memory before triggering an OOM-class risk — is there a hard ceiling or a reference to the 128 MB global limit? [Non-Functional, Gap]
  > ✅ RESOLVIDO — FR2.5 adicionado: o teto de download é o mesmo parâmetro configurável `web.max_file_upload_size` (configurável via Odoo UI). Apenas arquivos que passaram pela validação de upload existem no storage — não há limite adicional.
- [x] CHK026 - Does the spec require a `Content-Length` header in download responses (needed by clients for progress indicators and integrity checks)? [Coverage, Gap]
  > ✅ PASS — Fora de escopo. Detalhe de implementação deixado para o desenvolvedor. `werkzeug.wrappers.Response` pode incluir automaticamente.
- [x] CHK027 - Are CORS requirements specified for the download endpoint — should it accept cross-origin requests from React Native (e.g., via `cors='*'`) or restrict origins? [Completeness, Gap]
  > ✅ PASS — React Native é app mobile nativo; CORS não se aplica. Padrão `cors='*'` do projeto (ADR-011) é suficiente.

---

## File Size & Quantity Limit Requirements

- [x] CHK028 - Is the 413 error response body format fully specified with exact field names (e.g., `max_size_bytes`, `max_size_mb`, `received_size`) — not just the status code? [Clarity, Spec §US1-AC, §US5-AC]
  > ✅ RESOLVIDO — FR1.3 atualizado: body `{"error": "file_too_large", "max_size_bytes": <limite>, "received_size": <recebido>}`. `max_size_mb` removido (inconsistência eliminada). AC de US1 e tabela de status codes atualizados.
- [x] CHK029 - Is the `web.max_file_upload_size` default of 128 MB (134217728 bytes) explicitly stated as a requirement, distinguishing it from an implementation detail or code comment? [Completeness, Spec §FR1.3]
  > ✅ PASS — FR1.3 especifica `default=128*1024*1024` explicitamente com o caminho do Odoo UI. FR4.1/4.2 documentam o parâmetro configurável.
- [x] CHK030 - Are the hardcoded quantity constants (`MAX_IMAGES_PER_PROPERTY=50`, `MAX_DOCUMENTS_PER_PROPERTY=20`) specified as requirements in the spec, including the exact 422 error body format when exceeded? [Completeness, Spec §FR1.4, Gap]
  > ✅ RESOLVIDO — FR1.4 atualizado: body `{"error": "attachment_limit_exceeded", "attachment_type": "<image|document>", "limit": <constante>, "current": <quantidade_atual>}`. Tabela de status codes atualizada.
- [x] CHK031 - Does the spec define behavior for concurrent upload requests that would simultaneously push the property past the quantity limit (race condition / double-submit scenario)? [Edge Case, Gap]
  > ✅ PASS — Fora de escopo. Transações PostgreSQL com isolamento padrão do Odoo garantem consistência. Não há requisito de negócio para lock explícito nesta feature.
- [x] CHK032 - Is there a requirement for how the quantity limit check and the file write operation are performed atomically, preventing a TOCTOU (time-of-check / time-of-use) window? [Edge Case, Gap]
  > ✅ PASS — Fora de escopo. Odoo ORM opera dentro de transação PostgreSQL única por request. Atomicidade garantida por infraestrutura — não requer requisito explícito na spec.

---

## Error Handling & Information Disclosure Requirements

- [ ] CHK033 - Do the error response body requirements explicitly prohibit disclosure of internal paths, ORM IDs from other companies, stack traces, or database error messages? [Completeness, Spec §FR6.5]
- [ ] CHK034 - Is the 400 error body format for each specific bad-request condition (missing `file`, missing `attachment_type`, invalid `attachment_type` value) specified with exact field names and messages? [Clarity, Gap]
- [ ] CHK035 - Is there a requirement that all 4 endpoints return error responses in a consistent JSON envelope structure (same top-level fields: `error`, `detail`, etc.)? [Consistency, Gap]
- [ ] CHK036 - Does the spec require that the 415 response body never reveals which specific magic byte signature was detected (preventing file type fingerprinting by attackers)? [Clarity, Gap]

---

## Audit & Logging Requirements

- [ ] CHK037 - Are audit logging requirements specified with: (a) which events trigger a log entry (rejected uploads only, or also successes?), (b) minimum required fields per log entry, and (c) log level? [Completeness, Spec §FR6.5]
- [ ] CHK038 - Does the spec explicitly require that audit log entries for rejected uploads must NOT include the binary file content or full MIME signature detail (log injection / data exfiltration risk)? [Clarity, Gap]
- [ ] CHK039 - Are requirements defined for audit log retention period and access control (admin-only vs. visible to Owner/Manager in the Odoo UI)? [Completeness, Gap]

---

## Hard Delete & Data Lifecycle Requirements

- [ ] CHK040 - Is the hard delete exception to ADR-015 (soft-delete policy) documented with its justification in the spec itself (not just in plan.md), so reviewers understand the conscious deviation? [Completeness, Spec §US4-AC]
- [ ] CHK041 - Is the cascade deletion behavior (when a `real.estate.property` is soft-deleted, Odoo auto-removes linked `ir.attachment` records) specified as a verified requirement vs. an assumed behavior? [Coverage, Spec §FR3.4]
- [ ] CHK042 - Does the spec define the behavior if `ir.attachment.unlink()` raises an exception (file-system error, locked record) — is partial deletion acceptable, or must the controller rollback atomically? [Edge Case, Gap]

---

## Notes

- Check off items as validated: `[x]`
- Mark gaps with inline notes: `<!-- gap: reason not covered -->`
- Items marked `[Gap]` indicate security requirements that may be missing from the spec — review and add explicit requirements before merge
- Items marked `[Consistency]` indicate cross-endpoint alignment checks
- Items marked `[Non-Functional]` require measurable NFR thresholds to be defined
