# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, ValidationError
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.invite_service import InviteService
from ..services.token_service import PasswordTokenService

_logger = logging.getLogger(__name__)


class InviteController(http.Controller):
    @http.route(
        "/api/v1/users/invite",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def invite_user(self, **kwargs):
        try:
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                return self._error_response(
                    400, "validation_error", "Invalid JSON in request body"
                )

            # Feature 010: Unified profile flow requires ONLY profile_id + session_id
            profile_id = data.get("profile_id")
            
            if not profile_id:
                return self._error_response(
                    400,
                    "validation_error",
                    "Missing required field: profile_id",
                    {"missing_fields": ["profile_id"]},
                )
            
            # Load profile record
            ProfileModel = request.env["thedevkitchen.estate.profile"]
            profile_record = ProfileModel.sudo().browse(int(profile_id))
            
            if not profile_record.exists():
                return self._error_response(
                    404, "not_found", f"Profile {profile_id} not found"
                )
            
            # Check if profile already has a user (via partner_id)
            if profile_record.partner_id:
                existing_user = (
                    request.env["res.users"]
                    .sudo()
                    .search([("partner_id", "=", profile_record.partner_id.id)], limit=1)
                )
                if existing_user:
                    return self._error_response(
                        409,
                        "conflict",
                        f"Profile {profile_id} already has a linked user account",
                        {"user_id": existing_user.id},
                    )
            
            # Extract ALL data from profile (no manual input needed)
            name = profile_record.name
            email = profile_record.email
            document = profile_record.document
            phone = profile_record.phone
            mobile = profile_record.mobile
            birthdate = profile_record.birthdate.strftime("%Y-%m-%d") if profile_record.birthdate else None
            company_id = profile_record.company_id.id
            company = profile_record.company_id
            profile = profile_record.profile_type_id.code

            # Validate email format
            if not self._validate_email_format(email):
                return self._error_response(
                    400, "validation_error", f"Invalid email format: {email}"
                )

            # Validate profile value (10 RBAC types - ADR-024)
            valid_profiles = [
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
            ]
            if profile not in valid_profiles:
                return self._error_response(
                    400,
                    "validation_error",
                    f'Invalid profile: {profile}. Must be one of: {", ".join(valid_profiles)}',
                )

            # Get authenticated user
            current_user = request.env.user

            # Initialize services
            invite_service = InviteService(request.env)
            token_service = PasswordTokenService(request.env)

            # Check authorization
            try:
                invite_service.check_authorization(current_user, profile)
            except UserError as e:
                _logger.warning(f"[INVITE] Authorization denied: {e}")
                return self._error_response(403, "forbidden", str(e))

            # Handle external profiles (tenant, property_owner) - dual record creation
            extension_record = None
            if profile in ["tenant", "property_owner"]:
                # Validate external profile required fields from profile record
                if not phone or not birthdate:
                    return self._error_response(
                        400,
                        "validation_error",
                        f"Profile {profile_id} missing required fields: phone and birthdate are required for {profile} profile",
                    )

                # Create external user (tenant or property_owner) with dual record
                try:
                    user, extension_record = invite_service.create_external_user(
                        profile_type=profile,
                        name=name,
                        email=email,
                        document=document,
                        phone=phone,
                        birthdate=birthdate,
                        company_id=company_id,
                        created_by=current_user,
                        occupation=profile_record.occupation if hasattr(profile_record, 'occupation') else None,
                        profile_id=profile_id,
                        profile_record=profile_record,
                    )
                except ValidationError as e:
                    if "already exists" in str(e) or "already registered" in str(e):
                        field = "document" if "document" in str(e).lower() else "email"
                        return self._error_response(
                            409, "conflict", str(e), {"field": field}
                        )
                    return self._error_response(400, "validation_error", str(e))
            else:
                # Standard user creation (operational/admin profiles)
                try:
                    user = invite_service.create_invited_user(
                        name=name,
                        email=email,
                        document=document,
                        profile=profile,
                        company=company,
                        created_by=current_user,
                        phone=phone,
                        mobile=mobile,
                        profile_id=profile_id,
                        profile_record=profile_record,
                    )
                except ValidationError as e:
                    if "already exists" in str(e):
                        field = "cpf" if "CPF" in str(e) else "email"
                        return self._error_response(
                            409, "conflict", str(e), {"field": field}
                        )
                    return self._error_response(400, "validation_error", str(e))

            # Generate invite token
            raw_token, token_record = token_service.generate_token(
                user=user, token_type="invite", company=company, created_by=current_user
            )

            # Get settings for TTL and frontend URL
            settings = request.env["thedevkitchen.email.link.settings"].get_settings()

            # Send invite email
            email_sent = invite_service.send_invite_email(
                user=user,
                raw_token=raw_token,
                expires_hours=settings.invite_link_ttl_hours,
                frontend_base_url=settings.frontend_base_url,
            )

            # Build response data
            response_data = {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "document": document,
                "profile": profile,
                "profile_id": profile_id,
                "signup_pending": user.signup_pending,
                "invite_sent_at": (
                    token_record.create_date.isoformat()
                    if token_record.create_date
                    else None
                ),
                "invite_expires_at": (
                    token_record.expires_at.isoformat()
                    if token_record.expires_at
                    else None
                ),
            }

            # Add extension data for external profiles (tenant, property_owner)
            if profile in ["tenant", "property_owner"] and extension_record:
                extension_key = f"{profile}_id"
                response_data[extension_key] = extension_record.id
                response_data[profile] = {
                    "id": extension_record.id,
                    "name": extension_record.name,
                    "document": getattr(extension_record, 'document', document),
                    "phone": extension_record.phone,
                    "birthdate": (
                        extension_record.birthdate.isoformat() if hasattr(extension_record, 'birthdate') and extension_record.birthdate 
                        else extension_record.birth_date.isoformat() if hasattr(extension_record, 'birth_date') and extension_record.birth_date 
                        else None
                    ),
                    "company_id": company_id,
                }

            # Add email status if failed
            if not email_sent:
                response_data["email_status"] = "failed"

            # Build HATEOAS links (as dict for easier access in tests)
            links = {
                "self": f"/api/v1/users/{user.id}",
                "resend_invite": f"/api/v1/users/{user.id}/resend-invite",
                "collection": "/api/v1/users",
                "profile": f"/api/v1/profiles/{profile_id}",
            }

            if extension_record:
                if profile == "tenant":
                    links["tenant"] = f"/api/v1/tenants/{extension_record.id}"
                elif profile == "property_owner":
                    links["property_owner"] = f"/api/v1/property-owners/{extension_record.id}"

            return self._success_response(
                201,
                response_data,
                f"User invited successfully. Email sent to {email}",
                links,
            )

        except Exception as e:
            _logger.exception("[INVITE ERROR] Unexpected error in invite_user")
            return self._error_response(
                500, "internal_error", f"An unexpected error occurred: {str(e)}"
            )

    # Helper methods

    def _validate_email_format(self, email):
        """Basic email format validation"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _success_response(self, status_code, data, message, links=None):
        """Build success response"""
        response_body = {
            "success": True,
            "data": data,
            "message": message,
        }
        if links:
            response_body["links"] = links

        return Response(
            json.dumps(response_body, default=str),
            status=status_code,
            content_type="application/json",
        )

    def _error_response(self, status_code, error_type, message, details=None):
        """Build error response"""
        response_body = {
            "success": False,
            "error": error_type,
            "message": message,
        }
        if details:
            response_body["details"] = details

        return Response(
            json.dumps(response_body),
            status=status_code,
            content_type="application/json",
        )

    @http.route(
        "/api/v1/users/<int:user_id>/resend-invite",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def resend_invite(self, user_id, **kwargs):
        try:
            # Context validated by decorators:
            # - @require_session sets request.env user
            # - @require_company enforces company access
            requester = request.env.user
            company_id = request.httprequest.headers.get("X-Company-ID")

            if not requester or not requester.id or not company_id:
                return self._error_response(
                    401, "ERR_UNAUTHORIZED", "Missing session context"
                )

            try:
                company_id = int(company_id)
            except (TypeError, ValueError):
                return self._error_response(
                    400, "validation_error", "Invalid X-Company-ID header"
                )

            # Get user record
            user = (
                request.env["res.users"]
                .sudo()
                .search(
                    [("id", "=", user_id), ("estate_company_ids", "in", [company_id])],
                    limit=1,
                )
            )

            if not user:
                return self._error_response(
                    404,
                    "ERR_NOT_FOUND",
                    f"User with ID {user_id} not found in your company",
                )

            # Check if user already active
            if not user.signup_pending:
                return self._error_response(
                    400,
                    "ERR_USER_ALREADY_ACTIVE",
                    "User has already set their password. Use forgot-password flow instead.",
                    details={
                        "user_id": user_id,
                        "suggestion": "Use POST /api/v1/auth/forgot-password",
                    },
                )

            # Check authorization using InviteService
            invite_service = InviteService(request.env)

            # Determine target profile from user's groups
            profile = self._get_user_profile(user)

            try:
                invite_service.check_authorization(requester, profile)
            except UserError as e:
                return self._error_response(403, "ERR_FORBIDDEN", str(e))

            # Invalidate previous invite tokens
            token_service = PasswordTokenService(request.env)
            token_service.invalidate_previous_tokens(user.id, "invite")

            # Generate new token
            settings = (
                request.env["thedevkitchen.email.link.settings"].sudo().get_settings()
            )
            company = (
                request.env["thedevkitchen.estate.company"].sudo().browse(company_id)
            )
            raw_token, token_record = token_service.generate_token(
                user=user,
                token_type="invite",
                company=company,
                created_by=requester,
            )

            # Resend invite email
            try:
                invite_service.send_invite_email(
                    user, raw_token, settings.invite_link_ttl_hours
                )
                email_status = "sent"
            except Exception as email_error:
                _logger.error(
                    f"Failed to send resend invite email to {user.email}: {email_error}"
                )
                email_status = "failed"

            _logger.info(
                f"Invite resent to user {user.id} ({user.email}) by {requester.login}"
            )

            # Return success response
            response_body = {
                "message": "Invite email resent successfully",
                "invite_expires_at": (
                    token_record.expires_at.isoformat()
                    if token_record.expires_at
                    else None
                ),
                "email_status": email_status,
            }

            return Response(
                json.dumps(response_body), status=200, content_type="application/json"
            )

        except Exception as e:
            _logger.exception(f"Unexpected error in resend_invite: {e}")
            return self._error_response(
                500, "ERR_INTERNAL_SERVER_ERROR", "An unexpected error occurred"
            )

    def _get_user_profile(self, user):

        # Map of group XML IDs to profile names
        group_to_profile = {
            "quicksol_estate.group_real_estate_owner": "owner",
            "quicksol_estate.group_real_estate_director": "director",
            "quicksol_estate.group_real_estate_manager": "manager",
            "quicksol_estate.group_real_estate_agent": "agent",
            "quicksol_estate.group_real_estate_prospector": "prospector",
            "quicksol_estate.group_real_estate_receptionist": "receptionist",
            "quicksol_estate.group_real_estate_financial": "financial",
            "quicksol_estate.group_real_estate_legal": "legal",
            "base.group_portal": "portal",
        }

        for xml_id, profile in group_to_profile.items():
            try:
                group = request.env.ref(xml_id)
                if group.id in user.groups_id.ids:
                    return profile
            except ValueError:
                continue

        return "unknown"
