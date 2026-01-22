# -*- coding: utf-8 -*-

"""
Real Estate Management Module - Tests

Test Organization (ADR-002 + ADR-003):

├── unit/ (unittest.mock - NO database, NO Odoo)
│   ├── run_unit_tests.py: Standalone test runner
│   └── test_*_unit.py: Pure logic tests with mocks
│   Run: python3 tests/unit/run_unit_tests.py
│
├── integration/ (TransactionCase - WITH database)
│   └── test_*_integration.py: ACL, record rules, DB constraints
│   Run: docker compose run --rm odoo odoo --test-enable --test-tags=quicksol_estate
│
├── observers/ (Observer pattern tests)
│   └── test_*_observer.py: Event bus and observer tests
│   Run: Included in integration tests
│
└── api/ (HttpCase - DEPRECATED, being migrated to curl)
    └── test_*_api.py: Legacy API tests
    ⚠️  Being migrated to ../../../integration_tests/*.sh (curl scripts)

Legacy Tests (pre-RBAC, run with integration tests):
├── test_validations.py: Email, date, CNPJ validation tests
├── test_company_unit.py: Company model unit tests
├── test_agent_unit.py: Agent model unit tests
├── test_utils_unit.py: Utils (auth, response, serializers) unit tests
└── test_odoo_bridge.py: Odoo bridge integration tests

To run all integration tests:
    docker compose run --rm odoo odoo --test-enable --test-tags=quicksol_estate --stop-after-init

To run unit tests only:
    cd tests/unit && python3 run_unit_tests.py

⚠️ IMPORTANT: tests/unit/ is NOT auto-discovered by Odoo (runs independently with unittest)
"""

# NOTE: Do NOT import tests/unit/* here - they run independently with unittest
# Unit tests are executed via: python3 tests/unit/run_unit_tests.py

# Legacy validation tests (pre-RBAC)

from . import base_validation_test
from . import base_company_test  
from . import base_agent_test
from . import test_validations
from . import test_company_unit
from . import test_agent_unit
from . import test_utils_unit
from . import test_odoo_bridge
from . import test_agent_crud
from . import test_assignment
from . import test_commission_calculation
from . import test_performance

# HTTP/API integration tests (tagged post_install)
from .api import test_property_api
from .api import test_property_api_auth
from .api import test_master_data_api
from .api import test_company_isolation_api

# RBAC v18.0.2.0.0 - Observer Pattern Tests (ADR-020, ADR-021)
from . import test_event_bus
from . import test_abstract_observer
from . import test_rbac_owner
from . import test_rbac_director
from . import test_rbac_receptionist
from . import test_rbac_financial
from . import test_rbac_legal
from . import test_rbac_agent
from . import test_rbac_manager
from . import test_rbac_prospector
from . import test_commission_split
from . import observers

# Integration tests directory (TransactionCase - WITH database)
from . import integration