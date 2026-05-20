# -*- coding: utf-8 -*-
ESTATE_ROLE_MAP = (
    ("quicksol_estate.group_real_estate_owner", "owner"),
    ("quicksol_estate.group_real_estate_director", "director"),
    ("quicksol_estate.group_real_estate_manager", "manager"),
    ("quicksol_estate.group_real_estate_agent", "agent"),
    ("quicksol_estate.group_real_estate_prospector", "prospector"),
    ("quicksol_estate.group_real_estate_receptionist", "receptionist"),
    ("quicksol_estate.group_real_estate_financial", "financial"),
    ("quicksol_estate.group_real_estate_legal", "legal"),
    ("quicksol_estate.group_real_estate_property_owner", "property_owner"),
    ("quicksol_estate.group_real_estate_tenant", "tenant"),
    ("quicksol_estate.group_real_estate_portal_user", "tenant"),
)


def resolve_role(user):
    """Return the first matching estate role label for the user, or None."""
    if not user:
        return None

    for xml_id, role_name in ESTATE_ROLE_MAP:
        try:
            if user.has_group(xml_id):
                return role_name
        except Exception:
            continue

    return None
