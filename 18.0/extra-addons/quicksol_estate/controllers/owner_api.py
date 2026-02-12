# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from ..utils.responses import (
    success_response as util_success,
    error_response as util_error,
    paginated_response,
    build_hateoas_links
)
from ..utils.validators import validate_email_format

_logger = logging.getLogger(__name__)


class OwnerApiController(http.Controller):
    @http.route('/api/v1/owners', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def create_owner(self, **kwargs):

        try:
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Validate required fields (FR-028, FR-029, FR-030)
            required_fields = ['name', 'email', 'password']
            missing_fields = [f for f in required_fields if not data.get(f)]
            if missing_fields:
                return error_response(400, f"Missing required fields: {', '.join(missing_fields)}")
            
            # Validate email format
            if not validate_email_format(data['email']):
                return error_response(400, f"Invalid email format: {data['email']}")
            
            # Validate password length (FR-030)
            if len(data['password']) < 8:
                return error_response(400, 'Password must be at least 8 characters')
            
            # Check if email already exists (FR-029 unique constraint)
            existing_user = request.env['res.users'].sudo().search([
                ('login', '=', data['email'])
            ], limit=1)
            
            if existing_user:
                return error_response(409, f"Email already exists: {data['email']}")
            
            # Get Owner group
            owner_group = request.env.ref('quicksol_estate.group_real_estate_owner')
            
            # Prepare user data (T015)
            user_vals = {
                'name': data['name'],
                'login': data['email'],
                'email': data['email'],
                'password': data['password'],
                'groups_id': [(6, 0, [owner_group.id])],  # Assign group_real_estate_owner
                'estate_company_ids': [(6, 0, [])],  # FR-009: Start with no companies
            }
            
            # Optional fields
            if 'phone' in data:
                user_vals['phone'] = data['phone']
            if 'mobile' in data:
                user_vals['mobile'] = data['mobile']
            
            # Create Owner
            new_owner = request.env['res.users'].sudo().create(user_vals)
            
            # Build response with HATEOAS links
            owner_data = {
                'id': new_owner.id,
                'name': new_owner.name,
                'email': new_owner.email,
                'phone': new_owner.phone,
                'mobile': new_owner.mobile,
                'company_count': len(new_owner.estate_company_ids),
                'companies': []
            }
            
            links = build_hateoas_links(
                base_url='/api/v1/owners',
                resource_id=new_owner.id,
                relations={'companies': '/companies'}
            )
            
            response, status = util_success(
                data=owner_data,
                message='Owner created successfully',
                links=links,
                status_code=201
            )
            
            return request.make_json_response(response, status=status)
            
        except ValidationError as e:
            _logger.warning(f"Validation error creating owner: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error creating owner: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== LINK OWNER TO COMPANY (T022) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>/companies', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def link_owner_to_company(self, owner_id, **kwargs):

        try:
            user = request.env.user
            
            # Get owner
            owner = request.env['res.users'].sudo().browse(owner_id)
            
            if not owner.exists():
                return error_response(404, 'Owner not found')
            
            # Verify owner has Owner group
            owner_group = request.env.ref('quicksol_estate.group_real_estate_owner')
            if owner_group not in owner.groups_id:
                return error_response(404, 'Owner not found')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            company_id = data.get('company_id')
            if not company_id:
                return error_response(400, 'Missing required field: company_id')
            
            # Get company
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists() or not company.active:
                return error_response(404, 'Company not found')
            
            # RBAC Check (FR-020): User must be Owner of target company
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    return error_response(403, 'You can only link Owners to your own companies')
            
            # Check if already linked
            if company_id in owner.estate_company_ids.ids:
                return error_response(409, f"Owner already linked to company '{company.name}'")
            
            # Link owner to company
            owner.write({
                'estate_company_ids': [(4, company_id)]  # Add to Many2many
            })
            
            # Response
            owner_data = {
                'id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'company_count': len(owner.estate_company_ids),
                'companies': [{'id': c.id, 'name': c.name} for c in owner.estate_company_ids]
            }
            
            links = build_hateoas_links('/api/v1/owners', owner_id, {'companies': '/companies'})
            
            response, status = util_success(
                data=owner_data,
                message=f"Owner linked to company '{company.name}' successfully",
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error linking owner {owner_id} to company: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== UNLINK OWNER FROM COMPANY (T023) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>/companies/<int:company_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def unlink_owner_from_company(self, owner_id, company_id, **kwargs):

        try:
            user = request.env.user
            
            # Get owner
            owner = request.env['res.users'].sudo().browse(owner_id)
            
            if not owner.exists():
                return error_response(404, 'Owner not found')
            
            # Verify owner has Owner group
            owner_group = request.env.ref('quicksol_estate.group_real_estate_owner')
            if owner_group not in owner.groups_id:
                return error_response(404, 'Owner not found')
            
            # Get company
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists():
                return error_response(404, 'Company not found')
            
            # RBAC Check (FR-020)
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    return error_response(403, 'You can only unlink Owners from your own companies')
            
            # Check if owner is linked to company
            if company_id not in owner.estate_company_ids.ids:
                return error_response(404, f"Owner not linked to company '{company.name}'")
            
            # Last Owner Protection (FR-031)
            # Count active owners of this company (excluding current owner)
            active_owners_count = request.env['res.users'].sudo().search_count([
                ('groups_id', 'in', [owner_group.id]),
                ('estate_company_ids', 'in', [company_id]),
                ('active', '=', True),
                ('id', '!=', owner_id)
            ])
            
            if active_owners_count == 0:
                return error_response(
                    400,
                    f"Cannot unlink owner: {owner.name} is the last active owner of company '{company.name}'"
                )
            
            # Unlink owner from company
            owner.write({
                'estate_company_ids': [(3, company_id)]  # Remove from Many2many
            })
            
            # Response
            owner_data = {
                'id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'company_count': len(owner.estate_company_ids),
                'companies': [{'id': c.id, 'name': c.name} for c in owner.estate_company_ids]
            }
            
            links = build_hateoas_links('/api/v1/owners', owner_id)
            
            response, status = util_success(
                data=owner_data,
                message=f"Owner unlinked from company '{company.name}' successfully",
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error unlinking owner {owner_id} from company {company_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
