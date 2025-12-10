# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from .utils.auth import require_jwt
from .utils.response import error_response, success_response
from odoo.addons.thedevkitchen_apigateway.middleware import require_session, require_company

_logger = logging.getLogger(__name__)


class MasterDataApiController(http.Controller):
    """REST API Controller for Master Data endpoints"""
    
    @http.route('/api/v1/property-types', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_property_types(self, **kwargs):
        """
        List all available property types.
        
        Requires: JWT token
        Returns: JSON array with property types
        """
        try:
            PropertyType = request.env['real.estate.property.type'].sudo()
            domain = request.company_domain
            property_types = PropertyType.search(domain)
            
            types_list = []
            for prop_type in property_types:
                types_list.append({
                    'id': prop_type.id,
                    'name': prop_type.name,
                })
            
            types_list.sort(key=lambda x: x['id'])
            
            return success_response(types_list)
            
        except Exception as e:
            _logger.error(f"Error in list_property_types: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/location-types', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_location_types(self, **kwargs):
        """
        List all available location types.
        
        Requires: JWT token
        Returns: JSON array with location types
        """
        try:
            LocationType = request.env['real.estate.location.type'].sudo()
            domain = request.company_domain
            location_types = LocationType.search(domain, order='sequence, name')
            
            types_list = []
            for loc_type in location_types:
                types_list.append({
                    'id': loc_type.id,
                    'name': loc_type.name,
                    'code': loc_type.code,
                })
            
            return success_response(types_list)
            
        except Exception as e:
            _logger.error(f"Error in list_location_types: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/states', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_states(self, **kwargs):
        """
        List all states/provinces.
        
        Requires: JWT token
        Optional query params:
        - country_id: Filter by country ID
        Returns: JSON array with states
        """
        try:
            country_id = kwargs.get('country_id')
            
            domain = request.company_domain[:]
            if country_id:
                domain.append(('country_id', '=', int(country_id)))
            
            State = request.env['real.estate.state'].sudo()
            states = State.search(domain, order='name')
            
            states_list = []
            for state in states:
                states_list.append({
                    'id': state.id,
                    'name': state.name,
                    'code': state.code,
                    'country': {
                        'id': state.country_id.id,
                        'name': state.country_id.name,
                        'code': state.country_id.code,
                    } if state.country_id else None,
                })
            
            return success_response(states_list)
            
        except Exception as e:
            _logger.error(f"Error in list_states: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/agents', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_agents(self, **kwargs):
        """
        List all real estate agents.
        
        Requires: JWT token
        Returns: JSON array with agents
        """
        try:
            Agent = request.env['real.estate.agent'].sudo()
            domain = request.company_domain
            agents = Agent.search(domain, order='name')
            
            agents_list = []
            for agent in agents:
                agents_list.append({
                    'id': agent.id,
                    'name': agent.name,
                    'email': agent.email,
                    'phone': agent.phone,
                })
            
            return success_response(agents_list)
            
        except Exception as e:
            _logger.error(f"Error in list_agents: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/owners', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_owners(self, **kwargs):
        """
        List all property owners.
        
        Requires: JWT token
        Returns: JSON array with owners
        """
        try:
            Owner = request.env['real.estate.property.owner'].sudo()
            domain = [('active', '=', True)] + request.company_domain
            owners = Owner.search(domain, order='name')
            
            owners_list = []
            for owner in owners:
                owners_list.append({
                    'id': owner.id,
                    'name': owner.name,
                    'cpf': owner.cpf,
                    'cnpj': owner.cnpj,
                    'email': owner.email,
                    'phone': owner.phone,
                    'mobile': owner.mobile,
                })
            
            return success_response(owners_list)
            
        except Exception as e:
            _logger.error(f"Error in list_owners: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/companies', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_companies(self, **kwargs):
        """
        List all real estate companies.
        
        Requires: JWT token
        Returns: JSON array with companies
        """
        try:
            Company = request.env['thedevkitchen.estate.company'].sudo()
            domain = [('id', 'in', request.user_company_ids)]
            companies = Company.search(domain, order='name')
            
            companies_list = []
            for company in companies:
                companies_list.append({
                    'id': company.id,
                    'name': company.name,
                    'email': company.email,
                    'phone': company.phone,
                    'website': company.website,
                })
            
            return success_response(companies_list)
            
        except Exception as e:
            _logger.error(f"Error in list_companies: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/tags', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_tags(self, **kwargs):
        """
        List all property tags.
        
        Requires: JWT token
        Returns: JSON array with tags
        """
        try:
            Tag = request.env['real.estate.property.tag'].sudo()
            domain = [('active', '=', True)] + request.company_domain
            tags = Tag.search(domain, order='name')
            
            tags_list = []
            for tag in tags:
                tags_list.append({
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color,
                })
            
            return success_response(tags_list)
            
        except Exception as e:
            _logger.error(f"Error in list_tags: {e}")
            return error_response(500, 'Internal server error')
    
    @http.route('/api/v1/amenities', 
                type='http', auth='none', methods=['GET'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def list_amenities(self, **kwargs):
        """
        List all property amenities.
        
        Requires: JWT token
        Returns: JSON array with amenities
        """
        try:
            Amenity = request.env['real.estate.amenity'].sudo()
            domain = request.company_domain
            amenities = Amenity.search(domain, order='name')
            
            amenities_list = []
            for amenity in amenities:
                amenities_list.append({
                    'id': amenity.id,
                    'name': amenity.name,
                    'icon': amenity.icon if hasattr(amenity, 'icon') else None,
                })
            
            return success_response(amenities_list)
            
        except Exception as e:
            _logger.error(f"Error in list_amenities: {e}")
            return error_response(500, 'Internal server error')
