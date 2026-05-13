{
    "name": "TheDevKitchen Estate Goals",
    "version": "18.0.1.0.0",
    "category": "Real Estate",
    "summary": "Monthly performance goals and achievement tracking for real estate teams",
    "description": """
Estate Goals & Results (Metas e Resultados)
============================================

Enables Owners, Directors and Managers to define monthly performance targets per
agent across 5 real estate funnel metrics (captações, novos clientes, visitas,
propostas, fechamento). Achievement data is computed at query time by joining
existing domain entities.

Features:
---------
* Goal CRUD via REST API (POST, PUT, DELETE, GET list)
* Achievements computed from real.estate.service / property / proposal
* Team report with per-metric totals and goal_status filter
* Agent self-view (own metrics only)
* Admin Odoo UI (list + form views)
* Soft-delete (active=False)
* Multitenancy isolation (company_id record rule)
* Composite DB index for report queries
* 200-user hard cap on report endpoint

Technical Details:
------------------
* Five REST endpoints with triple auth (@require_jwt + @require_session + @require_company)
* Raw SQL via env.cr.execute for achievement aggregation (no N+1)
* Composite index: (company_id, year, month, operation_type) WHERE active = true
* Swagger auto-registration via thedevkitchen_api_endpoint table
* ADR-003 (tests), ADR-005 (Swagger), ADR-011 (security), ADR-015 (soft delete)
    """,
    "author": "TheDevKitchen",
    "website": "https://www.thedevkitchen.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "quicksol_estate",
        "thedevkitchen_apigateway",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "data/api_endpoints_data.xml",
        "views/estate_goal_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
