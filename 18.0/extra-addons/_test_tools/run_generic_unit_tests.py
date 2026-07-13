#!/usr/bin/env python3
"""Generic unit-test runner for modules without their own tests/run_unit_tests.py.

Handles the two things a bare `python3 -m unittest discover` gets wrong when run
inside the odoo container against an extra-addons module:

1. `odoo.addons.<module>...` absolute imports (lazy imports inside test methods,
   e.g. thedevkitchen_estate_credit_check) fail unless the odoo.addons namespace
   package is extended to include /mnt/extra-addons first.
2. `from .common import X` relative imports inside tests/ (e.g. auditlog) fail
   unless unittest's discover is given the module directory as top_level_dir,
   not the tests/ subdirectory itself.

Usage: run_generic_unit_tests.py <module_name> [<tests_subdir>]
  <tests_subdir> defaults to "tests"; pass "tests/unit" for modules that split
  pure unit tests into a unit/ subfolder.
"""
import sys
import unittest
from pathlib import Path

import odoo.addons

EXTRA_ADDONS = "/mnt/extra-addons"
if EXTRA_ADDONS not in odoo.addons.__path__:
    odoo.addons.__path__.insert(0, EXTRA_ADDONS)


def main():
    module = sys.argv[1]
    subdir = sys.argv[2] if len(sys.argv) > 2 else "tests"

    module_dir = Path(EXTRA_ADDONS) / module
    start_dir = module_dir / subdir

    loader = unittest.TestLoader()
    suite = loader.discover(str(start_dir), pattern="test_*.py", top_level_dir=str(module_dir))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
