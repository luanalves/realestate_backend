# -*- coding: utf-8 -*-
"""
Unit Tests for Quicksol Estate Module

These tests use unittest.mock and do NOT require:
- Odoo framework
- Database connection
- External services

Purpose: Test pure business logic and validations in isolation
Execution: python3 run_unit_tests.py (< 5 seconds expected)

Guidelines (ADR-003):
- 100% coverage of all validations (required, constraints, compute)
- Use unittest.TestCase (NOT TransactionCase)
- Use unittest.mock for all dependencies
- No database, no Odoo env, no sudo()
"""
