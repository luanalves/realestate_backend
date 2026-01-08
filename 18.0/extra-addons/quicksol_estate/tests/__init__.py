# -*- coding: utf-8 -*-

"""
Real Estate Management Module - Tests

This package contains comprehensive tests for the quicksol_estate module.

Test Structure:
├── Unit Tests (run with --test-enable):
│   ├── base_validation_test.py: Base class for validation tests
│   ├── base_company_test.py: Company-specific base class with CNPJ utilities
│   ├── base_agent_test.py: Agent-specific base class
│   ├── test_validations.py: Email, date, and CNPJ validation tests
│   ├── test_company_unit.py: Company model unit tests
│   ├── test_agent_unit.py: Agent model unit tests
│   ├── test_utils_unit.py: Utils (auth, response, serializers) unit tests
│   ├── test_odoo_bridge.py: Odoo bridge integration tests
│   ├── test_property_api.py: Property API access control tests
│   └── test_company_isolation.py: Multi-tenant company isolation test suite
│
└── HTTP/API Integration Tests (run with Odoo running):
    └── api/
        ├── test_property_api_auth.py: OAuth authentication tests
        └── test_master_data_api.py: Master data endpoints tests (expanded)

To run unit tests:
    docker compose run --rm odoo python3 /usr/bin/odoo -d realestate --test-enable --stop-after-init --test-tags=quicksol_estate

To run HTTP/API tests:
    ./run_http_tests.sh
"""

from . import base_validation_test
from . import base_company_test  
from . import base_agent_test
from . import test_validations
from . import test_company_unit
from . import test_agent_unit
from . import test_utils_unit
from . import test_odoo_bridge
from . import test_company_isolation

# HTTP/API integration tests (tagged post_install)
from .api import test_property_api
from .api import test_property_api_auth
from .api import test_master_data_api
from .api import test_company_isolation_api