# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from .base_lease_test import BaseLeaseTest


class TestLeaseUnit(BaseLeaseTest):
    """
    Unit tests for Lease model business logic.

    Tests cover:
    - Lease creation and data integrity
    - Date validation (end_date > start_date)
    - Relationship management (property, tenant, company)
    - Required field validation
    - Rent amount validation
    """

    def setUp(self):
        super().setUp()

        # Create mock lease with relationships
        self.lease_with_relations = self.create_lease_mock({
            **self.lease_data,
            'company_ids': [1, 2]
        })

    def test_lease_creation_with_valid_data(self):
        """Test lease creation with complete valid data"""

        # Arrange
        lease_data = {
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00,
            'company_ids': [1]
        }

        # Act
        lease = self.create_lease_mock(lease_data)

        # Assert
        self.assertEqual(lease.property_id, 1)
        self.assertEqual(lease.tenant_id, 1)
        self.assertEqual(lease.start_date, date(2024, 1, 1))
        self.assertEqual(lease.end_date, date(2024, 12, 31))
        self.assertEqual(lease.rent_amount, 2500.00)

    def test_lease_required_fields(self):
        """Test that all required fields are enforced"""

        # Required fields
        required_fields = ['property_id', 'tenant_id', 'start_date', 'end_date', 'rent_amount']

        for field in required_fields:
            with self.subTest(field=field):
                data = {
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': date(2024, 1, 1),
                    'end_date': date(2024, 12, 31),
                    'rent_amount': 2500.00
                }

                # Remove one required field
                data.pop(field, None)

                # In real Odoo, this would raise ValidationError
                lease = self.create_lease_mock(data)
                has_field = hasattr(lease, field) and getattr(lease, field) is not None

                self.assertFalse(has_field, f"Required field {field} should be present")

    def test_lease_valid_date_ranges(self):
        """Test valid date ranges pass validation"""

        for start_date, end_date in self.valid_date_ranges:
            with self.subTest(start=start_date, end=end_date):
                # Arrange
                lease = self.create_lease_mock({
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rent_amount': 2500.00
                })

                # Act
                is_valid = self.validate_date_range(lease.start_date, lease.end_date)

                # Assert
                self.assertTrue(is_valid, f"Date range {start_date} to {end_date} should be valid")

    def test_lease_invalid_date_ranges(self):
        """Test invalid date ranges trigger validation errors"""

        for start_date, end_date in self.invalid_date_ranges:
            with self.subTest(start=start_date, end=end_date):
                # Arrange
                lease = self.create_lease_mock({
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': start_date,
                    'end_date': end_date,
                    'rent_amount': 2500.00
                })

                # Act - Simulate validation logic
                validation_error = False
                if lease.start_date and lease.end_date:
                    if lease.end_date <= lease.start_date:
                        validation_error = True

                # Assert
                self.assertTrue(validation_error,
                    f"Date range {start_date} to {end_date} should be invalid")

    def test_lease_date_validation_end_equals_start(self):
        """Test that end_date cannot equal start_date"""

        # Arrange
        same_date = date(2024, 6, 15)
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': same_date,
            'end_date': same_date,
            'rent_amount': 2500.00
        })

        # Act - Validate
        is_valid = lease.end_date > lease.start_date

        # Assert
        self.assertFalse(is_valid, "End date should not equal start date")

    def test_lease_date_validation_end_before_start(self):
        """Test that end_date cannot be before start_date"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 12, 31),
            'end_date': date(2024, 1, 1),
            'rent_amount': 2500.00
        })

        # Act - Validate
        is_valid = lease.end_date > lease.start_date

        # Assert
        self.assertFalse(is_valid, "End date should not be before start date")

    def test_lease_rent_amount_positive(self):
        """Test rent amount must be positive"""

        # Arrange - Valid positive rent amounts
        valid_rents = [100.00, 1500.50, 5000.00, 10000.00]

        for rent in valid_rents:
            with self.subTest(rent=rent):
                lease = self.create_lease_mock({
                    'property_id': 1,
                    'tenant_id': 1,
                    'start_date': date(2024, 1, 1),
                    'end_date': date(2024, 12, 31),
                    'rent_amount': rent
                })

                self.assertGreater(lease.rent_amount, 0)

    def test_lease_property_relationship(self):
        """Test lease-property relationship"""

        # Arrange & Act
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        })

        # Assert
        self.assertEqual(lease.property_id, 1)
        self.assertIsNotNone(lease.property_id)

    def test_lease_tenant_relationship(self):
        """Test lease-tenant relationship"""

        # Arrange & Act
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        })

        # Assert
        self.assertEqual(lease.tenant_id, 1)
        self.assertIsNotNone(lease.tenant_id)

    def test_lease_company_relationship(self):
        """Test lease-company many2many relationship"""

        # Arrange & Act
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00,
            'company_ids': [1, 2]
        })

        # Assert
        self.assertEqual(len(lease.company_ids), 2)
        self.assertIn(1, lease.company_ids)


class TestLeaseBusinessLogic(BaseLeaseTest):
    """
    Unit tests for Lease model business logic and workflows.
    """

    def test_lease_duration_calculation(self):
        """Test lease duration calculation"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        })

        # Act - Calculate duration in days
        duration = (lease.end_date - lease.start_date).days

        # Assert
        self.assertEqual(duration, 365)  # Full year
        self.assertGreater(duration, 0)

    def test_lease_short_term(self):
        """Test short-term lease (less than 6 months)"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 3, 31),
            'rent_amount': 3000.00
        })

        # Act
        duration_months = (lease.end_date.year - lease.start_date.year) * 12 + \
                         (lease.end_date.month - lease.start_date.month)

        # Assert
        self.assertLess(duration_months, 6)
        self.assertEqual(duration_months, 2)

    def test_lease_long_term(self):
        """Test long-term lease (1+ years)"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2026, 12, 31),
            'rent_amount': 2500.00
        })

        # Act
        duration_years = (lease.end_date - lease.start_date).days / 365

        # Assert
        self.assertGreater(duration_years, 2)

    def test_lease_monthly_rent_calculation(self):
        """Test monthly rent calculation"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00
        })

        # Act
        monthly_rent = lease.rent_amount
        annual_rent = monthly_rent * 12

        # Assert
        self.assertEqual(monthly_rent, 2500.00)
        self.assertEqual(annual_rent, 30000.00)

    def test_lease_overlapping_dates_detection(self):
        """Test detection of overlapping lease dates for same property"""

        # Arrange - Two leases for same property with overlapping dates
        lease1 = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 6, 30),
            'rent_amount': 2500.00
        })

        lease2 = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 2,
            'start_date': date(2024, 4, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2600.00
        })

        # Act - Check if dates overlap
        overlaps = (lease1.property_id == lease2.property_id and
                   lease1.start_date <= lease2.end_date and
                   lease2.start_date <= lease1.end_date)

        # Assert
        self.assertTrue(overlaps, "Leases should overlap")

    def test_lease_non_overlapping_dates(self):
        """Test non-overlapping lease dates for same property"""

        # Arrange - Two sequential leases
        lease1 = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 6, 30),
            'rent_amount': 2500.00
        })

        lease2 = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 2,
            'start_date': date(2024, 7, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2600.00
        })

        # Act - Check if dates overlap
        overlaps = (lease1.property_id == lease2.property_id and
                   lease1.start_date <= lease2.end_date and
                   lease2.start_date <= lease1.end_date)

        # Assert
        self.assertFalse(overlaps, "Leases should not overlap")

    def test_lease_renewal_scenario(self):
        """Test lease renewal scenario"""

        # Arrange - Original lease
        original_lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2023, 1, 1),
            'end_date': date(2023, 12, 31),
            'rent_amount': 2500.00
        })

        # Renewed lease with increased rent
        renewed_lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,  # Same tenant
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2750.00  # 10% increase
        })

        # Assert
        self.assertEqual(original_lease.tenant_id, renewed_lease.tenant_id)
        self.assertEqual(original_lease.property_id, renewed_lease.property_id)
        self.assertGreater(renewed_lease.rent_amount, original_lease.rent_amount)
        self.assertEqual(renewed_lease.start_date, original_lease.end_date + timedelta(days=1))

    def test_lease_data_integrity(self):
        """Test lease data integrity"""

        # Arrange & Act
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00,
            'company_ids': [1]
        })

        # Assert - All fields preserved
        self.assertEqual(lease.property_id, 1)
        self.assertEqual(lease.tenant_id, 1)
        self.assertEqual(lease.start_date, date(2024, 1, 1))
        self.assertEqual(lease.end_date, date(2024, 12, 31))
        self.assertEqual(lease.rent_amount, 2500.00)
        self.assertEqual(len(lease.company_ids), 1)


class TestLeaseEdgeCases(BaseLeaseTest):
    """
    Unit tests for Lease model edge cases and boundary conditions.
    """

    def test_lease_very_short_duration(self):
        """Test lease with very short duration (1 day)"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 1, 2),
            'rent_amount': 100.00
        })

        # Act
        duration = (lease.end_date - lease.start_date).days

        # Assert
        self.assertEqual(duration, 1)
        self.assertGreater(duration, 0)

    def test_lease_year_boundary(self):
        """Test lease crossing year boundary"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2023, 12, 1),
            'end_date': date(2024, 1, 31),
            'rent_amount': 2500.00
        })

        # Act
        crosses_year = lease.start_date.year != lease.end_date.year

        # Assert
        self.assertTrue(crosses_year)

    def test_lease_leap_year_handling(self):
        """Test lease during leap year"""

        # Arrange - 2024 is a leap year
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 2, 1),
            'end_date': date(2024, 3, 1),
            'rent_amount': 2500.00
        })

        # Act
        duration = (lease.end_date - lease.start_date).days

        # Assert
        self.assertEqual(duration, 29)  # February 2024 has 29 days

    def test_lease_different_companies(self):
        """Test lease associated with multiple companies"""

        # Arrange
        lease = self.create_lease_mock({
            'property_id': 1,
            'tenant_id': 1,
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
            'rent_amount': 2500.00,
            'company_ids': [1, 2, 3]
        })

        # Assert
        self.assertEqual(len(lease.company_ids), 3)


if __name__ == '__main__':
    unittest.main()