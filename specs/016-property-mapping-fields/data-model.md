# Data Model: Property Mapping Fields API Completion

## Property Field Mapping

| API field | Storage | Type/default | Notes |
|---|---|---|---|
| `owner_email` | `owner_email` | char/null | Direct property-level owner contact value. |
| `owner_home_phone` | `owner_home_phone` | char/null | Direct property-level owner contact value. |
| `owner_business_phone` | `owner_business_phone` | char/null | Direct property-level owner contact value. |
| `owner_mobile_phone` | `owner_mobile_phone` | char/null | Direct property-level owner contact value. |
| `source_medium` | `origin_media` | selection/null | Existing source/origin field. |
| `send_activities_to_owner` | `send_activities_to_owner` | boolean/false | Direct boolean because existing `activity_notification` is a tri-state selection. |
| `search_street` | `street` | char/null | Existing address street field. |
| `registered_by` | `registered_by` | char/null | Direct form value. |
| `alternative_reference` | `alternative_reference` | char/null | Direct form value; does not replace generated `reference_code`. |
| `intention` | `intention` | char/null | Direct form value; does not replace `for_sale`/`for_rent`. |
| `iptu_payment_condition` | `iptu_payment_condition` | char/null | Direct form value. |
| `iptu_value` | `iptu_value` | char/null | Direct form value; does not replace monetary IPTU fields. |
| `rental_guarantee_insurance` | `rental_guarantee_insurance` | char/null | Direct form value. |
| `fire_insurance` | `fire_insurance` | char/null | Direct form value; does not replace `insurance_value`. |
| `exclusivity` | `exclusivity` | boolean/false | Direct form value. |
| `property_situation` | `property_situation` | char/null | Direct form value; does not replace status/condition. |
| `year_of_renovation` | `reform_year` | char/null in API | Existing integer field serialized as string. |
| `zoning` | `zoning_type` | selection/null | Existing zoning field. |
| `internal_comments` | `internal_notes` | text/null | Existing confidential notes field. |
| `tags` | `tag_ids` | array/[] | Existing M2M. |
| `key_location` | `key_location` | char/null | Direct form value; does not mutate key records. |
| `property_images` | `photo_ids` | array/[] | Existing photo records, response metadata only. |
| `advertise` | `publish_website` | boolean/false | Existing web publishing field. |
| `featured_property` | `publish_featured` | boolean/false | Existing web publishing field. |
| `virtual_tour` | `virtual_tour_url` | char/null | Existing web publishing field. |
| `sign_on_site` | `has_sign` | boolean/false | Existing sign field. |
| `super_featured` | `publish_super_featured` | boolean/false | Existing web publishing field. |
| `youtube_video` | `youtube_video_url` | char/null | Existing web publishing field. |
| `commission_type` | `commission_type` | char/null | Direct form value; does not replace commission line records. |
| `captured_intention` | `captured_intention` | char/null | Direct form value. |
| `included_in_commission_date` | `included_in_commission_date` | date/null | ISO date. |
| `commercial_condition` | `commercial_condition` | char/null | Direct free-text form value; only the string type is validated. |
| `iptu_code` | `iptu_code` | char/null | Existing documentation field. |
| `registration_number` | `matricula_number` | char/null | Existing documentation field. |
| `electricity_network_code` | `electricity_network_code` | char/null | Direct form value. |
| `water_network_code` | `water_network_code` | char/null | Direct form value. |
| `titles_rights` | `titles_rights` | char/null | Direct form value. |
| `approved_environmental_agency` | `approved_environmental_agency` | boolean/false | Direct form value. |
| `approved_project` | `approved_project` | boolean/false | Direct form value. |
| `documentation_observations` | `documentation_observations` | text/null | Direct form value. |
| `property_files` | `document_ids` | array/[] | Existing document records, response metadata only. |

## Attachment Metadata

Image and file responses expose:

```json
{
  "id": 1,
  "name": "fachada.jpg",
  "mimetype": "image/jpeg",
  "size": 12345,
  "download_url": "/web/content/real.estate.property.photo/1/image?download=true"
}
```

Binary fields are never returned inline.
