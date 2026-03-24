#!/usr/bin/env python3
"""
Standalone test for Phase 6 Task 1 query fingerprinting
Tests the _generate_query_fingerprint function without requiring Odoo
"""

import re
import sys


def _generate_query_fingerprint(query):
    """
    Generate a normalized fingerprint of a SQL query for grouping similar queries.
    This allows aggregating metrics across queries that differ only in literal values.
    
    Normalization steps:
    1. Replace numeric literals with ?
    2. Replace string literals with ?
    3. Normalize IN clauses: IN (1,2,3) → IN (?)
    4. Normalize whitespace
    
    Args:
        query (str): The SQL query string
        
    Returns:
        str: Normalized query fingerprint
        
    Examples:
        >>> _generate_query_fingerprint("SELECT * FROM users WHERE id = 123")
        'SELECT * FROM users WHERE id = ?'
        
        >>> _generate_query_fingerprint("SELECT * FROM users WHERE name = 'John'")
        'SELECT * FROM users WHERE name = ?'
        
        >>> _generate_query_fingerprint("SELECT * FROM users WHERE id IN (1,2,3)")
        'SELECT * FROM users WHERE id IN (?)'
    """
    if not query:
        return ""
    
    # Normalize query string
    normalized = query.strip()
    
    # Replace IN clauses first (before individual number replacement)
    # Matches: IN (1,2,3) or IN ('a','b','c')
    normalized = re.sub(r'IN\s*\([^)]+\)', 'IN (?)', normalized, flags=re.IGNORECASE)
    
    # Replace numeric literals with ?
    # Matches: standalone numbers (not part of identifiers)
    normalized = re.sub(r'\b\d+\b', '?', normalized)
    
    # Replace string literals with ?
    # Matches: 'string' or "string"
    normalized = re.sub(r"'[^']*'", '?', normalized)
    normalized = re.sub(r'"[^"]*"', '?', normalized)
    
    # Normalize whitespace (collapse multiple spaces into one)
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def test_numeric_literals():
    """Test replacement of numeric literals"""
    query = "SELECT * FROM real_estate_property WHERE id = 123"
    fingerprint = _generate_query_fingerprint(query)
    expected = "SELECT * FROM real_estate_property WHERE id = ?"
    assert fingerprint == expected, f"Expected '{expected}', got '{fingerprint}'"
    print("✓ test_numeric_literals passed")


def test_string_literals():
    """Test replacement of string literals"""
    query = "SELECT * FROM real_estate_property WHERE name = 'Luxury Apartment'"
    fingerprint = _generate_query_fingerprint(query)
    expected = "SELECT * FROM real_estate_property WHERE name = ?"
    assert fingerprint == expected, f"Expected '{expected}', got '{fingerprint}'"
    print("✓ test_string_literals passed")


def test_in_clauses():
    """Test normalization of IN clauses"""
    query = "SELECT * FROM real_estate_property WHERE id IN (1,2,3,4,5)"
    fingerprint = _generate_query_fingerprint(query)
    expected = "SELECT * FROM real_estate_property WHERE id IN (?)"
    assert fingerprint == expected, f"Expected '{expected}', got '{fingerprint}'"
    print("✓ test_in_clauses passed")


def test_complex_query():
    """Test complex query with multiple literal types"""
    query = """
        SELECT p.id, p.name, p.price 
        FROM real_estate_property p 
        WHERE p.property_type = 'apartment' 
          AND p.price > 100000 
          AND p.bedrooms IN (2,3,4)
          AND p.company_id = 1
    """
    fingerprint = _generate_query_fingerprint(query)
    # Check that all literals are replaced (4 total: 'apartment', 100000, IN(...), 1)
    assert fingerprint.count('?') >= 4, f"Expected at least 4 placeholders, got: {fingerprint}"
    assert '100000' not in fingerprint, f"Numeric literal not replaced: {fingerprint}"
    assert "'apartment'" not in fingerprint, f"String literal not replaced: {fingerprint}"
    assert 'IN (2,3,4)' not in fingerprint, f"IN clause not normalized: {fingerprint}"
    print("✓ test_complex_query passed")


def test_similar_queries_same_fingerprint():
    """Test that similar queries produce the same fingerprint"""
    queries = [
        "SELECT * FROM users WHERE id = 123",
        "SELECT * FROM users WHERE id = 456",
        "SELECT * FROM users WHERE id = 789",
    ]
    
    fingerprints = [_generate_query_fingerprint(q) for q in queries]
    expected = "SELECT * FROM users WHERE id = ?"
    
    for i, fp in enumerate(fingerprints):
        assert fp == expected, f"Query {i+1} fingerprint mismatch: '{fp}' != '{expected}'"
    
    # All fingerprints should be identical
    assert len(set(fingerprints)) == 1, "Expected all fingerprints to be identical"
    print("✓ test_similar_queries_same_fingerprint passed")


def test_insert_statement():
    """Test INSERT statement fingerprinting"""
    query = "INSERT INTO real_estate_property (name, price, bedrooms) VALUES ('Villa', 500000, 4)"
    fingerprint = _generate_query_fingerprint(query)
    expected = "INSERT INTO real_estate_property (name, price, bedrooms) VALUES (?, ?, ?)"
    assert fingerprint == expected, f"Expected '{expected}', got '{fingerprint}'"
    print("✓ test_insert_statement passed")


def test_update_statement():
    """Test UPDATE statement fingerprinting"""
    query = "UPDATE real_estate_property SET price = 450000, status = 'sold' WHERE id = 123"
    fingerprint = _generate_query_fingerprint(query)
    expected = "UPDATE real_estate_property SET price = ?, status = ? WHERE id = ?"
    assert fingerprint == expected, f"Expected '{expected}', got '{fingerprint}'"
    print("✓ test_update_statement passed")


def test_delete_statement():
    """Test DELETE statement fingerprinting"""
    query = "DELETE FROM real_estate_property WHERE company_id = 5 AND created_at < '2025-01-01'"
    fingerprint = _generate_query_fingerprint(query)
    assert 'DELETE FROM real_estate_property WHERE company_id = ? AND created_at < ?' == fingerprint
    print("✓ test_delete_statement passed")


def run_all_tests():
    """Run all fingerprinting tests"""
    print("Running Phase 6 Task 1 Query Fingerprinting Tests")
    print("=" * 60)
    
    tests = [
        test_numeric_literals,
        test_string_literals,
        test_in_clauses,
        test_complex_query,
        test_similar_queries_same_fingerprint,
        test_insert_statement,
        test_update_statement,
        test_delete_statement,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
