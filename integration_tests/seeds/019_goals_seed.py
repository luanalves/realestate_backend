#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed data for Feature 019 — Goals & Results integration tests.

Usage (from repo root):
    cd 18.0
    docker compose exec odoo python /mnt/extra-addons/thedevkitchen_estate_goals/scripts/seed_019.py
    # OR via odoo shell:
    docker compose exec odoo odoo shell -d realestate < /path/to/this/file

Idempotent: all creates check-before-insert.
Creates:
    - 2 companies
    - 5 users with seed_019_ prefix
    - Real estate data for May 2026 (properties, services, proposals)
    - 6 goals for agent_a (May 2026)
"""
import logging
import sys
import os

# Allow running standalone with odoo in PYTHONPATH
try:
    import odoo
    from odoo import api, SUPERUSER_ID
    from odoo.tools import config
except ImportError:
    print("This script must be run inside the Odoo container.")
    sys.exit(1)

_logger = logging.getLogger(__name__)

DB_NAME = os.environ.get('ODOO_DATABASE', 'realestate')

# ── Credentials used in integration tests ──────────────────────────────────
USERS = [
    {
        'login': 'owner_019@example.com',
        'name': 'Owner Seed 019',
        'password': 'OwnerPass019!',
        'group_xml': 'quicksol_estate.group_real_estate_owner',
    },
    {
        'login': 'manager_019@example.com',
        'name': 'Manager Seed 019',
        'password': 'ManagerPass019!',
        'group_xml': 'quicksol_estate.group_real_estate_manager',
    },
    {
        'login': 'agent_019@example.com',
        'name': 'Agent Seed 019',
        'password': 'AgentPass019!',
        'group_xml': 'quicksol_estate.group_real_estate_agent',
    },
    {
        'login': 'owner_b_019@example.com',
        'name': 'Owner B Seed 019',
        'password': 'OwnerBPass019!',
        'group_xml': 'quicksol_estate.group_real_estate_owner',
        'company': 'company_b',
    },
]

COMPANY_A_NAME = 'Imobiliária Seed A (019)'
COMPANY_B_NAME = 'Imobiliária Seed B (019)'


def seed(env):
    """Main seed function — idempotent."""

    # ── Companies ───────────────────────────────────────────────────────────
    ResCompany = env['res.company']
    company_a = ResCompany.sudo().search([('name', '=', COMPANY_A_NAME)], limit=1)
    if not company_a:
        company_a = ResCompany.sudo().create({'name': COMPANY_A_NAME})
        _logger.info('Created company A: %s', COMPANY_A_NAME)
    else:
        _logger.info('Company A already exists: %s', COMPANY_A_NAME)

    company_b = ResCompany.sudo().search([('name', '=', COMPANY_B_NAME)], limit=1)
    if not company_b:
        company_b = ResCompany.sudo().create({'name': COMPANY_B_NAME})
        _logger.info('Created company B: %s', COMPANY_B_NAME)
    else:
        _logger.info('Company B already exists: %s', COMPANY_B_NAME)

    company_map = {'company_a': company_a, 'company_b': company_b}

    # ── Users ───────────────────────────────────────────────────────────────
    ResUsers = env['res.users'].sudo()
    created_users = {}

    for u in USERS:
        existing = ResUsers.search([('login', '=', u['login'])], limit=1)
        company = company_map.get(u.get('company', 'company_a'), company_a)
        if not existing:
            partner = env['res.partner'].sudo().create({
                'name': u['name'],
                'company_id': company.id,
            })
            user = ResUsers.create({
                'name': u['name'],
                'login': u['login'],
                'password': u['password'],
                'company_id': company.id,
                'company_ids': [(4, company.id)],
                'partner_id': partner.id,
            })
            # Assign group
            try:
                group = env.ref(u['group_xml'])
                user.write({'groups_id': [(4, group.id)]})
            except Exception as e:
                _logger.warning('Could not assign group %s: %s', u['group_xml'], e)
            _logger.info('Created user %s', u['login'])
        else:
            user = existing
            _logger.info('User %s already exists', u['login'])
        created_users[u['login']] = user

    agent_a = created_users['agent_019@example.com']
    company_a_id = company_a.id

    # ── Real estate agent record for agent_a ────────────────────────────────
    # (Only if real.estate.agent model exists)
    try:
        REAgent = env['real.estate.agent'].sudo()
        agent_rec = REAgent.search([('user_id', '=', agent_a.id), ('company_id', '=', company_a_id)], limit=1)
        if not agent_rec:
            agent_rec = REAgent.create({
                'user_id': agent_a.id,
                'company_id': company_a_id,
                'name': agent_a.name,
            })
            _logger.info('Created real.estate.agent for agent_019')
        agent_re_id = agent_rec.id
    except Exception as e:
        _logger.warning('real.estate.agent model unavailable: %s', e)
        agent_re_id = None

    # ── Properties (for captação metric) ────────────────────────────────────
    if agent_re_id:
        try:
            REProperty = env['real.estate.property'].sudo()
            for i, prop in enumerate([
                {'for_sale': True, 'price': 500000.0, 'for_rent': False, 'rent_price': 0},
                {'for_sale': True, 'price': 750000.0, 'for_rent': False, 'rent_price': 0},
                {'for_sale': False, 'price': 0, 'for_rent': True, 'rent_price': 3500.0},
            ], start=1):
                existing_prop = REProperty.search([
                    ('name', '=', f'Seed Prop 019-A-{i}'),
                    ('company_id', '=', company_a_id),
                ], limit=1)
                if not existing_prop:
                    REProperty.create(dict(prop,
                        name=f'Seed Prop 019-A-{i}',
                        agent_id=agent_re_id,
                        company_id=company_a_id,
                    ))
                    _logger.info('Created property Seed Prop 019-A-%s', i)
        except Exception as e:
            _logger.warning('Could not create properties: %s', e)

    # ── Services (for novos_clientes + visitas + fechamento) ─────────────────
    service_ids = []
    try:
        REService = env['real.estate.service'].sudo()
        for i in range(1, 4):
            existing_svc = REService.search([
                ('name', '=', f'Seed Service 019-A-{i}'),
                ('company_id', '=', company_a_id),
            ], limit=1)
            if not existing_svc:
                svc = REService.create({
                    'name': f'Seed Service 019-A-{i}',
                    'agent_id': agent_a.id,
                    'company_id': company_a_id,
                    'operation_type': 'sale',
                })
                service_ids.append(svc.id)
                _logger.info('Created service Seed Service 019-A-%s', i)
            else:
                service_ids.append(existing_svc.id)
    except Exception as e:
        _logger.warning('Could not create services: %s', e)

    # ── Goals for agent_a (May 2026) ─────────────────────────────────────────
    GoalModel = env['thedevkitchen.estate.goal'].sudo()
    GOALS = [
        {'metric_type': 'captacao',       'operation_type': 'sale', 'target_count': 3,  'target_vgv': 1500000.0},
        {'metric_type': 'novos_clientes', 'operation_type': 'all',  'target_count': 5,  'target_vgv': False},
        {'metric_type': 'visitas',        'operation_type': 'all',  'target_count': 10, 'target_vgv': False},
        {'metric_type': 'propostas',      'operation_type': 'sale', 'target_count': 4,  'target_vgv': 2000000.0},
        {'metric_type': 'fechamento',     'operation_type': 'all',  'target_count': 2,  'target_vgv': 1000000.0},
        {'metric_type': 'captacao',       'operation_type': 'rent', 'target_count': 2,  'target_vgv': 84000.0},
    ]
    for g in GOALS:
        existing_goal = GoalModel.search([
            ('user_id', '=', agent_a.id),
            ('year', '=', 2026),
            ('month', '=', 5),
            ('metric_type', '=', g['metric_type']),
            ('operation_type', '=', g['operation_type']),
            ('company_id', '=', company_a_id),
        ], limit=1)
        if not existing_goal:
            vals = dict(g,
                user_id=agent_a.id,
                year=2026,
                month=5,
                company_id=company_a_id,
            )
            if not vals.get('target_vgv'):
                vals.pop('target_vgv', None)
            GoalModel.create(vals)
            _logger.info('Created goal metric=%s op=%s', g['metric_type'], g['operation_type'])
        else:
            _logger.info('Goal already exists: metric=%s op=%s', g['metric_type'], g['operation_type'])

    _logger.info('✓ Feature 019 seed complete.')
    print("✓ Feature 019 seed complete.")


if __name__ == '__main__':
    # When executed via odoo shell
    seed(env)  # noqa: F821 — 'env' is injected by odoo shell
