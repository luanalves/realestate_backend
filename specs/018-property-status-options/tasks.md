# Tasks: Property Status and Situation Options

## Phase 1 - Serializer

- [x] Add `for_sale` to property serializer response.
- [x] Add `for_rent` to property serializer response.
- [x] Add `property_status` to property serializer response.
- [x] Keep `status` as legacy alias.
- [x] Add `property_situation` fallback mapping from `property_status`.

## Phase 2 - Model

- [x] Convert `property_situation` from `fields.Char` to `fields.Selection`.
- [x] Define allowed values:
  - `Não Informado`
  - `Desocupado`
  - `Ocupado`
  - `Reservado`
  - `Em construção`
  - `Lançamento`
  - `Novo`

## Phase 3 - Options API

- [x] Add `property_situation` to `PROPERTY_SELECTION_FIELDS`.
- [x] Confirm `GET /api/v1/properties/options` returns `property_situation`.
- [x] Confirm `GET /api/v1/properties/options` still returns `property_status`.

## Phase 4 - Swagger/OpenAPI

- [x] Update `quicksol_estate/data/api_endpoints.xml`.
- [x] Parse embedded JSON schemas from XML.
- [x] Upgrade `quicksol_estate`.
- [x] Validate generated `/api/v1/openapi.json`.

## Phase 5 - Postman

- [x] Create `docs/postman/quicksol_api_v1.30_postman_collection.json`.
- [x] Update examples to use valid `property_situation` values.
- [x] Validate Postman JSON.
- [x] Update `docs/postman/README.md`.

## Phase 6 - Tests

- [x] Add unit test for `property_status` in serializer response.
- [x] Add unit test for `property_situation` options output.
- [x] Add unit test for fallback from `property_status`.
- [x] Add unit test preserving explicit `property_situation`.
- [x] Run unit test suite.
- [x] Run `py_compile`.
- [x] Run `git diff --check`.

## Phase 7 - Flow Documentation

- [x] Add `flowcharts.md` for API journeys.
- [x] Document option loading before form usage.
- [x] Document create/update flows for sale, rent, status and situation.
- [x] Document listing/filtering flows.
- [x] Document Swagger/OpenAPI validation flow.

## Follow-up Candidates

- [ ] Add a database migration/cleanup if production has invalid historical `property_situation` strings.
- [ ] Add an integration test that calls `/api/v1/properties/options` over HTTP.
- [ ] Decide whether `status` alias should be deprecated in a future breaking-change spec.
