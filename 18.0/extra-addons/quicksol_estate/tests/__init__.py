# -*- coding: utf-8 -*-

"""
Real Estate Management Module - Unit Tests

This package contains comprehensive unit tests for the quicksol_estate module.
All tests use mocks to avoid database dependencies, ensuring fast execution
and isolation from external dependencies.

Test Structure:
- base_validation_test.py: Base class for validation tests with common utilities
- base_company_test.py: Company-specific base class with CNPJ and company utilities  
- base_agent_test.py: Agent-specific base class with user synchronization utilities
- test_validations.py: Email, date, and CNPJ validation tests
- test_company_unit.py: Company model unit tests
- test_agent_unit.py: Agent model unit tests
- test_tenant_unit.py: Tenant model unit tests
- test_lease_unit.py: Lease model unit tests
- test_sale_unit.py: Sale model unit tests
- test_access_control.py: Access control and security tests
"""

from . import base_validation_test
from . import base_company_test  
from . import base_agent_test
from . import test_validations
from . import test_company_unit
from . import test_agent_unit
from . import test_odoo_bridge