# -*- coding: utf-8 -*-
"""
HTTP/API Integration Tests

These tests use HttpCase to make real HTTP requests to test REST API endpoints.
They are tagged with 'post_install' and '-at_install' to run AFTER all modules
are installed.

To run these tests:
    docker compose run --rm odoo python3 /usr/bin/odoo \
        -d realestate \
        -i quicksol_estate \
        --test-tags=post_install \
        --stop-after-init

Or run all tests (unit + HTTP):
    docker compose run --rm odoo python3 /usr/bin/odoo \
        -d realestate \
        -i quicksol_estate \
        --test-tags=quicksol_estate,post_install \
        --stop-after-init
"""

from . import test_property_api
from . import test_property_api_auth
from . import test_master_data_api
