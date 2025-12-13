# -*- coding: utf-8 -*-
"""Me Controller - Dados do usuário autenticado"""

import logging
from odoo import http
from odoo.http import request
from ..middleware import require_jwt, require_session

_logger = logging.getLogger(__name__)


class MeController(http.Controller):
    """Endpoint /api/v1/me - Retorna dados do usuário da sessão"""

    @http.route('/api/v1/me', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def get_me(self, **kwargs):
        """
        GET /api/v1/me
        
        Returns authenticated user data including companies.
        Requires OAuth 2.0 Bearer token + valid user session (ADR-009).
        """
        try:
            user = request.env.user

            if not user or user.id == 4:
                _logger.warning('Unauthorized /api/v1/me access attempt')
                return {
                    'error': 'session_required',
                    'error_description': 'Valid user session required'
                }

            companies = [
                {
                    'id': c.id,
                    'name': c.name,
                    'cnpj': c.cnpj or '',
                    'email': c.email or '',
                    'phone': c.phone or '',
                    'website': c.website or ''
                }
                for c in getattr(user, 'estate_company_ids', [])
            ]

            user_data = {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'login': user.login,
                'phone': user.phone or '',
                'mobile': user.mobile or '',
                'companies': companies,
                'default_company_id': user.main_estate_company_id.id if hasattr(user, 'main_estate_company_id') and user.main_estate_company_id else None,
                'is_admin': user.has_group('base.group_system'),
                'active': user.active
            }

            _logger.info(f'User {user.login} (UID {user.id}) retrieved profile - {len(companies)} company(ies)')
            return {'user': user_data}

        except Exception as e:
            _logger.error(f'Error in /api/v1/me: {e}', exc_info=True)
            return {'error': 'server_error', 'error_description': str(e)}
