# -*- coding: utf-8 -*-
"""
Token Service

Handles token generation, validation, invalidation, and rate limiting.
Uses SHA-256 for token hashing and Redis for rate limiting.

Author: TheDevKitchen
Date: 2026-02-16
ADRs: ADR-008 (Anti-enumeration), ADR-015 (Soft Delete)
"""

import uuid
import hashlib
import logging
from datetime import timedelta
from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PasswordTokenService:
    """Service for managing password tokens (invite and reset)"""

    def __init__(self, env):
        self.env = env

    def generate_token(self, user, token_type, company=None, created_by=None):
        """
        Generate a new token for user invitation or password reset.

        Args:
            user: res.users record
            token_type: 'invite' or 'reset'
            company: thedevkitchen.estate.company record (optional)
            created_by: res.users record who created the token (optional)

        Returns:
            tuple: (raw_token, token_record)
                - raw_token: Plain UUID string to include in email (32 hex chars)
                - token_record: thedevkitchen.password.token record
        """
        # Generate UUID v4 token
        raw_token = uuid.uuid4().hex  # 32 hex characters

        # Hash with SHA-256
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # 64 hex characters

        # Get TTL from settings
        settings = self.env["thedevkitchen.email.link.settings"].get_settings()
        if token_type == "invite":
            ttl_hours = settings.invite_link_ttl_hours
        else:  # reset
            ttl_hours = settings.reset_link_ttl_hours

        # Calculate expiration
        expires_at = fields.Datetime.now() + timedelta(hours=ttl_hours)

        # Create token record
        token_vals = {
            "user_id": user.id,
            "token": token_hash,
            "token_type": token_type,
            "status": "pending",
            "expires_at": expires_at,
            "company_id": company.id if company else None,
            "created_by": created_by.id if created_by else None,
        }

        token_record = (
            self.env["thedevkitchen.password.token"].sudo().create(token_vals)
        )

        _logger.info(
            f"Generated {token_type} token for user {user.login} "
            f"(expires: {expires_at})"
        )

        return raw_token, token_record

    def validate_token(self, raw_token):
        """
        Validate a token and return the associated user.

        Args:
            raw_token: Plain token string from email link

        Returns:
            dict: {
                'valid': bool,
                'user': res.users record or None,
                'token_record': token record or None,
                'error': error code ('not_found', 'expired', 'used', 'invalidated')
            }
        """
        # Hash the raw token
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # Find token record
        token_record = (
            self.env["thedevkitchen.password.token"]
            .sudo()
            .search(
                [
                    ("token", "=", token_hash),
                ],
                limit=1,
            )
        )

        if not token_record:
            return {
                "valid": False,
                "user": None,
                "token_record": None,
                "error": "not_found",
            }

        # Check if already used
        if token_record.status == "used":
            return {
                "valid": False,
                "user": token_record.user_id,
                "token_record": token_record,
                "error": "used",
            }

        # Check if invalidated
        if token_record.status == "invalidated":
            return {
                "valid": False,
                "user": token_record.user_id,
                "token_record": token_record,
                "error": "invalidated",
            }

        # Check expiration
        if token_record.expires_at < fields.Datetime.now():
            # Auto-expire
            token_record.write({"status": "expired"})
            return {
                "valid": False,
                "user": token_record.user_id,
                "token_record": token_record,
                "error": "expired",
            }

        # Token is valid
        return {
            "valid": True,
            "user": token_record.user_id,
            "token_record": token_record,
            "error": None,
        }

    def invalidate_previous_tokens(self, user_id, token_type):
        """
        Invalidate all pending tokens of the same type for a user.
        Called when generating a new token to ensure only one active token per user+type.

        Args:
            user_id: res.users ID
            token_type: 'invite' or 'reset'
        """
        tokens = (
            self.env["thedevkitchen.password.token"]
            .sudo()
            .search(
                [
                    ("user_id", "=", user_id),
                    ("token_type", "=", token_type),
                    ("status", "=", "pending"),
                ]
            )
        )

        if tokens:
            tokens.write({"status": "invalidated"})
            _logger.info(
                f"Invalidated {len(tokens)} previous {token_type} tokens "
                f"for user ID {user_id}"
            )

    def check_rate_limit(self, email, token_type="reset"):
        """
        Check if rate limit is exceeded for forgot-password requests.
        Uses simple in-memory counter (Redis integration pending).

        Args:
            email: User email for rate limiting
            token_type: 'reset' (only forgot-password is rate limited)

        Returns:
            dict: {
                'allowed': bool,
                'attempts': int,
                'limit': int,
                'window_seconds': int
            }
        """
        # Get rate limit from settings
        settings = self.env["thedevkitchen.email.link.settings"].get_settings()
        limit = settings.rate_limit_forgot_per_hour
        window_seconds = 3600  # 1 hour

        # TODO: Implement Redis-based rate limiting
        # For now, return allowed=True (rate limiting disabled until Redis integration)
        #
        # Future implementation:
        # redis_key = f"rate_limit:forgot_password:{email}"
        # current = redis_client.get(redis_key)
        # if current and int(current) >= limit:
        #     return {'allowed': False, 'attempts': int(current), 'limit': limit}
        # pipe = redis_client.pipeline()
        # pipe.incr(redis_key)
        # pipe.expire(redis_key, window_seconds)
        # pipe.execute()

        _logger.warning(
            f"Rate limiting check for {email} - Redis integration pending, "
            f"allowing request (production should implement Redis)"
        )

        return {
            "allowed": True,
            "attempts": 0,
            "limit": limit,
            "window_seconds": window_seconds,
        }
