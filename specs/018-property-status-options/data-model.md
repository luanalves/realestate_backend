# Data Model: Property Status and Situation Options

## Entity: `real.estate.property`

### Existing Fields Used

| Field | Type | Required | Default | API exposure | Notes |
|---|---|---:|---|---|---|
| `for_sale` | Boolean | no | `True` | `for_sale` | Indicates the property is offered for sale. |
| `for_rent` | Boolean | no | `False` | `for_rent` | Indicates the property is offered for rent. |
| `property_status` | Selection | yes | `available` | `property_status`, `status` | Canonical operational status. `status` is a legacy alias in API response. |
| `property_situation` | Selection | no | `Não Informado` | `property_situation` | User-facing situation label for app/UI selectors. |
| `commercial_condition` | Char | no | empty | `commercial_condition` | Free-text commercial condition. This replaced the ambiguous `standard` naming in property API interfaces. |
| `fgts.accepts_fgts` | Boolean | no | `False` | `accepts_fgts` | Indicates the property accepts FGTS in the negotiation. |
| `fgts.used_fgts` | Boolean | no | `False` | `used_fgts` | Indicates known previous FGTS use for this property. |
| `fgts.last_usage_date` | Date | no | empty | `fgts_last_usage_date` | Registry/reference date of the last known FGTS use. |
| `fgts.eligible_from` | Computed Date | no | computed | `fgts_eligible_from` | First date when FGTS may be used again. |
| `fgts.eligible_now` | Computed Boolean | no | computed | `fgts_eligible_now` | Whether the property is currently outside the 3-year restriction window. |
| `fgts.usage_notes` | Text | no | empty | `fgts_usage_notes` | Optional review notes from registration/certificate analysis. |
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

### `commercial_condition`

- Serialized as `commercial_condition`.
- Written by sending `commercial_condition` in `POST /api/v1/properties` or `PUT /api/v1/properties/{id}`.
- It is not a relationship field and is not selected from `/api/v1/properties/options`.
- It accepts a JSON string with the commercial condition text.
- It accepts `null` or an empty string to clear the stored value.
- It rejects arrays, objects, numbers, and booleans with `400 Bad Request`.

Accepted examples:

| Payload value | Result |
|---|---|
| `"Condição comercial padrão"` | Accepted and stored as sent. |
| `"Aceita financiamento"` | Accepted and stored as sent. |
| `"Venda à vista ou financiamento bancário"` | Accepted and stored as sent. |
| `""` | Accepted and clears the value. |
| `null` | Accepted and clears the value. |

Rejected examples:

| Payload value | Reason |
|---|---|
| `["Condição comercial padrão"]` | Must be a string. |
| `{"value": "Condição comercial padrão"}` | Must be a string. |
| `123` | Must be a string. |
| `true` | Must be a string. |

### FGTS Fields

The existing Odoo field `accepts_fgts` is exposed through `fgts.accepts_fgts` and means the property accepts FGTS as a payment/negotiation option.

The new FGTS usage fields summarize whether the same property is known to have used FGTS in a previous acquisition/construction transaction. Official CAIXA/FGTS rules use a 3-year property-side interval counted from the registry/reference date, so the API stores a single current summary instead of a multi-item history.

- `fgts.used_fgts` is written as a JSON boolean.
- `fgts.last_usage_date` is written as an ISO date string (`YYYY-MM-DD`) or cleared with `null`/`""`.
- `fgts.usage_notes` is written as a string or cleared with `null`/`""`.
- `fgts.eligible_from` is read-only and computed as `fgts.last_usage_date + 3 years + 1 day`.
- `fgts.eligible_now` is read-only.
- The response returns these fields only once inside the `fgts` object, matching the grouped shape used by `owner`.

Example response fragment:

```json
{
  "fgts": {
    "accepts_fgts": true,
    "used_fgts": true,
    "last_usage_date": "2024-03-10",
    "eligible_from": "2027-03-11",
    "eligible_now": false,
    "usage_notes": "Uso identificado na matricula anterior"
  }
}
```

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
