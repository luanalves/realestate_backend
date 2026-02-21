# -*- coding: utf-8 -*-

import logging
from odoo import _
from odoo.exceptions import UserError, ValidationError
from validate_docbr import CPF

_logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations"""

    # Authorization Matrix (R11): Who can invite which profiles
    # Feature 010: Updated for unified profile system (tenant/property_owner replace portal)
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
            "tenant",
            "property_owner",
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
        "quicksol_estate.group_real_estate_agent": ["property_owner", "tenant"],
    }

    # Profile to Odoo Group Mapping (R11)
    # Feature 010: Updated for unified profile system (tenant/property_owner replace portal)
    PROFILE_TO_GROUP = {
        "owner": "quicksol_estate.group_real_estate_owner",
        "director": "quicksol_estate.group_real_estate_director",
        "manager": "quicksol_estate.group_real_estate_manager",
        "agent": "quicksol_estate.group_real_estate_agent",
        "prospector": "quicksol_estate.group_real_estate_prospector",
        "receptionist": "quicksol_estate.group_real_estate_receptionist",
        "financial": "quicksol_estate.group_real_estate_financial",
        "legal": "quicksol_estate.group_real_estate_legal",
        "tenant": "base.group_portal",
        "property_owner": "base.group_portal",
    }

    def __init__(self, env):
        self.env = env

    def create_user_from_profile(self, profile_record, created_by):
        """
        Feature 010: Unified user creation from profile.
        Creates res.users (login) and links to existing profile via partner_id.
        
        NO dual records created (tenant/property_owner) - profile IS the single source of truth.
        
        Args:
            profile_record: thedevkitchen.estate.profile record (already created by POST /api/v1/profiles)
            created_by: res.users record of the user creating this invite
            
        Returns:
            res.users record with signup_pending=True (waiting for password set)
        """
        # Extract data from profile
        name = profile_record.name
        email = profile_record.email
        document = profile_record.document
        phone = profile_record.phone
        mobile = profile_record.mobile
        company_id = profile_record.company_id.id
        profile_type = profile_record.profile_type_id.code
        
        # Validate document based on profile type
        if profile_type in ["tenant", "property_owner"]:
            # External profiles: CPF or CNPJ
            self._validate_document_external(document)
        else:
            # Operational profiles: CPF only
            self._validate_cpf(document)
        
        # Check email uniqueness
        existing_email = self.env["res.users"].sudo().search([("login", "=", email)], limit=1)
        if existing_email:
            raise ValidationError(_("Email already exists: {}").format(email))
        
        # Check document uniqueness (CPF field for operational profiles)
        if profile_type not in ["tenant", "property_owner"]:
            existing_cpf = self.env["res.users"].sudo().search([("cpf", "=", document)], limit=1)
            if existing_cpf:
                raise ValidationError(_("CPF already exists: {}").format(document))
        
        # Get target group from profile's profile_type
        group_xml_id = profile_record.profile_type_id.group_xml_id
        target_group = self.env.ref(group_xml_id)
        
        # Prepare user data
        user_vals = {
            "name": name,
            "login": email,
            "email": email,
            # No password field - user cannot login until password is set via invite link
            "signup_pending": True,  # Waiting for invite link
            "groups_id": [(6, 0, [target_group.id])],
            "estate_company_ids": [(4, company_id)],
        }
        
        # Add CPF for operational profiles (not stored in res.users for external profiles)
        if profile_type not in ["tenant", "property_owner"]:
            user_vals["cpf"] = document
        
        # Add optional fields
        if phone:
            user_vals["phone"] = phone
        if mobile:
            user_vals["mobile"] = mobile
        
        # Create user (res.users automatically creates res.partner)
        new_user = self.env["res.users"].sudo().create(user_vals)
        
        # Link profile to user via partner_id
        profile_record.sudo().write({
            'partner_id': new_user.partner_id.id
        })
        
        _logger.info(
            f"User created from profile {profile_record.id}: {email} (profile: {profile_type}) "
            f"linked via partner_id {new_user.partner_id.id} by {created_by.login}"
        )
        
        return new_user

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
        self, name, email, document, profile, company, created_by, profile_id=None, profile_record=None, **extra_fields
    ):
        """
        DEPRECATED: Use create_user_from_profile() instead (Feature 010).
        
        Legacy method for operational/admin profiles.
        Kept for backward compatibility with existing tests/integrations.
        
        T13 (Feature 010): If profile_id is provided, link user to existing profile via partner_id.
        """

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

        # Get target group (T13: from profile_record if provided, else from mapping)
        if profile_record and profile_record.profile_type_id:
            group_xml_id = profile_record.profile_type_id.group_xml_id
            target_group = self.env.ref(group_xml_id)
        else:
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
        
        # T13: Link profile to user via partner_id
        if profile_id and profile_record:
            profile_record.sudo().write({
                'partner_id': new_user.partner_id.id
            })
            _logger.info(f"Linked profile {profile_id} to user {new_user.id} via partner_id {new_user.partner_id.id}")

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
        profile_id=None,
        profile_record=None,
    ):
        """
        DEPRECATED: Use create_user_from_profile() instead (Feature 010).
        
        Legacy method for tenant/buyer access.
        Kept for backward compatibility with existing tests/integrations.
        
        T13 (Feature 010): If profile_id is provided, skip tenant creation and link 
        existing profile to user via partner_id.
        """
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

        # T13: Skip tenant existence check when profile_id is provided (unified profile flow)
        tenant = None
        if not profile_id:
            # Legacy flow: Check if document exists in tenant table without linked user (409 conflict)
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

        # T13: Two flows - unified profile OR legacy tenant creation
        if profile_id and profile_record:
            # Unified profile flow: Link profile to user via partner_id
            profile_record.sudo().write({
                'partner_id': user.partner_id.id
            })
            _logger.info(
                f"Portal user created and linked to profile {profile_id}: {email} "
                f"by {created_by.login}"
            )
            tenant = None  # No tenant created in unified flow
        else:
            # Legacy flow: Create real.estate.tenant linked via partner_id
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

    def _validate_document_external(self, document):
        """
        Validate CPF or CNPJ for external profiles (tenant/property_owner).
        Renamed from _validate_document_portal for Feature 010.
        """
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
