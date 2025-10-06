{
    'name': 'Real Estate Management',
    'version': '1.0',
    'category': 'Real Estate',
    'summary': 'Manage properties, sales, leases, tenants, and agents',
    'description': """
Real Estate Management Module
This module allows real estate agencies, property managers, and landlords to manage their properties, agents, tenants, and leases easily.

Key Features:
- Property Management**: Add and manage properties with detailed information like size, number of rooms, amenities, and condition.
- Image Gallery**: Upload multiple images for each property.
- Agent and Tenant Management**: Assign agents and tenants to properties and track their information.
- Lease Management**: Handle leasing contracts and track rental properties.
- Property Status**: Set the status of a property (available, sold, rented, etc.).

""",
    'author': 'Quicksol Technolgies',
    'website': 'https://quicksol.ca',
    'depends': ['base', 'portal'],
    'data': [
        # Security files (must be loaded first)
        'security/groups.xml',
        'security/real_estate_security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        
        # Data files
        'data/property_type_data.xml',
        'data/company_data.xml',
        'data/demo_users.xml',
        
        # Views
        'views/company_views.xml',
        'views/property_views.xml',
        'views/agent_views.xml',
        'views/lease_views.xml',
        'views/sale_views.xml',
        'views/tenant_views.xml',
        'views/res_users_views.xml',
        'views/real_estate_menus.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install' : False,
    'application': True,

}