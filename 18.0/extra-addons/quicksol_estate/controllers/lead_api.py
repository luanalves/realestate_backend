# -*- coding: utf-8 -*-
"""
Lead API Controller

RESTful API endpoints for lead management with agent isolation,
multi-tenant support, and pipeline state tracking.

Author: Quicksol Technologies
Date: 2026-01-29
Branch: 006-lead-management
ADRs: ADR-005 (OpenAPI), ADR-007 (HATEOAS), ADR-008 (Multi-tenancy),
      ADR-011 (Security), ADR-015 (Soft-delete)
FRs: FR-001 to FR-047 (see specs/006-lead-management/spec.md)
"""

import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError, ValidationError
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company

_logger = logging.getLogger(__name__)


class LeadApiController(http.Controller):
    """REST API Controller for Lead endpoints following ADR-011"""
    
    @http.route('/api/v1/leads', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_leads(self, **kwargs):
        """
        List leads with pagination and filtering (FR-019, FR-024, FR-031).
        
        Query Parameters:
            - state: Filter by state (new/contacted/qualified/won/lost)
            - agent_id: Filter by agent (managers only)
            - search: Free-text search across name, phone, email
            - active: Filter by active status ('true', 'false', 'all')
            - limit: Number of records to return (default: 20, max: 100)
            - offset: Number of records to skip (default: 0)
            
        Returns:
            JSON object with lead list and pagination metadata
        """
        try:
            user = request.env.user
            
            # Parse query parameters
            state_filter = kwargs.get('state')
            agent_filter = kwargs.get('agent_id')
            search_query = kwargs.get('search', '').strip()
            active_filter = kwargs.get('active', 'true')
            limit = min(int(kwargs.get('limit', 20)), 100)
            offset = int(kwargs.get('offset', 0))
            
            # Build domain for filtering
            domain = []
            
            # Active filter (ADR-015: soft-delete)
            if active_filter == 'true':
                domain.append(('active', '=', True))
            elif active_filter == 'false':
                domain.append(('active', '=', False))
            # 'all' includes both active and inactive
            
            # State filter
            if state_filter:
                domain.append(('state', '=', state_filter))
            
            # Agent filter (managers can filter by agent)
            if agent_filter and user.has_group('quicksol_estate.group_real_estate_manager'):
                domain.append(('agent_id', '=', int(agent_filter)))
            
            # Free-text search
            if search_query:
                domain.append('|')
                domain.append('|')
                domain.append(('name', 'ilike', search_query))
                domain.append(('phone', 'ilike', search_query))
                domain.append(('email', 'ilike', search_query))
            
            # Query leads (record rules auto-filter by agent/company)
            Lead = request.env['real.estate.lead']
            
            total = Lead.with_context(active_test=False).sudo().search_count(domain)
            leads = Lead.sudo().search(domain, limit=limit, offset=offset, order='create_date desc')
            
            # Serialize leads
            lead_list = []
            for lead in leads:
                lead_data = {
                    'id': lead.id,
                    'name': lead.name,
                    'state': lead.state,
                    'phone': lead.phone,
                    'email': lead.email,
                    'agent_id': lead.agent_id.id if lead.agent_id else None,
                    'agent_name': lead.agent_id.name if lead.agent_id else None,
                    'budget_min': lead.budget_min,
                    'budget_max': lead.budget_max,
                    'property_type_interest': lead.property_type_interest.name if lead.property_type_interest else None,
                    'first_contact_date': lead.first_contact_date.strftime('%Y-%m-%d') if lead.first_contact_date else None,
                    'expected_closing_date': lead.expected_closing_date.strftime('%Y-%m-%d') if lead.expected_closing_date else None,
                    'days_in_state': lead.days_in_state,
                    'created_at': lead.create_date.strftime('%Y-%m-%d %H:%M:%S') if lead.create_date else None,
                    'updated_at': lead.write_date.strftime('%Y-%m-%d %H:%M:%S') if lead.write_date else None,
                }
                lead_list.append(lead_data)
            
            # Build response
            response_data = {
                'leads': lead_list,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_next': (offset + limit) < total
                }
            }
            
            return success_response(response_data, 200)
            
        except Exception as e:
            _logger.error(f"Error listing leads: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_lead(self, **kwargs):
        """
        Create new lead (FR-001, FR-002, FR-003, FR-004, FR-005).
        
        Request Body (JSON):
            - name: Lead title (required, max 100 chars)
            - phone: Phone number (optional, max 20 chars)
            - email: Email address (optional, max 120 chars)
            - partner_id: Contact ID (optional)
            - state: Initial state (optional, default: 'new')
            - budget_min: Minimum budget (optional, BRL)
            - budget_max: Maximum budget (optional, BRL)
            - property_type_interest: Property type ID (optional)
            - location_preference: Location preference (optional, max 200 chars)
            - bedrooms_needed: Number of bedrooms (optional)
            - min_area: Minimum area m² (optional)
            - max_area: Maximum area m² (optional)
            - property_interest: Property of interest ID (optional)
            - first_contact_date: First contact date (optional, YYYY-MM-DD)
            - expected_closing_date: Expected closing date (optional, YYYY-MM-DD)
            
        Returns:
            JSON object with created lead
        """
        try:
            # Parse JSON body
            body_data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            if not body_data.get('name'):
                return error_response('Field "name" is required', 400, 'VALIDATION_ERROR')
            
            # Build lead values (agent_id and company_ids auto-assigned via defaults)
            lead_vals = {
                'name': body_data['name'],
            }
            
            # Optional fields
            if body_data.get('phone'):
                lead_vals['phone'] = body_data['phone']
            if body_data.get('email'):
                lead_vals['email'] = body_data['email']
            if body_data.get('partner_id'):
                lead_vals['partner_id'] = int(body_data['partner_id'])
            if body_data.get('state'):
                lead_vals['state'] = body_data['state']
            if body_data.get('budget_min'):
                lead_vals['budget_min'] = float(body_data['budget_min'])
            if body_data.get('budget_max'):
                lead_vals['budget_max'] = float(body_data['budget_max'])
            if body_data.get('property_type_interest'):
                lead_vals['property_type_interest'] = int(body_data['property_type_interest'])
            if body_data.get('location_preference'):
                lead_vals['location_preference'] = body_data['location_preference']
            if body_data.get('bedrooms_needed'):
                lead_vals['bedrooms_needed'] = int(body_data['bedrooms_needed'])
            if body_data.get('min_area'):
                lead_vals['min_area'] = float(body_data['min_area'])
            if body_data.get('max_area'):
                lead_vals['max_area'] = float(body_data['max_area'])
            if body_data.get('property_interest'):
                lead_vals['property_interest'] = int(body_data['property_interest'])
            if body_data.get('first_contact_date'):
                lead_vals['first_contact_date'] = body_data['first_contact_date']
            if body_data.get('expected_closing_date'):
                lead_vals['expected_closing_date'] = body_data['expected_closing_date']
            
            # Create lead (validation constraints run automatically)
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().create(lead_vals)
            
            # Serialize response
            response_data = self._serialize_lead(lead)
            
            return success_response(response_data, 201)
            
        except ValidationError as ve:
            _logger.warning(f"Validation error creating lead: {str(ve)}")
            return error_response(str(ve), 400, 'VALIDATION_ERROR')
        except Exception as e:
            _logger.error(f"Error creating lead: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_lead(self, lead_id, **kwargs):
        """
        Get lead details (FR-020, FR-025, FR-032).
        
        Returns:
            JSON object with full lead details
        """
        try:
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().browse(lead_id)
            
            if not lead.exists():
                return error_response(f'Lead with ID {lead_id} not found', 404, 'NOT_FOUND')
            
            # Check access (record rules enforce agent isolation)
            try:
                lead.check_access_rights('read')
                lead.check_access_rule('read')
            except AccessError:
                return error_response('Access denied', 403, 'ACCESS_DENIED')
            
            # Serialize response
            response_data = self._serialize_lead(lead)
            
            return success_response(response_data, 200)
            
        except Exception as e:
            _logger.error(f"Error getting lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>', 
                type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_lead(self, lead_id, **kwargs):
        """
        Update lead (FR-007, FR-008, FR-009, FR-021, FR-022).
        
        Request Body (JSON): Same fields as create_lead (all optional)
        
        Returns:
            JSON object with updated lead
        """
        try:
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().browse(lead_id)
            
            if not lead.exists():
                return error_response(f'Lead with ID {lead_id} not found', 404, 'NOT_FOUND')
            
            # Check access
            try:
                lead.check_access_rights('write')
                lead.check_access_rule('write')
            except AccessError:
                return error_response('Access denied', 403, 'ACCESS_DENIED')
            
            # Parse JSON body
            body_data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Build update values
            update_vals = {}
            
            # Agents cannot change agent_id (FR-022)
            user = request.env.user
            is_agent = user.has_group('quicksol_estate.group_real_estate_agent')
            is_manager = user.has_group('quicksol_estate.group_real_estate_manager')
            
            if 'agent_id' in body_data and is_agent and not is_manager:
                return error_response('Agents cannot change agent assignment', 403, 'PERMISSION_DENIED')
            
            # Update allowed fields
            allowed_fields = [
                'name', 'phone', 'email', 'partner_id', 'state',
                'budget_min', 'budget_max', 'property_type_interest',
                'location_preference', 'bedrooms_needed', 'min_area', 'max_area',
                'property_interest', 'first_contact_date', 'expected_closing_date',
                'lost_reason'
            ]
            
            if is_manager:
                allowed_fields.append('agent_id')
            
            for field in allowed_fields:
                if field in body_data:
                    if field in ['partner_id', 'property_type_interest', 'property_interest', 'agent_id']:
                        update_vals[field] = int(body_data[field]) if body_data[field] else False
                    elif field in ['budget_min', 'budget_max', 'min_area', 'max_area']:
                        update_vals[field] = float(body_data[field]) if body_data[field] else 0.0
                    elif field == 'bedrooms_needed':
                        update_vals[field] = int(body_data[field]) if body_data[field] else 0
                    else:
                        update_vals[field] = body_data[field]
            
            # Update lead (validation constraints and write override run automatically)
            lead.write(update_vals)
            
            # Serialize response
            response_data = self._serialize_lead(lead)
            
            return success_response(response_data, 200)
            
        except ValidationError as ve:
            _logger.warning(f"Validation error updating lead {lead_id}: {str(ve)}")
            return error_response(str(ve), 400, 'VALIDATION_ERROR')
        except Exception as e:
            _logger.error(f"Error updating lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>', 
                type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_lead(self, lead_id, **kwargs):
        """
        Archive lead (soft delete) (FR-018b).
        
        Returns:
            204 No Content on success
        """
        try:
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().browse(lead_id)
            
            if not lead.exists():
                return error_response(f'Lead with ID {lead_id} not found', 404, 'NOT_FOUND')
            
            # Check access
            try:
                lead.check_access_rights('unlink')
                lead.check_access_rule('unlink')
            except AccessError:
                return error_response('Access denied', 403, 'ACCESS_DENIED')
            
            # Soft delete (unlink override sets active=False)
            lead.unlink()
            
            return Response(status=204)
            
        except Exception as e:
            _logger.error(f"Error deleting lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>/convert', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def convert_lead(self, lead_id, **kwargs):
        """
        Convert lead to sale (FR-010, FR-011, FR-012, FR-013, FR-014).
        
        Request Body (JSON):
            - property_id: Property ID to link to sale (required)
            
        Returns:
            JSON object with conversion result
        """
        try:
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().browse(lead_id)
            
            if not lead.exists():
                return error_response(f'Lead with ID {lead_id} not found', 404, 'NOT_FOUND')
            
            # Check access
            try:
                lead.check_access_rights('write')
                lead.check_access_rule('write')
            except AccessError:
                return error_response('Access denied', 403, 'ACCESS_DENIED')
            
            # Parse JSON body
            body_data = json.loads(request.httprequest.data.decode('utf-8'))
            
            if not body_data.get('property_id'):
                return error_response('Field "property_id" is required', 400, 'VALIDATION_ERROR')
            
            property_id = int(body_data['property_id'])
            
            # Call model method (handles atomic transaction and validation)
            sale_id = lead.action_convert_to_sale(property_id)
            
            # Load sale and serialize response
            Sale = request.env['real.estate.sale']
            sale = Sale.sudo().browse(sale_id)
            
            response_data = {
                'lead_id': lead.id,
                'lead_state': lead.state,
                'sale_id': sale.id,
                'property_id': property_id,
                'message': 'Lead converted successfully'
            }
            
            return success_response(response_data, 200)
            
        except ValidationError as ve:
            _logger.warning(f"Validation error converting lead {lead_id}: {str(ve)}")
            return error_response(str(ve), 400, 'VALIDATION_ERROR')
        except Exception as e:
            _logger.error(f"Error converting lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>/reopen', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def reopen_lead(self, lead_id, **kwargs):
        """
        Reopen lost lead (FR-018a).
        
        Request Body (JSON):
            - reason: Reason for reopening (optional)
            
        Returns:
            JSON object with reopened lead
        """
        try:
            Lead = request.env['real.estate.lead']
            lead = Lead.sudo().browse(lead_id)
            
            if not lead.exists():
                return error_response(f'Lead with ID {lead_id} not found', 404, 'NOT_FOUND')
            
            # Check access
            try:
                lead.check_access_rights('write')
                lead.check_access_rule('write')
            except AccessError:
                return error_response('Access denied', 403, 'ACCESS_DENIED')
            
            # Call model method (validates state == 'lost')
            lead.action_reopen()
            
            # Serialize response
            response_data = self._serialize_lead(lead)
            
            return success_response(response_data, 200)
            
        except UserError as ue:
            _logger.warning(f"User error reopening lead {lead_id}: {str(ue)}")
            return error_response(str(ue), 400, 'INVALID_STATE')
        except Exception as e:
            _logger.error(f"Error reopening lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    # ==================== PRIVATE HELPERS ====================
    
    def _serialize_lead(self, lead):
        """Serialize lead record to JSON (ADR-007: HATEOAS)"""
        data = {
            'id': lead.id,
            'name': lead.name,
            'active': lead.active,
            'state': lead.state,
            'phone': lead.phone,
            'email': lead.email,
            'partner_id': lead.partner_id.id if lead.partner_id else None,
            'partner_name': lead.partner_id.name if lead.partner_id else None,
            'agent_id': lead.agent_id.id if lead.agent_id else None,
            'agent_name': lead.agent_id.name if lead.agent_id else None,
            'company_ids': lead.company_ids.ids if lead.company_ids else [],
            'budget_min': lead.budget_min,
            'budget_max': lead.budget_max,
            'property_type_interest': lead.property_type_interest.name if lead.property_type_interest else None,
            'location_preference': lead.location_preference,
            'bedrooms_needed': lead.bedrooms_needed,
            'min_area': lead.min_area,
            'max_area': lead.max_area,
            'property_interest': lead.property_interest.id if lead.property_interest else None,
            'property_interest_name': lead.property_interest.name if lead.property_interest else None,
            'first_contact_date': lead.first_contact_date.strftime('%Y-%m-%d') if lead.first_contact_date else None,
            'expected_closing_date': lead.expected_closing_date.strftime('%Y-%m-%d') if lead.expected_closing_date else None,
            'lost_date': lead.lost_date.strftime('%Y-%m-%d') if lead.lost_date else None,
            'lost_reason': lead.lost_reason,
            'converted_property_id': lead.converted_property_id.id if lead.converted_property_id else None,
            'converted_sale_id': lead.converted_sale_id.id if lead.converted_sale_id else None,
            'days_in_state': lead.days_in_state,
            'created_at': lead.create_date.strftime('%Y-%m-%d %H:%M:%S') if lead.create_date else None,
            'updated_at': lead.write_date.strftime('%Y-%m-%d %H:%M:%S') if lead.write_date else None,
        }
        
        return data
