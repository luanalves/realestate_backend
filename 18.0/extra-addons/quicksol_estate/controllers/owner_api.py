# -*- coding: utf-8 -*-
"""
Owner API Controller - Feature 007: Company & Owner Management

Independent Owner CRUD endpoints (not nested under Company).
Owners can be created without a company and linked later.

Endpoints:
    POST   /api/v1/owners                        → Create owner (no company)
    GET    /api/v1/owners                        → List all owners from user's companies
    GET    /api/v1/owners/{id}                   → Get owner details
    PUT    /api/v1/owners/{id}                   → Update owner
    DELETE /api/v1/owners/{id}                   → Soft delete
    POST   /api/v1/owners/{id}/companies         → Link owner to company
    DELETE /api/v1/owners/{id}/companies/{cid}   → Unlink owner from company
"""
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
    """REST API Controller for Owner endpoints (Feature 007)"""
    
    # ========== CREATE OWNER (T014, T015, T016) ==========
    
    @http.route('/api/v1/owners', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    # No @require_company - Owner can exist without company (FR-010 exception)
    def create_owner(self, **kwargs):
        """
        Create a new Owner without company association.
        
        RBAC: Only Owner (for their companies) or Admin can create Owners (FR-018, T016)
        
        Request Body:
            {
                "name": "Owner Name",
                "email": "owner@example.com",
                "password": "secure_password",
                "phone": "(11) 98765-4321",  // optional
                "mobile": "(11) 98765-4321"  // optional
            }
        
        Returns:
            201: Owner created successfully
            400: Validation error
            403: Forbidden (not Owner or Admin)
            409: Email already exists
        """
        try:
            user = request.env.user
            
            # RBAC Check (T016): Only Owner or Admin can create Owners
            is_owner = user.has_group('quicksol_estate.group_real_estate_owner')
            is_admin = user.has_group('base.group_system')
            
            if not (is_owner or is_admin):
                return error_response(403, 'Only Owners or Admins can create new Owners')
            
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
    
    # ========== LIST OWNERS (T017) ==========
    
    @http.route('/api/v1/owners', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    # No @require_company - returns Owners from all user's companies (FR-040)
    def list_owners(self, page=1, page_size=20, **kwargs):
        """
        List all Owners from companies the user has access to.
        
        Multi-tenancy: Returns Owners from all companies in user.estate_company_ids (FR-040)
        
        Query Parameters:
            page: Page number (default: 1)
            page_size: Items per page (default: 20, max: 100)
        
        Returns:
            200: List of owners with pagination
            403: Forbidden
        """
        try:
            user = request.env.user
            
            # Convert pagination parameters
            try:
                page = int(page)
                page_size = min(int(page_size), 100)  # Max 100 items per page
            except (ValueError, TypeError):
                return error_response(400, 'Invalid pagination parameters')
            
            if page < 1 or page_size < 1:
                return error_response(400, 'Page and page_size must be positive integers')
            
            # Get Owner group
            owner_group = request.env.ref('quicksol_estate.group_real_estate_owner')
            
            # Multi-tenancy filter (FR-037, FR-040)
            if user.has_group('base.group_system'):
                # Admin sees all Owners
                domain = [('groups_id', 'in', [owner_group.id])]
            else:
                # User sees Owners from their companies
                if not user.estate_company_ids:
                    # User has no companies - return empty list
                    response, status = paginated_response(
                        items=[],
                        total=0,
                        page=page,
                        page_size=page_size
                    )
                    return request.make_json_response(response, status=status)
                
                # Find all users who have any of the user's companies
                domain = [
                    ('groups_id', 'in', [owner_group.id]),
                    ('estate_company_ids', 'in', user.estate_company_ids.ids)
                ]
            
            # Count total
            total = request.env['res.users'].sudo().search_count(domain)
            
            # Get paginated results
            offset = (page - 1) * page_size
            owners = request.env['res.users'].sudo().search(
                domain,
                limit=page_size,
                offset=offset,
                order='name'
            )
            
            # Serialize owners
            owner_list = []
            for owner in owners:
                owner_list.append({
                    'id': owner.id,
                    'name': owner.name,
                    'email': owner.email,
                    'phone': owner.phone,
                    'mobile': owner.mobile,
                    'company_count': len(owner.estate_company_ids),
                    'companies': [{'id': c.id, 'name': c.name} for c in owner.estate_company_ids]
                })
            
            # Build pagination links
            from ..utils.responses import build_pagination_links
            links = build_pagination_links(
                base_url='/api/v1/owners',
                page=page,
                total_pages=(total + page_size - 1) // page_size
            )
            
            response, status = paginated_response(
                items=owner_list,
                total=total,
                page=page,
                page_size=page_size,
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error listing owners: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== GET OWNER (T018) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def get_owner(self, owner_id, **kwargs):
        """
        Get Owner details by ID.
        
        Multi-tenancy: Returns 404 if Owner not accessible (FR-039)
        
        Returns:
            200: Owner details
            404: Owner not found or not accessible
        """
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
            
            # Multi-tenancy check (FR-039: return 404 for inaccessible)
            if not user.has_group('base.group_system'):
                # Non-admin: verify owner belongs to one of user's companies
                common_companies = set(owner.estate_company_ids.ids) & set(user.estate_company_ids.ids)
                if not common_companies:
                    return error_response(404, 'Owner not found')
            
            # Serialize owner
            owner_data = {
                'id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'phone': owner.phone,
                'mobile': owner.mobile,
                'active': owner.active,
                'company_count': len(owner.estate_company_ids),
                'companies': [
                    {
                        'id': c.id,
                        'name': c.name,
                        'cnpj': c.cnpj
                    } for c in owner.estate_company_ids
                ]
            }
            
            # Build HATEOAS links
            links = build_hateoas_links(
                base_url='/api/v1/owners',
                resource_id=owner_id,
                relations={
                    'companies': '/companies',
                    'link_company': '/companies'
                }
            )
            
            response, status = util_success(
                data=owner_data,
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error getting owner {owner_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== UPDATE OWNER (T019) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def update_owner(self, owner_id, **kwargs):
        """
        Update Owner information.
        
        RBAC: Only Owners of same companies or Admin can update (FR-020)
        
        Request Body:
            {
                "name": "Updated Name",  // optional
                "phone": "...",          // optional
                "mobile": "..."          // optional
            }
        
        Returns:
            200: Owner updated successfully
            400: Validation error
            403: Forbidden
            404: Owner not found
        """
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
            
            # RBAC Check (FR-020)
            if not user.has_group('base.group_system'):
                # Non-admin: verify owner belongs to one of user's companies
                common_companies = set(owner.estate_company_ids.ids) & set(user.estate_company_ids.ids)
                if not common_companies:
                    return error_response(404, 'Owner not found')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Prepare update values
            update_vals = {}
            
            allowed_fields = ['name', 'phone', 'mobile']
            for field in allowed_fields:
                if field in data:
                    update_vals[field] = data[field]
            
            if not update_vals:
                return error_response(400, 'No valid fields to update')
            
            # Update owner
            owner.write(update_vals)
            
            # Serialize response
            owner_data = {
                'id': owner.id,
                'name': owner.name,
                'email': owner.email,
                'phone': owner.phone,
                'mobile': owner.mobile,
                'company_count': len(owner.estate_company_ids)
            }
            
            links = build_hateoas_links('/api/v1/owners', owner_id)
            
            response, status = util_success(
                data=owner_data,
                message='Owner updated successfully',
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except ValidationError as e:
            _logger.warning(f"Validation error updating owner {owner_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error updating owner {owner_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== DELETE OWNER (T020, T021) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def delete_owner(self, owner_id, **kwargs):
        """
        Soft delete Owner (set active=False).
        
        Protection: Prevents deletion of last active Owner of any company (FR-031, T021)
        RBAC: Only Owners of same companies or Admin can delete
        
        Returns:
            200: Owner deleted successfully
            400: Cannot delete last owner
            403: Forbidden
            404: Owner not found
        """
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
            
            # RBAC Check
            if not user.has_group('base.group_system'):
                common_companies = set(owner.estate_company_ids.ids) & set(user.estate_company_ids.ids)
                if not common_companies:
                    return error_response(404, 'Owner not found')
            
            # Last Owner Protection (FR-031, T021)
            # Check if this owner is the ONLY active owner of any company
            for company in owner.estate_company_ids:
                # Count active owners of this company
                active_owners_count = request.env['res.users'].sudo().search_count([
                    ('groups_id', 'in', [owner_group.id]),
                    ('estate_company_ids', 'in', [company.id]),
                    ('active', '=', True),
                    ('id', '!=', owner_id)  # Exclude current owner
                ])
                
                if active_owners_count == 0:
                    return error_response(
                        400,
                        f"Cannot delete owner: {owner.name} is the last active owner of company '{company.name}'"
                    )
            
            # Soft delete (ADR-015)
            owner.write({'active': False})
            
            response, status = util_success(
                data={'id': owner_id, 'active': False},
                message='Owner deactivated successfully'
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error deleting owner {owner_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== LINK OWNER TO COMPANY (T022) ==========
    
    @http.route('/api/v1/owners/<int:owner_id>/companies', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def link_owner_to_company(self, owner_id, **kwargs):
        """
        Link an existing Owner to a Company.
        
        RBAC: Only Owner of target company or Admin can link (FR-020)
        
        Request Body:
            {
                "company_id": 123
            }
        
        Returns:
            200: Owner linked successfully
            400: Validation error
            403: Forbidden
            404: Owner or Company not found
            409: Owner already linked to company
        """
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
        """
        Unlink Owner from a Company.
        
        Protection: Prevents unlinking last active Owner from company (FR-031)
        RBAC: Only Owner of target company or Admin can unlink (FR-020)
        
        Returns:
            200: Owner unlinked successfully
            400: Cannot unlink last owner
            403: Forbidden
            404: Owner or Company not found
        """
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
