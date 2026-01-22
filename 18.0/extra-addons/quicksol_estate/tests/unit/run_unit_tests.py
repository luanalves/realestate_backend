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

# Add parent directory to Python path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_tests():
    """Discover and run all unit tests"""
    # Discover tests in current directory
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(str(start_dir), pattern='test_*_unit.py')
    
    # Run tests with TextTestRunner
    verbosity = 2 if '-v' in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Unit Tests Summary")
    print(f"{'='*70}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Exit with appropriate code
    if result.wasSuccessful():
        print(f"\n✅ All unit tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    run_tests()
