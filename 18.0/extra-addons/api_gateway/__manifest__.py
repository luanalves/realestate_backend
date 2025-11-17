{
    'name': 'API Gateway',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'OAuth 2.0 API Gateway for Odoo REST APIs',
    'description': """
API Gateway - OAuth 2.0 Server
==============================

Generic module for managing REST APIs with OAuth 2.0 authentication.

Features:
---------
* OAuth 2.0 Server (Client Credentials Grant)
* Token management (access tokens, refresh tokens, revocation)
* API endpoint registry (other modules can register their endpoints)
* Swagger/OpenAPI documentation
* JWT authentication middleware
* Access logs
* Admin interface for OAuth applications

Technical Details:
------------------
* Uses authlib for OAuth 2.0 implementation
* Integrates with base_rest for REST framework
* RFC 6749 compliant (OAuth 2.0)
* RFC 7009 compliant (Token Revocation)
* RFC 7662 compliant (Token Introspection)
* RFC 9068 compliant (JWT Profile for OAuth 2.0)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'external_dependencies': {
        'python': [
            'authlib',
        ],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menu_root.xml',
        'views/oauth_application_views.xml',
        'views/oauth_token_views.xml',
        'views/api_endpoint_views.xml',
        'views/api_access_log_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
