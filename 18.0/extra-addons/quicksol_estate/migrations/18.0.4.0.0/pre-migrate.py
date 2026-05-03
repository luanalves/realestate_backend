# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Create EXCLUDE constraint for real_estate_service table if not present."""
    # The table may not exist yet on a fresh install — handled by try/except.
    try:
        cr.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'real_estate_service_unique_active_per_client_type_agent'
                ) THEN
                    ALTER TABLE real_estate_service
                        ADD CONSTRAINT real_estate_service_unique_active_per_client_type_agent
                        EXCLUDE USING btree (
                            client_partner_id WITH =,
                            operation_type WITH =,
                            agent_id WITH =
                        ) WHERE (active = TRUE AND stage NOT IN ('won', 'lost'));
                END IF;
            END;
            $$;
        """)
        _logger.info(
            'Feature 015: EXCLUDE constraint real_estate_service_unique_active_per_client_type_agent '
            'ensured on real_estate_service.'
        )
    except Exception as e:  # noqa: BLE001
        _logger.warning(
            'Feature 015: Could not create EXCLUDE constraint on real_estate_service '
            '(table may not exist yet on fresh install — will be applied after model creation): %s',
            e,
        )
