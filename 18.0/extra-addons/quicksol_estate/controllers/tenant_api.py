# -*- coding: utf-8 -*-
"""
Tenant API Controller — Feature 008

Provides 5 REST endpoints for tenant CRUD management:
  GET    /api/v1/tenants          — Paginated list with company filter
  POST   /api/v1/tenants          — Create tenant with schema validation
  GET    /api/v1/tenants/<id>     — Detail with lease references
  PUT    /api/v1/tenants/<id>     — Update tenant
  DELETE /api/v1/tenants/<id>     — Soft archive (ADR-015)

Reference: owner_api.py, company_api.py patterns
FRs covered: FR-001..FR-006, FR-030..FR-034, FR-037
"""
import json
import logging
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
from ..utils.validators import validate_email_format

_logger = logging.getLogger(__name__)


class TenantApiController(http.Controller):

    # ========== HELPERS ==========

    def _get_company_ids(self):
        """Get company IDs from current session context."""
        user = request.env.user
        if user.has_group('base.group_system'):
            return None  # Admin sees all
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

    def _serialize_tenant(self, tenant):
        """Serialize a tenant record to dict with HATEOAS links."""
        links = build_hateoas_links(
            base_url='/api/v1/tenants',
            resource_id=tenant.id,
            relations={'leases': '/leases'}
        )
        return {
            'id': tenant.id,
            'name': tenant.name,
            'phone': tenant.phone or None,
            'email': tenant.email or None,
            'occupation': tenant.occupation or None,
            'birthdate': str(tenant.birthdate) if tenant.birthdate else None,
            'active': tenant.active,
            'company_ids': tenant.company_ids.ids,
            'lease_count': len(tenant.leases),
            '_links': links,
        }

    # ========== LIST TENANTS (FR-001, FR-030, FR-033) ==========

    @http.route('/api/v1/tenants', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_tenants(self, page=1, page_size=20, **kwargs):
        """List tenants with pagination and company isolation."""
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

            # Base domain: active records only (soft delete)
            domain = [('active', '=', True)]

            # is_active filter (US5 — will be enhanced in Phase 7)
            is_active = kwargs.get('is_active')
            if is_active is not None and is_active.lower() == 'false':
                domain = [('active', '=', False)]

            # Company isolation (FR-030)
            if company_ids is not None:
                domain.append(('company_ids', 'in', company_ids))

            # Agent RBAC: transitive filtering via property assignment (R3)
            if self._is_agent_role(user):
                assigned_prop_ids = self._get_agent_property_ids(user, company_ids or [])
                if assigned_prop_ids:
                    # Filter tenants who have leases on assigned properties
                    tenant_ids = request.env['real.estate.lease'].sudo().search([
                        ('property_id', 'in', assigned_prop_ids),
                    ]).mapped('tenant_id').ids
                    domain.append(('id', 'in', tenant_ids))
                else:
                    # Agent has no assignments → empty result
                    resp, code = paginated_response(items=[], total=0, page=page, page_size=page_size)
                    return request.make_json_response(resp, status=code)

            # Search
            Tenant = request.env['real.estate.tenant'].sudo()
            if is_active is not None and is_active.lower() == 'false':
                Tenant = Tenant.with_context(active_test=False)

            total = Tenant.search_count(domain)
            offset = (page - 1) * page_size
            tenants = Tenant.search(domain, limit=page_size, offset=offset, order='name')

            # Serialize
            items = [self._serialize_tenant(t) for t in tenants]

            # Pagination links
            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            links = build_pagination_links(
                base_url='/api/v1/tenants',
                page=page,
                total_pages=total_pages,
            )

            resp, code = paginated_response(
                items=items, total=total, page=page, page_size=page_size, links=links,
            )
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error listing tenants: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== CREATE TENANT (FR-002, FR-003) ==========

    @http.route('/api/v1/tenants', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_tenant(self, **kwargs):
        """Create a new tenant with schema validation."""
        try:
            # Parse body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.TENANT_CREATE_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            # Validate email format (FR-002)
            if data.get('email') and not validate_email_format(data['email']):
                resp, code = util_error(f"Invalid email format: {data['email']}", status_code=400)
                return request.make_json_response(resp, status=code)

            # Get company from request context
            company_ids = self._get_company_ids()
            if not company_ids:
                return error_response(400, 'No company context available')

            # Prepare vals
            tenant_vals = {
                'name': data['name'].strip(),
                'company_ids': [(6, 0, company_ids)],
            }

            # Optional fields
            for field in ['phone', 'email', 'occupation', 'birthdate']:
                if field in data and data[field] is not None:
                    tenant_vals[field] = data[field]

            # Create
            tenant = request.env['real.estate.tenant'].sudo().create(tenant_vals)

            # Response
            tenant_data = self._serialize_tenant(tenant)
            links = build_hateoas_links('/api/v1/tenants', tenant.id, {'leases': '/leases'})

            resp, code = util_success(
                data=tenant_data,
                message='Tenant created successfully',
                links=links,
                status_code=201,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error creating tenant: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error creating tenant: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== GET TENANT (FR-003) ==========

    @http.route('/api/v1/tenants/<int:tenant_id>', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_tenant(self, tenant_id, **kwargs):
        """Get tenant by ID with lease references."""
        try:
            user = request.env.user
            company_ids = self._get_company_ids()

            tenant = request.env['real.estate.tenant'].sudo().browse(tenant_id)
            if not tenant.exists() or not tenant.active:
                return error_response(404, 'Tenant not found')

            # Company isolation (FR-030)
            if company_ids is not None:
                if not any(cid in company_ids for cid in tenant.company_ids.ids):
                    return error_response(404, 'Tenant not found')

            # Agent RBAC
            if self._is_agent_role(user):
                assigned_prop_ids = self._get_agent_property_ids(user, company_ids or [])
                tenant_lease_props = tenant.leases.mapped('property_id').ids
                if not any(pid in assigned_prop_ids for pid in tenant_lease_props):
                    return error_response(404, 'Tenant not found')

            # Serialize with lease details
            tenant_data = self._serialize_tenant(tenant)
            tenant_data['leases'] = [{
                'id': lease.id,
                'name': lease.name,
                'property_id': lease.property_id.id,
                'property_name': lease.property_id.name,
                'start_date': str(lease.start_date) if lease.start_date else None,
                'end_date': str(lease.end_date) if lease.end_date else None,
                'rent_amount': lease.rent_amount,
                'status': lease.status if hasattr(lease, 'status') else None,
            } for lease in tenant.leases]

            links = build_hateoas_links('/api/v1/tenants', tenant.id, {'leases': '/leases'})
            resp, code = util_success(data=tenant_data, links=links)
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error getting tenant {tenant_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== UPDATE TENANT (FR-004) ==========

    @http.route('/api/v1/tenants/<int:tenant_id>', type='http', auth='none', methods=['PUT'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def update_tenant(self, tenant_id, **kwargs):
        """Update an existing tenant. Supports reactivation via active=true (US5 / FR-007)."""
        try:
            company_ids = self._get_company_ids()

            # Browse with active_test=False to allow reactivation of archived records
            tenant = request.env['real.estate.tenant'].sudo().with_context(active_test=False).browse(tenant_id)
            if not tenant.exists():
                return error_response(404, 'Tenant not found')

            # Company isolation (FR-030)
            if company_ids is not None:
                if not any(cid in company_ids for cid in tenant.company_ids.ids):
                    return error_response(404, 'Tenant not found')

            # Parse body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                return error_response(400, 'Invalid JSON in request body')

            # If record is inactive and no reactivation requested, reject
            if not tenant.active and data.get('active') is not True:
                return error_response(404, 'Tenant not found')

            # Validate schema
            is_valid, errors = SchemaValidator.validate_request(data, SchemaValidator.TENANT_UPDATE_SCHEMA)
            if not is_valid:
                resp, code = util_error('Validation failed', errors={'validation': errors}, status_code=400)
                return request.make_json_response(resp, status=code)

            # Validate email if provided
            if data.get('email') and not validate_email_format(data['email']):
                resp, code = util_error(f"Invalid email format: {data['email']}", status_code=400)
                return request.make_json_response(resp, status=code)

            # Build update vals
            update_vals = {}
            for field in ['name', 'phone', 'email', 'occupation', 'birthdate']:
                if field in data:
                    update_vals[field] = data[field].strip() if isinstance(data[field], str) else data[field]

            # Reactivation support (US5 / FR-007)
            if data.get('active') is True and not tenant.active:
                update_vals['active'] = True
                update_vals['deactivation_date'] = False
                update_vals['deactivation_reason'] = False

            if not update_vals:
                resp, code = util_error('No fields to update', status_code=400)
                return request.make_json_response(resp, status=code)

            tenant.write(update_vals)

            # Response
            tenant_data = self._serialize_tenant(tenant)
            links = build_hateoas_links('/api/v1/tenants', tenant.id, {'leases': '/leases'})

            resp, code = util_success(
                data=tenant_data,
                message='Tenant updated successfully',
                links=links,
            )
            return request.make_json_response(resp, status=code)

        except ValidationError as e:
            _logger.warning(f"Validation error updating tenant {tenant_id}: {str(e)}")
            return error_response(400, str(e))
        except Exception as e:
            _logger.error(f"Error updating tenant {tenant_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== DELETE / ARCHIVE TENANT (FR-005, FR-006 — ADR-015 soft delete) ==========

    @http.route('/api/v1/tenants/<int:tenant_id>', type='http', auth='none', methods=['DELETE'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def delete_tenant(self, tenant_id, **kwargs):
        """Soft-archive a tenant (ADR-015). Sets active=False."""
        try:
            company_ids = self._get_company_ids()

            tenant = request.env['real.estate.tenant'].sudo().browse(tenant_id)
            if not tenant.exists() or not tenant.active:
                return error_response(404, 'Tenant not found')

            # Company isolation (FR-030)
            if company_ids is not None:
                if not any(cid in company_ids for cid in tenant.company_ids.ids):
                    return error_response(404, 'Tenant not found')

            # Parse optional reason from body
            reason = None
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
                reason = data.get('reason')
            except Exception:
                pass

            # Soft delete
            tenant.write({
                'active': False,
                'deactivation_date': odoo_fields.Datetime.now(),
                'deactivation_reason': reason,
            })

            resp, code = util_success(
                data={'id': tenant.id, 'active': False},
                message='Tenant archived successfully',
            )
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error archiving tenant {tenant_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')

    # ========== TENANT LEASE HISTORY (US4 — FR-008) ==========

    @http.route('/api/v1/tenants/<int:tenant_id>/leases', type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def get_tenant_leases(self, tenant_id, page=1, page_size=20, **kwargs):
        """Get paginated list of all leases (active + historical) for a tenant."""
        try:
            user = request.env.user
            company_ids = self._get_company_ids()

            # Validate tenant exists
            tenant = request.env['real.estate.tenant'].sudo().with_context(active_test=False).browse(tenant_id)
            if not tenant.exists():
                return error_response(404, 'Tenant not found')

            # Company isolation
            if company_ids is not None:
                if not any(cid in company_ids for cid in tenant.company_ids.ids):
                    return error_response(404, 'Tenant not found')

            # Pagination
            try:
                page = int(page)
                page_size = min(int(page_size), 100)
            except (ValueError, TypeError):
                resp, code = util_error('Invalid pagination parameters', status_code=400)
                return request.make_json_response(resp, status=code)

            # Include both active and inactive leases (historical view)
            Lease = request.env['real.estate.lease'].sudo().with_context(active_test=False)

            domain = [('tenant_id', '=', tenant_id)]

            # Company isolation on leases
            if company_ids is not None:
                domain.append(('company_ids', 'in', company_ids))

            # Agent RBAC
            if self._is_agent_role(user):
                assigned_prop_ids = self._get_agent_property_ids(user, company_ids or [])
                if assigned_prop_ids:
                    domain.append(('property_id', 'in', assigned_prop_ids))
                else:
                    resp, code = paginated_response(items=[], total=0, page=page, page_size=page_size)
                    return request.make_json_response(resp, status=code)

            total = Lease.search_count(domain)
            offset = (page - 1) * page_size
            leases = Lease.search(domain, limit=page_size, offset=offset, order='start_date desc')

            items = []
            for lease in leases:
                lease_links = build_hateoas_links('/api/v1/leases', lease.id)
                items.append({
                    'id': lease.id,
                    'property_id': lease.property_id.id,
                    'property_name': lease.property_id.name if lease.property_id else None,
                    'start_date': str(lease.start_date) if lease.start_date else None,
                    'end_date': str(lease.end_date) if lease.end_date else None,
                    'rent_amount': lease.rent_amount,
                    'status': lease.status,
                    'active': lease.active,
                    '_links': lease_links,
                })

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            links = build_pagination_links(
                f'/api/v1/tenants/{tenant_id}/leases', page, total_pages,
            )
            links['tenant'] = f'/api/v1/tenants/{tenant_id}'

            resp, code = paginated_response(
                items=items, total=total, page=page, page_size=page_size, links=links,
            )
            return request.make_json_response(resp, status=code)

        except Exception as e:
            _logger.error(f"Error listing leases for tenant {tenant_id}: {str(e)}", exc_info=True)
            return error_response(500, 'Internal server error')
