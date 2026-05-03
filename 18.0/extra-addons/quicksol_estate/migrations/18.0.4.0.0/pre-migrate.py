# -*- coding: utf-8 -*-

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Feature 015 migration:
    1. EXCLUDE constraint for uniqueness per active client+operation+agent (FR-003a).
    2. Performance indexes for the real_estate_service table (T071).
    """
    # ------------------------------------------------------------------ #
    # 1. EXCLUDE constraint                                               #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 2. Performance indexes (T071)                                       #
    #    All idempotent via IF NOT EXISTS.                                #
    # ------------------------------------------------------------------ #
    indexes = [
        (
            'idx_service_company_stage',
            'real_estate_service',
            'company_id, stage',
            None,  # no WHERE clause
        ),
        (
            'idx_service_company_agent',
            'real_estate_service',
            'company_id, agent_id',
            None,
        ),
        (
            'idx_service_company_lastactivity',
            'real_estate_service',
            'company_id, last_activity_date DESC NULLS LAST',
            None,
        ),
        (
            'idx_service_active',
            'real_estate_service',
            'company_id, stage',
            'active = TRUE',  # partial index
        ),
        (
            'idx_service_client_partner',
            'real_estate_service',
            'client_partner_id',
            None,
        ),
        (
            'idx_service_is_pending',
            'real_estate_service',
            'company_id, is_pending',
            'is_pending = TRUE',
        ),
        (
            'idx_service_is_orphan',
            'real_estate_service',
            'company_id, is_orphan_agent',
            'is_orphan_agent = TRUE',
        ),
    ]

    for idx_name, table, columns, where_clause in indexes:
        where_sql = f' WHERE ({where_clause})' if where_clause else ''
        try:
            cr.execute(f"""
                CREATE INDEX IF NOT EXISTS {idx_name}
                ON {table} ({columns}){where_sql};
            """)
            _logger.info('Feature 015: index %s ensured on %s.', idx_name, table)
        except Exception as e:  # noqa: BLE001
            _logger.warning(
                'Feature 015: Could not create index %s (table may not exist yet): %s',
                idx_name, e,
            )
