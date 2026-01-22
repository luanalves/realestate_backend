"""
Pre-migration script for RBAC User Profiles feature (version 18.0.2.0.0).

ADR-019: RBAC User Profiles System
Backs up current group assignments before restructuring security groups.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Backup current group assignments before RBAC restructuring.
    
    Args:
        cr: Database cursor
        version: Current module version before migration
    """
    _logger.info("Starting pre-migration for RBAC User Profiles (18.0.2.0.0)")
    
    cr.execute("""
        CREATE TABLE IF NOT EXISTS res_groups_users_backup_rbac (
            user_id INTEGER,
            group_id INTEGER,
            backup_date TIMESTAMP DEFAULT NOW()
        );
    """)
    
    cr.execute("""
        INSERT INTO res_groups_users_backup_rbac (user_id, group_id)
        SELECT uid, gid FROM res_groups_users_rel
        WHERE gid IN (
            SELECT id FROM res_groups 
            WHERE name LIKE 'Real Estate%'
        );
    """)
    
    backup_count = cr.rowcount
    _logger.info(f"Backed up {backup_count} group assignments to res_groups_users_backup_rbac")
    
    _logger.info("Pre-migration completed successfully")
