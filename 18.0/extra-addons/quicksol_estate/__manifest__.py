{
    'name': 'Real Estate Management - Kenlo Imóveis Edition',
    'version': '18.0.2.0.0',
    'category': 'Real Estate',
    'summary': 'Complete property management system following Kenlo Imóveis standards with RBAC',
    'description': """
Real Estate Management Module - Kenlo Imóveis Edition
=====================================================

This module provides a complete property management system for real estate agencies following Kenlo Imóveis standards.

Version 18.0.2.0.0 Changes:
===========================
- **RBAC User Profiles**: 9 predefined user profiles (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal User)
- **Observer Pattern**: Event-driven architecture for decoupled business logic (ADR-020)
- **Async Messaging**: RabbitMQ + Celery for background processing (ADR-021)
- **Commission Split**: Prospector + Agent commission split functionality
- **Multi-Tenancy**: Enhanced company isolation with comprehensive record rules

Key Features:
============
- **Property Management**: Complete property registration with 13 organized sections
- **Owner Management**: Detailed owner profiles with CPF/CNPJ validation
- **Building/Condominium**: Track buildings and condominiums
- **Contact Management**: Multiple phones and emails per property
- **Photo Gallery**: Advanced photo management with main photo selection
- **Document Management**: Organize all property documents (matrícula, IPTU, contracts, etc.)
- **Key Control**: Track keys and their whereabouts
- **Commission Management**: Configure commissions per property
- **Web Publishing**: SEO-optimized property publishing
- **Authorization Control**: Track authorization periods
- **Brazilian Market**: CEP integration, IPTU, CNPJ, CPF validations
- **Agent and Tenant Management**: Assign agents and tenants to properties
- **Lease Management**: Handle leasing contracts
- **Sales Management**: Track property sales

Property Form Sections:
======================
1. Owner Data
2. Structure
3. Location (with CEP search)
4. Primary Data (pricing, taxes, status)
5. Features (rooms, areas, amenities)
6. Zoning
7. Tags/Markers
8. Key Control
9. Photo Gallery
10. Web Publishing
11. Signs and Banners
12. Commissions
13. Documents

""",
    'author': 'Quicksol Technologies',
    'website': 'https://quicksol.ca',
    'depends': ['base', 'portal', 'mail', 'thedevkitchen_apigateway'],
    'data': [
        # Security files (must be loaded first)
        'security/groups.xml',
        'security/real_estate_security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        
        # Data files (sequences and master data)
        'data/location_types.xml',
        'data/states.xml',
        'data/property_data.xml',
        'data/amenity_data.xml',
        'data/demo_users.xml',
        'data/property_demo_data.xml',
        'data/agent_seed.xml',
        'data/api_endpoints.xml',
        'data/user_auth_endpoints_data.xml',
        'data/system_parameters.xml',
        # 'data/default_groups.xml',  # Demo data temporarily disabled - complex dependencies
        
        # Views (actions must be loaded before menus that reference them)
        'views/property_views.xml',
        'views/property_auxiliary_views.xml',
        'views/agent_views.xml',
        'views/lead_views.xml',  # FR-001: Lead views for managers
        'views/lead_filter_views.xml',  # FR-048: Saved search filters
        'views/commission_rule_views.xml',
        'views/assignment_views.xml',
        'views/lease_views.xml',
        'views/sale_views.xml',
        'views/tenant_views.xml',
        'views/real_estate_menus.xml',
        'views/res_users_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'quicksol_estate/static/src/js/phone_widget.js',
            'quicksol_estate/static/src/js/email_widget.js',
        ],
    },
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}