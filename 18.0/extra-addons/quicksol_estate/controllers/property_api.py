# -*- coding: utf-8 -*-
import json
import logging
import psycopg2
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from .utils.serializers import serialize_property, validate_property_access
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from ..services.company_validator import CompanyValidator

_logger = logging.getLogger(__name__)


class PropertyApiController(http.Controller):
    @http.route('/api/v1/properties',type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_properties(self, **kwargs):
        try:
            user = request.env.user
            
            # Parse query parameters
            is_active = kwargs.get('is_active')  
            company_ids_param = kwargs.get('company_ids')  
            limit = min(int(kwargs.get('limit', 20)), 100)
            offset = int(kwargs.get('offset', 0))
            
            # Validate company_ids parameter (REQUIRED)
            if not company_ids_param:
                return error_response(400, 'company_ids parameter is required')
            
            # Parse company_ids (can be comma-separated: "1,2,3")
            try:
                requested_company_ids = [int(cid.strip()) for cid in company_ids_param.split(',')]
            except ValueError:
                return error_response(400, 'Invalid company_ids format. Use comma-separated integers (e.g., "1,2,3")')
            
            # Validate user has access to all requested companies (multi-tenancy security)
            # Admin users (request.user_company_ids is empty for admins) skip this validation
            if request.user_company_ids:  # Not admin
                unauthorized_companies = [cid for cid in requested_company_ids if cid not in request.user_company_ids]
                if unauthorized_companies:
                    return error_response(403, f'Access denied to company IDs: {unauthorized_companies}. You can only access companies: {request.user_company_ids}')
            
            # Build domain for filtering
            domain = []
            
            # Active filter (ADR-015: soft-delete)
            if is_active is not None:
                if is_active.lower() == 'true':
                    domain.append(('active', '=', True))
                elif is_active.lower() == 'false':
                    domain.append(('active', '=', False))
            # If is_active is None, no filter is applied (returns all)
            
            # Company filter using validated company_ids
            if len(requested_company_ids) == 1:
                domain.append(('company_ids', 'in', requested_company_ids))
            else:
                domain.append(('company_ids', 'in', requested_company_ids))
            
            # Optional filters
            if kwargs.get('property_type_id'):
                try:
                    domain.append(('property_type_id', '=', int(kwargs['property_type_id'])))
                except ValueError:
                    return error_response(400, 'Invalid property_type_id')
            
            if kwargs.get('property_status'):
                status = kwargs['property_status']
                if status not in ['available', 'sold', 'rented', 'unavailable']:
                    return error_response(400, 'Invalid property_status. Must be: available, sold, rented, unavailable')
                domain.append(('property_status', '=', status))
            
            if kwargs.get('agent_id'):
                try:
                    domain.append(('agent_id', '=', int(kwargs['agent_id'])))
                except ValueError:
                    return error_response(400, 'Invalid agent_id')
            
            if kwargs.get('city'):
                domain.append(('city', 'ilike', kwargs['city']))
            
            if kwargs.get('state_id'):
                try:
                    domain.append(('state_id', '=', int(kwargs['state_id'])))
                except ValueError:
                    return error_response(400, 'Invalid state_id')
            
            if kwargs.get('min_price'):
                try:
                    domain.append(('price', '>=', float(kwargs['min_price'])))
                except ValueError:
                    return error_response(400, 'Invalid min_price')
            
            if kwargs.get('max_price'):
                try:
                    domain.append(('price', '<=', float(kwargs['max_price'])))
                except ValueError:
                    return error_response(400, 'Invalid max_price')
            
            if kwargs.get('for_sale') is not None:
                for_sale = kwargs['for_sale'].lower() == 'true'
                domain.append(('for_sale', '=', for_sale))
            
            if kwargs.get('for_rent') is not None:
                for_rent = kwargs['for_rent'].lower() == 'true'
                domain.append(('for_rent', '=', for_rent))
            
            # RBAC filter
            is_admin = user.has_group('base.group_system')
            is_manager = user.has_group('quicksol_estate.group_real_estate_manager')
            is_owner = user.has_group('quicksol_estate.group_real_estate_owner')
            is_agent = user.has_group('quicksol_estate.group_real_estate_agent')
            
            if not is_admin and not is_manager and not is_owner:
                if is_agent:
                    # Agent sees only their assigned properties
                    agent_record = request.env['real.estate.agent'].sudo().search([
                        ('user_id', '=', user.id)
                    ], limit=1)
                    
                    if agent_record:
                        domain.append(('agent_id', '=', agent_record.id))
                    else:
                        # Agent without agent record sees nothing
                        domain.append(('id', '=', False))
            
            # Query properties
            Property = request.env['real.estate.property']
            
            # Use active_test=False to include inactive records when is_active is not specified
            total = Property.with_context(active_test=False).sudo().search_count(domain)
            properties = Property.with_context(active_test=False).sudo().search(
                domain, limit=limit, offset=offset, order='name asc'
            )
            
            # Serialize properties
            property_list = []
            for prop in properties:
                property_list.append(serialize_property(prop))
            
            # Build response with pagination (ADR-007: HATEOAS)
            company_ids_str = ','.join(str(cid) for cid in requested_company_ids)
            response_data = {
                'success': True,
                'data': property_list,
                'count': len(property_list),
                'total': total,
                'limit': limit,
                'offset': offset,
                '_links': {
                    'self': f'/api/v1/properties?company_ids={company_ids_str}&limit={limit}&offset={offset}',
                }
            }
            
            # Add next/prev links
            if offset + limit < total:
                response_data['_links']['next'] = f'/api/v1/properties?company_ids={company_ids_str}&limit={limit}&offset={offset + limit}'
            if offset > 0:
                prev_offset = max(0, offset - limit)
                response_data['_links']['prev'] = f'/api/v1/properties?company_ids={company_ids_str}&limit={limit}&offset={prev_offset}'
            
            return success_response(response_data)
            
        except ValueError as e:
            return error_response(400, f'Invalid parameter: {str(e)}')
        except Exception as e:
            _logger.exception('Error listing properties')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/properties', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_property(self, **kwargs):

        try:
            user = request.env.user
            
            # RBAC: Owners, Managers, and Admins can create properties (ADR-019)
            is_owner = user.has_group('quicksol_estate.group_real_estate_owner')
            is_manager = user.has_group('quicksol_estate.group_real_estate_manager')
            is_admin = user.has_group('base.group_system')
            
            if not (is_owner or is_manager or is_admin):
                return error_response(403, 'Only Owners, Managers, or Admins can create properties')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Garantir que company_ids está presente (usa default se não tiver)
            data = CompanyValidator.ensure_company_ids(data)
            
            # Validar que as empresas estão autorizadas
            company_ids = None
            if 'company_ids' in data:
                # Extrai IDs da tupla many2many (6, 0, [id1, id2])
                if isinstance(data['company_ids'], list) and data['company_ids']:
                    if isinstance(data['company_ids'][0], (tuple, list)):
                        company_ids = data['company_ids'][0][2]
                    else:
                        company_ids = data['company_ids']
            
            if company_ids:
                valid, error = CompanyValidator.validate_company_ids(company_ids)
                if not valid:
                    return error_response(403, error)
            
            # Validate required fields
            required_fields = ['name', 'property_type_id', 'area', 'zip_code', 'state_id', 'city', 'street', 'street_number', 'location_type_id']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return error_response(400, f"Missing required fields: {', '.join(missing_fields)}")
            
            # Prepare property data
            property_vals = {
                'name': data.get('name'),
                'property_type_id': data.get('property_type_id'),
                'area': data.get('area'),
                'zip_code': data.get('zip_code'),
                'state_id': data.get('state_id'),
                'city': data.get('city'),
                'street': data.get('street'),
                'street_number': data.get('street_number'),
                'location_type_id': data.get('location_type_id'),
            }
            
            # Optional fields
            optional_fields = {
                'description': str,
                'price': float,
                'rent_price': float,
                'property_status': str,
                'property_purpose': str,
                'num_rooms': int,
                'num_suites': int,
                'num_bathrooms': int,
                'num_parking': int,
                'total_area': float,
                'agent_id': int,
                'owner_id': int,
                'complement': str,
                'neighborhood': str,
                'latitude': float,
                'longitude': float,
                'condition': str,
                'construction_year': int,
                'for_sale': bool,
                'for_rent': bool,
                'accepts_financing': bool,
                'accepts_fgts': bool,
                # Structure fields
                'building_id': int,
                'floor_number': int,
                'unit_number': str,
                'num_floors': int,
                'private_area': float,
                'land_area': float,
                # Primary data fields
                'iptu_annual': float,
                'insurance_value': float,
                'condominium_fee': float,
                'authorization_start_date': str,
                'authorization_end_date': str,
                'reform_year': int,
                # Zoning fields
                'zoning_type': str,
                'zoning_restrictions': str,
                # Web publishing fields
                'publish_website': bool,
                'publish_featured': bool,
                'publish_super_featured': bool,
                'youtube_video_url': str,
                'virtual_tour_url': str,
                'meta_title': str,
                'meta_description': str,
                'meta_keywords': str,
                'description_short': str,
                'internal_notes': str,
                # Signs fields
                'has_sign': bool,
                'sign_type': str,
                'sign_installation_date': str,
                'sign_removal_date': str,
                'sign_notes': str,
                # Documents fields
                'matricula_number': str,
                'iptu_code': str,
                # Other fields
                'origin_media': str,
            }
            
            for field, field_type in optional_fields.items():
                if field in data and data[field] is not None:
                    property_vals[field] = data[field]
            
            # Handle Many2many fields
            if 'company_ids' in data:
                property_vals['company_ids'] = [(6, 0, data['company_ids'])]
            elif user.company_ids:
                # Assign to user's companies by default
                property_vals['company_ids'] = [(6, 0, user.company_ids.ids)]
            
            if 'tag_ids' in data:
                property_vals['tag_ids'] = [(6, 0, data['tag_ids'])]
            
            if 'amenities' in data:
                property_vals['amenities'] = [(6, 0, data['amenities'])]
            
            # Create property with savepoint to catch integrity errors
            Property = request.env['real.estate.property'].sudo()
            
            try:
                with request.env.cr.savepoint():
                    property_record = Property.create(property_vals)
                    # Force flush to catch integrity errors immediately
                    request.env.cr.flush()
            except Exception as savepoint_error:
                # Handle errors that occur during creation/flush
                error_str = str(savepoint_error)
                if "foreign key constraint" in error_str.lower() or "violates foreign key" in error_str.lower():
                    if "real_estate_amenity" in error_str:
                        return error_response(400, "One or more amenity IDs do not exist. Please verify the amenity IDs.", 'foreign_key_violation')
                    elif "real_estate_property_tag" in error_str:
                        return error_response(400, "One or more tag IDs do not exist. Please verify the tag IDs.", 'foreign_key_violation')
                    elif "real_estate_property_owner" in error_str:
                        return error_response(400, "Owner ID does not exist. Please verify the owner_id.", 'foreign_key_violation')
                    elif "real_estate_agent" in error_str:
                        return error_response(400, "Agent ID does not exist. Please verify the agent_id.", 'foreign_key_violation')
                    elif "real_estate_property_type" in error_str:
                        return error_response(400, "Property type ID does not exist. Please verify the property_type_id.", 'foreign_key_violation')
                    elif "real_estate_location_type" in error_str:
                        return error_response(400, "Location type ID does not exist. Please verify the location_type_id.", 'foreign_key_violation')
                    elif "real_estate_state" in error_str:
                        return error_response(400, "State ID does not exist. Please verify the state_id.", 'foreign_key_violation')
                    elif "real_estate_property_building" in error_str:
                        return error_response(400, "Building ID does not exist. Please verify the building_id.", 'foreign_key_violation')
                    elif "thedevkitchen_estate_company" in error_str:
                        return error_response(400, "One or more company IDs do not exist. Please verify the company_ids.", 'foreign_key_violation')
                    else:
                        return error_response(400, "Invalid reference ID. One or more related records do not exist.", 'foreign_key_violation')
                # Re-raise if not a foreign key error
                raise
            
            # Serialize and return
            property_data = serialize_property(property_record)
            return success_response(property_data, status_code=201)
            
        except ValidationError as e:
            _logger.error(f"Validation error in create_property: {e}")
            return error_response(400, str(e), 'validation_error')
        except AccessError as e:
            _logger.error(f"Access error in create_property: {e}")
            return error_response(403, 'Access denied', 'access_denied')
        except UserError as e:
            _logger.error(f"User error in create_property: {e}")
            return error_response(400, str(e), 'user_error')
        except ValueError as e:
            # Catches "Wrong value for..." errors from Selection fields
            _logger.error(f"Value error in create_property: {e}")
            error_msg = str(e)
            # Extract field name and invalid value for better error message
            if "Wrong value for" in error_msg:
                return error_response(400, error_msg, 'invalid_field_value')
            return error_response(400, error_msg, 'value_error')
        except psycopg2.IntegrityError as e:
            # Catches foreign key violations, unique constraints, etc
            _logger.error(f"Integrity error in create_property: {e}")
            error_msg = str(e)
            
            # Parse foreign key errors for better messages
            if "foreign key constraint" in error_msg.lower():
                # Extract table and key information
                if "real_estate_amenity" in error_msg:
                    return error_response(400, "One or more amenity IDs do not exist. Please verify the amenity IDs.", 'foreign_key_violation')
                elif "real_estate_property_tag" in error_msg:
                    return error_response(400, "One or more tag IDs do not exist. Please verify the tag IDs.", 'foreign_key_violation')
                elif "real_estate_property_owner" in error_msg:
                    return error_response(400, "Owner ID does not exist. Please verify the owner_id.", 'foreign_key_violation')
                elif "real_estate_agent" in error_msg:
                    return error_response(400, "Agent ID does not exist. Please verify the agent_id.", 'foreign_key_violation')
                elif "real_estate_property_type" in error_msg:
                    return error_response(400, "Property type ID does not exist. Please verify the property_type_id.", 'foreign_key_violation')
                elif "real_estate_location_type" in error_msg:
                    return error_response(400, "Location type ID does not exist. Please verify the location_type_id.", 'foreign_key_violation')
                elif "real_estate_state" in error_msg:
                    return error_response(400, "State ID does not exist. Please verify the state_id.", 'foreign_key_violation')
                elif "real_estate_property_building" in error_msg:
                    return error_response(400, "Building ID does not exist. Please verify the building_id.", 'foreign_key_violation')
                elif "thedevkitchen_estate_company" in error_msg:
                    return error_response(400, "One or more company IDs do not exist. Please verify the company_ids.", 'foreign_key_violation')
                else:
                    return error_response(400, "Invalid reference ID. One or more related records do not exist.", 'foreign_key_violation')
            elif "unique constraint" in error_msg.lower():
                return error_response(400, "Duplicate value detected. This record already exists.", 'unique_violation')
            else:
                return error_response(400, f"Data integrity error: {error_msg}", 'integrity_error')
        except Exception as e:
            # Check if it's a wrapped IntegrityError or contains integrity error message
            error_str = str(e)
            _logger.error(f"Unexpected error in create_property: {e}", exc_info=True)
            
            # Check for integrity errors in the exception message
            if "foreign key constraint" in error_str.lower() or "violates foreign key" in error_str.lower():
                if "real_estate_amenity" in error_str:
                    return error_response(400, "One or more amenity IDs do not exist. Please verify the amenity IDs.", 'foreign_key_violation')
                elif "real_estate_property_tag" in error_str:
                    return error_response(400, "One or more tag IDs do not exist. Please verify the tag IDs.", 'foreign_key_violation')
                elif "real_estate_property_owner" in error_str:
                    return error_response(400, "Owner ID does not exist. Please verify the owner_id.", 'foreign_key_violation')
                elif "real_estate_agent" in error_str:
                    return error_response(400, "Agent ID does not exist. Please verify the agent_id.", 'foreign_key_violation')
                elif "real_estate_property_type" in error_str:
                    return error_response(400, "Property type ID does not exist. Please verify the property_type_id.", 'foreign_key_violation')
                elif "real_estate_location_type" in error_str:
                    return error_response(400, "Location type ID does not exist. Please verify the location_type_id.", 'foreign_key_violation')
                elif "real_estate_state" in error_str:
                    return error_response(400, "State ID does not exist. Please verify the state_id.", 'foreign_key_violation')
                elif "real_estate_property_building" in error_str:
                    return error_response(400, "Building ID does not exist. Please verify the building_id.", 'foreign_key_violation')
                elif "thedevkitchen_estate_company" in error_str:
                    return error_response(400, "One or more company IDs do not exist. Please verify the company_ids.", 'foreign_key_violation')
                else:
                    return error_response(400, "Invalid reference ID. One or more related records do not exist.", 'foreign_key_violation')
            
            return error_response(500, f'Internal server error: {str(e)}', 'internal_error')
    
    @http.route('/api/v1/properties/<int:property_id>',type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            
            # Search for property with company filter
            Property = request.env['real.estate.property'].sudo()
            domain = [('id', '=', property_id)] + request.company_domain
            property_record = Property.search(domain, limit=1)
            
            # Check if property exists and user has access
            if not property_record:
                return error_response(404, 'Property not found')
            
            # Serialize and return
            property_data = serialize_property(property_record)
            return success_response(property_data)
            
        except AccessError as e:
            _logger.error(f"Access error in get_property: {e}")
            return error_response(403, 'Access denied')
        except Exception as e:
            _logger.error(f"Error in get_property: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/properties/<int:property_id>',type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            
            # Parse request body - use get_json_data() to avoid consuming request body twice
            try:
                data = request.get_json_data()
                if data is None:
                    return error_response(400, 'Invalid JSON in request body')
            except Exception:
                return error_response(400, 'Invalid JSON in request body')
            
            # IMPORTANTE: Bloquear alteração de company_ids via API
            if 'company_ids' in data:
                return error_response(403, 'Cannot change company_ids via API')
            
            # Search for property with company filter
            Property = request.env['real.estate.property'].sudo()
            domain = [('id', '=', property_id)] + request.company_domain
            property_record = Property.search(domain, limit=1)
            
            # Check if property exists and user has access
            if not property_record:
                return error_response(404, 'Property not found')
            
            # Build update values (only allowed fields)
            allowed_fields = {
                'name', 'description', 'price', 'status', 'street', 'street2',
                'city', 'state_id', 'zip_code', 'bedrooms', 'bathrooms', 
                'garage_spaces', 'total_area'
            }
            
            update_vals = {}
            for key, value in data.items():
                if key in allowed_fields:
                    update_vals[key] = value
            
            if not update_vals:
                return error_response(400, 'No valid fields to update')
            
            # Update property
            property_record.write(update_vals)
            
            # Return updated property
            property_data = serialize_property(property_record)
            return success_response(property_data)
            
        except ValidationError as e:
            _logger.error(f"Validation error in update_property: {e}")
            return error_response(400, str(e), 'validation_error')
        except AccessError as e:
            _logger.error(f"Access error in update_property: {e}")
            return error_response(403, 'Access denied', 'access_denied')
        except UserError as e:
            _logger.error(f"User error in update_property: {e}")
            return error_response(400, str(e), 'user_error')
        except ValueError as e:
            # Catches "Wrong value for..." errors from Selection fields
            _logger.error(f"Value error in update_property: {e}")
            error_msg = str(e)
            if "Wrong value for" in error_msg:
                return error_response(400, error_msg, 'invalid_field_value')
            return error_response(400, error_msg, 'value_error')
        except psycopg2.IntegrityError as e:
            # Catches foreign key violations, unique constraints, etc
            _logger.error(f"Integrity error in update_property: {e}")
            error_msg = str(e)
            
            if "foreign key constraint" in error_msg.lower():
                if "real_estate_amenity" in error_msg:
                    return error_response(400, "One or more amenity IDs do not exist. Please verify the amenity IDs.", 'foreign_key_violation')
                elif "real_estate_property_tag" in error_msg:
                    return error_response(400, "One or more tag IDs do not exist. Please verify the tag IDs.", 'foreign_key_violation')
                else:
                    return error_response(400, "Invalid reference ID. One or more related records do not exist.", 'foreign_key_violation')
            elif "unique constraint" in error_msg.lower():
                return error_response(400, "Duplicate value detected. This record already exists.", 'unique_violation')
            else:
                return error_response(400, f"Data integrity error: {error_msg}", 'integrity_error')
        except Exception as e:
            _logger.error(f"Unexpected error in update_property: {e}", exc_info=True)
            return error_response(500, f'Internal server error: {str(e)}', 'internal_error')
    
    @http.route('/api/v1/properties/<int:property_id>',type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_property(self, property_id, **kwargs):
        try:
            user = request.env.user
            
            # Only managers can delete properties
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can delete properties')
            
            # Search for property with company filter
            Property = request.env['real.estate.property'].sudo()
            domain = [('id', '=', property_id)] + request.company_domain
            property_record = Property.search(domain, limit=1)
            
            # Check if property exists and user has access
            if not property_record:
                return error_response(404, 'Property not found')
            
            # Delete property
            property_title = property_record.name
            property_record.unlink()
            
            # Return success message
            return success_response({
                'message': 'Property deleted successfully',
                'id': property_id,
                'name': property_title
            })
            
        except AccessError as e:
            _logger.error(f"Access error in delete_property: {e}")
            return error_response(403, 'Access denied')
        except Exception as e:
            _logger.error(f"Error in delete_property: {e}")
            return error_response(500, 'Internal server error')


# Aliases for backward compatibility with tests
_serialize_property = serialize_property
_validate_property_access = validate_property_access
_error_response = error_response
_success_response = success_response
