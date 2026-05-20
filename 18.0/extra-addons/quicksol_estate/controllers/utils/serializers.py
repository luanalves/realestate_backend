# -*- coding: utf-8 -*-
import base64
import mimetypes
import re
from datetime import date


def serialize_property(property_record):

    if not property_record:
        return None

    property_status = property_record.property_status or "available"

    return {
        "id": property_record.id,
        "name": property_record.name or "",
        "description": property_record.description or "",
        "price": float(property_record.price) if property_record.price else 0.0,
        "price_formatted": (
            f"R$ {property_record.price:,.2f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
            if property_record.price
            else "R$ 0,00"
        ),
        "status": property_status,
        "property_status": property_status,
        "for_sale": bool(property_record.for_sale),
        "for_rent": bool(property_record.for_rent),
        "property_type": (
            {
                "id": property_record.property_type_id.id,
                "name": property_record.property_type_id.name,
            }
            if property_record.property_type_id
            else None
        ),
        "agent": (
            {
                "id": property_record.agent_id.id,
                "name": property_record.agent_id.name,
                "email": property_record.agent_id.email or "",
            }
            if property_record.agent_id
            else None
        ),
        "owner": serialize_property_owner(property_record),
        "company": {
            "id": property_record.company_id.id if property_record.company_id else None,
            "name": (
                property_record.company_id.name if property_record.company_id else None
            ),
        },
        "address": {
            "street": property_record.street or "",
            "number": property_record.street_number or "",
            "complement": property_record.complement or "",
            "neighborhood": property_record.neighborhood or "",
            "city": property_record.city or "",
            "state": (
                {
                    "id": property_record.state_id.id,
                    "name": property_record.state_id.name,
                    "code": property_record.state_id.code,
                }
                if property_record.state_id
                else None
            ),
            "zip_code": property_record.zip_code or "",
            "location_type": (
                {
                    "id": property_record.location_type_id.id,
                    "name": property_record.location_type_id.name,
                    "code": property_record.location_type_id.code,
                }
                if property_record.location_type_id
                else None
            ),
        },
        "features": {
            "bedrooms": property_record.num_rooms or 0,
            "suites": property_record.num_suites or 0,
            "bathrooms": property_record.num_bathrooms or 0,
            "parking_spaces": property_record.num_parking or 0,
            "area": float(property_record.area) if property_record.area else 0.0,
            "total_area": (
                float(property_record.total_area) if property_record.total_area else 0.0
            ),
        },
        "created_date": (
            property_record.create_date.isoformat()
            if property_record.create_date
            else None
        ),
        "updated_date": (
            property_record.write_date.isoformat()
            if property_record.write_date
            else None
        ),
        **serialize_property_mapping_fields(property_record),
    }


def serialize_property_owner(property_record):
    owner = getattr(property_record, "owner_id", False)
    if not owner:
        return None

    partner = getattr(owner, "partner_id", False)
    state = getattr(owner, "state_id", False)

    return {
        "id": owner.id,
        "name": owner.name or "",
        "email": owner.email or "",
        "phone": owner.phone or "",
        "mobile": owner.mobile or "",
        "whatsapp": owner.whatsapp or "",
        "partner_id": partner.id if partner else None,
        "address": owner.address or "",
        "city": owner.city or "",
        "state": (
            {
                "id": state.id,
                "name": state.name,
                "code": state.code,
            }
            if state
            else None
        ),
        "zip_code": owner.zip_code or "",
    }


PROPERTY_MAPPING_SCALAR_FIELDS = {
    "source_medium": ("origin_media", "string"),
    "send_activities_to_owner": ("send_activities_to_owner", "boolean"),
    "search_street": ("street", "string"),
    "registered_by": ("registered_by", "string"),
    "alternative_reference": ("alternative_reference", "string"),
    "intention": ("intention", "string"),
    "iptu_payment_condition": ("iptu_payment_condition", "string"),
    "iptu_value": ("iptu_value", "string"),
    "rental_guarantee_insurance": ("rental_guarantee_insurance", "string"),
    "fire_insurance": ("fire_insurance", "string"),
    "exclusivity": ("exclusivity", "boolean"),
    "accepts_financing": ("accepts_financing", "boolean"),
    "property_situation": ("property_situation", "string"),
    "year_of_renovation": ("reform_year", "integer_string"),
    "zoning": ("zoning_type", "string"),
    "internal_comments": ("internal_notes", "string"),
    "key_location": ("key_location", "string"),
    "advertise": ("publish_website", "boolean"),
    "featured_property": ("publish_featured", "boolean"),
    "virtual_tour": ("virtual_tour_url", "string"),
    "sign_on_site": ("has_sign", "boolean"),
    "super_featured": ("publish_super_featured", "boolean"),
    "youtube_video": ("youtube_video_url", "string"),
    "commission_type": ("commission_type", "string"),
    "captured_intention": ("captured_intention", "string"),
    "included_in_commission_date": ("included_in_commission_date", "date"),
    "commercial_condition": ("commercial_condition", "string"),
    "iptu_code": ("iptu_code", "string"),
    "registration_number": ("matricula_number", "string"),
    "electricity_network_code": ("electricity_network_code", "string"),
    "water_network_code": ("water_network_code", "string"),
    "titles_rights": ("titles_rights", "string"),
    "approved_environmental_agency": ("approved_environmental_agency", "boolean"),
    "approved_project": ("approved_project", "boolean"),
    "documentation_observations": ("documentation_observations", "string"),
}

PROPERTY_MAPPING_COLLECTION_FIELDS = {"tags", "property_images", "property_files"}
FGTS_TOP_LEVEL_FIELDS = {
    "accepts_fgts",
    "used_fgts",
    "fgts_last_usage_date",
    "fgts_eligible_from",
    "fgts_eligible_now",
    "fgts_usage_notes",
}
FGTS_INPUT_FIELDS = {
    "accepts_fgts": ("accepts_fgts", "boolean"),
    "used_fgts": ("used_fgts", "boolean"),
    "last_usage_date": ("fgts_last_usage_date", "date"),
    "usage_notes": ("fgts_usage_notes", "string"),
}
FGTS_READ_ONLY_FIELDS = {"eligible_from", "eligible_now"}
LEGACY_PROPERTY_OWNER_FIELDS = {
    "owner",
    "owner_email",
    "owner_home_phone",
    "owner_business_phone",
    "owner_mobile_phone",
}
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PROPERTY_SITUATION_FALLBACKS = {
    "available": "Desocupado",
    "occupied": "Ocupado",
    "rented": "Ocupado",
    "reserved": "Reservado",
    "sold": "Ocupado",
    "under_construction": "Em construção",
    "maintenance": "Não Informado",
}


def serialize_property_mapping_fields(property_record):
    result = {}

    for api_field, (odoo_field, field_type) in PROPERTY_MAPPING_SCALAR_FIELDS.items():
        value = getattr(property_record, odoo_field, False)
        if field_type == "boolean":
            result[api_field] = bool(value)
        elif field_type == "date":
            result[api_field] = value.isoformat() if value else None
        elif field_type == "integer_string":
            result[api_field] = str(value) if value not in (False, None, 0) else None
        else:
            result[api_field] = value or None

    if not result["property_situation"]:
        property_status = getattr(property_record, "property_status", False)
        result["property_situation"] = PROPERTY_SITUATION_FALLBACKS.get(
            property_status,
            "Não Informado",
        )

    fgts_eligible_from = (
        property_record.fgts_eligible_from.isoformat()
        if getattr(property_record, "fgts_eligible_from", False)
        else None
    )
    result["fgts"] = {
        "accepts_fgts": bool(getattr(property_record, "accepts_fgts", False)),
        "used_fgts": bool(getattr(property_record, "used_fgts", False)),
        "last_usage_date": (
            property_record.fgts_last_usage_date.isoformat()
            if getattr(property_record, "fgts_last_usage_date", False)
            else None
        ),
        "eligible_from": fgts_eligible_from,
        "eligible_now": bool(getattr(property_record, "fgts_eligible_now", False)),
        "usage_notes": getattr(property_record, "fgts_usage_notes", False) or None,
    }

    result["tags"] = [tag.name for tag in property_record.tag_ids if tag.name]

    # Batch-fetch ir.attachment IDs for legacy photo/document records (T021)
    # Both Binary fields use attachment=True, so Odoo stores them in ir.attachment.
    # We look up those attachment IDs to build /api/v1/ download URLs.
    Attachment = property_record.env["ir.attachment"].sudo()

    photo_atts = Attachment.search(
        [
            ("res_model", "=", "real.estate.property.photo"),
            ("res_id", "in", property_record.photo_ids.ids),
            ("res_field", "=", "image"),
        ]
    )
    photo_att_map = {att.res_id: att.id for att in photo_atts}

    doc_atts = Attachment.search(
        [
            ("res_model", "=", "real.estate.property.document"),
            ("res_id", "in", property_record.document_ids.ids),
            ("res_field", "=", "file"),
        ]
    )
    doc_att_map = {att.res_id: att.id for att in doc_atts}

    result["property_images"] = [
        _serialize_binary_metadata(
            photo,
            photo.name,
            photo.image,
            (
                f"/api/v1/properties/{property_record.id}/attachments/{photo_att_map[photo.id]}/download"
                if photo.id in photo_att_map
                else None
            ),
        )
        for photo in property_record.photo_ids
    ]
    result["property_files"] = [
        _serialize_binary_metadata(
            document,
            document.file_name or document.name,
            document.file,
            (
                f"/api/v1/properties/{property_record.id}/attachments/{doc_att_map[document.id]}/download"
                if document.id in doc_att_map
                else None
            ),
        )
        for document in property_record.document_ids
    ]

    return result


def _serialize_binary_metadata(record, name, binary_value, download_url):
    return {
        "id": record.id,
        "name": name or record.display_name or "",
        "mimetype": mimetypes.guess_type(name or "")[0] or "application/octet-stream",
        "size": _binary_size(binary_value),
        "download_url": download_url,
    }


def _binary_size(binary_value):
    if not binary_value:
        return 0
    if isinstance(binary_value, bytes):
        binary_value = binary_value.decode("ascii")
    try:
        return len(base64.b64decode(binary_value))
    except Exception:
        return 0


def build_property_mapping_values(data):
    vals = {}
    errors = []

    for field in sorted(LEGACY_PROPERTY_OWNER_FIELDS):
        if field in data:
            errors.append(
                {
                    "field": field,
                    "message": "Use owner_id to link a property owner",
                }
            )

    for field in sorted(FGTS_TOP_LEVEL_FIELDS):
        if field in data:
            errors.append(
                {
                    "field": field,
                    "message": "Use fgts object to send FGTS data",
                }
            )

    for api_field, (odoo_field, field_type) in PROPERTY_MAPPING_SCALAR_FIELDS.items():
        if api_field not in data:
            continue

        value = data.get(api_field)
        normalized, error = _normalize_property_mapping_value(
            api_field, value, field_type
        )
        if error:
            errors.append(error)
            continue
        vals[odoo_field] = normalized

    if "fgts" in data:
        fgts_vals, fgts_errors = _normalize_fgts_values(data["fgts"])
        errors.extend(fgts_errors)
        vals.update(fgts_vals)

    for field in PROPERTY_MAPPING_COLLECTION_FIELDS:
        if field in data and not isinstance(data[field], list):
            errors.append(
                {
                    "field": field,
                    "message": "Must be an array",
                }
            )

    return vals, errors


def _normalize_fgts_values(value):
    if value in (None, ""):
        return {
            "accepts_fgts": False,
            "used_fgts": False,
            "fgts_last_usage_date": False,
            "fgts_usage_notes": False,
        }, []

    if not isinstance(value, dict):
        return {}, [
            {
                "field": "fgts",
                "message": "Must be an object",
            }
        ]

    vals = {}
    errors = []

    for field in sorted(FGTS_READ_ONLY_FIELDS):
        if field in value:
            errors.append(
                {
                    "field": f"fgts.{field}",
                    "message": "Read-only field",
                }
            )

    for api_field, (odoo_field, field_type) in FGTS_INPUT_FIELDS.items():
        if api_field not in value:
            continue

        normalized, error = _normalize_property_mapping_value(
            f"fgts.{api_field}",
            value.get(api_field),
            field_type,
        )
        if error:
            errors.append(error)
            continue
        vals[odoo_field] = normalized

    return vals, errors


def _normalize_property_mapping_value(api_field, value, field_type):
    if value in (None, ""):
        if field_type == "boolean":
            return False, None
        return False, None

    if field_type == "boolean":
        if isinstance(value, bool):
            return value, None
        return None, {
            "field": api_field,
            "message": "Must be a boolean",
        }

    if field_type == "email":
        if not isinstance(value, str) or not EMAIL_REGEX.match(value.strip()):
            return None, {
                "field": api_field,
                "message": "Must be a valid email",
            }
        return value.strip().lower(), None

    if field_type == "date":
        if not isinstance(value, str):
            return None, {
                "field": api_field,
                "message": "Must be an ISO date string",
            }
        try:
            return date.fromisoformat(value), None
        except ValueError:
            return None, {
                "field": api_field,
                "message": "Must be an ISO date string",
            }

    if field_type == "integer_string":
        try:
            return int(value), None
        except (TypeError, ValueError):
            return None, {
                "field": api_field,
                "message": "Must be a numeric year",
            }

    if not isinstance(value, str):
        return None, {
            "field": api_field,
            "message": "Must be a string",
        }

    return value, None


def apply_property_mapping_relations(property_record, data):
    errors = []

    if "tags" in data:
        tag_ids, tag_errors = _resolve_property_tags(property_record.env, data["tags"])
        errors.extend(tag_errors)
        if not tag_errors:
            property_record.write({"tag_ids": [(6, 0, tag_ids)]})

    if "property_images" in data:
        errors.extend(
            _replace_property_images(property_record, data["property_images"])
        )

    if "property_files" in data:
        errors.extend(_replace_property_files(property_record, data["property_files"]))

    return errors


def _resolve_property_tags(env, tags):
    if not isinstance(tags, list):
        return [], [{"field": "tags", "message": "Must be an array"}]

    tag_ids = []
    errors = []
    Tag = env["real.estate.property.tag"].sudo()

    for item in tags:
        if isinstance(item, int):
            tag = Tag.browse(item)
            if not tag.exists():
                errors.append(
                    {"field": "tags", "message": f"Tag ID {item} does not exist"}
                )
                continue
        elif isinstance(item, str):
            tag_name = item.strip()
            if not tag_name:
                continue
            tag = Tag.search([("name", "=ilike", tag_name)], limit=1)
            if not tag:
                tag = Tag.create({"name": tag_name})
        else:
            errors.append(
                {"field": "tags", "message": "Tags must contain strings or IDs"}
            )
            continue

        if tag.id not in tag_ids:
            tag_ids.append(tag.id)

    return tag_ids, errors


def _replace_property_images(property_record, images):
    if not isinstance(images, list):
        return [{"field": "property_images", "message": "Must be an array"}]

    normalized_images = []
    for index, image in enumerate(images):
        if not isinstance(image, dict):
            return [{"field": "property_images", "message": "Items must be objects"}]
        if not image.get("image"):
            return [
                {
                    "field": f"property_images[{index}].image",
                    "message": "Image content is required",
                }
            ]
        normalized_images.append(image)

    property_record.photo_ids.unlink()
    Photo = property_record.env["real.estate.property.photo"].sudo()
    for index, image in enumerate(normalized_images):
        Photo.create(
            {
                "property_id": property_record.id,
                "name": image.get("name")
                or image.get("file_name")
                or f"property-image-{index + 1}",
                "image": image["image"],
                "description": image.get("description"),
                "is_main": (
                    bool(image.get("is_main"))
                    if isinstance(image.get("is_main"), bool)
                    else False
                ),
                "sequence": (
                    image.get("sequence")
                    if isinstance(image.get("sequence"), int)
                    else 10
                ),
            }
        )

    return []


def _replace_property_files(property_record, files):
    if not isinstance(files, list):
        return [{"field": "property_files", "message": "Must be an array"}]

    normalized_files = []
    for index, file_data in enumerate(files):
        if not isinstance(file_data, dict):
            return [{"field": "property_files", "message": "Items must be objects"}]
        name = file_data.get("name") or file_data.get("file_name")
        if not name:
            return [
                {
                    "field": f"property_files[{index}].name",
                    "message": "Name is required",
                }
            ]
        if not file_data.get("file"):
            return [
                {
                    "field": f"property_files[{index}].file",
                    "message": "File content is required",
                }
            ]
        normalized_files.append((name, file_data))

    property_record.document_ids.unlink()
    Document = property_record.env["real.estate.property.document"].sudo()
    for name, file_data in normalized_files:
        Document.create(
            {
                "property_id": property_record.id,
                "name": name,
                "file_name": file_data.get("file_name") or name,
                "file": file_data.get("file"),
                "document_type": file_data.get("document_type") or "other",
                "description": file_data.get("description"),
            }
        )

    return []


def validate_property_access(property_record, user, operation="read"):

    # Admin has full access
    if user.has_group("base.group_system"):
        return True, None

    # Owner/Manager: access to properties of their companies
    if user.has_group("quicksol_estate.group_real_estate_owner") or user.has_group(
        "quicksol_estate.group_real_estate_manager"
    ):
        user_companies = set(user.company_ids.ids)
        property_company = (
            property_record.company_id.id if property_record.company_id else None
        )

        if property_company and property_company in user_companies:
            return True, None
        return False, "Property does not belong to your companies"

    # Agent: access only to properties they manage
    if user.has_group("quicksol_estate.group_real_estate_agent"):
        if operation == "delete":
            return False, "Agents cannot delete properties"

        if property_record.agent_id and property_record.agent_id.user_id == user:
            return True, None
        return False, "You can only access your own properties"

    # User: read/write access to properties of their companies
    if user.has_group("quicksol_estate.group_real_estate_user"):
        if operation == "delete":
            return False, "Users cannot delete properties"

        user_companies = set(user.company_ids.ids)
        property_company = (
            property_record.company_id.id if property_record.company_id else None
        )

        if property_company and property_company in user_companies:
            return True, None
        return False, "Property does not belong to your companies"

    # Portal users have no access
    return False, "Insufficient permissions"
