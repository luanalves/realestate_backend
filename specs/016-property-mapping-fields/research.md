# Research: Property Mapping Fields API Completion

## Decisions

### D001 - Scope stays in `quicksol_estate`

**Decision**: Implement the feature in the existing `quicksol_estate` addon.

**Rationale**: The affected model (`real.estate.property`) and endpoints already live there. Creating a new addon would add manifest/security complexity without a domain boundary benefit.

### D002 - Reuse existing property relations for collections

**Decision**: Map:

- `tags` -> `tag_ids`
- `property_images` -> `photo_ids`
- `property_files` -> `document_ids`

**Rationale**: These relations already represent the form sections and avoid duplicate storage. API responses will expose metadata only and will not inline binary data.

### D003 - Use API aliases for existing scalar fields when semantics match

**Decision**: Map these API fields to existing model fields:

- `source_medium` -> `origin_media`
- `search_street` -> `street`
- `year_of_renovation` -> `reform_year`
- `zoning` -> `zoning_type`
- `internal_comments` -> `internal_notes`
- `advertise` -> `publish_website`
- `featured_property` -> `publish_featured`
- `virtual_tour` -> `virtual_tour_url`
- `sign_on_site` -> `has_sign`
- `super_featured` -> `publish_super_featured`
- `youtube_video` -> `youtube_video_url`
- `iptu_code` -> `iptu_code`
- `registration_number` -> `matricula_number`

**Rationale**: The current model already has fields with matching business meaning.

### D004 - Add direct fields for unmatched concepts

**Decision**: Add direct fields on `real.estate.property` for missing scalar concepts that do not have a safe existing target.

**Rationale**: Some spreadsheet fields represent specific form data that cannot be derived from current relations without destructive or ambiguous side effects.

### D005 - Unknown payload fields remain ignored

**Decision**: Preserve current create/update behavior: unsupported keys are ignored unless they target protected fields such as `company_ids`.

**Rationale**: Current endpoints build whitelisted values and ignore unrelated keys. This aligns with ADR-018 when the behavior is documented and avoids breaking existing clients.

### D006 - Tags accept strings and IDs

**Decision**: `tags` accepts an array of strings or integers. String tags are resolved case-insitively where possible and created when absent; integer tags behave like `tag_ids`.

**Rationale**: The spreadsheet API field is `array[string]`, while the existing Odoo relation is Many2many. Accepting IDs keeps backward compatibility with existing integrations.

### D007 - Attachment create/update is metadata-first

**Decision**: For this implementation, `property_images` and `property_files` responses return metadata. Requests accept arrays of metadata objects only when enough existing model data is supplied to create records; omitted arrays do not clear existing records.

**Rationale**: Binary upload format is not defined in the spreadsheet. Returning metadata satisfies the read contract without introducing a new binary transport convention.
