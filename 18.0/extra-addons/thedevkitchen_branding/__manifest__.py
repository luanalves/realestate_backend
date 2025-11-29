# -*- coding: utf-8 -*-
{
    'name': 'TheDevKitchen Branding',
    'version': '18.0.1.0.0',
    'category': 'Customizations',
    'summary': 'Custom branding and UI customizations',
    'description': """
TheDevKitchen Branding
======================
This module provides custom branding and UI customizations for Odoo applications.

Features:
* Custom login page design
* Removed unnecessary login page elements
* Custom logo and branding
    """,
    'author': 'TheDevKitchen',
    'website': 'https://www.thedevkitchen.com',
    'license': 'LGPL-3',
    'depends': [
        'web',
    ],
    'data': [
        'views/webclient_templates.xml',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'thedevkitchen_branding/static/src/scss/login.scss',
        ],
        'web.assets_backend': [
            'thedevkitchen_branding/static/src/scss/login.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
