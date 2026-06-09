#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Runner for Quicksol Estate Module

Executes all unit tests using unittest framework (NO Odoo, NO database)

Usage:
    python3 run_unit_tests.py
    python3 run_unit_tests.py -v  # Verbose output
    python3 run_unit_tests.py TestClassName  # Run specific test class
"""

import sys
import unittest
from pathlib import Path

# -----------------------------------------------------------------------
# Extend odoo.addons namespace so we can import quicksol_estate modules
# without a running Odoo server or database.
# -----------------------------------------------------------------------
import odoo.addons
_addons_root = str(Path(__file__).parent.parent.parent.parent)  # /mnt/extra-addons
if _addons_root not in odoo.addons.__path__:
    odoo.addons.__path__.insert(0, _addons_root)

# Files that use odoo.tests.TransactionCase and require the full Odoo runner
_ODOO_RUNNER_ONLY = {
    'test_agent_unit.py',
    'test_utils_unit.py',
}


def run_tests():
    """Discover and run all pure unit tests (unittest.TestCase only)"""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent

    # Discover only pure unit test files; skip TransactionCase-based files
    suite = unittest.TestSuite()
    for test_file in sorted(start_dir.glob("test_*_unit.py")):
        if test_file.name in _ODOO_RUNNER_ONLY:
            continue
        sub = loader.discover(str(start_dir), pattern=test_file.name)
        suite.addTests(sub)

    # Run tests with TextTestRunner
    verbosity = 2 if "-v" in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Print summary
    print(f"\n{'='*70}")
    print("Unit Tests Summary")
    print(f"{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    # Exit with appropriate code
    if result.wasSuccessful():
        print("\n✅ All unit tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
