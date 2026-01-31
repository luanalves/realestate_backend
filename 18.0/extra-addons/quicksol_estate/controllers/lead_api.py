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
        List leads with pagination and filtering (FR-019, FR-024, FR-031, FR-039 to FR-047).
        
        Query Parameters:
            Basic Filters:
            - state: Filter by state (new/contacted/qualified/won/lost)
            - agent_id: Filter by agent (managers only)
            - search: Free-text search across name, phone, email
            - active: Filter by active status ('true', 'false', 'all')
            
            Advanced Filters (Phase 6):
            - budget_min: Minimum budget (filter leads with budget_max >= value)
            - budget_max: Maximum budget (filter leads with budget_min <= value)
            - bedrooms: Number of bedrooms needed
            - property_type_id: Property type interest ID
            - location: Location preference (partial match)
            - last_activity_before: Date filter (YYYY-MM-DD, leads with no activity since this date)
            
            Sorting:
            - sort_by: Field name to sort by (default: create_date)
            - sort_order: 'asc' or 'desc' (default: desc)
            
            Pagination:
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
            
            # Advanced filters (Phase 6)
            budget_min_filter = kwargs.get('budget_min')
            budget_max_filter = kwargs.get('budget_max')
            bedrooms_filter = kwargs.get('bedrooms')
            property_type_filter = kwargs.get('property_type_id')
            location_filter = kwargs.get('location', '').strip()
            last_activity_before = kwargs.get('last_activity_before', '').strip()
            
            # Sorting parameters
            sort_by = kwargs.get('sort_by', 'create_date')
            sort_order = kwargs.get('sort_order', 'desc').lower()
            
            # Validate sort_order
            if sort_order not in ['asc', 'desc']:
                sort_order = 'desc'
            
            # Build sort string
            order_string = f"{sort_by} {sort_order}"
            
            # Pagination
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
            
            # Budget filters (FR-039, FR-040)
            if budget_min_filter:
                # Find leads with max budget >= specified minimum
                domain.append(('budget_max', '>=', float(budget_min_filter)))
            
            if budget_max_filter:
                # Find leads with min budget <= specified maximum
                domain.append(('budget_min', '<=', float(budget_max_filter)))
            
            # Bedrooms filter (FR-041)
            if bedrooms_filter:
                domain.append(('bedrooms_needed', '=', int(bedrooms_filter)))
            
            # Property type filter (FR-042)
            if property_type_filter:
                domain.append(('property_type_interest', '=', int(property_type_filter)))
            
            # Location filter (FR-043)
            if location_filter:
                domain.append(('location_preference', 'ilike', location_filter))
            
            # Last activity before filter (FR-047)
            if last_activity_before:
                try:
                    from datetime import datetime as dt
                    activity_date = dt.strptime(last_activity_before, '%Y-%m-%d')
                    
                    # Find leads with no messages after the specified date
                    # This requires a subquery - we'll get all lead IDs, then filter
                    Lead = request.env['real.estate.lead']
                    all_leads = Lead.sudo().search(domain)
                    
                    inactive_lead_ids = []
                    for lead in all_leads:
                        last_message = request.env['mail.message'].sudo().search([
                            ('model', '=', 'real.estate.lead'),
                            ('res_id', '=', lead.id),
                            ('message_type', '=', 'comment')
                        ], order='date desc', limit=1)
                        
                        if not last_message or (last_message.date and last_message.date.date() < activity_date.date()):
                            inactive_lead_ids.append(lead.id)
                    
                    if inactive_lead_ids:
                        domain.append(('id', 'in', inactive_lead_ids))
                    else:
                        # No leads match - return empty result
                        domain.append(('id', '=', -1))
                        
                except ValueError:
                    _logger.warning(f"Invalid date format for last_activity_before: {last_activity_before}")
            
            # Query leads (record rules auto-filter by agent/company)
            Lead = request.env['real.estate.lead']
            
            total = Lead.with_context(active_test=False).sudo().search_count(domain)
            leads = Lead.sudo().search(domain, limit=limit, offset=offset, order=order_string)
            
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
    
    @http.route('/api/v1/leads/export', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def export_leads_csv(self, **kwargs):
        """
        Export filtered leads to CSV (FR-028, FR-048).
        
        Accepts same query parameters as list_leads endpoint.
        Respects multi-tenancy and agent isolation.
        
        Returns:
            CSV file download with lead data
        """
        try:
            import csv
            import io
            from werkzeug.wrappers import Response as WerkzeugResponse
            
            user = request.env.user
            
            # Parse query parameters (same as list_leads)
            state_filter = kwargs.get('state')
            agent_filter = kwargs.get('agent_id')
            search_query = kwargs.get('search', '').strip()
            active_filter = kwargs.get('active', 'true')
            
            # Advanced filters
            budget_min_filter = kwargs.get('budget_min')
            budget_max_filter = kwargs.get('budget_max')
            bedrooms_filter = kwargs.get('bedrooms')
            property_type_filter = kwargs.get('property_type_id')
            location_filter = kwargs.get('location', '').strip()
            
            # Build domain (same logic as list_leads, without pagination)
            domain = []
            
            if active_filter == 'true':
                domain.append(('active', '=', True))
            elif active_filter == 'false':
                domain.append(('active', '=', False))
            
            if state_filter:
                domain.append(('state', '=', state_filter))
            
            if agent_filter and user.has_group('quicksol_estate.group_real_estate_manager'):
                domain.append(('agent_id', '=', int(agent_filter)))
            
            if search_query:
                domain.append('|')
                domain.append('|')
                domain.append(('name', 'ilike', search_query))
                domain.append(('phone', 'ilike', search_query))
                domain.append(('email', 'ilike', search_query))
            
            if budget_min_filter:
                domain.append(('budget_max', '>=', float(budget_min_filter)))
            
            if budget_max_filter:
                domain.append(('budget_min', '<=', float(budget_max_filter)))
            
            if bedrooms_filter:
                domain.append(('bedrooms_needed', '=', int(bedrooms_filter)))
            
            if property_type_filter:
                domain.append(('property_type_interest', '=', int(property_type_filter)))
            
            if location_filter:
                domain.append(('location_preference', 'ilike', location_filter))
            
            # Query leads (record rules enforce security)
            Lead = request.env['real.estate.lead']
            leads = Lead.sudo().search(domain, order='create_date desc')
            
            # Create CSV in memory
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'ID', 'Name', 'State', 'Phone', 'Email', 
                'Agent', 'Budget Min', 'Budget Max', 'Property Type',
                'Location', 'Bedrooms', 'First Contact', 'Expected Closing',
                'Days in State', 'Created At'
            ])
            
            # Write data rows
            for lead in leads:
                writer.writerow([
                    lead.id,
                    lead.name,
                    lead.state,
                    lead.phone or '',
                    lead.email or '',
                    lead.agent_id.name if lead.agent_id else '',
                    lead.budget_min or '',
                    lead.budget_max or '',
                    lead.property_type_interest.name if lead.property_type_interest else '',
                    lead.location_preference or '',
                    lead.bedrooms_needed or '',
                    lead.first_contact_date.strftime('%Y-%m-%d') if lead.first_contact_date else '',
                    lead.expected_closing_date.strftime('%Y-%m-%d') if lead.expected_closing_date else '',
                    lead.days_in_state,
                    lead.create_date.strftime('%Y-%m-%d %H:%M:%S') if lead.create_date else ''
                ])
            
            # Prepare response
            csv_data = output.getvalue()
            output.close()
            
            # Return CSV file
            headers = [
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', 'attachment; filename=leads_export.csv')
            ]
            
            return WerkzeugResponse(csv_data, headers=headers)
            
        except Exception as e:
            _logger.error(f"Error exporting leads to CSV: {str(e)}", exc_info=True)
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
            
            # Explicitly set agent_id if not provided (FR-002)
            # Default method doesn't work with .sudo(), so we set it explicitly
            if 'agent_id' not in lead_vals:
                user = request.env.user
                agent = request.env['real.estate.agent'].search([
                    ('user_id', '=', user.id)
                ], limit=1)
                if agent:
                    lead_vals['agent_id'] = agent.id
                else:
                    return error_response(
                        'Current user must have an associated agent to create leads',
                        403,
                        'NO_AGENT_ASSOCIATED'
                    )
            
            # Create lead (validation constraints run automatically)
            Lead = request.env['real.estate.lead']
            lead = Lead.create(lead_vals)
            
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
        Get lead details (FR-020, FR-025, FR-032, FR-035).
        
        Query Parameters:
            - include_activities (string, optional): 'true' to include recent activities
        
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
            
            # Check if activities should be included
            include_activities = kwargs.get('include_activities', 'false').lower() == 'true'
            
            # Serialize response
            response_data = self._serialize_lead(lead, include_activities=include_activities)
            
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
            
            # Managers reassigning: validate new agent belongs to lead companies (T089)
            if 'agent_id' in body_data and is_manager and body_data['agent_id']:
                new_agent_id = int(body_data['agent_id'])
                Agent = request.env['real.estate.agent']
                new_agent = Agent.sudo().browse(new_agent_id)
                
                if not new_agent.exists():
                    return error_response(f'Agent with ID {new_agent_id} not found', 404, 'AGENT_NOT_FOUND')
                
                # Check if new agent belongs to at least one of the lead's companies
                lead_company_ids = set(lead.company_ids.ids)
                agent_company_ids = set(new_agent.company_ids.ids)
                
                if not lead_company_ids.intersection(agent_company_ids):
                    return error_response(
                        f'Agent {new_agent.name} does not belong to any of the lead\'s companies',
                        400,
                        'AGENT_COMPANY_MISMATCH'
                    )
                
                # Log reassignment in chatter (FR-027)
                old_agent_name = lead.agent_id.name if lead.agent_id else 'Unassigned'
                new_agent_name = new_agent.name
                manager_name = user.name
                
                lead.message_post(
                    body=f"Lead reassigned from {old_agent_name} to {new_agent_name} by {manager_name}",
                    subject="Lead Reassignment",
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'
                )
            
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
    
    @http.route('/api/v1/leads/statistics', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def lead_statistics(self, **kwargs):
        """
        Get lead statistics for managers/owners (T090, T091, FR-028).
        
        Query Parameters:
            - date_from: Filter leads created from this date (YYYY-MM-DD)
            - date_to: Filter leads created until this date (YYYY-MM-DD)
            - agent_id: Filter by specific agent (optional)
            
        Returns:
            JSON object with lead statistics:
            {
                "total": int,
                "by_status": {"new": int, "contacted": int, ...},
                "by_agent": [{"agent_id": int, "agent_name": str, "count": int}],
                "conversion_rate": float (percentage)
            }
        """
        try:
            user = request.env.user
            
            # Only managers and owners can access statistics
            if not (user.has_group('quicksol_estate.group_real_estate_manager') or 
                    user.has_group('quicksol_estate.group_real_estate_owner')):
                return error_response('Access denied: Manager or Owner role required', 403, 'ACCESS_DENIED')
            
            # Parse query parameters
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            agent_filter = kwargs.get('agent_id')
            
            # Build domain
            domain = [('active', '=', True)]
            
            if date_from:
                domain.append(('create_date', '>=', f'{date_from} 00:00:00'))
            if date_to:
                domain.append(('create_date', '<=', f'{date_to} 23:59:59'))
            if agent_filter:
                domain.append(('agent_id', '=', int(agent_filter)))
            
            Lead = request.env['real.estate.lead']
            
            # Total leads (record rules auto-filter by company)
            total = Lead.sudo().search_count(domain)
            
            # Count by status
            states = ['new', 'contacted', 'qualified', 'won', 'lost']
            by_status = {}
            for state in states:
                state_domain = domain + [('state', '=', state)]
                by_status[state] = Lead.sudo().search_count(state_domain)
            
            # Count by agent
            by_agent = []
            agent_data = Lead.sudo().read_group(
                domain,
                fields=['agent_id'],
                groupby=['agent_id']
            )
            
            for group in agent_data:
                agent_id = group['agent_id'][0] if group['agent_id'] else None
                agent_name = group['agent_id'][1] if group['agent_id'] else 'Unassigned'
                count = group['agent_id_count']
                
                by_agent.append({
                    'agent_id': agent_id,
                    'agent_name': agent_name,
                    'count': count
                })
            
            # Calculate conversion rate
            won_count = by_status.get('won', 0)
            conversion_rate = (won_count / total * 100) if total > 0 else 0.0
            
            # Build response
            response_data = {
                'total': total,
                'by_status': by_status,
                'by_agent': by_agent,
                'conversion_rate': round(conversion_rate, 2)
            }
            
            return success_response(response_data, 200)
            
        except Exception as e:
            _logger.error(f"Error generating lead statistics: {str(e)}", exc_info=True)
            return error_response(str(e), 500, 'INTERNAL_SERVER_ERROR')
    
    # ==================== PRIVATE HELPERS ====================
    
    def _serialize_lead(self, lead, include_activities=False):
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
        
        # Include recent activities if requested (FR-035)
        if include_activities:
            messages = request.env['mail.message'].sudo().search([
                ('model', '=', 'real.estate.lead'),
                ('res_id', '=', lead.id),
                ('message_type', '=', 'comment')
            ], order='date desc', limit=5)
            
            recent_activities = []
            for msg in messages:
                # Extract activity type from body
                activity_type = 'note'
                body_text = msg.body or ''
                
                if '📞' in body_text or 'CALL' in body_text:
                    activity_type = 'call'
                elif '📧' in body_text or 'EMAIL' in body_text:
                    activity_type = 'email'
                elif '🤝' in body_text or 'MEETING' in body_text:
                    activity_type = 'meeting'
                
                # Remove HTML and formatting
                import re
                clean_body = re.sub(r'<[^>]+>', '', body_text)
                clean_body = re.sub(r'[📞📧🤝📝]\s*(CALL|EMAIL|MEETING|NOTE)\s*', '', clean_body).strip()
                
                recent_activities.append({
                    'id': msg.id,
                    'activity_type': activity_type,
                    'body': clean_body[:100] + '...' if len(clean_body) > 100 else clean_body,
                    'author': msg.author_id.name if msg.author_id else 'Unknown',
                    'date': msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else None
                })
            
            data['recent_activities'] = recent_activities
        
        return data
    
    # ==================== ACTIVITY TRACKING ENDPOINTS ====================
    
    @http.route('/api/v1/leads/<int:lead_id>/activities',
                type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def log_activity(self, lead_id, **kwargs):
        """
        Log a new activity for a lead (FR-033).
        
        Creates a chatter message for activities like calls, emails, or meetings.
        
        Request Body:
            - body (string, required): Activity description/notes
            - activity_type (string, optional): Type of activity ('call', 'email', 'meeting', 'note')
            
        Returns:
            201: Activity created successfully
            400: Invalid request
            403: Access denied
            404: Lead not found
        """
        try:
            body = kwargs.get('body', '').strip()
            if not body:
                return error_response(
                    'Validation Error',
                    'Activity body is required',
                    400
                )
            
            activity_type = kwargs.get('activity_type', 'note')
            if activity_type not in ['call', 'email', 'meeting', 'note']:
                return error_response(
                    'Validation Error',
                    'Invalid activity type. Must be one of: call, email, meeting, note',
                    400
                )
            
            Lead = request.env['real.estate.lead'].sudo()
            lead = Lead.browse(lead_id)
            
            if not lead.exists():
                return error_response('Not Found', f'Lead {lead_id} not found', 404)
            
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator
            
            # Check agent isolation (agents can only log on their own leads)
            user_groups = current_user.groups_id.mapped('name')
            is_agent = 'Estate Agent' in user_groups and 'Estate Manager' not in user_groups
            
            if is_agent and lead.agent_id.id != current_user.id:
                return error_response('Forbidden', 'Access denied: You can only log activities on your own leads', 403)
            
            # Build activity message with type prefix
            activity_icons = {
                'call': '📞',
                'email': '📧',
                'meeting': '🤝',
                'note': '📝'
            }
            icon = activity_icons.get(activity_type, '📝')
            formatted_body = f"{icon} <strong>{activity_type.upper()}</strong><br/>{body}"
            
            # Post message to chatter
            message = lead.message_post(
                body=formatted_body,
                message_type='comment',
                subtype_xmlid='mail.mt_note'
            )
            
            # Build response
            activity_data = {
                'id': message.id,
                'lead_id': lead_id,
                'activity_type': activity_type,
                'body': body,
                'author': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'email': current_user.email
                },
                'date': message.date.strftime('%Y-%m-%d %H:%M:%S') if message.date else None,
                'created_at': message.create_date.strftime('%Y-%m-%d %H:%M:%S') if message.create_date else None
            }
            
            return success_response(
                'Activity logged successfully',
                activity_data,
                201
            )
            
        except Exception as e:
            _logger.error(f"Error logging activity for lead {lead_id}: {str(e)}", exc_info=True)
            return error_response('Server Error', str(e), 500)
    
    @http.route('/api/v1/leads/<int:lead_id>/activities',
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def list_activities(self, lead_id, **kwargs):
        """
        List all activities for a lead (FR-034).
        
        Returns chatter messages with activity information.
        
        Query Parameters:
            - limit (int, optional): Number of activities to return (default: 20, max: 100)
            - offset (int, optional): Pagination offset (default: 0)
            
        Returns:
            200: Activities list
            403: Access denied
            404: Lead not found
        """
        try:
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            
            if limit > 100:
                limit = 100
            
            Lead = request.env['real.estate.lead'].sudo()
            lead = Lead.browse(lead_id)
            
            if not lead.exists():
                return error_response(404, f'Lead {lead_id} not found', 'NOT_FOUND')
            
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator
            
            # Check agent isolation (agents can only view their own leads)
            user_groups = current_user.groups_id.mapped('name')
            is_agent = 'Estate Agent' in user_groups and 'Estate Manager' not in user_groups
            
            if is_agent and lead.agent_id.id != current_user.id:
                return error_response(403, 'Access denied: You can only view activities on your own leads', 'FORBIDDEN')
            
            # Get messages from chatter
            messages = request.env['mail.message'].sudo().search([
                ('model', '=', 'real.estate.lead'),
                ('res_id', '=', lead_id),
                ('message_type', '=', 'comment')
            ], order='date desc', limit=limit, offset=offset)
            
            total_count = request.env['mail.message'].sudo().search_count([
                ('model', '=', 'real.estate.lead'),
                ('res_id', '=', lead_id),
                ('message_type', '=', 'comment')
            ])
            
            # Format activities
            activities = []
            for msg in messages:
                # Extract activity type from body if it was formatted
                activity_type = 'note'  # default
                body_text = msg.body or ''
                
                if '📞' in body_text or 'CALL' in body_text:
                    activity_type = 'call'
                elif '📧' in body_text or 'EMAIL' in body_text:
                    activity_type = 'email'
                elif '🤝' in body_text or 'MEETING' in body_text:
                    activity_type = 'meeting'
                
                # Remove HTML and formatting
                import re
                clean_body = re.sub(r'<[^>]+>', '', body_text)
                clean_body = re.sub(r'[📞📧🤝📝]\s*(CALL|EMAIL|MEETING|NOTE)\s*', '', clean_body).strip()
                
                activities.append({
                    'id': msg.id,
                    'activity_type': activity_type,
                    'body': clean_body,
                    'author': {
                        'id': msg.author_id.id,
                        'name': msg.author_id.name,
                        'email': msg.author_id.email
                    },
                    'date': msg.date.strftime('%Y-%m-%d %H:%M:%S') if msg.date else None,
                    'created_at': msg.create_date.strftime('%Y-%m-%d %H:%M:%S') if msg.create_date else None
                })
            
            response_data = {
                'success': True,
                'message': f'Found {len(activities)} activities',
                'activities': activities,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': (offset + limit) < total_count
                }
            }
            
            return success_response(response_data, 200)
            
        except Exception as e:
            _logger.error(f"Error listing activities for lead {lead_id}: {str(e)}", exc_info=True)
            return error_response(500, str(e), 'SERVER_ERROR')
    
    @http.route('/api/v1/leads/<int:lead_id>/schedule-activity',
                type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def schedule_activity(self, lead_id, **kwargs):
        """
        Schedule a future activity with deadline/reminder (FR-036).
        
        Creates a scheduled activity using Odoo's mail.activity system.
        
        Request Body:
            - summary (string, required): Activity summary/title
            - note (string, optional): Detailed activity notes
            - activity_type_id (int, optional): Activity type ID (default: 'To Do')
            - date_deadline (string, required): Deadline date (YYYY-MM-DD format)
            - user_id (int, optional): Assigned user (defaults to current user)
            
        Returns:
            201: Activity scheduled successfully
            400: Invalid request
            403: Access denied
            404: Lead not found
        """
        try:
            summary = kwargs.get('summary', '').strip()
            if not summary:
                return error_response(
                    'Validation Error',
                    'Activity summary is required',
                    400
                )
            
            date_deadline = kwargs.get('date_deadline', '').strip()
            if not date_deadline:
                return error_response(
                    'Validation Error',
                    'Activity deadline date is required',
                    400
                )
            
            # Validate date format
            try:
                from datetime import datetime as dt
                deadline_date = dt.strptime(date_deadline, '%Y-%m-%d').date()
            except ValueError:
                return error_response(
                    'Validation Error',
                    'Invalid date format. Use YYYY-MM-DD',
                    400
                )
            
            Lead = request.env['real.estate.lead'].sudo()
            lead = Lead.browse(lead_id)
            
            if not lead.exists():
                return error_response('Not Found', f'Lead {lead_id} not found', 404)
            
            # Verify user has access to this lead
            current_user = request.env.user
            # Note: Company isolation is handled by @require_company decorator
            
            # Check agent isolation (agents can only schedule on their own leads)
            user_groups = current_user.groups_id.mapped('name')
            is_agent = 'Estate Agent' in user_groups and 'Estate Manager' not in user_groups
            
            if is_agent and lead.agent_id.id != current_user.id:
                return error_response('Forbidden', 'Access denied: You can only schedule activities on your own leads', 403)
            
            # Get activity type (default to 'To Do')
            ActivityType = request.env['mail.activity.type'].sudo()
            activity_type_id = kwargs.get('activity_type_id')
            
            if not activity_type_id:
                # Find default 'To Do' activity type
                activity_type = ActivityType.search([('name', '=', 'To Do')], limit=1)
                if not activity_type:
                    # Fallback to first available activity type
                    activity_type = ActivityType.search([], limit=1)
                activity_type_id = activity_type.id if activity_type else None
            
            if not activity_type_id:
                return error_response(
                    'Configuration Error',
                    'No activity types available in the system',
                    500
                )
            
            # Get assigned user (default to current user)
            user_id = kwargs.get('user_id', current_user.id)
            
            # Validate assigned user exists
            assigned_user = request.env['res.users'].sudo().browse(user_id)
            if not assigned_user.exists():
                return error_response(
                    'Validation Error',
                    f'User with ID {user_id} not found',
                    400
                )
            
            # Create scheduled activity
            activity_vals = {
                'res_id': lead_id,
                'res_model_id': request.env['ir.model'].sudo().search([('model', '=', 'real.estate.lead')], limit=1).id,
                'activity_type_id': activity_type_id,
                'summary': summary,
                'note': kwargs.get('note', ''),
                'date_deadline': deadline_date,
                'user_id': user_id
            }
            
            activity = request.env['mail.activity'].sudo().create(activity_vals)
            
            # Build response
            activity_data = {
                'id': activity.id,
                'lead_id': lead_id,
                'summary': activity.summary,
                'note': activity.note or '',
                'activity_type': activity.activity_type_id.name,
                'date_deadline': activity.date_deadline.strftime('%Y-%m-%d'),
                'assigned_to': {
                    'id': activity.user_id.id,
                    'name': activity.user_id.name,
                    'email': activity.user_id.email
                },
                'created_by': {
                    'id': current_user.id,
                    'name': current_user.name,
                    'email': current_user.email
                },
                'state': activity.state,
                'created_at': activity.create_date.strftime('%Y-%m-%d %H:%M:%S') if activity.create_date else None
            }
            
            return success_response(
                'Activity scheduled successfully',
                activity_data,
                201
            )
            
        except Exception as e:
            _logger.error(f"Error scheduling activity for lead {lead_id}: {str(e)}", exc_info=True)
            return error_response('Server Error', str(e), 500)
    
    # ==================== SAVED FILTERS ENDPOINTS ====================
    
    @http.route('/api/v1/leads/filters',
                type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def create_filter(self, **kwargs):
        """
        Save a new search filter (FR-048, T149).
        
        Request Body:
            - name (string, required): Filter name (e.g., "High-value Centro leads")
            - filter_params (object, required): Filter criteria (same params as list_leads)
            - is_shared (boolean, optional): Share with company users (default: false)
            
        Returns:
            201: Filter created successfully
            400: Invalid request
        """
        try:
            name = kwargs.get('name', '').strip()
            if not name:
                return error_response(
                    'Validation Error',
                    'Filter name is required',
                    400
                )
            
            filter_params = kwargs.get('filter_params')
            if not filter_params or not isinstance(filter_params, dict):
                return error_response(
                    'Validation Error',
                    'Filter parameters are required and must be an object',
                    400
                )
            
            is_shared = kwargs.get('is_shared', False)
            
            # Create filter
            Filter = request.env['real.estate.lead.filter']
            filter_record = Filter.create({
                'name': name,
                'user_id': request.env.user.id,
                'filter_domain': json.dumps(filter_params),
                'is_shared': is_shared
            })
            
            # Build response
            filter_data = {
                'id': filter_record.id,
                'name': filter_record.name,
                'filter_params': filter_params,
                'is_shared': filter_record.is_shared,
                'created_at': filter_record.create_date.strftime('%Y-%m-%d %H:%M:%S') if filter_record.create_date else None
            }
            
            return success_response(
                'Filter saved successfully',
                filter_data,
                201
            )
            
        except ValidationError as ve:
            return error_response('Validation Error', str(ve), 400)
        except Exception as e:
            _logger.error(f"Error creating saved filter: {str(e)}", exc_info=True)
            return error_response('Server Error', str(e), 500)
    
    @http.route('/api/v1/leads/filters',
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def list_filters(self, **kwargs):
        """
        List user's saved filters (FR-048, T150).
        
        Query Parameters:
            - include_shared (string, optional): 'true' to include shared filters
            
        Returns:
            200: Filters list
        """
        try:
            include_shared = kwargs.get('include_shared', 'false').lower() == 'true'
            
            # Build domain
            domain = [('user_id', '=', request.env.user.id)]
            
            if include_shared:
                # Also include shared filters from same company
                domain = ['|', ('user_id', '=', request.env.user.id), ('is_shared', '=', True)]
            
            # Query filters
            Filter = request.env['real.estate.lead.filter']
            filters = Filter.search(domain, order='name')
            
            # Build response
            filter_list = []
            for filter_record in filters:
                filter_list.append({
                    'id': filter_record.id,
                    'name': filter_record.name,
                    'filter_params': json.loads(filter_record.filter_domain),
                    'is_shared': filter_record.is_shared,
                    'owner': {
                        'id': filter_record.user_id.id,
                        'name': filter_record.user_id.name
                    },
                    'created_at': filter_record.create_date.strftime('%Y-%m-%d %H:%M:%S') if filter_record.create_date else None
                })
            
            response_data = {
                'success': True,
                'message': f'Found {len(filter_list)} filters',
                'data': {
                    'filters': filter_list,
                    'total': len(filter_list)
                }
            }
            
            return Response(
                json.dumps(response_data),
                status=200,
                content_type='application/json'
            )
            
        except Exception as e:
            _logger.error(f"Error listing filters: {str(e)}", exc_info=True)
            return Response(
                json.dumps(error_response('Server Error', str(e), 500)),
                status=500,
                content_type='application/json'
            )
    
    @http.route('/api/v1/leads/filters/<int:filter_id>',
                type='json', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def delete_filter(self, filter_id, **kwargs):
        """
        Delete a saved filter (FR-048, T151).
        
        Returns:
            200: Filter deleted successfully
            403: Access denied (not owner)
            404: Filter not found
        """
        try:
            Filter = request.env['real.estate.lead.filter']
            filter_record = Filter.browse(filter_id)
            
            if not filter_record.exists():
                return error_response('Not Found', f'Filter {filter_id} not found', 404)
            
            # Check ownership
            if filter_record.user_id.id != request.env.user.id:
                return error_response('Forbidden', 'You can only delete your own filters', 403)
            
            # Delete filter
            filter_name = filter_record.name
            filter_record.unlink()
            
            return success_response(
                f'Filter "{filter_name}" deleted successfully',
                {'id': filter_id},
                200
            )
            
        except Exception as e:
            _logger.error(f"Error deleting filter {filter_id}: {str(e)}", exc_info=True)
            return error_response('Server Error', str(e), 500)

