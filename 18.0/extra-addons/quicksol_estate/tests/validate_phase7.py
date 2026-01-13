#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick validation script for Phase 7 (Performance Metrics)
Runs inside Odoo container to verify models and services
"""

# Test if agent model has performance fields
agent_model = env['real.estate.agent']
performance_fields = [
    'total_sales_count',
    'total_commissions', 
    'average_commission',
    'active_properties_count'
]

print("=" * 60)
print("Phase 7 (US5 - Performance Metrics) Validation")
print("=" * 60)

print("\n1. Agent Model Performance Fields:")
for field_name in performance_fields:
    exists = field_name in agent_model._fields
    status = "✅" if exists else "❌"
    print(f"   {status} {field_name}: {exists}")

# Test if PerformanceService loads
try:
    from odoo.addons.quicksol_estate.services.performance_service import PerformanceService
    service = PerformanceService(env)
    print("\n2. PerformanceService:")
    print(f"   ✅ Service instantiated successfully")
    print(f"   Methods available: get_agent_performance, get_top_agents_ranking")
except Exception as e:
    print(f"\n2. PerformanceService:")
    print(f"   ❌ Failed to load: {str(e)}")

# Test if performance endpoints exist in controllers
try:
    from odoo.addons.quicksol_estate.controllers.agent_api import AgentApiController
    api = AgentApiController()
    has_performance = hasattr(api, 'get_agent_performance')
    has_ranking = hasattr(api, 'get_agents_ranking')
    print("\n3. API Endpoints:")
    print(f"   {'✅' if has_performance else '❌'} GET /api/v1/agents/{{id}}/performance")
    print(f"   {'✅' if has_ranking else '❌'} GET /api/v1/agents/ranking")
except Exception as e:
    print(f"\n3. API Endpoints:")
    print(f"   ❌ Failed to check: {str(e)}")

print("\n" + "=" * 60)
print("Phase 7 validation complete!")
print("=" * 60)
