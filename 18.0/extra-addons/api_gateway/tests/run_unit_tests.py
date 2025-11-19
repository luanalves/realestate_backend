#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run all unit tests for api_gateway module

This script runs all pure unit tests (with mocks, no database required).
Execute with: python3 run_unit_tests.py
"""

import unittest
import sys
import os

# Add the tests directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import all test modules
from test_oauth_application_unit import (
    TestOAuthApplicationUnit,
    TestOAuthTokenUnit,
    TestMiddlewareUnit,
    TestAPIEndpointUnit,
    TestAccessLogUnit,
)

from test_jwt_unit import (
    TestJWTGeneration,
    TestAuthHeaderParsing,
    TestScopeValidation,
    TestRefreshTokenGeneration,
    TestClientCredentials,
    TestErrorResponses,
    TestTokenResponse,
)

from test_models_unit import (
    TestOAuthApplicationModel,
    TestOAuthTokenModel,
    TestAPIEndpointModel,
    TestAPIAccessLogModel,
    TestJSONSchemaValidation,
    TestMiddlewareFunctions,
)

from test_bcrypt_unit import (
    TestBcryptHashing,
)


def run_all_tests():
    """Run all unit tests and display summary"""
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        # From test_oauth_application_unit.py
        TestOAuthApplicationUnit,
        TestOAuthTokenUnit,
        TestMiddlewareUnit,
        TestAPIEndpointUnit,
        TestAccessLogUnit,
        
        # From test_jwt_unit.py
        TestJWTGeneration,
        TestAuthHeaderParsing,
        TestScopeValidation,
        TestRefreshTokenGeneration,
        TestClientCredentials,
        TestErrorResponses,
        TestTokenResponse,
        
        # From test_models_unit.py
        TestOAuthApplicationModel,
        TestOAuthTokenModel,
        TestAPIEndpointModel,
        TestAPIAccessLogModel,
        TestJSONSchemaValidation,
        TestMiddlewareFunctions,
        
        # From test_bcrypt_unit.py
        TestBcryptHashing,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("UNIT TESTS SUMMARY")
    print("=" * 70)
    print(f"Total tests run: {result.testsRun}")
    print(f"✅ Successful: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"❌ Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED! 100% SUCCESS RATE")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
        print(f"Success rate: {success_rate:.1f}%")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
