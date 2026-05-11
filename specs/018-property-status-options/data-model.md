# Data Model: Property Status and Situation Options

## Entity: `real.estate.property`

### Existing Fields Used

| Field | Type | Required | Default | API exposure | Notes |
|---|---|---:|---|---|---|
| `for_sale` | Boolean | no | `True` | `for_sale` | Indicates the property is offered for sale. |
| `for_rent` | Boolean | no | `False` | `for_rent` | Indicates the property is offered for rent. |
| `property_status` | Selection | yes | `available` | `property_status`, `status` | Canonical operational status. `status` is a legacy alias in API response. |
| `property_situation` | Selection | no | `Não Informado` | `property_situation` | User-facing situation label for app/UI selectors. |
| `owner_id` | Many2one | no | empty | `owner` response object; `owner_id` write field | Links the property to `real.estate.property.owner`. |

## `property_status` Selection

Defined in `18.0/extra-addons/quicksol_estate/models/property.py`.

| Value | Label | Meaning |
|---|---|---|
| `available` | `Available` | Operationally available. |
| `occupied` | `Occupied` | Occupied but not necessarily rented. |
| `rented` | `Rented` | Rented. |
| `reserved` | `Reserved` | Reserved. |
| `sold` | `Sold` | Sold. |
| `under_construction` | `Under Construction` | Under construction. |
| `maintenance` | `Under Maintenance` | Temporarily under maintenance. |

## `property_situation` Selection

Defined in `18.0/extra-addons/quicksol_estate/models/property.py`.

| Value | Label |
|---|---|
| `Não Informado` | `Não Informado` |
| `Desocupado` | `Desocupado` |
| `Ocupado` | `Ocupado` |
| `Reservado` | `Reservado` |
| `Em construção` | `Em construção` |
| `Lançamento` | `Lançamento` |
| `Novo` | `Novo` |

## Serialization Rules

### `owner`

- Serialized from the `owner_id` relationship.
- Returned as an object named `owner`.
- Written by sending `owner_id` as an integer in `POST` or `PUT`.
- Legacy scalar owner contact fields are not part of the property response and are rejected in property create/update payloads.

### `for_sale` / `for_rent`

- Serialized as booleans.
- Written as JSON booleans in `POST` and `PUT`.
- Used as string query params in `GET` filters because URLs do not carry native booleans.

### `property_status`

- Serialized as `property_status`.
- Also serialized as `status` for legacy compatibility.
- Options are generated dynamically from model selection metadata by `GET /api/v1/properties/options`.

### `property_situation`

- Serialized as explicit stored value when present.
- If stored value is empty/false, API response derives a display value from `property_status`.
- The fallback is response-only and does not persist a value to the database.

Fallback table:

| Source status | Response situation |
|---|---|
| `available` | `Desocupado` |
| `occupied` | `Ocupado` |
| `rented` | `Ocupado` |
| `reserved` | `Reservado` |
| `sold` | `Ocupado` |
| `under_construction` | `Em construção` |
| `maintenance` | `Não Informado` |
| missing/unknown | `Não Informado` |

## Options Endpoint

`GET /api/v1/properties/options` is backed by `controllers/utils/property_options.py`.

It returns options for these property selection fields:

- `source_medium`
- `zoning`
- `property_purpose`
- `property_status`
- `property_situation`
- `condition`
- `activity_notification`
- `sign_type`

## Migration Notes

Changing `property_situation` from `fields.Char` to `fields.Selection` is compatible with existing rows only when stored values match one of the allowed options or are empty.

If production data contains arbitrary values, a pre-migration cleanup should map legacy strings into the allowed values before upgrading the module.
