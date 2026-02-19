# -*- coding: utf-8 -*-
"""
Lease API Controller — Feature 008

Provides 7 REST endpoints for lease lifecycle management:
  GET    /api/v1/leases              — Paginated list with filters
  POST   /api/v1/leases              — Create lease with validation
  GET    /api/v1/leases/<id>         — Detail with property+tenant info
  PUT    /api/v1/leases/<id>         — Update (non-terminated only)
  DELETE /api/v1/leases/<id>         — Soft archive (ADR-015)
  POST   /api/v1/leases/<id>/renew   — In-place renewal with audit
  POST   /api/v1/leases/<id>/terminate — Early termination

Reference: owner_api.py, company_api.py patterns
FRs covered: FR-009..FR-020, FR-030..FR-034, FR-037
"""
import json
import logging
from datetime import datetime
from odoo import http, fields as odoo_fields
from odoo.http import request
from odoo.exceptions import AccessError, ValidationError
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from .utils.schema import SchemaValidator
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company
from ..utils.responses import (
    success_response as util_success,
    error_response as util_error,
    paginated_response,
    build_hateoas_links,
    build_pagination_links
)

_logger = logging.getLogger(__name__)


class LeaseApiController(http.Controller):

    # ========== HELPERS ==========

    def _get_company_ids(self):
        """Get company IDs from current session context."""
        user = request.env.user
        if user.has_group('base.group_system'):
            return None
        return user.estate_company_ids.ids

    def _get_agent_property_ids(self, user, company_ids):
        """Get property IDs assigned to agent (transitive RBAC per R3)."""
        agent = request.env['real.estate.agent'].sudo().search([
            ('user_id', '=', user.id),
            ('company_ids', 'in', company_ids),
        ], limit=1)
        if not agent:
            return []
        assignments = request.env['real.estate.agent.property.assignment'].sudo().search([
            ('agent_id', '=', agent.id),
        ])
        return assignments.mapped('property_id').ids

    def _is_agent_role(self, user):
        """Check if user has only agent role (not manager/owner)."""
        return (
            user.has_group('quicksol_estate.group_real_estate_agent')
            and not user.has_group('quicksol_estate.group_real_estate_manager')
            and not user.has_group('quicksol_estate.group_real_estate_owner')
            and not user.has_group('base.group_system')
        )

    def _serialize_lease(self, lease):
        """Serialize a lease record to dict with HATEOAS links."""
        relations = {
            'property': f'/api/v1/properties/{lease.property_id.id}' if lease.property_id else None,
            'profile': f'/api/v1/profiles/{lease.profile_id.id}' if lease.profile_id else None,
        }
        # Action links based on status
        if lease.status == 'active':
            relations['renew'] = '/renew'
            relations['terminate'] = '/terminate'

        links = build_hateoas_links(
            base_url='/api/v1/leases',
            resource_id=lease.id,
            relations={'renew': '/renew', 'terminate': '/terminate'},
        )
        # Add absolute related resource links
        if lease.property_id:
            links['property'] = f'/api/v1/properties/{lease.property_id.id}'
        if lease.profile_id:
            links['profile'] = f'/api/v1/profiles/{lease.profile_id.id}'

        return {
            'id': lease.id,
            'name': lease.name,
            'property_id': lease.property_id.id,
            'property_name': lease.property_id.name if lease.property_id else None,
            'profile_id': lease.profile_id.id,
            'profile_name': lease.profile_id.name if lease.profile_id else None,
            'start_date': str(lease.start_date) if lease.start_date else None,
            'end_date': str(lease.end_date) if lease.end_date else None,
            'rent_amount': lease.rent_amount,
            'status': lease.status,
            'active': lease.active,
            'termination_date': str(lease.termination_date) if lease.termination_date else None,
            'termination_reason': lease.termination_reason or None,
            'termination_penalty': lease.termination_penalty or 0.0,
            'renewal_count': len(lease.renewal_history_ids),
            'company_ids': lease.company_ids.ids,
            '_links': links,
        }

    # ========== LIST LEASES (FR-009, FR-030, FR-033) ==========

    @http.route('/api/v1/leases', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_leases(self, page=1, page_size=20, **kwargs):
        """List leases with pagination, filters, and company isolation."""
        try:
            user = request.env.user
            company_ids = self._get_company_ids()

            # Pagination
            try:
                page = int(page)
                page_size = min(int(page_size), 100)
            except (ValueError, TypeError):
                resp, code = util_error('Invalid pagination parameters', status_code=400)
                return request.make_json_response(resp, status=code)

            if page < 1 or page_size < 1:
                resp, code = util_error('Page and page_size must be positive integers', status_code=400)
                return request.make_json_response(resp, status=code)

            # Base domain
            domain = [('active', '=', True)]

            # is_active filter (US5)
            is_active = kwargs.get('is_active')
            if is_active is not None and is_active.lower() == 'false':
                domain = [('active', '=', False)]

            # Company isolation (FR-030)
            if company_ids is not None:
                domain.append(('company_ids', 'in', company_ids))

            # Optional filters
            if kwargs.get('property_id'):
                try:
                    domain.append(('property_id', '=', int(kwargs['property_id'])))
                except ValueError:
                    pass
            if kwargs.get('profile_id'):
                try:
                    domain.append(('profile_id', '=', int(kwargs['profile_id'])))
                except ValueError:
                    pass
            if kwargs.get('status'):
                domain.append(('status', '=', kwargs['status']))

            # Agent RBAC: filter by assigned properties (R3)
            if self._is_agent_role(user):
                assigned_prop_ids = self._get_agent_property_ids(user, company_ids or [])
                if assigned_prop_ids:
                    domain.append(('property_id', 'in', assigned_prop_ids))
                else:
                    resp, code = paginated_response(items=[], total=0, page=page, page_size=page_size)
                    return request.make_json_response(resp, status=code)

            # Search
            Lease = request.env['real.estate.lease'].sudo()
            if is_active is not None and is_active.lower() == 'false':
                Lease = Lease.with_context(active_test=False)

            total = Lease.search_count(domain)
            offset = (page - 1) * page_size
            leases = Lease.search(domain, limit=page_size, offset=offset, order='start_date desc')

            items = [self._serialize_lease(l) for l in leases]

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            links = build_pagination_links('/api/v1/leases', page, total_pages)

            resp, code = paginated_response(
                items=items, total=total, page=page, page_size=page_size, links=links,
            )
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error listing leases: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== CREATE LEASE (FR-010, FR-011, FR-012, FR-013) ==========

    @http.route('/api/v1/leases', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_lease(self, **kwargs):
        """Create a new lease with validation."""
        try:
            # Parse body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.LEASE_CREATE_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            company_ids = self._get_company_ids()
            if not company_ids:
                return error_response(400, 'No company context available')

            # Validate property exists and belongs to company (FR-012)
            prop = request.env['real.estate.property'].sudo().browse(data['property_id'])
            if not prop.exists():
                return error_response(404, 'Property not found')
            if company_ids is not None:
                if not any(cid in company_ids for cid in prop.company_ids.ids):
                    return error_response(404, 'Property not found')

            # Reject if property is sold (FR-029 / FR-013 guard)
            if hasattr(prop, 'state') and prop.state == 'sold':
                resp, code = util_error(
                    'Cannot create lease for a sold property',
                    status_code=400,
                )
                return request.make_json_response(resp, status=code)

            # Validate profile exists and belongs to company (FR-012)
            profile = request.env['thedevkitchen.estate.profile'].sudo().browse(data['profile_id'])
            if not profile.exists() or not profile.is_active:
                return error_response(404, 'Profile not found')
            if company_ids is not None:
                if profile.company_id.id not in company_ids:
                    return error_response(404, 'Profile not found')

            # Date validation (end > start) — FR-010
            try:
                start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
                end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                return error_response(400, 'Invalid date format. Use YYYY-MM-DD')

            if end_date <= start_date:
                resp, code = util_error('End date must be after start date', status_code=400)
                return request.make_json_response(resp, status=code)

            # Prepare vals
            lease_vals = {
                'property_id': data['property_id'],
                'profile_id': data['profile_id'],
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'rent_amount': data['rent_amount'],
                'status': data.get('status', 'draft'),
                'company_ids': [(6, 0, company_ids)],
            }

            # Create (constraint _check_concurrent_lease handles FR-013)
            try:
                lease = request.env['real.estate.lease'].sudo().create(lease_vals)
            except ValidationError as ve:
                resp, code = util_error(str(ve), status_code=400)
                return request.make_json_response(resp, status=code)

            lease_data = self._serialize_lease(lease)
            links = build_hateoas_links('/api/v1/leases', lease.id, {'renew': '/renew', 'terminate': '/terminate'})

            resp, code = util_success(
                data=lease_data,
                message='Lease created successfully',
                links=links,
                status_code=201,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error creating lease: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error creating lease: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== GET LEASE (FR-014, FR-015) ==========

    @http.route('/api/v1/leases/<int:lease_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_lease(self, lease_id, **kwargs):
        """Get lease by ID with property, tenant, and renewal info."""
        try:
            user = request.env.user
            company_ids = self._get_company_ids()

            lease = request.env['real.estate.lease'].sudo().browse(lease_id)
            if not lease.exists() or not lease.active:
                return error_response(404, 'Lease not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in lease.company_ids.ids):
                    return error_response(404, 'Lease not found')

            # Agent RBAC
            if self._is_agent_role(user):
                assigned_prop_ids = self._get_agent_property_ids(user, company_ids or [])
                if lease.property_id.id not in assigned_prop_ids:
                    return error_response(404, 'Lease not found')

            lease_data = self._serialize_lease(lease)

            # Add renewal history
            lease_data['renewal_history'] = [{
                'id': rh.id,
                'previous_end_date': str(rh.previous_end_date) if rh.previous_end_date else None,
                'previous_rent_amount': rh.previous_rent_amount,
                'new_end_date': str(rh.new_end_date) if rh.new_end_date else None,
                'new_rent_amount': rh.new_rent_amount,
                'renewed_by': rh.renewed_by_id.name if rh.renewed_by_id else None,
                'reason': rh.reason or None,
                'renewal_date': str(rh.renewal_date) if rh.renewal_date else None,
            } for rh in lease.renewal_history_ids]

            links = build_hateoas_links('/api/v1/leases', lease.id, {'renew': '/renew', 'terminate': '/terminate'})
            resp, code = util_success(data=lease_data, links=links)
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error getting lease {lease_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== UPDATE LEASE (FR-016) ==========

    @http.route('/api/v1/leases/<int:lease_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_lease(self, lease_id, **kwargs):
        """Update lease (non-terminated only). Supports reactivation via active=true (US5 / FR-007)."""
        try:
            company_ids = self._get_company_ids()

            # Browse with active_test=False to allow reactivation of archived records
            lease = request.env['real.estate.lease'].sudo().with_context(active_test=False).browse(lease_id)
            if not lease.exists():
                return error_response(404, 'Lease not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in lease.company_ids.ids):
                    return error_response(404, 'Lease not found')

            # Parse body first (needed to check reactivation intent)
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # If record is inactive and no reactivation requested, reject
            if not lease.active and data.get('active') is not True:
                return error_response(404, 'Lease not found')

            # Cannot update terminated/expired leases (FR-016) unless reactivating
            if lease.status in ('terminated', 'expired') and data.get('active') is not True:
                resp, code = util_error(
                    f'Cannot update a lease with status: {lease.status}',
                    status_code=400,
                )
                return request.make_json_response(resp, status=code)

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.LEASE_UPDATE_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            # Build update vals
            update_vals = {}
            for field in ['start_date', 'end_date', 'rent_amount', 'status']:
                if field in data:
                    update_vals[field] = data[field]

            # Reactivation support (US5 / FR-007)
            if data.get('active') is True and not lease.active:
                update_vals['active'] = True

            if not update_vals:
                resp, code = util_error('No fields to update', status_code=400)
                return request.make_json_response(resp, status=code)

            try:
                lease.write(update_vals)
            except ValidationError as ve:
                resp, code = util_error(str(ve), status_code=400)
                return request.make_json_response(resp, status=code)

            lease_data = self._serialize_lease(lease)
            links = build_hateoas_links('/api/v1/leases', lease.id, {'renew': '/renew', 'terminate': '/terminate'})

            resp, code = util_success(
                data=lease_data,
                message='Lease updated successfully',
                links=links,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error updating lease {lease_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error updating lease {lease_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== DELETE / ARCHIVE LEASE (ADR-015 soft delete) ==========

    @http.route('/api/v1/leases/<int:lease_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_lease(self, lease_id, **kwargs):
        """Soft-archive a lease."""
        try:
            company_ids = self._get_company_ids()

            lease = request.env['real.estate.lease'].sudo().browse(lease_id)
            if not lease.exists() or not lease.active:
                return error_response(404, 'Lease not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in lease.company_ids.ids):
                    return error_response(404, 'Lease not found')

            lease.write({'active': False})

            resp, code = util_success(
                data={'id': lease.id, 'active': False},
                message='Lease archived successfully',
            )
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error archiving lease {lease_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== RENEW LEASE (FR-017, R5 — in-place with audit) ==========

    @http.route('/api/v1/leases/<int:lease_id>/renew', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def renew_lease(self, lease_id, **kwargs):
        """Renew a lease in-place with audit history (Clarification C2)."""
        try:
            company_ids = self._get_company_ids()

            lease = request.env['real.estate.lease'].sudo().browse(lease_id)
            if not lease.exists() or not lease.active:
                return error_response(404, 'Lease not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in lease.company_ids.ids):
                    return error_response(404, 'Lease not found')

            # Only active leases can be renewed
            if lease.status != 'active':
                resp, code = util_error(
                    f'Cannot renew a lease with status: {lease.status}. Only active leases can be renewed.',
                    status_code=400,
                )
                return request.make_json_response(resp, status=code)

            # Parse body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.LEASE_RENEW_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            # Validate new_end_date > current end_date
            try:
                new_end_date = datetime.strptime(data['new_end_date'], '%Y-%m-%d').date()
            except ValueError:
                return error_response(400, 'Invalid date format. Use YYYY-MM-DD')

            if new_end_date <= lease.end_date:
                resp, code = util_error(
                    'New end date must be after current end date',
                    status_code=400,
                )
                return request.make_json_response(resp, status=code)

            # Capture previous values for audit
            previous_end_date = lease.end_date
            previous_rent_amount = lease.rent_amount
            new_rent_amount = data.get('new_rent_amount', lease.rent_amount)

            # Create renewal history record
            request.env['real.estate.lease.renewal.history'].sudo().create({
                'lease_id': lease.id,
                'previous_end_date': previous_end_date,
                'previous_rent_amount': previous_rent_amount,
                'new_end_date': new_end_date,
                'new_rent_amount': new_rent_amount,
                'renewed_by_id': request.env.user.id,
                'reason': data.get('reason', ''),
            })

            # Update lease in-place (C2: mutate with audit)
            update_vals = {'end_date': data['new_end_date']}
            if 'new_rent_amount' in data:
                update_vals['rent_amount'] = data['new_rent_amount']

            lease.write(update_vals)

            lease_data = self._serialize_lease(lease)
            links = build_hateoas_links('/api/v1/leases', lease.id, {'renew': '/renew', 'terminate': '/terminate'})

            resp, code = util_success(
                data=lease_data,
                message='Lease renewed successfully',
                links=links,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error renewing lease {lease_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error renewing lease {lease_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== TERMINATE LEASE (FR-018, FR-019) ==========

    @http.route('/api/v1/leases/<int:lease_id>/terminate', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def terminate_lease(self, lease_id, **kwargs):
        """Terminate a lease early with optional penalty (Clarification C4: informational only)."""
        try:
            company_ids = self._get_company_ids()

            lease = request.env['real.estate.lease'].sudo().browse(lease_id)
            if not lease.exists() or not lease.active:
                return error_response(404, 'Lease not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in lease.company_ids.ids):
                    return error_response(404, 'Lease not found')

            # Only active leases can be terminated
            if lease.status != 'active':
                resp, code = util_error(
                    f'Cannot terminate a lease with status: {lease.status}. Only active leases can be terminated.',
                    status_code=400,
                )
                return request.make_json_response(resp, status=code)

            # Parse body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.LEASE_TERMINATE_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            # Validate termination date
            try:
                termination_date = datetime.strptime(data['termination_date'], '%Y-%m-%d').date()
            except ValueError:
                return error_response(400, 'Invalid date format. Use YYYY-MM-DD')

            # Terminate
            update_vals = {
                'status': 'terminated',
                'termination_date': data['termination_date'],
                'termination_reason': data.get('reason', ''),
            }
            if 'penalty_amount' in data:
                update_vals['termination_penalty'] = data['penalty_amount']

            lease.with_context(lease_terminate=True).write(update_vals)

            lease_data = self._serialize_lease(lease)
            links = build_hateoas_links('/api/v1/leases', lease.id)

            resp, code = util_success(
                data=lease_data,
                message='Lease terminated successfully',
                links=links,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error terminating lease {lease_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error terminating lease {lease_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
