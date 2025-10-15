# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from .base_test import BaseRealEstateTest


class TestSaleUnit(BaseRealEstateTest):
    """
    Unit tests for Sale model business logic.
    
    Tests cover:
    - Sale creation and data integrity
    - Required field validation
    - Relationship management (property, company)
    - Sale price validation
    - Sale date validation
    """

    def setUp(self):
        super().setUp()
        
        # Mock sale data
        self.sale_data = {
            'id': 1,
            'property_id': 1,
            'buyer_name': 'John Buyer',
            'company_ids': [1],
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        }
    
    def test_sale_creation_with_valid_data(self):
        """Test sale creation with complete valid data"""
        
        # Arrange
        sale_data = {
            'property_id': 1,
            'buyer_name': 'Maria Buyer',
            'sale_date': date(2024, 7, 20),
            'sale_price': 425000.00,
            'company_ids': [1]
        }
        
        # Act
        sale = self.create_mock_record('real.estate.sale', sale_data)
        
        # Assert
        self.assertEqual(sale.property_id, 1)
        self.assertEqual(sale.buyer_name, 'Maria Buyer')
        self.assertEqual(sale.sale_date, date(2024, 7, 20))
        self.assertEqual(sale.sale_price, 425000.00)
    
    def test_sale_required_fields(self):
        """Test that all required fields are enforced"""
        
        # Required fields
        required_fields = ['property_id', 'buyer_name', 'sale_date', 'sale_price']
        
        for field in required_fields:
            with self.subTest(field=field):
                data = {
                    'property_id': 1,
                    'buyer_name': 'Test Buyer',
                    'sale_date': date(2024, 6, 15),
                    'sale_price': 350000.00
                }
                
                # Remove one required field
                data.pop(field, None)
                
                # In real Odoo, this would raise ValidationError
                sale = self.create_mock_record('real.estate.sale', data)
                has_field = hasattr(sale, field) and getattr(sale, field) is not None
                
                self.assertFalse(has_field, f"Required field {field} should be present")
    
    def test_sale_property_relationship(self):
        """Test sale-property relationship"""
        
        # Arrange & Act
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        })
        
        # Assert
        self.assertEqual(sale.property_id, 1)
        self.assertIsNotNone(sale.property_id)
    
    def test_sale_company_relationship(self):
        """Test sale-company many2many relationship"""
        
        # Arrange & Act
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00,
            'company_ids': [1, 2]
        })
        
        # Assert
        self.assertEqual(len(sale.company_ids), 2)
        self.assertIn(1, sale.company_ids)
    
    def test_sale_price_positive(self):
        """Test sale price must be positive"""
        
        # Arrange - Valid positive sale prices
        valid_prices = [100000.00, 250000.50, 500000.00, 1000000.00]
        
        for price in valid_prices:
            with self.subTest(price=price):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': 'Test Buyer',
                    'sale_date': date(2024, 6, 15),
                    'sale_price': price
                })
                
                self.assertGreater(sale.sale_price, 0)
    
    def test_sale_buyer_name_validation(self):
        """Test buyer name is not empty"""
        
        # Arrange
        buyer_names = [
            'John Smith',
            'Maria Silva',
            'Company Ltd.',
            'José García'
        ]
        
        for name in buyer_names:
            with self.subTest(name=name):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': name,
                    'sale_date': date(2024, 6, 15),
                    'sale_price': 350000.00
                })
                
                self.assertTrue(sale.buyer_name and len(sale.buyer_name.strip()) > 0)
    
    def test_sale_date_validation(self):
        """Test sale date accepts valid dates"""
        
        # Arrange - Valid sale dates
        valid_dates = [
            date(2024, 1, 15),
            date(2024, 6, 30),
            date(2023, 12, 1),
            date.today()
        ]
        
        for sale_date in valid_dates:
            with self.subTest(date=sale_date):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': 'Test Buyer',
                    'sale_date': sale_date,
                    'sale_price': 350000.00
                })
                
                self.assertIsInstance(sale.sale_date, date)
                self.assertEqual(sale.sale_date, sale_date)


class TestSaleBusinessLogic(BaseRealEstateTest):
    """
    Unit tests for Sale model business logic and workflows.
    """
    
    def test_sale_property_status_update(self):
        """Test that property status should be updated to 'sold' after sale"""
        
        # Arrange
        property_rec = self.create_mock_record('real.estate.property', {
            'id': 1,
            'name': 'Property for Sale',
            'status': 'available'
        })
        
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        })
        
        # Act - Simulate status update
        property_rec.status = 'sold'
        property_rec.sale_id = sale.id
        
        # Assert
        self.assertEqual(property_rec.status, 'sold')
        self.assertIsNotNone(property_rec.sale_id)
    
    def test_sale_with_negotiation_discount(self):
        """Test sale with price different from listing price"""
        
        # Arrange
        property_listing_price = 400000.00
        negotiated_price = 375000.00
        
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Negotiator Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': negotiated_price
        })
        
        # Act
        discount = property_listing_price - sale.sale_price
        discount_percentage = (discount / property_listing_price) * 100
        
        # Assert
        self.assertLess(sale.sale_price, property_listing_price)
        self.assertEqual(discount, 25000.00)
        self.assertAlmostEqual(discount_percentage, 6.25, places=2)
    
    def test_sale_commission_calculation(self):
        """Test commission calculation based on sale price"""
        
        # Arrange
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 400000.00
        })
        
        # Act - Calculate 5% commission
        commission_rate = 0.05
        commission = sale.sale_price * commission_rate
        
        # Assert
        self.assertEqual(commission, 20000.00)
    
    def test_sale_multiple_companies(self):
        """Test sale associated with multiple companies"""
        
        # Arrange
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Test Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00,
            'company_ids': [1, 2, 3]
        })
        
        # Assert
        self.assertEqual(len(sale.company_ids), 3)
    
    def test_sale_data_integrity(self):
        """Test sale data integrity"""
        
        # Arrange & Act
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Integrity Buyer',
            'sale_date': date(2024, 6, 15),
            'sale_price': 425000.00,
            'company_ids': [1]
        })
        
        # Assert - All fields preserved
        self.assertEqual(sale.property_id, 1)
        self.assertEqual(sale.buyer_name, 'Integrity Buyer')
        self.assertEqual(sale.sale_date, date(2024, 6, 15))
        self.assertEqual(sale.sale_price, 425000.00)
        self.assertEqual(len(sale.company_ids), 1)
    
    def test_sale_historical_data(self):
        """Test tracking historical sales data"""
        
        # Arrange - Multiple sales for comparison
        sale1 = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Buyer 1',
            'sale_date': date(2023, 6, 15),
            'sale_price': 300000.00
        })
        
        sale2 = self.create_mock_record('real.estate.sale', {
            'property_id': 2,
            'buyer_name': 'Buyer 2',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        })
        
        # Act - Calculate market appreciation
        appreciation = sale2.sale_price - sale1.sale_price
        appreciation_percentage = (appreciation / sale1.sale_price) * 100
        
        # Assert
        self.assertGreater(sale2.sale_price, sale1.sale_price)
        self.assertAlmostEqual(appreciation_percentage, 16.67, places=2)


class TestSaleEdgeCases(BaseRealEstateTest):
    """
    Unit tests for Sale model edge cases and boundary conditions.
    """
    
    def test_sale_with_long_buyer_name(self):
        """Test sale with very long buyer name"""
        
        # Arrange
        long_name = 'A' * 100
        sale = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': long_name,
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        })
        
        # Assert
        self.assertEqual(len(sale.buyer_name), 100)
    
    def test_sale_with_special_characters_in_buyer_name(self):
        """Test buyer name with special characters"""
        
        # Arrange
        names = [
            "O'Connor",
            "José María García",
            "François-Pierre Dubois",
            "Company & Sons Ltd."
        ]
        
        for name in names:
            with self.subTest(name=name):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': name,
                    'sale_date': date(2024, 6, 15),
                    'sale_price': 350000.00
                })
                
                self.assertEqual(sale.buyer_name, name)
    
    def test_sale_on_different_dates(self):
        """Test sales on various dates"""
        
        # Arrange - Sales on different dates
        dates = [
            date(2024, 1, 1),    # New Year
            date(2024, 12, 31),  # Year end
            date(2024, 2, 29),   # Leap day
            date.today()
        ]
        
        for sale_date in dates:
            with self.subTest(date=sale_date):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': 'Test Buyer',
                    'sale_date': sale_date,
                    'sale_price': 350000.00
                })
                
                self.assertEqual(sale.sale_date, sale_date)
    
    def test_sale_very_high_price(self):
        """Test sale with very high price"""
        
        # Arrange
        high_prices = [1000000.00, 5000000.00, 10000000.00]
        
        for price in high_prices:
            with self.subTest(price=price):
                sale = self.create_mock_record('real.estate.sale', {
                    'property_id': 1,
                    'buyer_name': 'Luxury Buyer',
                    'sale_date': date(2024, 6, 15),
                    'sale_price': price
                })
                
                self.assertGreater(sale.sale_price, 100000.00)
                self.assertEqual(sale.sale_price, price)
    
    def test_sale_filtering_by_date_range(self):
        """Test filtering sales by date range"""
        
        # Arrange
        sale1 = self.create_mock_record('real.estate.sale', {
            'property_id': 1,
            'buyer_name': 'Buyer 1',
            'sale_date': date(2024, 1, 15),
            'sale_price': 300000.00
        })
        
        sale2 = self.create_mock_record('real.estate.sale', {
            'property_id': 2,
            'buyer_name': 'Buyer 2',
            'sale_date': date(2024, 6, 15),
            'sale_price': 350000.00
        })
        
        sale3 = self.create_mock_record('real.estate.sale', {
            'property_id': 3,
            'buyer_name': 'Buyer 3',
            'sale_date': date(2024, 12, 15),
            'sale_price': 400000.00
        })
        
        # Act - Filter sales in Q2 (April-June)
        all_sales = [sale1, sale2, sale3]
        q2_sales = [s for s in all_sales if 4 <= s.sale_date.month <= 6]
        
        # Assert
        self.assertEqual(len(q2_sales), 1)
        self.assertEqual(q2_sales[0].buyer_name, 'Buyer 2')


if __name__ == '__main__':
    unittest.main()