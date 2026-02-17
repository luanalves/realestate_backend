# -*- coding: utf-8 -*-

import logging
from odoo import _
from odoo.exceptions import UserError, ValidationError
from validate_docbr import CPF

_logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations"""

    # Authorization Matrix (R11): Who can invite which profiles
    INVITE_AUTHORIZATION = {
        "quicksol_estate.group_real_estate_owner": [
            "owner",
            "director",
            "manager",
            "agent",
            "prospector",
            "receptionist",
            "financial",
            "legal",
            "portal",
        ],
        "quicksol_estate.group_real_estate_director": [
            "agent",
            "prospector",
            "receptionist",
            "financial",
            "legal",
        ],
        "quicksol_estate.group_real_estate_manager": [
            "agent",
            "prospector",
            "receptionist",
            "financial",
            "legal",
        ],
        "quicksol_estate.group_real_estate_agent": ["owner", "portal"],
    }

    # Profile to Odoo Group Mapping (R11)
    PROFILE_TO_GROUP = {
        "owner": "quicksol_estate.group_real_estate_owner",
        "director": "quicksol_estate.group_real_estate_director",
        "manager": "quicksol_estate.group_real_estate_manager",
        "agent": "quicksol_estate.group_real_estate_agent",
        "prospector": "quicksol_estate.group_real_estate_prospector",
        "receptionist": "quicksol_estate.group_real_estate_receptionist",
        "financial": "quicksol_estate.group_real_estate_financial",
        "legal": "quicksol_estate.group_real_estate_legal",
        "portal": "base.group_portal",
    }

    def __init__(self, env):
        self.env = env

    def check_authorization(self, requester_user, target_profile):

        # Get requester's group IDs
        requester_group_ids = requester_user.groups_id.ids

        # Check each authorization rule
        for group_xml_id, allowed_profiles in self.INVITE_AUTHORIZATION.items():
            group = self.env.ref(group_xml_id, raise_if_not_found=False)
            if group and group.id in requester_group_ids:
                if target_profile in allowed_profiles:
                    return True

        # Not authorized
        raise UserError(
            _(
                "You do not have permission to invite {} profile. "
                "Contact your administrator for assistance."
            ).format(target_profile)
        )

    def create_invited_user(
        self, name, email, document, profile, company, created_by, **extra_fields
    ):

        # Validate document (CPF for non-portal profiles)
        if profile != "portal":
            self._validate_cpf(document)

        # Check email uniqueness
        existing_email = (
            self.env["res.users"].sudo().search([("login", "=", email)], limit=1)
        )
        if existing_email:
            raise ValidationError(_("Email already exists: {}").format(email))

        # Check document uniqueness
        if profile != "portal":
            existing_cpf = (
                self.env["res.users"].sudo().search([("cpf", "=", document)], limit=1)
            )
            if existing_cpf:
                raise ValidationError(_("CPF already exists: {}").format(document))

        # Get target group
        group_xml_id = self.PROFILE_TO_GROUP.get(profile)
        if not group_xml_id:
            raise ValidationError(_("Invalid profile: {}").format(profile))

        target_group = self.env.ref(group_xml_id)

        # Prepare user data
        user_vals = {
            "name": name,
            "login": email,
            "email": email,
            # No password field - user cannot login until password is set via invite link
            "signup_pending": True,  # Waiting for invite link
            "groups_id": [(6, 0, [target_group.id])],
            "estate_company_ids": [(4, company.id)] if hasattr(company, "id") else [],
        }

        # Add CPF for non-portal profiles
        if profile != "portal":
            user_vals["cpf"] = document

        # Add extra fields
        if extra_fields.get("phone"):
            user_vals["phone"] = extra_fields["phone"]
        if extra_fields.get("mobile"):
            user_vals["mobile"] = extra_fields["mobile"]

        # Create user
        new_user = self.env["res.users"].sudo().create(user_vals)

        _logger.info(
            f"User invited: {email} (profile: {profile}) by {created_by.login}"
        )

        return new_user

    def create_portal_user(
        self,
        name,
        email,
        document,
        phone,
        birthdate,
        company_id,
        created_by,
        occupation=None,
    ):
        # Validate required fields
        if not phone:
            raise ValidationError(_("Phone is required for portal profile"))
        if not birthdate:
            raise ValidationError(_("Birthdate is required for portal profile"))
        if not company_id:
            raise ValidationError(_("Company ID is required for portal profile"))

        # Validate document (CPF or CNPJ for portal)
        self._validate_document_portal(document)

        # Check email uniqueness
        existing_email = (
            self.env["res.users"].sudo().search([("login", "=", email)], limit=1)
        )
        if existing_email:
            raise ValidationError(_("Email already exists: {}").format(email))

        # Check if document exists in tenant table without linked user (409 conflict)
        existing_tenant = (
            self.env["real.estate.tenant"]
            .sudo()
            .search([("document", "=", document)], limit=1)
        )
        if existing_tenant:
            linked_user = (
                self.env["res.users"]
                .sudo()
                .search([("partner_id", "=", existing_tenant.partner_id.id)], limit=1)
            )
            if not linked_user:
                raise ValidationError(
                    _(
                        "Document already registered for another tenant. "
                        "Please link the existing tenant to a user account manually."
                    )
                )

        # Get portal group
        portal_group = self.env.ref("quicksol_estate.group_real_estate_portal_user")

        # Step 1: Create res.users with portal group
        user_vals = {
            "name": name,
            "login": email,
            "email": email,
            # No password field - user cannot login until password is set via invite link
            "signup_pending": True,
            "groups_id": [(6, 0, [portal_group.id])],
        }

        user = self.env["res.users"].sudo().create(user_vals)

        # Step 2: Create real.estate.tenant linked via partner_id
        # Note: res.users.create() automatically creates res.partner
        company = self.env["thedevkitchen.estate.company"].sudo().browse(company_id)

        tenant_vals = {
            "name": name,
            "email": email,
            "document": document,
            "phone": phone,
            "birthdate": birthdate,
            "partner_id": user.partner_id.id,  # Link to auto-created partner
            "company_ids": [(4, company_id)],
        }

        if occupation:
            tenant_vals["occupation"] = occupation

        tenant = self.env["real.estate.tenant"].sudo().create(tenant_vals)

        _logger.info(
            f"Portal user + tenant created: {email} (tenant_id: {tenant.id}) "
            f"by {created_by.login}"
        )

        return user, tenant

    def send_invite_email(self, user, raw_token, expires_hours, frontend_base_url):
        try:
            # Get email template
            template = self.env.ref(
                "thedevkitchen_user_onboarding.email_template_user_invite"
            )

            # Construct invite link
            invite_link = f"{frontend_base_url}/set-password?token={raw_token}"

            # Prepare template context
            ctx = {
                "invite_link": invite_link,
                "expires_hours": expires_hours,
            }

            # Send email (async via Odoo mail queue)
            template.with_context(ctx).send_mail(
                user.id,
                force_send=False,  # Queue for async sending
                raise_exception=False,  # Don't block on email failure
            )

            _logger.info(f"Invite email sent to {user.email}")
            return True

        except Exception as e:
            _logger.error(f"Failed to send invite email to {user.email}: {e}")
            return False

    # Private helper methods

    def _validate_cpf(self, cpf):
        """Validate CPF using validate_docbr"""
        cpf_validator = CPF()
        cpf_clean = "".join(filter(str.isdigit, cpf))

        if not cpf_validator.validate(cpf_clean):
            raise ValidationError(
                _("Invalid CPF: {}. Must have 11 valid digits.").format(cpf)
            )

    def _validate_document_portal(self, document):

        document_clean = "".join(filter(str.isdigit, document))

        if len(document_clean) == 11:
            # CPF
            self._validate_cpf(document)
        elif len(document_clean) == 14:
            # CNPJ - Use existing quicksol_estate validator
            from ..utils import validators

            if hasattr(validators, "validate_cnpj"):
                if not validators.validate_cnpj(document):
                    raise ValidationError(_("Invalid CNPJ: {}").format(document))
            else:
                # Fallback: basic length check
                _logger.warning(
                    "CNPJ validation unavailable - using basic length check"
                )
        else:
            raise ValidationError(
                _(
                    "Invalid document: {}. Must be CPF (11 digits) or CNPJ (14 digits)."
                ).format(document)
            )
