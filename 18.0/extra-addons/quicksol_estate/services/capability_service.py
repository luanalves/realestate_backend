# -*- coding: utf-8 -*-
ALLOWED_ACTIONS = (
    "view",
    "create",
    "update",
    "delete",
    "reassign",
    "approve",
    "cancel",
    "export",
)

ALLOWED_SUBJECTS = (
    "MenuCRM",
    "MenuAdmin",
    "MenuCMS",
    "Dashboard",
    "Property",
    "Lead",
    "Service",
    "Proposal",
    "Agent",
    "Company",
    "Settings",
    "Appointment",
    "Report",
    "Goal",
    "CMSPage",
    "CMSMedia",
)

# Canonical contract order lives in declaration order:
# subject order = MenuCRM → MenuAdmin → MenuCMS → Dashboard → Property → Lead
# → Service → Proposal → Agent → Company → Settings → Appointment → Report
# → Goal → CMSPage → CMSMedia
# action order within each subject = view → create → update → delete
# → reassign → approve → cancel → export
ROLE_RULES = {
    "owner": [
        ("view", "MenuCRM"),
        ("view", "MenuAdmin"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        ("update", "Property"),
        ("delete", "Property"),
        ("view", "Lead"),
        ("create", "Lead"),
        ("update", "Lead"),
        ("delete", "Lead"),
        ("reassign", "Lead"),
        ("view", "Service"),
        ("create", "Service"),
        ("update", "Service"),
        ("delete", "Service"),
        ("reassign", "Service"),
        ("cancel", "Service"),
        ("view", "Proposal"),
        ("create", "Proposal"),
        ("update", "Proposal"),
        ("delete", "Proposal"),
        ("approve", "Proposal"),
        ("cancel", "Proposal"),
        ("view", "Agent"),
        ("create", "Agent"),
        ("update", "Agent"),
        ("delete", "Agent"),
        ("view", "Company"),
        ("update", "Company"),
        ("view", "Settings"),
        ("update", "Settings"),
        ("view", "Report"),
        ("export", "Report"),
        ("view", "Goal"),
    ],
    "director": [
        ("view", "MenuCRM"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        ("update", "Property"),
        ("view", "Lead"),
        ("create", "Lead"),
        ("update", "Lead"),
        ("reassign", "Lead"),
        ("view", "Service"),
        ("create", "Service"),
        ("update", "Service"),
        ("reassign", "Service"),
        ("cancel", "Service"),
        ("view", "Proposal"),
        ("create", "Proposal"),
        ("update", "Proposal"),
        ("approve", "Proposal"),
        ("cancel", "Proposal"),
        ("view", "Agent"),
        ("update", "Agent"),
        ("view", "Company"),
        ("view", "Report"),
        ("export", "Report"),
        ("view", "Goal"),
    ],
    "manager": [
        ("view", "MenuCRM"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        ("update", "Property"),
        ("view", "Lead"),
        ("create", "Lead"),
        ("update", "Lead"),
        ("reassign", "Lead"),
        ("view", "Service"),
        ("create", "Service"),
        ("update", "Service"),
        ("reassign", "Service"),
        ("cancel", "Service"),
        ("view", "Proposal"),
        ("create", "Proposal"),
        ("update", "Proposal"),
        ("approve", "Proposal"),
        ("cancel", "Proposal"),
        ("view", "Agent"),
        ("update", "Agent"),
        ("view", "Company"),
        ("view", "Report"),
        ("export", "Report"),
        ("view", "Goal"),
    ],
    "agent": [
        ("view", "MenuCRM"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        ("update", "Property"),
        ("view", "Lead"),
        ("create", "Lead"),
        ("update", "Lead"),
        ("view", "Service"),
        ("create", "Service"),
        ("update", "Service"),
        ("cancel", "Service"),
        ("view", "Proposal"),
        ("create", "Proposal"),
        ("update", "Proposal"),
        ("cancel", "Proposal"),
        ("view", "Goal"),
    ],
    "prospector": [
        ("view", "MenuCRM"),
        ("view", "Dashboard"),
        ("view", "Property"),
        ("create", "Property"),
        ("update", "Property"),
    ],
    "receptionist": [
        ("view", "MenuCRM"),
        ("view", "Property"),
        ("view", "Service"),
        ("create", "Service"),
        ("view", "Proposal"),
    ],
    "financial": [
        ("view", "MenuCRM"),
        ("view", "Property"),
        ("view", "Service"),
        ("view", "Proposal"),
        ("view", "Company"),
        ("view", "Report"),
        ("export", "Report"),
    ],
    "legal": [
        ("view", "MenuCRM"),
        ("view", "Property"),
        ("view", "Service"),
        ("view", "Proposal"),
        ("view", "Company"),
    ],
    "property_owner": [
        ("view", "Property"),
        ("view", "Proposal"),
    ],
    "tenant": [
        ("view", "Property"),
        ("view", "Proposal"),
    ],
}


class CapabilityService:
    """Project allowed frontend capabilities from resolved role labels."""

    def __init__(self, env=None):
        self.env = env

    def get_rules(self, role):
        """Return ordered, deduplicated safe rules for the given role."""
        if not role:
            return []

        declared_rules = ROLE_RULES.get(role, [])
        seen = set()
        serialized = []

        for action, subject in declared_rules:
            if action not in ALLOWED_ACTIONS or subject not in ALLOWED_SUBJECTS:
                continue

            pair = (action, subject)
            if pair in seen:
                continue

            seen.add(pair)
            serialized.append(
                {
                    "action": action,
                    "subject": subject,
                }
            )

        return serialized

    def build_payload(self, user, role, company_id):
        """Build the exact response contract for the capabilities endpoint."""
        return {
            "user": {
                "id": user.id,
                "role": role,
                "company_id": company_id,
            },
            "rules": self.get_rules(role),
        }
