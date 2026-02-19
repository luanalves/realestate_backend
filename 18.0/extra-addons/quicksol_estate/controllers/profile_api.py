# -*- coding: utf-8 -*-
"""
Profile API Controller (Feature 010 - T11)

REST endpoints for unified profile management (9 RBAC types).
Follows triple decorator pattern (ADR-011), HATEOAS, RBAC authorization matrix.

Endpoints:
- POST   /api/v1/profiles          - Create profile
- GET    /api/v1/profiles          - List profiles (paginated)
- GET    /api/v1/profiles/<id>     - Get profile detail
- PUT    /api/v1/profiles/<id>     - Update profile
- DELETE /api/v1/profiles/<id>     - Soft delete profile
- GET    /api/v1/profile-types     - List profile types
"""

import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from .utils.schema import SchemaValidator
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from ..utils import validators

_logger = logging.getLogger(__name__)


# RBAC Authorization Matrix (FR1.10, ADR-019)
# Maps creator role → list of profile types they can create
PROFILE_CREATION_MATRIX = {
    'quicksol_estate.group_real_estate_owner': [
        'owner', 'director', 'manager', 'agent', 'prospector', 
        'receptionist', 'financial', 'legal', 'portal'
    ],
    'quicksol_estate.group_real_estate_director': [
        'agent', 'prospector', 'receptionist', 'financial', 'legal'
    ],
    'quicksol_estate.group_real_estate_manager': [
        'agent', 'prospector', 'receptionist', 'financial', 'legal'
    ],
    'quicksol_estate.group_real_estate_agent': [
        'owner', 'portal'  # Agent can create owner (property owner) or portal (tenant)
    ],
}


class ProfileApiController(http.Controller):
    
    def _get_user_allowed_profile_types(self, user):
        """Get list of profile type codes the user is authorized to create"""
        allowed_types = []
        
        for group_xml_id, types in PROFILE_CREATION_MATRIX.items():
            if user.has_group(group_xml_id):
                # Return the most permissive role (owner has all)
                if len(types) > len(allowed_types):
                    allowed_types = types
        
        return allowed_types
    
    def _serialize_profile(self, profile):
        """Serialize profile record to JSON dict with HATEOAS links"""
        data = {
            'id': profile.id,
            'name': profile.name,
            'document': profile.document,
            'email': profile.email,
            'phone': profile.phone,
            'mobile': profile.mobile,
            'occupation': profile.occupation,
            'birthdate': profile.birthdate.isoformat() if profile.birthdate else None,
            'hire_date': profile.hire_date.isoformat() if profile.hire_date else None,
            'profile_type': profile.profile_type_id.code if profile.profile_type_id else None,
            'profile_type_name': profile.profile_type_id.name if profile.profile_type_id else None,
            'company_id': profile.company_id.id if profile.company_id else None,
            'company_name': profile.company_id.name if profile.company_id else None,
            'active': profile.active,
            'created_at': profile.created_at.isoformat() if profile.created_at else None,
            'updated_at': profile.updated_at.isoformat() if profile.updated_at else None,
            '_links': {
                'self': f'/api/v1/profiles/{profile.id}',
                'company': f'/api/v1/companies/{profile.company_id.id}' if profile.company_id else None,
            }
        }
        
        # Add agent extension link if profile_type='agent'
        if profile.profile_type_id.code == 'agent':
            agent = request.env['real.estate.agent'].sudo().search([
                ('profile_id', '=', profile.id)
            ], limit=1)
            if agent:
                data['agent_id'] = agent.id
                data['_links']['agent'] = f'/api/v1/agents/{agent.id}'
        
        # Add invite link if no user yet (partner_id exists but no user)
        if profile.partner_id and not profile.partner_id.user_ids:
            data['_links']['invite'] = f'/api/v1/users/invite'
        
        return data
    
    @http.route('/api/v1/profiles', 
                type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_profile(self, **kwargs):
        """
        Create a new profile (US1, FR1.1)
        
        Body: name, company_id, document, email, birthdate, profile_type, 
              phone*, mobile*, occupation*, hire_date*
        
        RBAC: Owner→all 9, Manager→5 operational, Agent→owner+portal
        Auto-creates agent extension if profile_type='agent'
        """
        try:
            user = request.env.user
            
            # Parse and validate JSON body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            validator = SchemaValidator()
            
            is_valid, errors = validator.validate(body, 'PROFILE_CREATE_SCHEMA')
            if not is_valid:
                return error_response(400, f'Validation error: {errors}')
            
            # Validate company_id from body against user's companies (D5.1)
            company_id = body['company_id']
            if request.user_company_ids and company_id not in request.user_company_ids:
                return error_response(403, f'Access denied to company {company_id}')
            
            # Lookup profile_type record by code
            profile_type_code = body['profile_type']
            ProfileType = request.env['thedevkitchen.profile.type']
            profile_type = ProfileType.sudo().search([
                ('code', '=', profile_type_code),
                ('is_active', '=', True)
            ], limit=1)
            
            if not profile_type:
                return error_response(400, f'Invalid profile_type: {profile_type_code}')
            
            # Check RBAC authorization matrix (FR1.10)
            allowed_types = self._get_user_allowed_profile_types(user)
            if profile_type_code not in allowed_types:
                return error_response(403, f'Your role cannot create profile_type: {profile_type_code}')
            
            # Normalize document (D11)
            document_raw = body['document']
            document_normalized = validators.normalize_document(document_raw)
            
            if not validators.validate_document(document_normalized):
                return error_response(400, f'Invalid document (CPF/CNPJ): {document_raw}')
            
            # Check for duplicate (document, company_id, profile_type_id)
            Profile = request.env['thedevkitchen.estate.profile']
            existing = Profile.sudo().search([
                ('document', '=', document_normalized),
                ('company_id', '=', company_id),
                ('profile_type_id', '=', profile_type.id)
            ], limit=1)
            
            if existing:
                return error_response(409, 
                    f'Profile already exists with this document ({document_raw}) for profile_type {profile_type_code} in company {company_id}')
            
            # Build profile vals
            profile_vals = {
                'name': body['name'],
                'company_id': company_id,
                'profile_type_id': profile_type.id,
                'document': document_normalized,
                'email': body['email'],
                'birthdate': body['birthdate'],
                'phone': body.get('phone'),
                'mobile': body.get('mobile'),
                'occupation': body.get('occupation'),
                'hire_date': body.get('hire_date'),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            }
            
            # Create profile
            profile = Profile.sudo().create(profile_vals)
            
            # If profile_type='agent', auto-create agent extension (FR1.4)
            if profile_type_code == 'agent':
                Agent = request.env['real.estate.agent']
                agent_vals = {
                    'profile_id': profile.id,
                    'name': profile.name,
                    'cpf': profile.document,
                    'email': profile.email,
                    'phone': profile.phone,
                    'mobile': profile.mobile,
                    'company_id': company_id,
                    'hire_date': profile.hire_date,
                }
                agent = Agent.sudo().create(agent_vals)
                _logger.info(f'Auto-created agent {agent.id} for profile {profile.id}')
            
            # Serialize response with HATEOAS (FR1.9)
            response_data = self._serialize_profile(profile)
            
            return success_response(response_data, status=201)
            
        except ValidationError as e:
            _logger.warning(f'Validation error creating profile: {str(e)}')
            return error_response(400, str(e))
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON body')
        except Exception as e:
            _logger.exception('Error creating profile')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/profiles', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_profiles(self, **kwargs):
        """
        List profiles with filtering and pagination (US2, FR2.1)
        
        Query params:
        - company_ids: Required, comma-separated (D5.2)
        - profile_type*: Filter by type code
        - document*: Filter by document
        - name*: Search by name (ilike)
        - active*: 'true', 'false', or omit for all
        - limit: Max 100, default 20
        - offset: Default 0
        """
        try:
            user = request.env.user
            
            # Validate required company_ids parameter (D5.2)
            company_ids_param = kwargs.get('company_ids')
            if not company_ids_param:
                return error_response(400, 'company_ids parameter is required')
            
            # Parse company_ids
            try:
                requested_company_ids = [int(cid.strip()) for cid in company_ids_param.split(',')]
            except ValueError:
                return error_response(400, 'Invalid company_ids format. Use comma-separated integers.')
            
            # Validate user access to requested companies
            if request.user_company_ids:  # Not admin
                unauthorized = [cid for cid in requested_company_ids if cid not in request.user_company_ids]
                if unauthorized:
                    return error_response(403, f'Access denied to company IDs: {unauthorized}')
            
            # Build domain
            domain = []
            
            # Company filter
            if len(requested_company_ids) == 1:
                domain.append(('company_id', '=', requested_company_ids[0]))
            else:
                domain.append(('company_id', 'in', requested_company_ids))
            
            # Optional filters
            profile_type = kwargs.get('profile_type')
            if profile_type:
                ProfileType = request.env['thedevkitchen.profile.type']
                ptype = ProfileType.sudo().search([('code', '=', profile_type)], limit=1)
                if ptype:
                    domain.append(('profile_type_id', '=', ptype.id))
                else:
                    return error_response(400, f'Invalid profile_type: {profile_type}')
            
            document = kwargs.get('document')
            if document:
                normalized = validators.normalize_document(document)
                domain.append(('document', '=', normalized))
            
            name = kwargs.get('name')
            if name:
                domain.append(('name', 'ilike', name))
            
            # Active filter (ADR-015)
            is_active = kwargs.get('active')
            if is_active is not None:
                if is_active.lower() == 'true':
                    domain.append(('active', '=', True))
                elif is_active.lower() == 'false':
                    domain.append(('active', '=', False))
            
            # Pagination
            limit = min(int(kwargs.get('limit', 20)), 100)
            offset = int(kwargs.get('offset', 0))
            
            # Query profiles
            Profile = request.env['thedevkitchen.estate.profile']
            total = Profile.with_context(active_test=False).sudo().search_count(domain)
            profiles = Profile.with_context(active_test=False).sudo().search(
                domain, limit=limit, offset=offset, order='name asc'
            )
            
            # Serialize profiles
            profile_list = [self._serialize_profile(p) for p in profiles]
            
            # HATEOAS pagination links (FR2.4)
            company_ids_str = ','.join(str(cid) for cid in requested_company_ids)
            response_data = {
                'success': True,
                'data': profile_list,
                'count': len(profile_list),
                'total': total,
                'limit': limit,
                'offset': offset,
                '_links': {
                    'self': f'/api/v1/profiles?company_ids={company_ids_str}&limit={limit}&offset={offset}',
                }
            }
            
            # Next/prev links
            if offset + limit < total:
                response_data['_links']['next'] = f'/api/v1/profiles?company_ids={company_ids_str}&limit={limit}&offset={offset + limit}'
            if offset > 0:
                prev_offset = max(0, offset - limit)
                response_data['_links']['prev'] = f'/api/v1/profiles?company_ids={company_ids_str}&limit={limit}&offset={prev_offset}'
            
            return success_response(response_data)
            
        except ValueError as e:
            return error_response(400, f'Invalid parameter: {str(e)}')
        except Exception as e:
            _logger.exception('Error listing profiles')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/profiles/<int:profile_id>', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_profile(self, profile_id, **kwargs):
        """
        Get profile detail by ID (US2, FR2.6)
        
        Returns 404 if profile not found or cross-company access (anti-enumeration)
        """
        try:
            user = request.env.user
            
            Profile = request.env['thedevkitchen.estate.profile']
            profile = Profile.sudo().search([('id', '=', profile_id)], limit=1)
            
            if not profile:
                return error_response(404, 'Profile not found')
            
            # Company isolation check (FR1.12, anti-enumeration)
            if request.user_company_ids and profile.company_id.id not in request.user_company_ids:
                return error_response(404, 'Profile not found')  # Don't reveal existence
            
            # Serialize with HATEOAS
            response_data = self._serialize_profile(profile)
            
            return success_response(response_data)
            
        except Exception as e:
            _logger.exception(f'Error fetching profile {profile_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/profiles/<int:profile_id>', 
                type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_profile(self, profile_id, **kwargs):
        """
        Update profile (US3, FR3.1)
        
        Immutable fields: profile_type, company_id, document
        Syncs changes to agent extension if profile_type='agent'
        """
        try:
            user = request.env.user
            
            # Parse and validate body
            body = json.loads(request.httprequest.data.decode('utf-8'))
            validator = SchemaValidator()
            
            is_valid, errors = validator.validate(body, 'PROFILE_UPDATE_SCHEMA')
            if not is_valid:
                return error_response(400, f'Validation error: {errors}')
            
            # Reject immutable fields (FR3.2)
            immutable_fields = ['profile_type', 'company_id', 'document']
            for field in immutable_fields:
                if field in body:
                    return error_response(400, f'Field {field} is immutable and cannot be updated')
            
            # Fetch profile
            Profile = request.env['thedevkitchen.estate.profile']
            profile = Profile.sudo().search([('id', '=', profile_id)], limit=1)
            
            if not profile:
                return error_response(404, 'Profile not found')
            
            # Company isolation check
            if request.user_company_ids and profile.company_id.id not in request.user_company_ids:
                return error_response(404, 'Profile not found')
            
            # Build update vals
            update_vals = {
                'updated_at': datetime.now()
            }
            
            # Update mutable fields
            for field in ['name', 'email', 'phone', 'mobile', 'occupation', 'birthdate', 'hire_date']:
                if field in body:
                    update_vals[field] = body[field]
            
            # Update profile
            profile.write(update_vals)
            
            # Sync to agent extension if profile_type='agent' (FR3.4)
            if profile.profile_type_id.code == 'agent':
                Agent = request.env['real.estate.agent']
                agent = Agent.sudo().search([('profile_id', '=', profile.id)], limit=1)
                if agent:
                    agent_update_vals = {}
                    if 'name' in body:
                        agent_update_vals['name'] = body['name']
                    if 'email' in body:
                        agent_update_vals['email'] = body['email']
                    if 'phone' in body:
                        agent_update_vals['phone'] = body['phone']
                    if 'mobile' in body:
                        agent_update_vals['mobile'] = body['mobile']
                    if 'hire_date' in body:
                        agent_update_vals['hire_date'] = body['hire_date']
                    
                    if agent_update_vals:
                        agent.write(agent_update_vals)
                        _logger.info(f'Synced profile {profile.id} updates to agent {agent.id}')
            
            # Serialize response
            response_data = self._serialize_profile(profile)
            
            return success_response(response_data)
            
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON body')
        except Exception as e:
            _logger.exception(f'Error updating profile {profile_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/profiles/<int:profile_id>', 
                type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_profile(self, profile_id, **kwargs):
        """
        Soft delete profile (US4, FR4.1)
        
        Sets active=False, deactivation_date, deactivation_reason.
        Cascades to agent extension and linked res.users (FR4.2).
        """
        try:
            user = request.env.user
            
            # Parse optional body for deactivation_reason
            deactivation_reason = None
            try:
                body = json.loads(request.httprequest.data.decode('utf-8'))
                deactivation_reason = body.get('reason')
            except (json.JSONDecodeError, AttributeError):
                pass  # Optional body
            
            # Fetch profile
            Profile = request.env['thedevkitchen.estate.profile']
            profile = Profile.sudo().search([('id', '=', profile_id)], limit=1)
            
            if not profile:
                return error_response(404, 'Profile not found')
            
            # Company isolation check
            if request.user_company_ids and profile.company_id.id not in request.user_company_ids:
                return error_response(404, 'Profile not found')
            
            # Check if already inactive (ADR-015)
            if not profile.active:
                return error_response(400, 'Profile is already inactive')
            
            # Soft delete profile
            profile.write({
                'active': False,
                'deactivation_date': datetime.now(),
                'deactivation_reason': deactivation_reason or 'Deactivated via API',
            })
            
            # Cascade to agent extension if profile_type='agent' (FR4.2)
            if profile.profile_type_id.code == 'agent':
                Agent = request.env['real.estate.agent']
                agent = Agent.sudo().search([('profile_id', '=', profile.id)], limit=1)
                if agent and agent.active:
                    agent.write({
                        'active': False,
                        'deactivation_date': datetime.now(),
                        'deactivation_reason': deactivation_reason or 'Profile deactivated',
                    })
                    _logger.info(f'Cascaded deactivation to agent {agent.id}')
            
            # Cascade to linked res.users (FR4.2)
            if profile.partner_id:
                User = request.env['res.users']
                users = User.sudo().search([('partner_id', '=', profile.partner_id.id)])
                for user_record in users:
                    if user_record.active:
                        user_record.write({'active': False})
                        _logger.info(f'Deactivated user {user_record.id} linked to profile {profile.id}')
            
            return success_response({
                'success': True,
                'message': f'Profile {profile_id} deactivated successfully',
            })
            
        except Exception as e:
            _logger.exception(f'Error deleting profile {profile_id}')
            return error_response(500, f'Internal server error: {str(e)}')
    
    @http.route('/api/v1/profile-types', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    def list_profile_types(self, **kwargs):
        """
        List all active profile types (FR1.11)
        
        No @require_company decorator — profile types are global.
        Returns seed data from profile_type_data.xml.
        """
        try:
            ProfileType = request.env['thedevkitchen.profile.type']
            types = ProfileType.sudo().search([('is_active', '=', True)], order='name asc')
            
            type_list = []
            for ptype in types:
                type_list.append({
                    'id': ptype.id,
                    'code': ptype.code,
                    'name': ptype.name,
                    'level': ptype.level,
                    'group_xml_id': ptype.group_xml_id,
                })
            
            return success_response({
                'success': True,
                'data': type_list,
                'count': len(type_list),
            })
            
        except Exception as e:
            _logger.exception('Error listing profile types')
            return error_response(500, f'Internal server error: {str(e)}')
