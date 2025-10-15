# -*- coding: utf-8 -*-

"""
Real Estate Management Module - Unit Tests

This package contains comprehensive unit tests for the quicksol_estate module.
All tests use mocks to avoid database dependencies, ensuring fast execution
and isolation from external dependencies.

Test Structure:
- base_test.py: Base class with common mock utilities
- base_validation_test.py: Base class for validation tests with common utilities
- base_company_test.py: Company-specific base class with CNPJ and company utilities  
- base_agent_test.py: Agent-specific base class with user synchronization utilities
- base_property_test.py: Property-specific base class with property utilities
- base_tenant_test.py: Tenant-specific base class with email validation utilities
- base_lease_test.py: Lease-specific base class with date validation utilities

Unit Test Files:
- test_validations.py: Email, date, and CNPJ validation tests
- test_company_unit.py: Company model unit tests
- test_agent_unit.py: Agent model unit tests
- test_property_unit.py: Property model unit tests
- test_tenant_unit.py: Tenant model unit tests
- test_lease_unit.py: Lease model unit tests
- test_sale_unit.py: Sale model unit tests
- test_res_users_unit.py: ResUsers extension unit tests

Integration:
- test_odoo_bridge.py: Bridge to run tests within Odoo test framework
"""

from . import base_test
from . import base_validation_test
from . import base_company_test  
from . import base_agent_test
from . import base_property_test
from . import base_tenant_test
from . import base_lease_test
from . import test_validations
from . import test_company_unit
from . import test_agent_unit
from . import test_property_unit
from . import test_tenant_unit
from . import test_lease_unit
from . import test_sale_unit
from . import test_res_users_unit
from . import test_odoo_bridge