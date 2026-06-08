#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Runner for TheDevKitchen APIGateway Module

Executes all unit tests using unittest framework (NO database required).
Tests use unittest.mock to isolate from Odoo ORM and Redis.

Usage:
    python3 run_unit_tests.py
    python3 run_unit_tests.py -v          # Verbose output
    python3 run_unit_tests.py TestClass   # Run specific test class

Inside Docker:
    docker exec odoo18 python3 /mnt/extra-addons/thedevkitchen_apigateway/tests/unit/run_unit_tests.py -v
"""

import sys
import unittest
from pathlib import Path

# -----------------------------------------------------------------------
# Extend odoo.addons namespace so we can import apigateway modules
# without a running Odoo server or database.
# -----------------------------------------------------------------------
import odoo.addons
_addons_root = str(Path(__file__).parent.parent.parent.parent)  # /mnt/extra-addons
if _addons_root not in odoo.addons.__path__:
    odoo.addons.__path__.insert(0, _addons_root)


def run_tests():
    """Discover and run all unit tests in this directory."""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(str(start_dir), pattern="test_*_unit.py")

    verbosity = 2 if "-v" in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    print(f"\n{'=' * 70}")
    print("APIGateway Unit Tests Summary")
    print(f"{'=' * 70}")
    print(f"Tests run:  {result.testsRun}")
    print(f"Failures:   {len(result.failures)}")
    print(f"Errors:     {len(result.errors)}")
    print(f"Skipped:    {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✅ All unit tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        for fname, tb in result.failures + result.errors:
            print(f"\n--- {fname} ---\n{tb}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
