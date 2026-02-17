# -*- coding: utf-8 -*-
"""
Invite Controller

Handles user invitation endpoints: POST /api/v1/users/invite and POST /api/v1/users/{id}/resend-invite.
All endpoints require authentication (JWT + session + company).

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-005 (API-First), ADR-007 (HATEOAS), ADR-011 (Security), ADR-018 (Validation)
"""

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
        """
        POST /api/v1/users/invite

        Create a new user and send invite email with password creation link.
        Supports dual record creation for portal profile (res.users + real.estate.tenant).

        Authorization Matrix:
        - Owner: can invite all profiles
        - Manager: can invite agent, prospector, receptionist, financial, legal
        - Agent: can invite owner (property owner), portal (tenant)

        Request Body:
        {
            "name": "string (required)",
            "email": "string (required)",
            "document": "string (required - CPF or CNPJ)",
            "profile": "string (required - owner|director|manager|agent|prospector|receptionist|financial|legal|portal)",
            "phone": "string (optional for most, required for portal)",
            "mobile": "string (optional)",
            "birthdate": "string (required for portal - YYYY-MM-DD)",
            "company_id": "integer (required for portal)",
            "occupation": "string (optional for portal)"
        }

        Returns:
            201: User invited successfully
            400: Validation error
            401: Unauthorized (missing/invalid JWT)
            403: Forbidden (authorization matrix violation)
            409: Conflict (email or document already exists)
        """
        try:
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as e:
                return self._error_response(
                    400, "validation_error", "Invalid JSON in request body"
                )

            # Validate required base fields
            required_fields = ["name", "email", "document", "profile"]
            missing_fields = [f for f in required_fields if not data.get(f)]
            if missing_fields:
                return self._error_response(
                    400,
                    "validation_error",
                    f"Missing required fields: {', '.join(missing_fields)}",
                    {"missing_fields": missing_fields},
                )

            # Validate email format
            email = data["email"]
            if not self._validate_email_format(email):
                return self._error_response(
                    400, "validation_error", f"Invalid email format: {email}"
                )

            # Validate profile value
            valid_profiles = [
                "owner",
                "director",
                "manager",
                "agent",
                "prospector",
                "receptionist",
                "financial",
                "legal",
                "portal",
            ]
            profile = data["profile"]
            if profile not in valid_profiles:
                return self._error_response(
                    400,
                    "validation_error",
                    f'Invalid profile: {profile}. Must be one of: {", ".join(valid_profiles)}',
                )

            # Get authenticated user and company context
            current_user = request.env["res.users"].sudo().browse(request.session.uid)
            company_id = request.httprequest.headers.get("X-Company-ID")
            company = (
                request.env["thedevkitchen.estate.company"]
                .sudo()
                .browse(int(company_id))
            )

            # Initialize services
            invite_service = InviteService(request.env)
            token_service = PasswordTokenService(request.env)

            # Check authorization
            try:
                invite_service.check_authorization(current_user, profile)
            except UserError as e:
                return self._error_response(403, "forbidden", str(e))

            # Handle portal profile (dual record creation)
            if profile == "portal":
                # Validate portal-specific required fields
                portal_required = ["phone", "birthdate", "company_id"]
                missing_portal = [f for f in portal_required if not data.get(f)]
                if missing_portal:
                    return self._error_response(
                        400,
                        "validation_error",
                        f'Fields {", ".join(missing_portal)} are required for portal profile',
                        {"missing_fields": missing_portal},
                    )

                # Create portal user + tenant
                try:
                    user, tenant = invite_service.create_portal_user(
                        name=data["name"],
                        email=email,
                        document=data["document"],
                        phone=data["phone"],
                        birthdate=data["birthdate"],
                        company_id=data["company_id"],
                        created_by=current_user,
                        occupation=data.get("occupation"),
                    )
                except ValidationError as e:
                    if "already exists" in str(e) or "already registered" in str(e):
                        field = "document" if "document" in str(e).lower() else "email"
                        return self._error_response(
                            409, "conflict", str(e), {"field": field}
                        )
                    return self._error_response(400, "validation_error", str(e))
            else:
                # Standard user creation (non-portal)
                try:
                    user = invite_service.create_invited_user(
                        name=data["name"],
                        email=email,
                        document=data["document"],
                        profile=profile,
                        company=company,
                        created_by=current_user,
                        phone=data.get("phone"),
                        mobile=data.get("mobile"),
                    )
                    tenant = None
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
                "document": data["document"],
                "profile": profile,
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

            # Add tenant data for portal
            if profile == "portal" and tenant:
                response_data["tenant_id"] = tenant.id
                response_data["tenant"] = {
                    "id": tenant.id,
                    "name": tenant.name,
                    "document": tenant.document,
                    "phone": tenant.phone,
                    "birthdate": (
                        tenant.birthdate.isoformat() if tenant.birthdate else None
                    ),
                    "company_id": data["company_id"],
                }

            # Add email status if failed
            if not email_sent:
                response_data["email_status"] = "failed"

            # Build HATEOAS links
            links = [
                {"href": f"/api/v1/users/{user.id}", "rel": "self", "type": "GET"},
                {
                    "href": f"/api/v1/users/{user.id}/resend-invite",
                    "rel": "resend_invite",
                    "type": "POST",
                },
                {"href": "/api/v1/users", "rel": "collection", "type": "GET"},
            ]

            if tenant:
                links.insert(
                    1,
                    {
                        "href": f"/api/v1/tenants/{tenant.id}",
                        "rel": "tenant",
                        "type": "GET",
                    },
                )

            return self._success_response(
                201,
                response_data,
                f"User invited successfully. Email sent to {email}",
                links,
            )

        except Exception as e:
            _logger.exception(f"Unexpected error in invite_user: {e}")
            return self._error_response(
                500, "internal_error", "An unexpected error occurred"
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
        """
        POST /api/v1/users/{id}/resend-invite

        Resend invite email to a user who has not yet set their password.
        Invalidates previous invite tokens and generates a new one.

        Authorization Matrix: Same as invite endpoint
        - Owner: can resend to all profiles
        - Manager: can resend to agent, prospector, receptionist, financial, legal
        - Agent: can resend to owner (property owner), portal (tenant)

        Path Parameters:
        - user_id: ID of the user to resend invite

        Returns:
        - 200: Invite resent successfully
        - 400: User already active (password already set)
        - 401: Unauthorized (no JWT or session)
        - 403: Forbidden (authorization matrix violation)
        - 404: User not found or not in requester's company

        Response Body (200):
        {
            "message": "Invite email resent successfully",
            "invite_expires_at": "2026-02-17T14:30:00Z",
            "email_status": "sent" | "failed"
        }
        """
        try:
            # Get session context
            session_data = getattr(request, "session_data", {})
            requester_id = session_data.get("user_id")
            company_id = session_data.get("company_id")

            if not requester_id or not company_id:
                return self._error_response(
                    401, "ERR_UNAUTHORIZED", "Missing session context"
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

            # Get requester
            requester = request.env["res.users"].sudo().browse(requester_id)

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
            token_service.invalidate_previous_tokens(user, "invite")

            # Generate new token
            settings = (
                request.env["thedevkitchen.email.link.settings"].sudo().get_settings()
            )
            raw_token, token_record = token_service.generate_token(
                user=user,
                token_type="invite",
                ttl_hours=settings.invite_link_ttl_hours,
                company_id=company_id,
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
        """
        Determine the profile of a user based on their groups.

        Args:
            user: res.users record

        Returns:
            str: Profile name (owner, director, manager, agent, etc.)
        """
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
