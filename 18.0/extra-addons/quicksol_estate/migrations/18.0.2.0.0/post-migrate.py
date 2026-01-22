"""
Post-migration script for RBAC User Profiles feature (version 18.0.2.0.0).

ADR-019: RBAC User Profiles System
Adds prospector_id field to properties and creates performance indexes.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Add prospector_id field and create indexes for performance.
    
    Args:
        cr: Database cursor
        version: Current module version before migration
    """
    _logger.info("Starting post-migration for RBAC User Profiles (18.0.2.0.0)")
    
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='real_estate_property' AND column_name='prospector_id'
    """)
    
    if not cr.fetchone():
        _logger.info("Adding prospector_id column to real_estate_property")
        cr.execute("""
            ALTER TABLE real_estate_property
            ADD COLUMN prospector_id INTEGER
            REFERENCES real_estate_agent(id) ON DELETE SET NULL;
        """)
        _logger.info("prospector_id column added successfully")
    else:
        _logger.info("prospector_id column already exists, skipping")
    
    cr.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename='real_estate_property' AND indexname='idx_property_prospector'
    """)
    
    if not cr.fetchone():
        _logger.info("Creating index idx_property_prospector")
        cr.execute("""
            CREATE INDEX idx_property_prospector
            ON real_estate_property(prospector_id)
            WHERE prospector_id IS NOT NULL;
        """)
        _logger.info("Index created successfully")
    else:
        _logger.info("Index idx_property_prospector already exists, skipping")
    
    cr.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename='real_estate_property' AND indexname='idx_property_agent_company'
    """)
    
    if not cr.fetchone():
        _logger.info("Creating composite index idx_property_agent_company for performance")
        cr.execute("""
            CREATE INDEX idx_property_agent_company
            ON real_estate_property(agent_id, company_id);
        """)
        _logger.info("Composite index created successfully")
    else:
        _logger.info("Index idx_property_agent_company already exists, skipping")
    
    _logger.info("Post-migration completed successfully")
