# -*- coding: utf-8 -*-
"""
Agent API Controller

RESTful API endpoints for agent management with CRECI validation,
multi-tenant isolation, and commission tracking.

Author: Quicksol Technologies
Date: 2026-01-12
ADRs: ADR-005 (OpenAPI), ADR-007 (HATEOAS), ADR-008 (Multi-tenancy), 
      ADR-011 (Security), ADR-012 (CRECI Validation)
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
from ..services.company_validator import CompanyValidator

_logger = logging.getLogger(__name__)


class AgentApiController(http.Controller):
    """REST API Controller for Agent endpoints following ADR-011"""
    
    @http.route('/api/v1/agents', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_agents(self, **kwargs):
        """
        List all agents with pagination and filtering.
        
        Query Parameters:
            - active: Filter by active status ('true', 'false', 'all')
            - company_id: Filter by company (multi-tenancy)
            - creci_number: Filter by CRECI number
            - creci_state: Filter by CRECI state (UF)
            - limit: Number of records to return (default: 20, max: 100)
            - offset: Number of records to skip (default: 0)
            
        Returns:
            JSON object with agent list and pagination metadata
        """
        try:
            user = request.env.user
            
            # Parse query parameters
            active_filter = kwargs.get('active', 'true')
            company_id = kwargs.get('company_id')
            creci_number = kwargs.get('creci_number')
            creci_state = kwargs.get('creci_state')
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
            
            # Company filter (multi-tenancy isolation)
            if company_id:
                domain.append(('company_id', '=', int(company_id)))
            else:
                # Default: filter by user's default company
                if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                    domain.append(('company_id', '=', user.estate_default_company_id.id))
            
            # CRECI filters
            if creci_number:
                domain.append(('creci_number', 'ilike', creci_number))
            
            if creci_state:
                domain.append(('creci_state', '=', creci_state.upper()))
            
            # Query agents
            Agent = request.env['real.estate.agent']
            
            # Use sudo() with context to bypass record rules for counting
            total = Agent.with_context(active_test=False).sudo().search_count(domain)
            
            agents = Agent.sudo().search(domain, limit=limit, offset=offset, order='name asc')
            
            # Serialize agents
            agent_list = []
            for agent in agents:
                agent_list.append({
                    'id': agent.id,
                    'name': agent.name,
                    'email': agent.email,
                    'phone': agent.phone,
                    'mobile': agent.mobile,
                    'cpf': agent.cpf,
                    'creci': agent.creci,
                    'creci_number': agent.creci_number,
                    'creci_state': agent.creci_state,
                    'creci_normalized': agent.creci_normalized,
                    'active': agent.active,
                    'hire_date': agent.hire_date.isoformat() if agent.hire_date else None,
                    'company_id': agent.company_id.id if agent.company_id else None,
                    'company_name': agent.company_id.name if agent.company_id else None,
                    '_links': {
                        'self': f'/api/v1/agents/{agent.id}',
                        'properties': f'/api/v1/agents/{agent.id}/properties',
                    }
                })
            
            # Build response with pagination (ADR-007: HATEOAS)
            response_data = {
                'success': True,
                'data': agent_list,
                'count': len(agent_list),
                'total': total,
                'limit': limit,
                'offset': offset,
                '_links': {
                    'self': f'/api/v1/agents?limit={limit}&offset={offset}',
                }
            }
            
            # Add next/prev links
            if offset + limit < total:
                response_data['_links']['next'] = f'/api/v1/agents?limit={limit}&offset={offset + limit}'
            if offset > 0:
                prev_offset = max(0, offset - limit)
                response_data['_links']['prev'] = f'/api/v1/agents?limit={limit}&offset={prev_offset}'
            
            return success_response(response_data)
            
        except ValueError as e:
            return error_response(400, f'Invalid parameter: {str(e)}')
        except Exception as e:
            _logger.exception('Error listing agents')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_agent(self, **kwargs):
        """
        Create a new agent.
        
        Request Body:
            JSON object with agent data:
            - name (required): Agent full name
            - cpf (required): Brazilian CPF (11 digits)
            - email: Email address
            - phone: Phone number (Brazilian format)
            - creci: CRECI license (optional, flexible format)
            - company_id: Company ID (defaults to user's company)
            - hire_date: Hire date (ISO format)
            
        Returns:
            JSON object with created agent details (HTTP 201)
        """
        try:
            user = request.env.user
            
            # Only managers and admins can create agents
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can create agents')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Validate required fields
            required_fields = ['name', 'cpf']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return error_response(400, f"Missing required fields: {', '.join(missing_fields)}")
            
            # Prepare agent data
            agent_vals = {
                'name': data.get('name'),
                'cpf': data.get('cpf'),
                'email': data.get('email'),
                'phone': data.get('phone'),
                'mobile': data.get('mobile'),
                'creci': data.get('creci'),
                'hire_date': data.get('hire_date'),
                'bank_name': data.get('bank_name'),
                'bank_account': data.get('bank_account'),
                'pix_key': data.get('pix_key'),
            }
            
            # Company ID (multi-tenancy)
            company_id = data.get('company_id')
            if company_id:
                # Validate company access
                valid, error = CompanyValidator.validate_company_ids([company_id])
                if not valid:
                    return error_response(403, error)
                agent_vals['company_id'] = company_id
            else:
                # Default to user's company
                if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                    agent_vals['company_id'] = user.estate_default_company_id.id
                else:
                    return error_response(400, 'No company_id provided and user has no default company')
            
            # Create agent
            Agent = request.env['real.estate.agent']
            agent = Agent.sudo().create(agent_vals)
            
            # Serialize response
            agent_data = {
                'id': agent.id,
                'name': agent.name,
                'cpf': agent.cpf,
                'email': agent.email,
                'phone': agent.phone,
                'mobile': agent.mobile,
                'creci': agent.creci,
                'creci_normalized': agent.creci_normalized,
                'creci_number': agent.creci_number,
                'creci_state': agent.creci_state,
                'active': agent.active,
                'hire_date': agent.hire_date.isoformat() if agent.hire_date else None,
                'company_id': agent.company_id.id if agent.company_id else None,
                'company_name': agent.company_id.name if agent.company_id else None,
                '_links': {
                    'self': f'/api/v1/agents/{agent.id}',
                    'properties': f'/api/v1/agents/{agent.id}/properties',
                    'deactivate': f'/api/v1/agents/{agent.id}/deactivate',
                }
            }
            
            return Response(
                json.dumps({'success': True, 'data': agent_data}),
                status=201,
                mimetype='application/json'
            )
            
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception('Error creating agent')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_agent(self, agent_id, **kwargs):
        """
        Get agent details by ID.
        
        Returns:
            JSON object with agent details (HTTP 200)
            HTTP 404 if agent not found or not accessible
        """
        try:
            user = request.env.user
            Agent = request.env['real.estate.agent']
            
            # Query agent with company isolation
            agent = Agent.sudo().browse(agent_id)
            
            if not agent.exists():
                return error_response(404, 'Agent not found')
            
            # Verify company access (multi-tenancy)
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(404, 'Agent not found')
            
            # Serialize agent
            agent_data = {
                'id': agent.id,
                'name': agent.name,
                'cpf': agent.cpf,
                'email': agent.email,
                'phone': agent.phone,
                'mobile': agent.mobile,
                'creci': agent.creci,
                'creci_normalized': agent.creci_normalized,
                'creci_number': agent.creci_number,
                'creci_state': agent.creci_state,
                'active': agent.active,
                'hire_date': agent.hire_date.isoformat() if agent.hire_date else None,
                'deactivation_date': agent.deactivation_date.isoformat() if agent.deactivation_date else None,
                'deactivation_reason': agent.deactivation_reason,
                'company_id': agent.company_id.id if agent.company_id else None,
                'company_name': agent.company_id.name if agent.company_id else None,
                'bank_name': agent.bank_name,
                'bank_account': agent.bank_account,
                'pix_key': agent.pix_key,
                '_links': {
                    'self': f'/api/v1/agents/{agent.id}',
                    'properties': f'/api/v1/agents/{agent.id}/properties',
                    'update': f'/api/v1/agents/{agent.id}',
                    'deactivate': f'/api/v1/agents/{agent.id}/deactivate',
                    'reactivate': f'/api/v1/agents/{agent.id}/reactivate',
                }
            }
            
            return success_response(agent_data)
            
        except Exception as e:
            _logger.exception(f'Error getting agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>', 
                type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_agent(self, agent_id, **kwargs):
        """
        Update agent details.
        
        Request Body:
            JSON object with fields to update
            Note: company_id cannot be changed via API (security constraint)
            
        Returns:
            JSON object with updated agent details (HTTP 200)
        """
        try:
            user = request.env.user
            
            # Only managers and admins can update agents
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can update agents')
            
            # Parse request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')
            
            # Get agent
            Agent = request.env['real.estate.agent']
            agent = Agent.sudo().browse(agent_id)
            
            if not agent.exists():
                return error_response(404, 'Agent not found')
            
            # Verify company access
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot update agent from different company')
            
            # Prevent company_id changes (security constraint)
            if 'company_id' in data:
                return error_response(400, 'Cannot change company_id via API')
            
            # Prepare update data
            update_vals = {}
            allowed_fields = [
                'name', 'email', 'phone', 'mobile', 'creci',
                'bank_name', 'bank_account', 'bank_branch', 'bank_account_type', 'pix_key'
            ]
            
            for field in allowed_fields:
                if field in data:
                    update_vals[field] = data[field]
            
            # Update agent
            if update_vals:
                agent.write(update_vals)
            
            # Serialize response
            agent_data = {
                'id': agent.id,
                'name': agent.name,
                'cpf': agent.cpf,
                'email': agent.email,
                'phone': agent.phone,
                'mobile': agent.mobile,
                'creci': agent.creci,
                'creci_normalized': agent.creci_normalized,
                'active': agent.active,
                'company_id': agent.company_id.id if agent.company_id else None,
                '_links': {
                    'self': f'/api/v1/agents/{agent.id}',
                }
            }
            
            return success_response(agent_data)
            
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception(f'Error updating agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>/deactivate', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def deactivate_agent(self, agent_id, **kwargs):
        """
        Deactivate agent (soft-delete following ADR-015).
        
        Request Body:
            JSON object with optional 'reason' field
            
        Returns:
            JSON object confirming deactivation (HTTP 200)
        """
        try:
            user = request.env.user
            
            # Only managers and admins can deactivate agents
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can deactivate agents')
            
            # Parse request body
            reason = None
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
                reason = data.get('reason')
            except:
                pass
            
            # Get agent
            Agent = request.env['real.estate.agent']
            agent = Agent.sudo().browse(agent_id)
            
            if not agent.exists():
                return error_response(404, 'Agent not found')
            
            # Verify company access
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot deactivate agent from different company')
            
            # Deactivate agent
            agent.action_deactivate(reason=reason)
            
            return success_response({
                'message': 'Agent deactivated successfully',
                'agent_id': agent.id,
                'deactivation_date': agent.deactivation_date.isoformat() if agent.deactivation_date else None,
            })
            
        except UserError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception(f'Error deactivating agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>/reactivate', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def reactivate_agent(self, agent_id, **kwargs):
        """
        Reactivate a deactivated agent.
        
        Returns:
            JSON object confirming reactivation (HTTP 200)
        """
        try:
            user = request.env.user
            
            # Only managers and admins can reactivate agents
            if not user.has_group('quicksol_estate.group_real_estate_manager') and \
               not user.has_group('base.group_system'):
                return error_response(403, 'Only managers can reactivate agents')
            
            # Get agent
            Agent = request.env['real.estate.agent'].with_context(active_test=False)
            agent = Agent.sudo().browse(agent_id)
            
            if not agent.exists():
                return error_response(404, 'Agent not found')
            
            # Verify company access
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot reactivate agent from different company')
            
            # Reactivate agent
            agent.action_reactivate()
            
            return success_response({
                'message': 'Agent reactivated successfully',
                'agent_id': agent.id,
                'active': agent.active,
            })
            
        except UserError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception(f'Error reactivating agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    # ==================== ASSIGNMENT ENDPOINTS ====================
    
    @http.route('/api/v1/assignments', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_assignment(self, **kwargs):
        """
        Assign an agent to a property.
        
        Request Body (JSON):
            {
                "agent_id": int (required),
                "property_id": int (required),
                "responsibility_type": str (optional: 'primary', 'secondary', 'support'),
                "notes": str (optional)
            }
        
        Returns:
            JSON object with assignment details
        """
        try:
            # Parse JSON body
            try:
                data = json.loads(request.httprequest.data)
            except json.JSONDecodeError:
                return error_response(400, 'Invalid JSON in request body')
            
            # Validate required fields
            if 'agent_id' not in data:
                return error_response(400, 'Missing required field: agent_id')
            if 'property_id' not in data:
                return error_response(400, 'Missing required field: property_id')
            
            agent_id = data.get('agent_id')
            property_id = data.get('property_id')
            responsibility_type = data.get('responsibility_type', 'primary')
            notes = data.get('notes', '')
            
            # Validate agent and property exist
            Agent = request.env['real.estate.agent'].sudo()
            Property = request.env['real.estate.property'].sudo()
            
            agent = Agent.browse(agent_id)
            property_obj = Property.browse(property_id)
            
            if not agent.exists():
                return error_response(404, f'Agent with ID {agent_id} not found')
            if not property_obj.exists():
                return error_response(404, f'Property with ID {property_id} not found')
            
            # Check company access
            user = request.env.user
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot assign agent from different company')
                if user.estate_default_company_id not in property_obj.company_ids:
                    return error_response(403, 'Cannot assign to property from different company')
            
            # Create assignment
            Assignment = request.env['real.estate.agent.property.assignment'].sudo()
            assignment = Assignment.create({
                'agent_id': agent_id,
                'property_id': property_id,
                'responsibility_type': responsibility_type,
                'notes': notes,
            })
            
            return success_response({
                'message': 'Assignment created successfully',
                'assignment': {
                    'id': assignment.id,
                    'agent_id': assignment.agent_id.id,
                    'agent_name': assignment.agent_id.name,
                    'property_id': assignment.property_id.id,
                    'property_name': assignment.property_id.name,
                    'company_id': assignment.company_id.id,
                    'company_name': assignment.company_id.name,
                    'responsibility_type': assignment.responsibility_type,
                    'assignment_date': assignment.assignment_date.isoformat() if assignment.assignment_date else None,
                    'active': assignment.active,
                    'notes': assignment.notes,
                }
            }, status_code=201)
            
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception('Error creating assignment')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>/properties', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_agent_properties(self, agent_id, **kwargs):
        """
        Get all properties assigned to a specific agent.
        
        Query Parameters:
            - active_only: Return only active assignments (default: true)
        
        Returns:
            JSON object with list of assigned properties
        """
        try:
            # Get agent
            Agent = request.env['real.estate.agent'].sudo()
            agent = Agent.browse(agent_id)
            
            if not agent.exists():
                return error_response(404, f'Agent with ID {agent_id} not found')
            
            # Check company access
            user = request.env.user
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if agent.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot access agent from different company')
            
            # Get active_only parameter
            active_only = kwargs.get('active_only', 'true').lower() == 'true'
            
            # Get assignments
            Assignment = request.env['real.estate.agent.property.assignment'].sudo()
            domain = [('agent_id', '=', agent_id)]
            if active_only:
                domain.append(('active', '=', True))
            
            assignments = Assignment.search(domain)
            
            # Build response
            properties_data = []
            for assignment in assignments:
                property_obj = assignment.property_id
                properties_data.append({
                    'assignment_id': assignment.id,
                    'property_id': property_obj.id,
                    'property_name': property_obj.name,
                    'property_reference': property_obj.reference_code,
                    'property_type': property_obj.property_type_id.name if property_obj.property_type_id else None,
                    'price': float(property_obj.price) if property_obj.price else 0.0,
                    'responsibility_type': assignment.responsibility_type,
                    'assignment_date': assignment.assignment_date.isoformat() if assignment.assignment_date else None,
                    'active': assignment.active,
                })
            
            return success_response({
                'agent_id': agent_id,
                'agent_name': agent.name,
                'total_assignments': len(properties_data),
                'properties': properties_data,
            })
            
        except Exception as e:
            _logger.exception(f'Error getting properties for agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/assignments/<int:assignment_id>', 
                type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_assignment(self, assignment_id, **kwargs):
        """
        Deactivate (soft delete) an assignment.
        
        Returns:
            JSON object confirming deactivation
        """
        try:
            # Get assignment
            Assignment = request.env['real.estate.agent.property.assignment'].sudo()
            assignment = Assignment.browse(assignment_id)
            
            if not assignment.exists():
                return error_response(404, f'Assignment with ID {assignment_id} not found')
            
            # Check company access
            user = request.env.user
            if hasattr(user, 'estate_default_company_id') and user.estate_default_company_id:
                if assignment.company_id != user.estate_default_company_id:
                    return error_response(403, 'Cannot delete assignment from different company')
            
            # Deactivate assignment
            if hasattr(assignment, 'action_deactivate'):
                assignment.action_deactivate()
            else:
                assignment.write({'active': False})
            
            return success_response({
                'message': 'Assignment deactivated successfully',
                'assignment_id': assignment_id,
                'active': assignment.active,
            })
            
        except Exception as e:
            _logger.exception(f'Error deleting assignment {assignment_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    # ==================== COMMISSION RULE ENDPOINTS (US4) ====================
    
    @http.route('/api/v1/agents/<int:agent_id>/commission-rules', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_commission_rule(self, agent_id, **kwargs):
        """
        Create commission rule for an agent.
        
        POST /api/v1/agents/{agent_id}/commission-rules
        
        Body:
        {
            "transaction_type": "sale",  // "sale", "rental", "both"
            "structure_type": "percentage",  // "percentage" or "fixed"
            "percentage": 3.0,  // 0-100 (if percentage type)
            "fixed_amount": 0.0,  // Fixed amount (if fixed type)
            "min_value": 100000.0,  // Optional
            "max_value": 5000000.0,  // Optional
            "valid_from": "2026-01-12",  // Required
            "valid_until": "2027-01-12"  // Optional
        }
        
        Response 201:
        {
            "data": {
                "id": 1,
                "agent_id": 1,
                "agent_name": "João Silva",
                "transaction_type": "sale",
                "structure_type": "percentage",
                "percentage": 3.0,
                "fixed_amount": 0.0,
                "is_active": true,
                "valid_from": "2026-01-12",
                "valid_until": "2027-01-12"
            }
        }
        """
        try:
            # Parse request body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate agent exists and belongs to user's company
            agent = request.env['real.estate.agent'].sudo().browse(agent_id)
            if not agent.exists():
                return error_response(404, f'Agent {agent_id} not found')
            
            # Company isolation check
            user = request.env.user
            if hasattr(user, 'estate_company_ids'):
                if agent.company_id.id not in user.estate_company_ids.ids:
                    return error_response(403, 'Cannot create commission rule for agent in different company')
            
            # Validate required fields
            required_fields = ['transaction_type', 'structure_type', 'valid_from']
            missing = [f for f in required_fields if f not in body]
            if missing:
                return error_response(400, f'Missing required fields: {", ".join(missing)}')
            
            # Prepare rule data
            rule_data = {
                'agent_id': agent_id,
                'company_id': agent.company_id.id,
                'transaction_type': body['transaction_type'],
                'structure_type': body['structure_type'],
                'percentage': body.get('percentage', 0.0),
                'fixed_amount': body.get('fixed_amount', 0.0),
                'min_value': body.get('min_value', 0.0),
                'max_value': body.get('max_value', 999999999.99),
                'valid_from': body['valid_from'],
                'valid_until': body.get('valid_until'),
            }
            
            # Create commission rule
            rule = request.env['real.estate.commission.rule'].sudo().create(rule_data)
            
            # Return created rule
            return success_response({
                'id': rule.id,
                'agent_id': rule.agent_id.id,
                'agent_name': rule.agent_id.name,
                'company_id': rule.company_id.id,
                'company_name': rule.company_id.name,
                'transaction_type': rule.transaction_type,
                'structure_type': rule.structure_type,
                'percentage': rule.percentage,
                'fixed_amount': rule.fixed_amount,
                'min_value': rule.min_value,
                'max_value': rule.max_value,
                'valid_from': str(rule.valid_from),
                'valid_until': str(rule.valid_until) if rule.valid_until else None,
                'is_active': rule.is_active,
                'active': rule.active,
            }, status=201)
            
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON in request body')
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception(f'Error creating commission rule for agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/agents/<int:agent_id>/commission-rules', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_commission_rules(self, agent_id, **kwargs):
        """
        List commission rules for an agent.
        
        GET /api/v1/agents/{agent_id}/commission-rules?active_only=true
        
        Query Parameters:
        - active_only: boolean (default: false) - Only return currently active rules
        
        Response 200:
        {
            "data": [
                {
                    "id": 1,
                    "agent_id": 1,
                    "transaction_type": "sale",
                    "percentage": 3.0,
                    "is_active": true,
                    "valid_from": "2026-01-12"
                }
            ],
            "count": 1
        }
        """
        try:
            # Validate agent exists and belongs to user's company
            agent = request.env['real.estate.agent'].sudo().browse(agent_id)
            if not agent.exists():
                return error_response(404, f'Agent {agent_id} not found')
            
            # Company isolation check
            user = request.env.user
            if hasattr(user, 'estate_company_ids'):
                if agent.company_id.id not in user.estate_company_ids.ids:
                    return error_response(403, 'Cannot access commission rules for agent in different company')
            
            # Build search domain
            domain = [('agent_id', '=', agent_id)]
            
            # Filter by active status
            active_only = kwargs.get('active_only', 'false').lower() == 'true'
            if active_only:
                domain.append(('active', '=', True))
            
            # Search commission rules
            rules = request.env['real.estate.commission.rule'].sudo().search(domain, order='valid_from desc')
            
            # Serialize rules
            rules_data = []
            for rule in rules:
                rules_data.append({
                    'id': rule.id,
                    'agent_id': rule.agent_id.id,
                    'agent_name': rule.agent_id.name,
                    'company_id': rule.company_id.id,
                    'transaction_type': rule.transaction_type,
                    'structure_type': rule.structure_type,
                    'percentage': rule.percentage,
                    'fixed_amount': rule.fixed_amount,
                    'min_value': rule.min_value,
                    'max_value': rule.max_value,
                    'valid_from': str(rule.valid_from),
                    'valid_until': str(rule.valid_until) if rule.valid_until else None,
                    'is_active': rule.is_active,
                    'active': rule.active,
                    'transaction_count': rule.transaction_count,
                })
            
            return success_response({
                'data': rules_data,
                'count': len(rules_data),
            })
            
        except Exception as e:
            _logger.exception(f'Error listing commission rules for agent {agent_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/commission-rules/<int:rule_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_commission_rule(self, rule_id, **kwargs):
        """
        Update commission rule (only valid_until and active status can be changed).
        
        PUT /api/v1/commission-rules/{rule_id}
        
        Body:
        {
            "valid_until": "2027-12-31",  // Optional
            "active": false  // Optional
        }
        
        Response 200:
        {
            "data": {
                "id": 1,
                "valid_until": "2027-12-31",
                "active": false,
                "is_active": false
            }
        }
        """
        try:
            # Parse request body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Find commission rule
            rule = request.env['real.estate.commission.rule'].sudo().browse(rule_id)
            if not rule.exists():
                return error_response(404, f'Commission rule {rule_id} not found')
            
            # Company isolation check
            user = request.env.user
            if hasattr(user, 'estate_company_ids'):
                if rule.company_id.id not in user.estate_company_ids.ids:
                    return error_response(403, 'Cannot update commission rule from different company')
            
            # Only allow updating valid_until and active
            update_data = {}
            if 'valid_until' in body:
                update_data['valid_until'] = body['valid_until']
            if 'active' in body:
                update_data['active'] = body['active']
            
            if not update_data:
                return error_response(400, 'No valid fields to update (only valid_until and active allowed)')
            
            # Update rule
            rule.write(update_data)
            
            return success_response({
                'id': rule.id,
                'valid_until': str(rule.valid_until) if rule.valid_until else None,
                'active': rule.active,
                'is_active': rule.is_active,
            })
            
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON in request body')
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception(f'Error updating commission rule {rule_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/commission-transactions', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_commission_transaction(self, **kwargs):
        """
        Create commission transaction using active rule.
        
        POST /api/v1/commission-transactions
        
        Body:
        {
            "agent_id": 1,
            "transaction_type": "sale",  // "sale" or "rental"
            "transaction_amount": 500000.00,
            "transaction_date": "2026-01-12",  // Optional (default: today)
            "transaction_reference": "SALE-2024-001"  // Optional
        }
        
        Response 201:
        {
            "data": {
                "id": 1,
                "agent_id": 1,
                "agent_name": "João Silva",
                "transaction_type": "sale",
                "transaction_amount": 500000.00,
                "commission_amount": 15000.00,
                "rule_percentage": 3.0,
                "payment_status": "pending",
                "transaction_date": "2026-01-12"
            }
        }
        """
        try:
            # Parse request body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            required_fields = ['agent_id', 'transaction_type', 'transaction_amount']
            missing = [f for f in required_fields if f not in body]
            if missing:
                return error_response(400, f'Missing required fields: {", ".join(missing)}')
            
            # Validate agent exists and belongs to user's company
            agent_id = body['agent_id']
            agent = request.env['real.estate.agent'].sudo().browse(agent_id)
            if not agent.exists():
                return error_response(404, f'Agent {agent_id} not found')
            
            # Company isolation check
            user = request.env.user
            if hasattr(user, 'estate_company_ids'):
                if agent.company_id.id not in user.estate_company_ids.ids:
                    return error_response(403, 'Cannot create commission transaction for agent in different company')
            
            # Use CommissionService to create transaction
            from ..services.commission_service import CommissionService
            commission_service = CommissionService(request.env)
            
            transaction = commission_service.create_commission_transaction(
                agent_id=agent_id,
                transaction_type=body['transaction_type'],
                transaction_amount=body['transaction_amount'],
                transaction_date=body.get('transaction_date'),
                transaction_reference=body.get('transaction_reference'),
            )
            
            # Return created transaction
            return success_response({
                'id': transaction.id,
                'agent_id': transaction.agent_id.id,
                'agent_name': transaction.agent_id.name,
                'company_id': transaction.company_id.id,
                'transaction_type': transaction.transaction_type,
                'transaction_amount': transaction.transaction_amount,
                'commission_amount': transaction.commission_amount,
                'rule_id': transaction.rule_id.id,
                'rule_percentage': transaction.rule_percentage,
                'rule_fixed_amount': transaction.rule_fixed_amount,
                'rule_structure_type': transaction.rule_structure_type,
                'payment_status': transaction.payment_status,
                'transaction_date': str(transaction.transaction_date),
                'transaction_reference': transaction.transaction_reference,
                'calculated_at': transaction.calculated_at.isoformat(),
            }, status=201)
            
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON in request body')
        except ValidationError as e:
            return error_response(400, str(e))
        except UserError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception('Error creating commission transaction')
            return error_response(500, f'Internal server error: {str(e)}')

    @http.route('/api/v1/agents/<int:agent_id>/performance', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_agent_performance(self, agent_id, **kwargs):
        """
        Get performance metrics for a specific agent.
        
        Query Parameters:
        - start_date (optional): ISO 8601 date string (YYYY-MM-DD) - Start of date range
        - end_date (optional): ISO 8601 date string (YYYY-MM-DD) - End of date range
        
        Returns:
        - 200: Performance metrics with transactions
        - 400: Validation error (invalid date format)
        - 403: Access denied (agent in different company)
        - 404: Agent not found
        - 500: Internal server error
        
        Response Format:
        {
            "agent_id": 1,
            "agent_name": "João Silva",
            "company_id": 5,
            "company_name": "Company A",
            "period": {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31"
            },
            "metrics": {
                "total_sales_count": 10,
                "total_commissions": 50000.00,
                "average_commission": 5000.00,
                "active_properties_count": 3,
                "pending_commissions": 10000.00,
                "paid_commissions": 35000.00,
                "cancelled_commissions": 5000.00
            },
            "transactions": [
                {
                    "id": 100,
                    "date": "2024-06-15",
                    "transaction_type": "sale",
                    "transaction_amount": 500000.00,
                    "commission_amount": 25000.00,
                    "payment_status": "paid",
                    "reference": "SALE-2024-001",
                    "property_id": 42,
                    "property_name": "Apt 301 - Edifício Central"
                }
            ]
        }
        """
        try:
            # Parse query parameters
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            
            # Validate date formats
            date_from = None
            date_to = None
            
            if start_date:
                try:
                    date_from = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    return error_response(400, f'Invalid start_date format: {start_date}. Use YYYY-MM-DD')
            
            if end_date:
                try:
                    date_to = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    return error_response(400, f'Invalid end_date format: {end_date}. Use YYYY-MM-DD')
            
            # Validate date range
            if date_from and date_to and date_from > date_to:
                return error_response(400, 'start_date cannot be after end_date')
            
            # Get performance data from service
            from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
            service = PerformanceService(request.env)
            
            performance_data = service.get_agent_performance(
                agent_id=agent_id,
                date_from=date_from,
                date_to=date_to
            )
            
            return success_response(performance_data)
            
        except UserError as e:
            # Handle not found / access denied from service
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                return error_response(404, error_msg)
            elif 'access denied' in error_msg.lower() or 'different company' in error_msg.lower():
                return error_response(403, error_msg)
            else:
                return error_response(400, error_msg)
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception('Error getting agent performance')
            return error_response(500, f'Internal server error: {str(e)}')

    @http.route('/api/v1/agents/ranking', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_agents_ranking(self, **kwargs):
        """
        Get top agents ranking by performance metrics.
        
        Query Parameters:
        - company_id (required): ID of the company
        - metric (optional): Ranking metric - 'total_commissions' (default), 'total_sales', 'average_commission'
        - limit (optional): Number of top agents to return (default: 10, max: 100)
        - start_date (optional): ISO 8601 date string (YYYY-MM-DD) - Start of date range
        - end_date (optional): ISO 8601 date string (YYYY-MM-DD) - End of date range
        
        Returns:
        - 200: Ranking data with top agents
        - 400: Validation error (missing company_id, invalid metric/limit/dates)
        - 403: Access denied (company not accessible to user)
        - 404: Company not found
        - 500: Internal server error
        
        Response Format:
        {
            "company_id": 5,
            "company_name": "Company A",
            "metric": "total_commissions",
            "period": {
                "date_from": "2024-01-01",
                "date_to": "2024-12-31"
            },
            "ranking": [
                {
                    "rank": 1,
                    "agent_id": 10,
                    "agent_name": "João Silva",
                    "total_sales_count": 15,
                    "total_commissions": 75000.00,
                    "average_commission": 5000.00,
                    "active_properties_count": 5
                },
                {
                    "rank": 2,
                    "agent_name": "Maria Santos",
                    ...
                }
            ]
        }
        """
        try:
            # Parse query parameters
            company_id = kwargs.get('company_id')
            metric = kwargs.get('metric', 'total_commissions')
            limit = kwargs.get('limit', '10')
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')
            
            # Validate company_id (required)
            if not company_id:
                return error_response(400, 'Missing required parameter: company_id')
            
            try:
                company_id = int(company_id)
            except ValueError:
                return error_response(400, f'Invalid company_id: {company_id}. Must be an integer')
            
            # Validate limit
            try:
                limit = int(limit)
                if limit < 1:
                    return error_response(400, 'limit must be at least 1')
                if limit > 100:
                    limit = 100  # Cap at 100
            except ValueError:
                return error_response(400, f'Invalid limit: {limit}. Must be an integer')
            
            # Validate metric
            valid_metrics = ['total_commissions', 'total_sales', 'average_commission']
            if metric not in valid_metrics:
                return error_response(400, f'Invalid metric: {metric}. Must be one of {", ".join(valid_metrics)}')
            
            # Validate date formats
            date_from = None
            date_to = None
            
            if start_date:
                try:
                    date_from = datetime.strptime(start_date, '%Y-%m-%d').date()
                except ValueError:
                    return error_response(400, f'Invalid start_date format: {start_date}. Use YYYY-MM-DD')
            
            if end_date:
                try:
                    date_to = datetime.strptime(end_date, '%Y-%m-%d').date()
                except ValueError:
                    return error_response(400, f'Invalid end_date format: {end_date}. Use YYYY-MM-DD')
            
            # Validate date range
            if date_from and date_to and date_from > date_to:
                return error_response(400, 'start_date cannot be after end_date')
            
            # Get ranking data from service
            from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
            service = PerformanceService(request.env)
            
            ranking_data = service.get_top_agents_ranking(
                company_id=company_id,
                metric=metric,
                limit=limit,
                date_from=date_from,
                date_to=date_to
            )
            
            return success_response(ranking_data)
            
        except UserError as e:
            # Handle not found / access denied from service
            error_msg = str(e)
            if 'not found' in error_msg.lower():
                return error_response(404, error_msg)
            elif 'access denied' in error_msg.lower() or 'different company' in error_msg.lower():
                return error_response(403, error_msg)
            else:
                return error_response(400, error_msg)
        except ValidationError as e:
            return error_response(400, str(e))
        except Exception as e:
            _logger.exception('Error getting agents ranking')
            return error_response(500, f'Internal server error: {str(e)}')