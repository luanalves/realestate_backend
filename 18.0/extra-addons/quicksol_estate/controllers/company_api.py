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
    build_hateoas_links,
    build_pagination_links
)
from ..utils.validators import validate_cnpj, format_cnpj, validate_email_format, validate_creci

_logger = logging.getLogger(__name__)


class CompanyApiController(http.Controller):
    @http.route('/api/v1/companies', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def create_company(self, **kwargs):
        try:
            user = request.env.user
            
            # RBAC Check (FR-019): Only Owner or Admin can create companies
            is_owner = user.has_group('quicksol_estate.group_real_estate_owner')
            is_admin = user.has_group('base.group_system')
            
            if not (is_owner or is_admin):
                return error_response(403, 'Only Owners or Admins can create companies')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Validate required fields (FR-023)
            if not data.get('name'):
                return error_response(400, 'Missing required field: name')
            
            if len(data['name']) > 255:
                return error_response(400, 'Company name must not exceed 255 characters')
            
            # Validate CNPJ if provided (FR-024, T030)
            if 'cnpj' in data and data['cnpj']:
                if not validate_cnpj(data['cnpj']):
                    return error_response(400, 'Invalid CNPJ format. Please use: XX.XXX.XXX/XXXX-XX')
                
                # Format CNPJ
                data['cnpj'] = format_cnpj(data['cnpj'])
                
                # Check CNPJ uniqueness (FR-025, T030) - including soft-deleted
                existing_company = request.env['thedevkitchen.estate.company'].sudo().search([
                    ('cnpj', '=', data['cnpj'])
                ], limit=1)
                
                if existing_company:
                    return error_response(409, f"CNPJ already exists: {data['cnpj']}")
            
            # Validate email if provided (FR-026)
            if 'email' in data and data['email']:
                if not validate_email_format(data['email']):
                    return error_response(400, f"Invalid email format: {data['email']}")
            
            # Validate CRECI format if provided (FR-027)
            if 'creci' in data and data['creci']:
                if not validate_creci(data['creci']):
                    return error_response(400, f"Invalid CRECI format: {data['creci']}")
            
            # Prepare company data
            company_vals = {
                'name': data['name'],
            }
            
            # Optional fields
            optional_fields = [
                'cnpj', 'creci', 'legal_name', 'email', 'phone', 'mobile',
                'website', 'street', 'street2', 'city', 'state_id', 'zip_code',
                'country_id', 'foundation_date', 'description'
            ]
            
            for field in optional_fields:
                if field in data and data[field] is not None:
                    company_vals[field] = data[field]
            
            # Create company
            new_company = request.env['thedevkitchen.estate.company'].sudo().create(company_vals)
            
            # Auto-linkage (FR-016, T031): Add company to creator's estate_company_ids
            if not user.has_group('base.group_system'):  # Skip for admin
                user.sudo().write({
                    'estate_company_ids': [(4, new_company.id)]
                })
            
            # Build response with HATEOAS links
            company_data = {
                'id': new_company.id,
                'name': new_company.name,
                'cnpj': new_company.cnpj,
                'creci': new_company.creci,
                'legal_name': new_company.legal_name,
                'email': new_company.email,
                'phone': new_company.phone,
                'mobile': new_company.mobile,
                'website': new_company.website,
                'city': new_company.city,
                'state': new_company.state_id.name if new_company.state_id else None,
                'property_count': new_company.property_count,
                'agent_count': new_company.agent_count,
            }
            
            links = build_hateoas_links(
                base_url='/api/v1/companies',
                resource_id=new_company.id,
                relations={
                    'properties': '/properties',
                    'agents': '/agents'
                }
            )
            
            response, status = util_success(
                data=company_data,
                message='Company created successfully',
                links=links,
                status_code=201
            )
            
            return request.make_json_response(response, status=status)
            
        except ValidationError as e:
            _logger.warning(f"Validation error creating company: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error creating company: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== LIST COMPANIES (T032) ==========
    
    @http.route('/api/v1/companies', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_companies(self, page=1, page_size=20, **kwargs):
        try:
            user = request.env.user
            
            # Convert pagination parameters
            try:
                page = int(page)
                page_size = min(int(page_size), 100)
            except (ValueError, TypeError):
                return error_response(400, 'Invalid pagination parameters')
            
            if page < 1 or page_size < 1:
                return error_response(400, 'Page and page_size must be positive integers')
            
            # Multi-tenancy filter (FR-037)
            if user.has_group('base.group_system'):
                domain = [('active', '=', True)]
            else:
                domain = [
                    ('id', 'in', user.estate_company_ids.ids),
                    ('active', '=', True)
                ]
            
            # Count total
            total = request.env['thedevkitchen.estate.company'].sudo().search_count(domain)
            
            # Get paginated results
            offset = (page - 1) * page_size
            companies = request.env['thedevkitchen.estate.company'].sudo().search(
                domain,
                limit=page_size,
                offset=offset,
                order='name'
            )
            
            # Serialize companies
            company_list = []
            for company in companies:
                company_list.append({
                    'id': company.id,
                    'name': company.name,
                    'cnpj': company.cnpj,
                    'email': company.email,
                    'phone': company.phone,
                    'city': company.city,
                    'state': company.state_id.name if company.state_id else None,
                    'property_count': company.property_count,
                    'agent_count': company.agent_count,
                })
            
            # Build pagination links
            links = build_pagination_links(
                base_url='/api/v1/companies',
                page=page,
                total_pages=(total + page_size - 1) // page_size
            )
            
            response, status = paginated_response(
                items=company_list,
                total=total,
                page=page,
                page_size=page_size,
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error listing companies: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== GET COMPANY (T033) ==========
    
    @http.route('/api/v1/companies/<int:company_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_company(self, company_id, **kwargs):
        try:
            user = request.env.user
            
            # Get company
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists() or not company.active:
                return error_response(404, 'Company not found')
            
            # Multi-tenancy check (FR-039: return 404 for inaccessible)
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    return error_response(404, 'Company not found')
            
            # Serialize company
            company_data = {
                'id': company.id,
                'name': company.name,
                'legal_name': company.legal_name,
                'cnpj': company.cnpj,
                'creci': company.creci,
                'email': company.email,
                'phone': company.phone,
                'mobile': company.mobile,
                'website': company.website,
                'street': company.street,
                'street2': company.street2,
                'city': company.city,
                'state_id': company.state_id.id if company.state_id else None,
                'state': company.state_id.name if company.state_id else None,
                'zip_code': company.zip_code,
                'foundation_date': company.foundation_date.isoformat() if company.foundation_date else None,
                'description': company.description,
                'property_count': company.property_count,
                'agent_count': company.agent_count,
                'tenant_count': company.tenant_count,
                'lease_count': company.lease_count,
            }
            
            # Build HATEOAS links
            links = build_hateoas_links(
                base_url='/api/v1/companies',
                resource_id=company_id,
                relations={
                    'properties': '/properties',
                    'agents': '/agents',
                    'tenants': '/tenants',
                    'leases': '/leases'
                }
            )
            
            response, status = util_success(
                data=company_data,
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error getting company {company_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== UPDATE COMPANY (T034) ==========
    
    @http.route('/api/v1/companies/<int:company_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_company(self, company_id, **kwargs):
        try:
            user = request.env.user
            
            # Get company
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists() or not company.active:
                return error_response(404, 'Company not found')
            
            # RBAC Check: User must be Owner of this company or Admin
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    return error_response(404, 'Company not found')
                
                # Verify user is Owner (not just Manager/Agent)
                if not user.has_group('quicksol_estate.group_real_estate_owner'):
                    return error_response(403, 'Only Owners can update companies')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Prepare update values
            update_vals = {}
            
            # Validate and prepare fields
            if 'name' in data:
                if not data['name'] or len(data['name']) > 255:
                    return error_response(400, 'Invalid company name')
                update_vals['name'] = data['name']
            
            if 'cnpj' in data and data['cnpj']:
                if not validate_cnpj(data['cnpj']):
                    return error_response(400, 'Invalid CNPJ format')
                
                formatted_cnpj = format_cnpj(data['cnpj'])
                
                # Check uniqueness (excluding current company)
                existing = request.env['thedevkitchen.estate.company'].sudo().search([
                    ('cnpj', '=', formatted_cnpj),
                    ('id', '!=', company_id)
                ], limit=1)
                
                if existing:
                    return error_response(409, f"CNPJ already exists: {formatted_cnpj}")
                
                update_vals['cnpj'] = formatted_cnpj
            
            if 'email' in data and data['email']:
                if not validate_email_format(data['email']):
                    return error_response(400, f"Invalid email format: {data['email']}")
                update_vals['email'] = data['email']
            
            if 'creci' in data and data['creci']:
                if not validate_creci(data['creci']):
                    return error_response(400, f"Invalid CRECI format: {data['creci']}")
                update_vals['creci'] = data['creci']
            
            # Other optional fields
            optional_fields = [
                'legal_name', 'phone', 'mobile', 'website', 'street', 'street2',
                'city', 'state_id', 'zip_code', 'country_id', 'foundation_date',
                'description'
            ]
            
            for field in optional_fields:
                if field in data:
                    update_vals[field] = data[field]
            
            if not update_vals:
                return error_response(400, 'No valid fields to update')
            
            # Update company
            company.write(update_vals)
            
            # Serialize response
            company_data = {
                'id': company.id,
                'name': company.name,
                'cnpj': company.cnpj,
                'email': company.email,
                'phone': company.phone,
                'city': company.city,
            }
            
            links = build_hateoas_links('/api/v1/companies', company_id)
            
            response, status = util_success(
                data=company_data,
                message='Company updated successfully',
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except ValidationError as e:
            _logger.warning(f"Validation error updating company {company_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error updating company {company_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== DELETE COMPANY (T035) ==========
    
    @http.route('/api/v1/companies/<int:company_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_company(self, company_id, **kwargs):
        try:
            user = request.env.user
            
            # Get company
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists() or not company.active:
                return error_response(404, 'Company not found')
            
            # RBAC Check
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    return error_response(404, 'Company not found')
                
                if not user.has_group('quicksol_estate.group_real_estate_owner'):
                    return error_response(403, 'Only Owners can delete companies')
            
            # Soft delete (ADR-015)
            company.write({'active': False})
            
            response, status = util_success(
                data={'id': company_id, 'active': False},
                message='Company deactivated successfully'
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f"Error deleting company {company_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
    
    # ========== LIST COMPANY PROPERTIES (T036) ==========
    
    @http.route('/api/v1/companies/<int:company_id>/properties', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_company_properties(self, company_id, page=1, page_size=20, **kwargs):
        try:
            user = request.env.user
            
            # Validate company exists and is active
            company = request.env['thedevkitchen.estate.company'].sudo().browse(company_id)
            
            if not company.exists() or not company.active:
                return error_response(404, 'Company not found')
            
            # Multi-tenancy validation (ADR-008): User must have access to company
            if not user.has_group('base.group_system'):
                if company_id not in user.estate_company_ids.ids:
                    _logger.warning(
                        f'User {user.login} (id={user.id}) attempted to access properties of '
                        f'unauthorized company {company_id}. Allowed: {user.estate_company_ids.ids}'
                    )
                    return error_response(404, 'Company not found')
            
            # Convert pagination parameters
            try:
                page = int(page)
                page_size = min(int(page_size), 100)
            except (ValueError, TypeError):
                return error_response(400, 'Invalid pagination parameters')
            
            if page < 1 or page_size < 1:
                return error_response(400, 'Page and page_size must be positive integers')
            
            # Build base domain (company filter)
            domain = [
                ('company_ids', 'in', [company_id]),
                ('active', '=', True)
            ]
            
            # RBAC filter (ADR-019)
            is_admin = user.has_group('base.group_system')
            is_manager = user.has_group('quicksol_estate.group_real_estate_manager')
            is_agent = user.has_group('quicksol_estate.group_real_estate_agent')
            
            if not is_admin and not is_manager:
                if is_agent:
                    # Agent sees only their assigned properties
                    agent_record = request.env['real.estate.agent'].search([
                        ('user_id', '=', user.id)
                    ], limit=1)
                    
                    if agent_record:
                        domain.append(('agent_id', '=', agent_record.id))
                    else:
                        # Agent without agent record sees nothing
                        domain.append(('id', '=', False))
            
            # Apply optional filters
            if 'property_type_id' in kwargs:
                try:
                    domain.append(('property_type_id', '=', int(kwargs['property_type_id'])))
                except (ValueError, TypeError):
                    return error_response(400, 'Invalid property_type_id')
            
            if 'property_status' in kwargs:
                status = kwargs['property_status']
                if status not in ['available', 'sold', 'rented', 'unavailable']:
                    return error_response(400, 'Invalid property_status. Must be: available, sold, rented, unavailable')
                domain.append(('property_status', '=', status))
            
            if 'city' in kwargs:
                domain.append(('city', 'ilike', kwargs['city']))
            
            if 'state_id' in kwargs:
                try:
                    domain.append(('state_id', '=', int(kwargs['state_id'])))
                except (ValueError, TypeError):
                    return error_response(400, 'Invalid state_id')
            
            if 'agent_id' in kwargs:
                try:
                    domain.append(('agent_id', '=', int(kwargs['agent_id'])))
                except (ValueError, TypeError):
                    return error_response(400, 'Invalid agent_id')
            
            if 'min_price' in kwargs:
                try:
                    domain.append(('price', '>=', float(kwargs['min_price'])))
                except (ValueError, TypeError):
                    return error_response(400, 'Invalid min_price')
            
            if 'max_price' in kwargs:
                try:
                    domain.append(('price', '<=', float(kwargs['max_price'])))
                except (ValueError, TypeError):
                    return error_response(400, 'Invalid max_price')
            
            if 'for_sale' in kwargs:
                for_sale = kwargs['for_sale'].lower() == 'true'
                domain.append(('for_sale', '=', for_sale))
            
            if 'for_rent' in kwargs:
                for_rent = kwargs['for_rent'].lower() == 'true'
                domain.append(('for_rent', '=', for_rent))
            
            # Order by
            order_by = kwargs.get('order_by', 'name')
            order_mapping = {
                'price': 'price',
                'area': 'area',
                'created_date': 'create_date',
                'name': 'name'
            }
            
            if order_by not in order_mapping:
                return error_response(400, f'Invalid order_by. Must be: {", ".join(order_mapping.keys())}')
            
            order_field = order_mapping[order_by]
            
            # Use request.env (user context, no sudo) - ADR-011
            Property = request.env['real.estate.property']
            
            # Count total
            total = Property.search_count(domain)
            
            # Get paginated results
            offset = (page - 1) * page_size
            properties = Property.search(
                domain,
                limit=page_size,
                offset=offset,
                order=order_field
            )
            
            # Serialize properties
            property_list = []
            for prop in properties:
                property_data = {
                    'id': prop.id,
                    'name': prop.name,
                    'property_type': prop.property_type_id.name if prop.property_type_id else None,
                    'property_status': prop.property_status,
                    'price': prop.price,
                    'area': prop.area,
                    'city': prop.city,
                    'state': prop.state_id.name if prop.state_id else None,
                    'agent': {
                        'id': prop.agent_id.id,
                        'name': prop.agent_id.name
                    } if prop.agent_id else None,
                    'for_sale': prop.for_sale,
                    'for_rent': prop.for_rent,
                    'num_rooms': prop.num_rooms,
                    'num_bathrooms': prop.num_bathrooms,
                    'created_date': prop.create_date.isoformat() if prop.create_date else None,
                }
                
                # HATEOAS links (ADR-007)
                property_data['links'] = [
                    {
                        'href': f'/api/v1/properties/{prop.id}',
                        'rel': 'self',
                        'type': 'GET',
                        'title': 'Get property details'
                    }
                ]
                
                property_list.append(property_data)
            
            # Build pagination links
            base_url = f'/api/v1/companies/{company_id}/properties'
            
            # Preserve query parameters in pagination links
            query_params = []
            for key in ['property_type_id', 'property_status', 'city', 'state_id', 
                       'agent_id', 'min_price', 'max_price', 'for_sale', 'for_rent', 'order_by']:
                if key in kwargs:
                    query_params.append(f'{key}={kwargs[key]}')
            
            query_string = '&'.join(query_params)
            if query_string:
                base_url += f'?{query_string}'
                separator = '&'
            else:
                separator = '?'
            
            links = []
            
            # Self link
            links.append({
                'href': f'{base_url}{separator}page={page}&page_size={page_size}',
                'rel': 'self',
                'type': 'GET'
            })
            
            # Previous page
            if page > 1:
                links.append({
                    'href': f'{base_url}{separator}page={page-1}&page_size={page_size}',
                    'rel': 'prev',
                    'type': 'GET'
                })
            
            # Next page
            total_pages = (total + page_size - 1) // page_size
            if page < total_pages:
                links.append({
                    'href': f'{base_url}{separator}page={page+1}&page_size={page_size}',
                    'rel': 'next',
                    'type': 'GET'
                })
            
            # Parent company link
            links.append({
                'href': f'/api/v1/companies/{company_id}',
                'rel': 'parent',
                'type': 'GET',
                'title': 'Get company details'
            })
            
            # Collection link
            links.append({
                'href': '/api/v1/companies',
                'rel': 'collection',
                'type': 'GET',
                'title': 'List all companies'
            })
            
            response, status = paginated_response(
                items=property_list,
                total=total,
                page=page,
                page_size=page_size,
                links=links
            )
            
            return request.make_json_response(response, status=status)
            
        except Exception as e:
            _logger.error(f'Error listing properties for company {company_id}: {str(e)}', exc_info=True)
            return error_response(500, 'Internal server error')
