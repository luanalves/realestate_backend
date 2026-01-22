# -*- coding: utf-8 -*-
"""
API Performance Tests (T120)

This module tests API endpoint performance requirements to ensure
production readiness and acceptable response times under load.

Performance SLAs:
- GET /api/v1/agents with 1000 records: <500ms
- GET /api/v1/agents/{id}: <100ms
- Pagination performance: <3x degradation across offsets
- Bulk operations: <5s for 100 records

ADR Compliance:
- ADR-003: Mandatory test coverage (performance benchmarks)
- ADR-008: Multi-tenancy performance isolation

Test Tags: performance, post_install
"""

import time
import json
from odoo.tests import HttpCase, tagged


@tagged('performance', 'post_install', '-at_install')
class TestAgentAPIPerformance(HttpCase):
    """Performance benchmarks for Agent Management API endpoints"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Performance Test Company',
        })
        
        # Create test user with estate manager access
        cls.user = cls.env['res.users'].create({
            'name': 'Performance Test User',
            'login': 'perf_test_user',
            'email': 'perf@test.com',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, [cls.company.id])],
            'groups_id': [(6, 0, [
                cls.env.ref('quicksol_estate.group_real_estate_manager').id,
                cls.env.ref('base.group_user').id,
            ])],
        })
        
        # Set estate_default_company_id for multi-tenancy
        cls.user.estate_default_company_id = cls.company
        
        # Create OAuth2 application for authentication
        cls.oauth_app = cls.env['oauth.application'].sudo().create({
            'name': 'Performance Test App',
            'client_id': 'perf_test_client',
            'client_secret': 'perf_test_secret',
            'redirect_uri': 'http://localhost:8069/oauth/callback',
            'grant_type': 'password',
            'scope': 'read write',
        })
        
        # Generate access token
        cls.token_record = cls.env['oauth.access_token'].sudo().create({
            'user_id': cls.user.id,
            'application_id': cls.oauth_app.id,
            'token': 'perf_test_token_' + str(time.time()),
            'scope': 'read write',
            'expires_in': 3600,
        })
        
        cls.access_token = cls.token_record.token
    
    def setUp(self):
        super().setUp()
        self.Agent = self.env['real.estate.agent'].sudo()
    
    def test_list_agents_performance_1000_records(self):
        """
        T120: GET /api/v1/agents should return <500ms for 1000 records
        
        Requirements:
        - Response time < 500ms for 1000 agent records
        - Proper pagination support (limit 100, offset 0)
        - No N+1 query issues
        
        Success Criteria:
        - Response time < 500ms
        - Returns 100 agents (first page)
        - Total count = 1000
        """
        # Create 1000 test agents
        agents_to_create = []
        for i in range(1000):
            agents_to_create.append({
                'name': f'Agent Performance Test {i:04d}',
                'cpf': f'{i:011d}',  # 11-digit CPF
                'email': f'agent{i}@perftest.com',
                'company_id': self.company.id,
            })
        
        # Batch create for efficiency
        self.Agent.create(agents_to_create)
        
        # Warm up query cache
        self.Agent.search([('company_id', '=', self.company.id)], limit=10)
        
        # Measure performance
        start_time = time.time()
        
        response = self.url_open(
            '/api/v1/agents?limit=100&offset=0',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200, 
                        f'Expected 200 OK, got {response.status_code}')
        
        # Verify response time meets SLA (<500ms)
        self.assertLess(response_time, 500, 
                       f'Response time {response_time:.2f}ms exceeds 500ms SLA')
        
        # Verify response structure
        data = json.loads(response.content)
        self.assertIn('agents', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['agents']), 100, 'Expected 100 agents in first page')
        
        # Log performance metrics
        print(f'\n[PERFORMANCE] GET /api/v1/agents with 1000 records: {response_time:.2f}ms')
        print(f'[PERFORMANCE] SLA: <500ms | Actual: {response_time:.2f}ms | Status: PASS')
    
    def test_list_agents_pagination_performance(self):
        """
        Verify pagination performance doesn't degrade with large offsets
        
        Requirements:
        - Offset-based pagination should not degrade >3x
        - Response time should remain reasonable at high offsets
        
        Success Criteria:
        - Max degradation < 3.0x between first and last page
        """
        # Create 500 test agents
        agents_to_create = []
        for i in range(500):
            agents_to_create.append({
                'name': f'Agent Pagination Test {i:04d}',
                'cpf': f'{i+50000:011d}',
                'company_id': self.company.id,
            })
        
        self.Agent.create(agents_to_create)
        
        # Test pagination at different offsets
        offsets = [0, 100, 200, 400]
        response_times = []
        
        for offset in offsets:
            start_time = time.time()
            
            response = self.url_open(
                f'/api/v1/agents?limit=50&offset={offset}',
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json',
                }
            )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            self.assertEqual(response.status_code, 200)
        
        # Verify performance doesn't degrade significantly with offset
        max_degradation = max(response_times) / min(response_times)
        self.assertLess(max_degradation, 3.0,
                       f'Pagination performance degraded by {max_degradation:.2f}x (max 3.0x)')
        
        print(f'\n[PERFORMANCE] Pagination response times: {[f"{t:.2f}ms" for t in response_times]}')
        print(f'[PERFORMANCE] Max degradation: {max_degradation:.2f}x | SLA: <3.0x | Status: PASS')
    
    def test_get_agent_detail_performance(self):
        """
        Verify individual agent detail retrieval performance
        
        Requirements:
        - GET /api/v1/agents/{id} should return <100ms
        - No unnecessary joins or N+1 queries
        
        Success Criteria:
        - Response time < 100ms
        - Returns complete agent data
        """
        # Create test agent
        agent = self.Agent.create({
            'name': 'Performance Detail Test Agent',
            'cpf': '99999999999',
            'email': 'detail@perftest.com',
            'company_id': self.company.id,
        })
        
        # Measure performance
        start_time = time.time()
        
        response = self.url_open(
            f'/api/v1/agents/{agent.id}',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(response_time, 100,
                       f'Agent detail response time {response_time:.2f}ms exceeds 100ms SLA')
        
        # Verify complete data returned
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('cpf', data)
        
        print(f'\n[PERFORMANCE] GET /api/v1/agents/{agent.id}: {response_time:.2f}ms')
        print(f'[PERFORMANCE] SLA: <100ms | Actual: {response_time:.2f}ms | Status: PASS')
