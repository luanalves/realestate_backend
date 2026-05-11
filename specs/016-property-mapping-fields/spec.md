# Feature Specification: Property Mapping Fields API Completion

**Feature Branch**: `016-property-mapping-fields`
**Created**: 2026-05-04
**Status**: Draft
**Input**: User description: "Atualizar endpoints de propriedades para incluir os campos faltantes da aba Mapping_Property do spreadsheet recentemente lido, sem depender de specs anteriores."

## Clarifications

### Session 2026-05-04

- Q: Quais campos entram nesta feature? → A: Apenas os campos da aba `Mapping_Property` cujo status é `❌ Faltando`.
- Q: Campos marcados como `✅ Mapeado`, `⚠️ Precisa mapping`, `⚠️ Precisa ajuste` ou `Parcial` entram? → A: Não. Esta feature não deve criar, renomear ou alterar esses campos.
- Q: Quais endpoints são afetados? → A: Endpoints REST de propriedades: listagem, detalhe, criação e atualização de propriedades.
- Q: A feature deve alterar endpoints de propostas, análise de ficha, leads ou outras áreas? → A: Não.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar propriedade com todos os campos faltantes (Priority: P1)

Um usuário autenticado que consulta uma propriedade precisa receber, na resposta da API, todos os campos atualmente faltantes no mapeamento do formulário de propriedade. Isso permite que o frontend exiba ou pré-preencha o formulário completo sem depender de dados paralelos.

**Why this priority**: É o caminho principal de consumo. Sem o retorno dos campos, qualquer criação/edição completa no frontend fica impossível de validar ponta a ponta.

**Independent Test**: Criar uma propriedade com valores nos campos faltantes, consultar `GET /api/v1/properties/{id}` e verificar que todos os campos aparecem no payload com valores corretos.

**Acceptance Scenarios**:

1. **Given** uma propriedade existente com os campos faltantes preenchidos, **When** o usuário consulta o detalhe da propriedade, **Then** a resposta inclui todos os campos listados em "Property Mapping Field Set" com seus valores.
2. **Given** uma propriedade existente sem valores para campos opcionais, **When** o usuário consulta o detalhe, **Then** campos string/date retornam `null`, booleanos retornam `false`, e coleções retornam `[]`.
3. **Given** uma propriedade com imagens, documentos e tags, **When** o usuário consulta o detalhe, **Then** imagens e documentos retornam metadados e links de download, e tags retornam uma lista de strings ou objetos estáveis.

---

### User Story 2 - Criar propriedade com campos faltantes (Priority: P1)

Um owner, manager ou usuário autorizado precisa criar uma propriedade enviando também os campos que hoje estão faltando no mapeamento do formulário.

**Why this priority**: Sem suporte na criação, dados preenchidos no formulário completo seriam descartados ou impossíveis de persistir.

**Independent Test**: Enviar `POST /api/v1/properties` com os campos faltantes preenchidos e verificar que a propriedade criada persiste e retorna esses valores.

**Acceptance Scenarios**:

1. **Given** um payload válido de criação contendo campos faltantes, **When** o usuário cria a propriedade, **Then** a propriedade é salva e a resposta retorna os campos persistidos.
2. **Given** campos booleanos omitidos, **When** a propriedade é criada, **Then** os campos assumem `false` por padrão.
3. **Given** campos de coleção omitidos, **When** a propriedade é criada, **Then** as coleções ficam vazias.
4. **Given** anexos ou imagens enviados no formato suportado pela API, **When** a propriedade é criada, **Then** eles são associados à propriedade e retornados como metadados.

---

### User Story 3 - Atualizar propriedade com campos faltantes (Priority: P1)

Um usuário autorizado precisa editar os campos faltantes de uma propriedade já existente sem afetar campos que já estavam mapeados.

**Why this priority**: O formulário de propriedade precisa funcionar para manutenção de cadastro, não apenas criação.

**Independent Test**: Atualizar uma propriedade via `PUT /api/v1/properties/{id}` com mudanças em campos faltantes e verificar que somente esses campos foram alterados.

**Acceptance Scenarios**:

1. **Given** uma propriedade existente, **When** o usuário atualiza campos faltantes, **Then** os novos valores são persistidos e retornados na resposta.
2. **Given** um update parcial contendo apenas um campo faltante, **When** a requisição é feita, **Then** os demais campos permanecem inalterados.
3. **Given** tentativa de atualizar campos de empresa ou campos não permitidos, **When** a requisição é feita, **Then** o sistema rejeita a alteração conforme as regras de segurança existentes.

---

### User Story 4 - Listar propriedades com resumo dos campos faltantes (Priority: P2)

Usuários que listam propriedades precisam receber um conjunto consistente dos campos faltantes para alimentar tabelas, filtros e cache do frontend, sem precisar consultar cada propriedade individualmente.

**Why this priority**: Melhora eficiência do frontend e evita múltiplas chamadas de detalhe, mas o detalhe já entrega o valor principal.

**Independent Test**: Criar propriedades com valores diferentes nos campos faltantes, consultar `GET /api/v1/properties`, e verificar que cada item inclui o mesmo conjunto de campos.

**Acceptance Scenarios**:

1. **Given** múltiplas propriedades, **When** o usuário consulta a listagem, **Then** cada item retorna o mesmo schema de campos faltantes.
2. **Given** uma listagem paginada, **When** há próxima página, **Then** os links de paginação continuam funcionando e os campos faltantes aparecem em todas as páginas.
3. **Given** filtros existentes de propriedades, **When** usados junto com campos faltantes, **Then** a resposta mantém isolamento por empresa e RBAC.

## Edge Cases

- Campos `null`, strings vazias e booleanos `false` devem ser serializados de forma previsível e não podem desaparecer do payload.
- Campos de imagem/documento não devem retornar binário inline em JSON.
- Campos de arquivo/imagem devem rejeitar formatos/tamanhos inválidos com erro estruturado.
- Tags duplicadas no payload devem ser normalizadas ou rejeitadas com erro claro.
- Atualizações parciais não devem limpar coleções existentes quando o campo não foi enviado.
- Usuário sem acesso à empresa da propriedade deve receber a mesma resposta anti-enumeração usada para propriedade inexistente.
- Campo `ownerEmail` deve aceitar email vazio/nulo, mas quando informado deve ter formato válido.
- Campo `virtualTour` e `youtubeVideo` devem aceitar URL vazia/nula; quando informados, devem ser strings válidas conforme validação definida.

## Requirements *(mandatory)*

### Functional Requirements

#### Endpoint Scope

- **FR-001**: The system MUST update `GET /api/v1/properties/{id}` to return all fields in the "Property Mapping Field Set".
- **FR-002**: The system MUST update `GET /api/v1/properties` so each listed property includes the same mapping field schema as the detail response, unless an explicit lightweight mode is requested.
- **FR-003**: The system MUST update `POST /api/v1/properties` to accept and persist all writable fields in the "Property Mapping Field Set".
- **FR-004**: The system MUST update `PUT /api/v1/properties/{id}` to support partial updates for all writable fields in the "Property Mapping Field Set".
- **FR-005**: The system MUST NOT modify proposal, credit-check, lead, service, lease, sale, or unrelated endpoints as part of this feature.

#### Serialization & Defaults

- **FR-006**: The system MUST serialize omitted string/date fields as `null`.
- **FR-007**: The system MUST serialize omitted boolean fields as `false`.
- **FR-008**: The system MUST serialize omitted collection fields as `[]`.
- **FR-009**: The system MUST expose file and image fields as metadata objects containing at minimum `id`, `name`, `mimetype`, `size`, and `download_url`.
- **FR-010**: The system MUST keep the field naming in API responses as `snake_case`.
- **FR-011**: The system MUST document the source form-field name for every API field so frontend mapping remains traceable.

#### Validation

- **FR-012**: The system MUST validate `owner_email` as an email when present.
- **FR-013**: The system MUST validate `included_in_commission_date` as an ISO date when present.
- **FR-014**: The system MUST validate boolean fields as booleans and reject ambiguous strings unless the existing API normalization explicitly supports them.
- **FR-015**: The system MUST validate collection fields (`tags`, `property_images`, `property_files`) as arrays.
- **FR-016**: The system MUST reject unknown fields in create/update payloads or ignore them only if the API already has a documented ignore-unknown-fields behavior.
- **FR-017**: The system MUST return structured validation errors identifying the invalid field and reason.

#### Security & Isolation

- **FR-018**: The system MUST preserve existing authentication requirements for all property endpoints.
- **FR-019**: The system MUST preserve company isolation for every field returned or modified.
- **FR-020**: The system MUST preserve role-based authorization for create/update/delete operations.
- **FR-021**: The system MUST avoid exposing confidential fields across companies or to unauthorized users.
- **FR-022**: The system MUST not return binary attachment content in JSON responses.

### Property Mapping Field Set

Only fields from the spreadsheet row status `❌ Faltando` are in scope.

| Category | Form field | API field | Type | Writable |
|---|---|---|---|---|
| Owner Details | `ownerEmail` | `owner_email` | string | yes |
| Owner Details | `ownerHomePhone` | `owner_home_phone` | string | yes |
| Owner Details | `ownerBusinessPhone` | `owner_business_phone` | string | yes |
| Owner Details | `ownerMobilePhone` | `owner_mobile_phone` | string | yes |
| Owner Details | `sourceMedium` | `source_medium` | string | yes |
| Owner Details | `sendActivitiesToOwner` | `send_activities_to_owner` | boolean | yes |
| Location | `searchStreet` | `search_street` | string | yes |
| Primary Data | `registeredBy` | `registered_by` | string | yes |
| Primary Data | `alternativeReference` | `alternative_reference` | string | yes |
| Primary Data | `intention` | `intention` | string | yes |
| Primary Data | `iptuPaymentCondition` | `iptu_payment_condition` | string | yes |
| Primary Data | `iptuValue` | `iptu_value` | string | yes |
| Primary Data | `rentalGuaranteeInsurance` | `rental_guarantee_insurance` | string | yes |
| Primary Data | `fireInsurance` | `fire_insurance` | string | yes |
| Primary Data | `exclusivity` | `exclusivity` | boolean | yes |
| Primary Data | `propertySituation` | `property_situation` | string | yes |
| Primary Data | `yearOfRenovation` | `year_of_renovation` | string | yes |
| Primary Data | `zoning` | `zoning` | string | yes |
| Primary Data | `internalComments` | `internal_comments` | string | yes |
| Tags | `tags` | `tags` | array[string] | yes |
| Key Control | `keyLocation` | `key_location` | string | yes |
| Photos | `propertyImages` | `property_images` | array[attachment] | yes |
| Web Publication | `advertise` | `advertise` | boolean | yes |
| Web Publication | `featuredProperty` | `featured_property` | boolean | yes |
| Web Publication | `virtualTour` | `virtual_tour` | string | yes |
| Signs and Banners | `signOnSite` | `sign_on_site` | boolean | yes |
| Signs and Banners | `superFeatured` | `super_featured` | boolean | yes |
| Signs and Banners | `youtubeVideo` | `youtube_video` | string | yes |
| Commissions | `commissionType` | `commission_type` | string | yes |
| Commissions | `capturedIntention` | `captured_intention` | string | yes |
| Commissions | `includedInCommissionDate` | `included_in_commission_date` | date | yes |
| Commissions | `commercialCondition` | `commercial_condition` | string (free text) | yes |
| Documentation | `iptuCode` | `iptu_code` | string | yes |
| Documentation | `registrationNumber` | `registration_number` | string | yes |
| Documentation | `electricityNetworkCode` | `electricity_network_code` | string | yes |
| Documentation | `waterNetworkCode` | `water_network_code` | string | yes |
| Documentation | `titlesRights` | `titles_rights` | string | yes |
| Documentation | `approvedEnvironmentalAgency` | `approved_environmental_agency` | boolean | yes |
| Documentation | `approvedProject` | `approved_project` | boolean | yes |
| Documentation | `documentationObservations` | `documentation_observations` | string | yes |
| Files | `propertyFiles` | `property_files` | array[attachment] | yes |

### Key Entities *(include if feature involves data)*

- **Property**: The central entity exposed by the property REST endpoints. This feature extends its writable and serialized payload with the missing mapping fields above.
- **Property Tag**: A reusable label associated with a property and exposed through `tags`.
- **Property Image Attachment**: Image metadata associated with a property, exposed through `property_images`.
- **Property File Attachment**: File/document metadata associated with a property, exposed through `property_files`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of fields in the "Property Mapping Field Set" are accepted by property create/update endpoints when valid.
- **SC-002**: 100% of fields in the "Property Mapping Field Set" are returned by property detail responses.
- **SC-003**: Property list responses include a stable mapping field schema for every returned item across paginated results.
- **SC-004**: Invalid field values return structured validation errors with the failing field name.
- **SC-005**: Existing property endpoint authorization and company isolation tests continue to pass unchanged.
- **SC-006**: JSON responses never include raw binary payloads for images or files.
- **SC-007**: Existing mapped/partial fields from the spreadsheet are not renamed, duplicated, or semantically changed by this feature.

## Out of Scope

- Changing proposal, credit-check, lead, lease, sale, service, or dashboard endpoints.
- Adding fields marked `✅ Mapeado`, `⚠️ Precisa mapping`, `⚠️ Precisa ajuste`, or `Parcial` in the spreadsheet.
- Redesigning property ownership semantics.
- Importing spreadsheet data automatically.
- Building frontend UI changes.
