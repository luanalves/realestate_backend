# -*- coding: utf-8 -*-
# NOTE: Do NOT import tests/unit/* here - they run independently with unittest
# Unit tests are executed via: python3 tests/unit/run_unit_tests.py

# Base test classes (always available)
from . import base_validation_test
from . import base_company_test
from . import base_agent_test

# HTTP/API integration tests (tagged post_install)
from .api import test_property_api
from .api import test_property_api_auth
from .api import test_master_data_api
from .api import test_company_isolation_api
from .api import test_property_attachments_api  # Feature 017
from .api import test_capabilities_api  # Feature 020

# Integration tests directory (TransactionCase - WITH database)
from . import integration
# Feature 013: Property Proposals (explicit imports for Odoo test discovery)
from .integration import test_proposal_create
from .integration import test_proposal_send
from .integration import test_proposal_queue
from .integration import test_proposal_counter
from .integration import test_proposal_accept_reject
from .integration import test_proposal_lead_integration
from .integration import test_proposal_list
from .integration import test_proposal_attachments
from .integration import test_proposal_expiration

# Observer pattern tests
from . import observers
