#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Migration Script for Agent Management Module (T122)

This script handles data migration for the quicksol_estate module when
upgrading from previous versions or importing existing agent data.

Migration Scenarios:
1. Fresh installation (no migration needed)
2. Upgrade from basic agent model to full featured version
3. Import agents from external systems

Usage:
    As Odoo pre-migration script:
    python migrate_agent_data.py --database=DB_NAME --mode=pre

    As Odoo post-migration script:
    python migrate_agent_data.py --database=DB_NAME --mode=post

Author: Quicksol Technologies
Date: 2026-01-15
ADR Compliance: ADR-015 (Soft-delete), ADR-008 (Multi-tenancy)
"""

import logging
import argparse
from datetime import datetime

_logger = logging.getLogger(__name__)


class AgentDataMigration:
    """
    Handles data migration for agent management module
    """
    
    def __init__(self, env):
        """
        Initialize migration handler
        
        Args:
            env: Odoo environment instance
        """
        self.env = env
        self.Agent = env['real.estate.agent']
        self.Company = env['res.company']
        
    def migrate_pre(self):
        """
        Pre-migration tasks (run before module upgrade)
        
        Tasks:
        - Backup critical data
        - Validate data integrity
        - Check for conflicts
        """
        _logger.info('Starting pre-migration for agent management module')
        
        try:
            # Count existing agents
            agent_count = self.Agent.search_count([])
            _logger.info(f'Found {agent_count} existing agents')
            
            # Validate company assignments
            agents_without_company = self.Agent.search([('company_id', '=', False)])
            if agents_without_company:
                _logger.warning(f'Found {len(agents_without_company)} agents without company assignment')
            
            # Check for duplicate CPFs
            self._check_duplicate_cpfs()
            
            _logger.info('Pre-migration checks completed successfully')
            return True
            
        except Exception as e:
            _logger.error(f'Pre-migration failed: {str(e)}')
            return False
    
    def migrate_post(self):
        """
        Post-migration tasks (run after module upgrade)
        
        Tasks:
        - Assign default companies to agents without company
        - Normalize CRECI numbers
        - Set default values for new fields
        - Update soft-delete flags
        """
        _logger.info('Starting post-migration for agent management module')
        
        try:
            # 1. Assign default company to agents without company
            self._assign_default_companies()
            
            # 2. Normalize CRECI numbers for existing agents
            self._normalize_creci_numbers()
            
            # 3. Set active=True for existing agents (soft-delete)
            self._set_default_active_status()
            
            # 4. Validate data integrity
            self._validate_migrated_data()
            
            _logger.info('Post-migration completed successfully')
            return True
            
        except Exception as e:
            _logger.error(f'Post-migration failed: {str(e)}')
            return False
    
    def _check_duplicate_cpfs(self):
        """Check for duplicate CPF numbers and report them"""
        # Query for duplicate CPFs
        query = """
            SELECT cpf, COUNT(*) as count
            FROM real_estate_agent
            WHERE cpf IS NOT NULL
            GROUP BY cpf
            HAVING COUNT(*) > 1
        """
        
        self.env.cr.execute(query)
        duplicates = self.env.cr.fetchall()
        
        if duplicates:
            _logger.warning(f'Found {len(duplicates)} duplicate CPF values:')
            for cpf, count in duplicates:
                _logger.warning(f'  CPF {cpf}: {count} occurrences')
        else:
            _logger.info('No duplicate CPFs found')
    
    def _assign_default_companies(self):
        """Assign default company to agents without company assignment"""
        agents_without_company = self.Agent.search([('company_id', '=', False)])
        
        if not agents_without_company:
            _logger.info('All agents have company assignments')
            return
        
        # Get default company (first company in system)
        default_company = self.Company.search([], limit=1)
        
        if not default_company:
            _logger.error('No company found in system. Cannot assign default company.')
            raise ValueError('No company available for agent assignment')
        
        _logger.info(f'Assigning {len(agents_without_company)} agents to company: {default_company.name}')
        
        # Batch update
        agents_without_company.write({'company_id': default_company.id})
        
        _logger.info(f'Successfully assigned {len(agents_without_company)} agents to default company')
    
    def _normalize_creci_numbers(self):
        """Normalize CRECI numbers to standard format"""
        agents_with_creci = self.Agent.search([('creci', '!=', False)])
        
        updated_count = 0
        for agent in agents_with_creci:
            if agent.creci:
                # Trigger CRECI normalization via write
                # The model's write method handles normalization
                agent.write({'creci': agent.creci})
                updated_count += 1
        
        _logger.info(f'Normalized CRECI numbers for {updated_count} agents')
    
    def _set_default_active_status(self):
        """Set active=True for existing agents (soft-delete strategy)"""
        # Count agents with NULL active status
        query = """
            SELECT COUNT(*)
            FROM real_estate_agent
            WHERE active IS NULL
        """
        
        self.env.cr.execute(query)
        null_count = self.env.cr.fetchone()[0]
        
        if null_count > 0:
            _logger.info(f'Setting active=True for {null_count} agents with NULL status')
            
            # Update using SQL for efficiency
            update_query = """
                UPDATE real_estate_agent
                SET active = TRUE
                WHERE active IS NULL
            """
            
            self.env.cr.execute(update_query)
            _logger.info(f'Updated {null_count} agents to active=True')
        else:
            _logger.info('All agents have active status set')
    
    def _validate_migrated_data(self):
        """Validate data integrity after migration"""
        # Check all agents have required fields
        agents_without_name = self.Agent.search([('name', '=', False)])
        agents_without_cpf = self.Agent.search([('cpf', '=', False)])
        agents_without_company = self.Agent.search([('company_id', '=', False)])
        
        issues = []
        
        if agents_without_name:
            issues.append(f'{len(agents_without_name)} agents without name')
        
        if agents_without_cpf:
            issues.append(f'{len(agents_without_cpf)} agents without CPF')
        
        if agents_without_company:
            issues.append(f'{len(agents_without_company)} agents without company')
        
        if issues:
            _logger.warning('Data validation found issues:')
            for issue in issues:
                _logger.warning(f'  - {issue}')
        else:
            _logger.info('Data validation passed - all required fields populated')


def migrate(cr, version):
    """
    Odoo migration entry point
    
    This function is called by Odoo's migration framework.
    
    Args:
        cr: Database cursor
        version: Module version being migrated from
    """
    from odoo import api, SUPERUSER_ID
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    migration = AgentDataMigration(env)
    
    # Run post-migration tasks
    success = migration.migrate_post()
    
    if success:
        _logger.info(f'Migration from version {version} completed successfully')
    else:
        _logger.error(f'Migration from version {version} failed')


def main():
    """
    Standalone migration script entry point
    """
    parser = argparse.ArgumentParser(description='Agent Data Migration Script')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--mode', choices=['pre', 'post'], default='post',
                       help='Migration mode: pre or post')
    parser.add_argument('--config', help='Odoo configuration file path')
    
    args = parser.parse_args()
    
    print(f"Agent Data Migration Script")
    print(f"Database: {args.database}")
    print(f"Mode: {args.mode}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("-" * 60)
    
    try:
        import odoo
        from odoo import api, SUPERUSER_ID
        
        # Initialize Odoo
        if args.config:
            odoo.tools.config.parse_config(['-c', args.config, '-d', args.database])
        else:
            odoo.tools.config.parse_config(['-d', args.database])
        
        # Get database cursor
        db = odoo.sql_db.db_connect(args.database)
        
        with db.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            migration = AgentDataMigration(env)
            
            if args.mode == 'pre':
                success = migration.migrate_pre()
            else:
                success = migration.migrate_post()
            
            if success:
                cr.commit()
                print("\n✅ Migration completed successfully")
            else:
                cr.rollback()
                print("\n❌ Migration failed - changes rolled back")
                exit(1)
    
    except Exception as e:
        print(f"\n❌ Migration error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()
