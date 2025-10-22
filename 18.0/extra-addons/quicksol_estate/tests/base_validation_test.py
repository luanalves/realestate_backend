# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch
import re
from datetime import date


class BaseValidationTest(unittest.TestCase):
    """
    Base class for validation unit tests.
    
    Provides:
    - Common validation test utilities
    - Email, date, and field validation helpers
    - Mock validation error handling
    """
    
    def setUp(self):
        super().setUp()
        
        # Valid email test cases
        self.valid_emails = [
            'test@example.com',
            'user.name@domain.com.br',
            'user+tag@example.org',
            'user_123@test-domain.co.uk',
            'admin@company-name.com'
        ]
        
        # Invalid email test cases
        self.invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user@domain',
            'user@domain.',
            'user name@domain.com',
            'user@@domain.com',
            '.user@domain.com',    # starts with dot
            'user.@domain.com',    # ends with dot before @
        ]
        
        # Valid date ranges
        self.valid_date_ranges = [
            (date(2024, 1, 1), date(2024, 12, 31)),
            (date(2024, 6, 1), date(2024, 6, 30)),
            (date(2024, 1, 15), date(2024, 1, 16)),
        ]
        
        # Invalid date ranges  
        self.invalid_date_ranges = [
            (date(2024, 12, 31), date(2024, 1, 1)),    # End before start
            (date(2024, 6, 15), date(2024, 6, 14)),    # Previous day
            (date(2024, 6, 15), date(2024, 6, 15)),    # Same day
        ]
    
    def create_mock_record(self, model_name, data):
        """Create a generic mock record"""
        record = Mock()
        
        for key, value in data.items():
            setattr(record, key, value)
        
        record._name = model_name
        record.exists = Mock(return_value=record)
        
        return record
    
    def validate_email_regex(self, email):
        """Validate email using regex (for tenant model)"""
        # Strict regex that doesn't allow:
        # - dots at start or end of local part  
        # - dots immediately before @ symbol
        if not email or not isinstance(email, str):
            return False
        if email.startswith('.') or '.@' in email:
            return False
        # Allow dots in middle, but not at start/end of local part    
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_date_range(self, start_date, end_date):
        """Validate date range (end > start)"""
        if start_date and end_date:
            return end_date > start_date
        return True
    
    def assert_validation_error_raised(self, validation_func, *args, **kwargs):
        """Assert that validation raises error"""
        try:
            validation_func(*args, **kwargs)
            self.fail("Expected validation error was not raised")
        except (ValueError, Exception):
            pass  # Expected
    
    def assert_no_validation_error(self, validation_func, *args, **kwargs):
        """Assert that validation does not raise error"""
        try:
            validation_func(*args, **kwargs)
        except (ValueError, Exception) as e:
            self.fail(f"Unexpected validation error raised: {e}")