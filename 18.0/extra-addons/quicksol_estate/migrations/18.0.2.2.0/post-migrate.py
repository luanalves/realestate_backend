# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create partial unique index for the active-slot invariant (ADR-027)."""
    if not version:
        return

    # Drop if it exists (idempotent re-run safety)
    cr.execute("""
        DROP INDEX IF EXISTS real_estate_proposal_one_active_per_property;
    """)

    cr.execute("""
        CREATE UNIQUE INDEX real_estate_proposal_one_active_per_property
        ON real_estate_proposal (property_id)
        WHERE state IN ('draft', 'sent', 'accepted')
          AND active = true
          AND parent_proposal_id IS NULL;
    """)
    _logger.info(
        "Feature 013: created partial unique index "
        "real_estate_proposal_one_active_per_property"
    )

    # Performance indexes per data-model.md §1.5
    _create_index(cr, 'real_estate_proposal_state_idx',
                  'real_estate_proposal', '(state)')
    _create_index(cr, 'real_estate_proposal_state_company_idx',
                  'real_estate_proposal', '(state, company_id)')
    _create_index(cr, 'real_estate_proposal_property_state_created_idx',
                  'real_estate_proposal', '(property_id, state, create_date)')
    _logger.info("Feature 013: created performance indexes for real_estate_proposal")


def _create_index(cr, name, table, columns):
    """Idempotently create a regular index."""
    cr.execute(f"DROP INDEX IF EXISTS {name};")
    cr.execute(f"CREATE INDEX {name} ON {table} {columns};")
