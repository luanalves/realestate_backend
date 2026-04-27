# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Add source column to real_estate_lead and backfill existing rows."""
    if not version:
        return

    # Add the column if it doesn't already exist
    cr.execute("""
        ALTER TABLE real_estate_lead
        ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'manual';
    """)
    _logger.info("Feature 013: added 'source' column to real_estate_lead")

    # Backfill existing rows
    cr.execute("""
        UPDATE real_estate_lead
        SET source = 'manual'
        WHERE source IS NULL;
    """)
    _logger.info("Feature 013: backfilled real_estate_lead.source = 'manual'")
