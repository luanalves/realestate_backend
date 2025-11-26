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

_logger = logging.getLogger(__name__)


class PropertyApiController(http.Controller):
    """REST API Controller for Property endpoints"""
    
    @http.route('/api/v1/properties', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    def create_property(self, **kwargs):
        """
        Create a new property.
        
        Requires: JWT token with 'write' scope
        Body: JSON object with property data
        Returns: JSON object with created property details
        """
        try:
            user = request.env.user
            
            # Only managers and admins can create properties
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can create properties')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
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
    
    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    def get_property(self, property_id, **kwargs):
        """
        Get property details by ID.
        
        Requires: JWT token with 'read' scope
        Returns: JSON object with property details
        """
        try:
            user = request.env.user
            
            # Search for property
            Property = request.env['real.estate.property'].sudo()
            property_record = Property.browse(property_id)
            
            # Check if property exists
            if not property_record.exists():
                return error_response(404, 'Property not found')
            
            # Validate access
            has_access, error_msg = validate_property_access(property_record, user, 'read')
            if not has_access:
                return error_response(403, error_msg)
            
            # Serialize and return
            property_data = serialize_property(property_record)
            return success_response(property_data)
            
        except AccessError as e:
            _logger.error(f"Access error in get_property: {e}")
            return error_response(403, 'Access denied')
        except Exception as e:
            _logger.error(f"Error in get_property: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    def update_property(self, property_id, **kwargs):
        """
        Update property by ID.
        
        Requires: JWT token with 'write' scope
        Body: JSON object with fields to update
        Returns: JSON object with updated property details
        """
        try:
            user = request.env.user
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Search for property
            Property = request.env['real.estate.property'].sudo()
            property_record = Property.browse(property_id)
            
            # Check if property exists
            if not property_record.exists():
                return error_response(404, 'Property not found')
            
            # Validate access
            has_access, error_msg = validate_property_access(property_record, user, 'write')
            if not has_access:
                return error_response(403, error_msg)
            
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
    
    @http.route('/api/v1/properties/<int:property_id>', 
                type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    def delete_property(self, property_id, **kwargs):
        """
        Delete property by ID.
        
        Requires: JWT token with 'write' scope AND Manager role
        Returns: JSON object confirming deletion
        """
        try:
            user = request.env.user
            
            # Only managers can delete properties
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can delete properties')
            
            # Search for property
            Property = request.env['real.estate.property'].sudo()
            property_record = Property.browse(property_id)
            
            # Check if property exists
            if not property_record.exists():
                return error_response(404, 'Property not found')
            
            # Validate access
            has_access, error_msg = validate_property_access(property_record, user, 'delete')
            if not has_access:
                return error_response(403, error_msg)
            
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
