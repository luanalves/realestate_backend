# Feature Specification: Property Status and Situation Options

**Feature Branch**: `018-property-status-options`
**Created**: 2026-05-11
**Status**: Implemented
**Continuação de**: Spec 016 — Property Mapping Fields API Completion
**Input**: "No domínio propriedades, expor os campos que indicam venda/aluguel e status/situação do imóvel, documentar opções no Swagger e atualizar Postman."

**Flowcharts**: [flowcharts.md](./flowcharts.md)

## Executive Summary

Esta spec documenta a normalização dos campos de disponibilidade, status operacional e situação do imóvel nos endpoints REST de propriedades.

O incremento fecha três lacunas observadas no consumo real de `GET /api/v1/properties/{id}`:

- `for_sale` e `for_rent` eram aceitos e filtráveis, mas não eram retornados no serializer principal.
- `property_status` existia no modelo e nos filtros, mas o payload retornava apenas o alias legado `status`.
- `property_situation` existia como string livre e podia vir `null`, sem opções documentadas para clientes renderizarem um seletor.

Após a implementação:

- `for_sale` e `for_rent` são retornados como booleanos.
- `property_status` é retornado explicitamente, mantendo `status` como alias legado.
- `property_situation` é `fields.Selection` e aparece em `GET /api/v1/properties/options`.
- `owner` é retornado a partir do relacionamento `owner_id`; campos soltos legados de contato do proprietário não fazem mais parte do payload de propriedades.
- O retorno da propriedade deriva uma situação legível quando o valor armazenado está vazio.
- Swagger/OpenAPI e Postman v1.30 foram atualizados e validados.

## Scope

### In Scope

- Modelo `real.estate.property`.
- Serializer compartilhado dos endpoints de propriedades.
- Endpoint `GET /api/v1/properties/options`.
- Swagger gerado por `thedevkitchen.api.endpoint`.
- Coleção Postman principal.
- Testes unitários para options e serializer.

### Out of Scope

- Propostas, atendimentos, leads, locações, vendas e anexos.
- Mudança de semântica de `for_sale` / `for_rent`.
- Remoção do alias legado `status`.
- Migração retroativa obrigatória para preencher `property_situation` em todos os registros existentes.

## User Scenarios & Testing

### User Story 1 - Identificar se imóvel está para venda ou aluguel (P1)

**As a** cliente de API
**I want to** receber `for_sale` e `for_rent` no detalhe/listagem de propriedades
**So that** o app saiba se o imóvel é ofertado para venda, aluguel ou ambos.

**Acceptance Criteria**:

- [x] `GET /api/v1/properties/{id}` retorna `for_sale` como booleano.
- [x] `GET /api/v1/properties/{id}` retorna `for_rent` como booleano.
- [x] Os campos preservam os valores persistidos no modelo.
- [x] `POST` e `PUT` continuam aceitando booleanos JSON para esses campos.
- [x] Filtros `GET /api/v1/properties?for_sale=true` e `?for_rent=true` continuam usando query string.

### User Story 2 - Expor status operacional do imóvel (P1)

**As a** cliente de API
**I want to** receber `property_status` explicitamente
**So that** não dependa do alias legado `status` para interpretar o estado operacional do imóvel.

**Acceptance Criteria**:

- [x] `GET /api/v1/properties/{id}` retorna `property_status`.
- [x] `status` permanece no payload como alias legado para compatibilidade.
- [x] `property_status` continua sendo `fields.Selection`.
- [x] `GET /api/v1/properties/options` retorna opções de `property_status`.
- [x] Swagger documenta `property_status` nas respostas.

### User Story 3 - Renderizar seletor de situação do imóvel (P1)

**As a** cliente de API
**I want to** consultar opções de `property_situation`
**So that** o app renderize um seletor com valores válidos e não envie strings arbitrárias.

**Acceptance Criteria**:

- [x] `property_situation` é `fields.Selection`.
- [x] `GET /api/v1/properties/options` retorna `property_situation`.
- [x] `POST` e `PUT` aceitam somente valores válidos de `property_situation`.
- [x] Swagger documenta enum de `property_situation`.
- [x] Postman usa exemplos válidos.

### User Story 4 - Evitar `property_situation: null` no retorno (P2)

**As a** cliente de API
**I want to** receber uma situação útil mesmo quando o banco não tem valor explícito
**So that** o app evite estados vazios em imóveis existentes.

**Acceptance Criteria**:

- [x] Se `property_situation` estiver vazio, o serializer deriva um valor a partir de `property_status`.
- [x] Se `property_situation` estiver preenchido, o serializer preserva o valor explícito.
- [x] O fallback não altera o valor armazenado no banco; atua somente no payload.

## Functional Requirements

- **FR-001**: The system MUST return `for_sale` and `for_rent` in property serializer responses.
- **FR-002**: The system MUST return `property_status` in property serializer responses.
- **FR-003**: The system MUST keep `status` as a legacy alias for `property_status`.
- **FR-004**: The system MUST keep `property_status` as a selectable Odoo field.
- **FR-005**: The system MUST convert `property_situation` from free text to selectable options.
- **FR-006**: The system MUST expose `property_situation` options in `GET /api/v1/properties/options`.
- **FR-007**: The system MUST use stable string values for `property_situation`.
- **FR-008**: The system MUST derive a non-null `property_situation` response value when the stored value is empty.
- **FR-009**: The system MUST document changed response fields in `quicksol_estate/data/api_endpoints.xml`.
- **FR-010**: The system MUST validate generated `/api/v1/openapi.json` after module upgrade.
- **FR-011**: The system MUST update the latest Postman collection or create a new version.
- **FR-012**: The system MUST add tests covering serializer response fields and options output.
- **FR-013**: The system MUST expose FGTS eligibility summary fields for property create/update/detail/list flows.
- **FR-014**: The system MUST compute `fgts.eligible_from` from `fgts.last_usage_date` and return `fgts.eligible_now`.
- **FR-015**: The system MUST validate `fgts.used_fgts` as JSON boolean and `fgts.last_usage_date` as ISO date.

## Field Contracts

### Availability Flags

| API field | Odoo field | Type | Accepted write value | Response value |
|---|---|---|---|---|
| `for_sale` | `for_sale` | boolean | JSON boolean | boolean |
| `for_rent` | `for_rent` | boolean | JSON boolean | boolean |

### FGTS Eligibility

| API field | Odoo field | Type | Accepted write value | Response value |
|---|---|---|---|---|
| `fgts.accepts_fgts` | `accepts_fgts` | boolean | JSON boolean | boolean |
| `fgts.used_fgts` | `used_fgts` | boolean | JSON boolean | boolean |
| `fgts.last_usage_date` | `fgts_last_usage_date` | date | ISO date string, `null`, or `""` | ISO date string or `null` |
| `fgts.eligible_from` | `fgts_eligible_from` | computed date | read-only | ISO date string or `null` |
| `fgts.eligible_now` | `fgts_eligible_now` | computed boolean | read-only | boolean |
| `fgts.usage_notes` | `fgts_usage_notes` | text | string, `null`, or `""` | string or `null` |

Query filters use URL strings:

- `GET /api/v1/properties?for_sale=true`
- `GET /api/v1/properties?for_rent=false`

### Owner Relationship

| API field | Odoo field | Type | Accepted write value | Response value |
|---|---|---|---|---|
| `owner_id` | `owner_id` | many2one | integer ID | not returned as scalar |
| `owner` | `owner_id` | object | read-only | related owner object |

`owner` is read-only in property responses. To create or update the property owner relationship, clients send `owner_id`.

Legacy scalar owner contact fields are rejected on `POST`/`PUT`:

- `owner_email`
- `owner_home_phone`
- `owner_business_phone`
- `owner_mobile_phone`

### Property Status

| API field | Odoo field | Type | Notes |
|---|---|---|---|
| `property_status` | `property_status` | selection | Canonical operational status |
| `status` | `property_status` | string alias | Legacy alias; do not remove without a breaking-change spec |

Current `property_status` options are sourced dynamically from the model through `GET /api/v1/properties/options`.

Known values at implementation time:

| Value | Label |
|---|---|
| `available` | `Available` |
| `occupied` | `Occupied` |
| `rented` | `Rented` |
| `reserved` | `Reserved` |
| `sold` | `Sold` |
| `under_construction` | `Under Construction` |
| `maintenance` | `Under Maintenance` |

### Property Situation

`property_situation` is now selectable.

| Value | Label |
|---|---|
| `Não Informado` | `Não Informado` |
| `Desocupado` | `Desocupado` |
| `Ocupado` | `Ocupado` |
| `Reservado` | `Reservado` |
| `Em construção` | `Em construção` |
| `Lançamento` | `Lançamento` |
| `Novo` | `Novo` |

Fallback mapping for response serialization when stored value is empty:

| `property_status` | Derived `property_situation` |
|---|---|
| `available` | `Desocupado` |
| `occupied` | `Ocupado` |
| `rented` | `Ocupado` |
| `reserved` | `Reservado` |
| `sold` | `Ocupado` |
| `under_construction` | `Em construção` |
| `maintenance` | `Não Informado` |
| unknown/empty | `Não Informado` |

## API Contracts

### GET `/api/v1/properties/{id}`

Relevant response fields:

```json
{
  "id": 4,
  "status": "available",
  "property_status": "available",
  "property_situation": "Desocupado",
  "owner": {
    "id": 4,
    "name": "Proprietário Seed",
    "email": "propowner@seed.com.br",
    "phone": "(11) 3000-4000",
    "mobile": "(11) 98888-7777",
    "whatsapp": "(11) 98888-7777",
    "partner_id": 26
  },
  "for_sale": true,
  "for_rent": false
}
```

### GET `/api/v1/properties/options`

Relevant response sections:

```json
{
  "property_status": [
    {"value": "available", "label": "Available"},
    {"value": "occupied", "label": "Occupied"},
    {"value": "rented", "label": "Rented"},
    {"value": "reserved", "label": "Reserved"},
    {"value": "sold", "label": "Sold"},
    {"value": "under_construction", "label": "Under Construction"},
    {"value": "maintenance", "label": "Under Maintenance"}
  ],
  "property_situation": [
    {"value": "Não Informado", "label": "Não Informado"},
    {"value": "Desocupado", "label": "Desocupado"},
    {"value": "Ocupado", "label": "Ocupado"},
    {"value": "Reservado", "label": "Reservado"},
    {"value": "Em construção", "label": "Em construção"},
    {"value": "Lançamento", "label": "Lançamento"},
    {"value": "Novo", "label": "Novo"}
  ]
}
```

## Implementation Notes

Changed implementation files:

- `18.0/extra-addons/quicksol_estate/models/property.py`
- `18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py`
- `18.0/extra-addons/quicksol_estate/controllers/utils/property_options.py`
- `18.0/extra-addons/quicksol_estate/data/api_endpoints.xml`
- `18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py`
- `docs/postman/quicksol_api_v1.30_postman_collection.json`
- `docs/postman/README.md`

Runtime actions performed:

- Restarted `odoo` to load Python changes.
- Upgraded `quicksol_estate` so Swagger endpoint records were updated in the database.
- Validated `/api/v1/openapi.json` after upgrade.

## Verification Evidence

Validated commands:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py

env PYTHONPYCACHEPREFIX=/private/tmp/codex-pycache \
  python3 -m py_compile \
  18.0/extra-addons/quicksol_estate/models/property.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/property_options.py \
  18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py \
  18.0/extra-addons/quicksol_estate/tests/unit/test_property_mapping_fields_unit.py

python3 -m json.tool docs/postman/quicksol_api_v1.30_postman_collection.json

git diff --check
```

Validated OpenAPI facts:

- `GET /api/v1/openapi.json` contains `property_situation` under `/api/v1/properties/options`.
- `GET /api/v1/openapi.json` contains enum values for `property_situation` under `/api/v1/properties/{id}`.
- `GET /api/v1/openapi.json` contains `property_status` under `/api/v1/properties/{id}`.

Validated API facts:

```text
GET /api/v1/properties/options -> 200
property_situation includes Não Informado, Desocupado, Ocupado, Reservado, Em construção, Lançamento, Novo

GET /api/v1/properties/4 -> 200
property_status=available
property_situation=Desocupado
```

## Success Criteria

- **SC-001**: Property detail responses include `for_sale`, `for_rent`, `property_status`, `property_situation`, and FGTS summary fields.
- **SC-002**: Existing clients using `status` continue to work.
- **SC-003**: API clients can discover `property_status` and `property_situation` options through `/api/v1/properties/options`.
- **SC-004**: Swagger/OpenAPI generated from the local Odoo database documents the new fields and enums.
- **SC-005**: Latest Postman collection contains valid examples for `property_situation`.
- **SC-006**: Unit tests cover options output, serializer fallback behavior, and FGTS validation/serialization.
- **SC-007**: API and UI E2E tests cover FGTS fields in property create/detail and Odoo form rendering.
