{
    "name": "TheDevKitchen Estate Credit Check",
    "version": "18.0.1.0.0",
    "category": "Real Estate",
    "summary": "Rental Credit Check (Análise de Ficha) for Lease Proposals",
    "description": """
Rental Credit Check — Análise de Ficha
=======================================

Credit analysis gate for rental proposals. Introduces a ``credit_check_pending``
state in the proposal FSM and a dedicated ``CreditCheck`` entity.

Features:
---------
* Initiate credit analysis on sent/negotiation lease proposals (US1)
* Register approved / rejected / cancelled results (US2)
* Automatic queue promotion on rejection (spec 013 FR-011)
* Automatic competitor cancellation on approval (spec 013 FR-014)
* Cron-driven expiry of pending checks (spec 013 FR-026 extension)
* Manual cancel guard: cancelling proposal marks active check as cancelled
* Client credit-history endpoint with agent scope enforcement
* Anti-enumeration 404 for out-of-scope clients (ADR-008)
* Full multi-tenant isolation via company_id record rules (ADR-015)
* Async notifications via Outbox/EventBus pattern (ADR-021)
* Partial unique index for one-pending-per-proposal invariant (ADR-027)
* 4 REST endpoints with triple-decorator auth (ADR-011)
* OpenAPI 3.0 Swagger records (ADR-005), Postman collection (ADR-016)

Technical:
----------
* Model: thedevkitchen.estate.credit.check
* Extends: real.estate.proposal (_inherit)
* ADR compliance: ADR-001, 004, 005, 007, 008, 011, 015, 016, 018, 019, 021, 022, 027
    """,
    "author": "TheDevKitchen",
    "website": "https://www.thedevkitchen.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "thedevkitchen_apigateway",
        "quicksol_estate",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "data/mail_templates.xml",
        "data/api_endpoints_data.xml",
        "views/credit_check_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "assets": {},
}
