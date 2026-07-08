# API Surface

> Sources: direct extraction of every `@http.route(...)` decorator (and the auth decorators wrapping each handler) from all `18.0/extra-addons/*/controllers/*.py` files. No GraphQL schema files (`*.graphqls`, `schema.graphql`) or `.proto` (gRPC) files were found anywhere in the repository — the API surface is 100% REST/JSON over HTTP.
>
> **Auth column legend:** `JWT+Session+Company` = `@require_jwt` → `@require_session` → `@require_company` (the standard triple-decorator chain, ADR-011); `none` = `auth='none'` at the Odoo route level with no additional decorator (fully public); other combinations noted explicitly.
>
> Full interactive documentation: `GET /api/docs` (Swagger UI), spec at `GET /api/v1/openapi.json` (generated dynamically from the `thedevkitchen.api.endpoint` table). Postman collections under `docs/postman/` (`quicksol_api_v1.31_postman_collection.json` is the latest, per `docs/postman/README.md`).

## Platform / Gateway endpoints (`thedevkitchen_apigateway`)

| Method | Route | Handler | Authentication | Module |
|---|---|---|---|---|
| POST | `/api/v1/auth/token` | `token` | none (OAuth2 client_credentials — validates client_id/secret in body) | thedevkitchen_apigateway |
| POST | `/api/v1/auth/revoke` | `revoke` | none (OAuth2 token in body) | thedevkitchen_apigateway |
| POST | `/api/v1/auth/refresh` | `refresh` | none (OAuth2 refresh token in body) | thedevkitchen_apigateway |
| GET | `/api/v1/health` | `health` | none (public health check) | thedevkitchen_apigateway |
| GET | `/api/v1/me` | `get_me` | JWT+Session | thedevkitchen_apigateway |
| GET | `/api/docs` | `swagger_ui` | none (public) | thedevkitchen_apigateway |
| GET | `/api/v1/openapi.json` | `openapi_spec` | none (public) | thedevkitchen_apigateway |
| GET | `/api/v1/test/public` | `test_public` | none | thedevkitchen_apigateway |
| GET | `/api/v1/test/protected` | `test_protected` | JWT | thedevkitchen_apigateway |
| GET | `/api/v1/test/scoped` | `test_scoped` | JWT + scope (`require_jwt_with_scope`) | thedevkitchen_apigateway |
| POST | `/api/v1/test/echo` | `test_echo` | JWT | thedevkitchen_apigateway |
| POST | `/api/v1/users/login` | `login` | JWT (OAuth2 app token required; blocks `base.group_system`, ADR-029) | thedevkitchen_apigateway |
| POST | `/api/v1/users/logout` | `logout` | JWT+Session | thedevkitchen_apigateway |
| PATCH | `/api/v1/users/profile` | `update_profile` | JWT+Session | thedevkitchen_apigateway |
| POST | `/api/v1/users/change-password` | `change_password` | JWT+Session | thedevkitchen_apigateway |
| POST | `/api/v1/users/switch-company` | `switch_company` | JWT+Session | thedevkitchen_apigateway |

## Users & Onboarding (`thedevkitchen_user_onboarding`)

| Method | Route | Handler | Authentication | Module |
|---|---|---|---|---|
| POST | `/api/v1/users/invite` | `invite_user` | JWT+Session+Company | thedevkitchen_user_onboarding |
| POST | `/api/v1/users/resend-invite` | `resend_invite` | JWT+Session+Company | thedevkitchen_user_onboarding |
| POST | `/api/v1/auth/set-password` | `set_password` | none (single-use invite/reset token in body) | thedevkitchen_user_onboarding |
| POST | `/api/v1/auth/forgot-password` | `forgot_password` | none (Redis rate-limited, 3 req/hr, anti-enumeration) | thedevkitchen_user_onboarding |
| POST | `/api/v1/auth/reset-password` | `reset_password` | none (single-use reset token in body) | thedevkitchen_user_onboarding |

## Profiles & RBAC (`quicksol_estate/controllers/profile_api.py`, `capabilities_controller.py`)

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/profiles` | `create_profile` | JWT+Session+Company |
| GET | `/api/v1/profiles` | `list_profiles` | JWT+Session+Company |
| GET | `/api/v1/profiles/<int:profile_id>` | `get_profile` | JWT+Session+Company |
| PUT | `/api/v1/profiles/<int:profile_id>` | `update_profile` | JWT+Session+Company |
| DELETE | `/api/v1/profiles/<int:profile_id>` | `delete_profile` | JWT+Session+Company |
| GET | `/api/v1/profile-types` | `list_profile_types` | JWT+Session |
| GET | `/api/v1/me/capabilities` | `get_capabilities` | JWT+Session+Company |

## Companies (Agencies) — `quicksol_estate/controllers/company_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/companies` | `create_company` | JWT+Session |
| GET | `/api/v1/companies` | `list_companies` | JWT+Session+Company |
| GET | `/api/v1/companies/<int:company_id>` | `get_company` | JWT+Session+Company |
| PUT | `/api/v1/companies/<int:company_id>` | `update_company` | JWT+Session+Company |
| DELETE | `/api/v1/companies/<int:company_id>` | `delete_company` | JWT+Session+Company |
| GET | `/api/v1/companies/<int:company_id>/properties` | `list_company_properties` | JWT+Session+Company |

## Owners — `quicksol_estate/controllers/owner_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/owners` | `create_owner` | JWT only |
| POST | `/api/v1/owners/<int:owner_id>/companies` | `link_owner_to_company` | JWT+Session+Company |
| DELETE | `/api/v1/owners/<int:owner_id>/companies/<int:company_id>` | `unlink_owner_from_company` | JWT+Session+Company |

## Agents, Assignments, Commissions — `quicksol_estate/controllers/agent_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/agents` | `list_agents` | JWT+Session+Company |
| POST | `/api/v1/agents` | `create_agent` | JWT+Session+Company |
| GET | `/api/v1/agents/<int:agent_id>` | `get_agent` | JWT+Session+Company |
| PUT | `/api/v1/agents/<int:agent_id>` | `update_agent` | JWT+Session+Company |
| POST | `/api/v1/agents/<int:agent_id>/deactivate` | `deactivate_agent` | JWT+Session+Company |
| POST | `/api/v1/agents/<int:agent_id>/reactivate` | `reactivate_agent` | JWT+Session+Company |
| GET | `/api/v1/agents/<int:agent_id>/properties` | `get_agent_properties` | JWT+Session+Company |
| GET | `/api/v1/agents/<int:agent_id>/performance` | `get_agent_performance` | JWT+Session+Company |
| GET | `/api/v1/agents/ranking` | `get_agents_ranking` | JWT+Session+Company |
| POST | `/api/v1/assignments` | `create_assignment` | JWT+Session+Company |
| GET | `/api/v1/assignments` | `list_assignments` | JWT+Session+Company |
| GET | `/api/v1/assignments/<int:assignment_id>` | `get_assignment` | JWT+Session+Company |
| PATCH | `/api/v1/assignments/<int:assignment_id>` | `update_assignment` | JWT+Session+Company |
| DELETE | `/api/v1/assignments/<int:assignment_id>` | `delete_assignment` | JWT+Session+Company |
| POST | `/api/v1/agents/<int:agent_id>/commission-rules` | `create_commission_rule` | JWT+Session+Company |
| GET | `/api/v1/agents/<int:agent_id>/commission-rules` | `list_commission_rules` | JWT+Session+Company |
| PUT | `/api/v1/commission-rules/<int:rule_id>` | `update_commission_rule` | JWT+Session+Company |
| POST | `/api/v1/commission-transactions` | `create_commission_transaction` | JWT+Session+Company |

## Properties — `quicksol_estate/controllers/property_api.py`, `property_attachments_controller.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/properties` | `list_properties` | JWT+Session+Company |
| POST | `/api/v1/properties` | `create_property` | JWT+Session+Company |
| GET | `/api/v1/properties/<int:property_id>` | `get_property` | JWT+Session+Company |
| PUT | `/api/v1/properties/<int:property_id>` | `update_property` | JWT+Session+Company |
| DELETE | `/api/v1/properties/<int:property_id>` | `delete_property` | JWT+Session+Company |
| POST | `/api/v1/properties/<int:property_id>/attachments` | `upload_attachment` | JWT+Session+Company |
| GET | `/api/v1/properties/<int:property_id>/attachments` | `list_attachments` | JWT+Session+Company |
| GET | `/api/v1/properties/<int:property_id>/attachments/<int:attachment_id>/download` | `download_attachment` | JWT+Session+Company |
| DELETE | `/api/v1/properties/<int:property_id>/attachments/<int:attachment_id>` | `delete_attachment` | JWT+Session+Company |

## Master data / lookups — `quicksol_estate/controllers/master_data_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/properties/options` | `list_property_options` | JWT+Session+Company |
| GET | `/api/v1/property-types` | `list_property_types` | JWT+Session |
| GET | `/api/v1/location-types` | `list_location_types` | JWT+Session |
| GET | `/api/v1/states` | `list_states` | JWT+Session |
| GET | `/api/v1/companies` | `list_companies` | JWT+Session+Company |
| GET | `/api/v1/tags` | `list_tags` | none (`cors='*'`) |
| GET | `/api/v1/amenities` | `list_amenities` | JWT+Session |

## Leads & Pipeline — `quicksol_estate/controllers/lead_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/leads` | `list_leads` | none (`cors='*'`) |
| GET | `/api/v1/leads/export` | `export_leads_csv` | JWT+Session+Company |
| POST | `/api/v1/leads` | `create_lead` | JWT+Session+Company |
| GET | `/api/v1/leads/<int:lead_id>` | `get_lead` | JWT+Session+Company |
| PUT | `/api/v1/leads/<int:lead_id>` | `update_lead` | JWT+Session+Company |
| DELETE | `/api/v1/leads/<int:lead_id>` | `delete_lead` | JWT+Session+Company |
| POST | `/api/v1/leads/<int:lead_id>/convert` | `convert_lead` | JWT+Session+Company |
| POST | `/api/v1/leads/<int:lead_id>/reopen` | `reopen_lead` | JWT+Session+Company |
| GET | `/api/v1/leads/statistics` | `lead_statistics` | JWT+Session+Company |
| POST | `/api/v1/leads/<int:lead_id>/activities` | `log_activity` | JWT+Session |
| GET | `/api/v1/leads/<int:lead_id>/activities` | `list_activities` | JWT+Session |
| POST | `/api/v1/leads/<int:lead_id>/schedule-activity` | `schedule_activity` | JWT+Session |
| POST | `/api/v1/leads/filters` | `create_filter` | JWT+Session |
| GET | `/api/v1/leads/filters` | `list_filters` | JWT+Session |
| DELETE | `/api/v1/leads/filters/<int:filter_id>` | `delete_filter` | JWT+Session |

## Leases — `quicksol_estate/controllers/lease_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/leases` | `list_leases` | JWT+Session+Company |
| POST | `/api/v1/leases` | `create_lease` | JWT+Session+Company |
| GET | `/api/v1/leases/<int:lease_id>` | `get_lease` | JWT+Session+Company |
| PUT | `/api/v1/leases/<int:lease_id>` | `update_lease` | JWT+Session+Company |
| DELETE | `/api/v1/leases/<int:lease_id>` | `delete_lease` | JWT+Session+Company |
| POST | `/api/v1/leases/<int:lease_id>/renew` | `renew_lease` | JWT+Session+Company |
| POST | `/api/v1/leases/<int:lease_id>/terminate` | `terminate_lease` | JWT+Session+Company |

## Sales — `quicksol_estate/controllers/sale_api.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| GET | `/api/v1/sales` | `list_sales` | none (`cors='*'`) |
| POST | `/api/v1/sales` | `create_sale` | JWT+Session+Company |
| GET | `/api/v1/sales/<int:sale_id>` | `get_sale` | JWT+Session+Company |
| PUT | `/api/v1/sales/<int:sale_id>` | `update_sale` | JWT+Session+Company |
| POST | `/api/v1/sales/<int:sale_id>/cancel` | `cancel_sale` | JWT+Session+Company |

## Proposals — `quicksol_estate/controllers/proposal_controller.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/proposals` | `create_proposal` | JWT+Session+Company |
| GET | `/api/v1/proposals` | `list_proposals` | JWT+Session+Company |
| GET | `/api/v1/proposals/stats` | `get_proposal_stats` | JWT+Session+Company |
| GET | `/api/v1/proposals/<int:proposal_id>` | `get_proposal` | JWT+Session+Company |
| PUT | `/api/v1/proposals/<int:proposal_id>` | `update_proposal` | JWT+Session+Company |
| DELETE | `/api/v1/proposals/<int:proposal_id>` | `cancel_proposal` | JWT+Session+Company |
| POST | `/api/v1/proposals/<int:proposal_id>/send` | `send_proposal` | JWT+Session+Company |
| POST | `/api/v1/proposals/<int:proposal_id>/accept` | `accept_proposal` | JWT+Session+Company |
| POST | `/api/v1/proposals/<int:proposal_id>/reject` | `reject_proposal` | JWT+Session+Company |
| POST | `/api/v1/proposals/<int:proposal_id>/counter` | `counter_proposal` | JWT+Session+Company |
| GET | `/api/v1/proposals/<int:proposal_id>/queue` | `get_proposal_queue` | JWT+Session+Company |
| POST | `/api/v1/proposals/<int:proposal_id>/attachments` | `upload_attachment` | JWT+Session+Company |

## Credit Checks — `thedevkitchen_estate_credit_check/controllers/credit_check_controller.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/proposals/<int:proposal_id>/credit-checks` | `initiate_credit_check` | JWT+Session+Company |
| GET | `/api/v1/proposals/<int:proposal_id>/credit-checks` | `list_credit_checks` | JWT+Session+Company |
| PATCH | `/api/v1/proposals/<int:proposal_id>/credit-checks/<int:check_id>` | `register_credit_check_result` | JWT+Session+Company |
| GET | `/api/v1/clients/<int:partner_id>/credit-history` | `get_client_credit_history` | JWT+Session+Company (agent-scope enforced, anti-enumeration 404, ADR-008) |

## Service Pipeline ("Atendimentos") — `quicksol_estate/controllers/service_controller.py`, `service_source_controller.py`, `service_tag_controller.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/services` | `create_service` | JWT+Session+Company |
| GET | `/api/v1/services` | `list_services` | JWT+Session+Company |
| GET | `/api/v1/services/summary` | `get_service_summary` | JWT+Session+Company |
| GET | `/api/v1/services/<int:service_id>` | `get_service` | JWT+Session+Company |
| PUT | `/api/v1/services/<int:service_id>` | `update_service` | JWT+Session+Company |
| DELETE | `/api/v1/services/<int:service_id>` | `delete_service` | JWT+Session+Company |
| PATCH | `/api/v1/services/<int:service_id>/stage` | `change_service_stage` | JWT+Session+Company |
| PATCH | `/api/v1/services/<int:service_id>/reassign` | `reassign_service` | JWT+Session+Company |
| GET / POST / PUT / DELETE | `/api/v1/service-sources[/<int:source_id>]` | `list/create/get/update/delete_source` | JWT+Session+Company |
| GET / POST / PUT / DELETE | `/api/v1/service-tags[/<int:tag_id>]` | `list/create/get/update/delete_tag` | JWT+Session+Company |

## Goals & Achievements — `thedevkitchen_estate_goals/controllers/goals_controller.py`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/goals` | `create_goal` | JWT+Session+Company |
| GET | `/api/v1/goals` | `list_goals` | JWT+Session+Company |
| PUT | `/api/v1/goals/<int:goal_id>` | `update_goal` | JWT+Session+Company |
| DELETE | `/api/v1/goals/<int:goal_id>` | `delete_goal` | JWT+Session+Company |
| GET | `/api/v1/goals/report` | `goals_report` | JWT+Session+Company (200-user hard cap) |

## Headless CMS — `thedevkitchen_cms/controllers/*`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST | `/api/v1/cms/pages` | `create_page` | JWT+Session+Company |
| GET | `/api/v1/cms/pages` | `list_pages` | JWT+Session+Company |
| GET | `/api/v1/cms/pages/<int:page_id>` | `get_page` | JWT+Session+Company |
| PUT | `/api/v1/cms/pages/<int:page_id>` | `update_page` | JWT+Session+Company |
| DELETE | `/api/v1/cms/pages/<int:page_id>` | `delete_page` | JWT+Session+Company |
| POST | `/api/v1/cms/pages/<int:page_id>/duplicate` | `duplicate_page` | JWT+Session+Company |
| POST | `/api/v1/cms/media/upload` | `upload_media` | JWT+Session+Company |
| GET | `/api/v1/cms/media` | `list_media` | JWT+Session+Company |
| GET | `/api/v1/cms/media/<int:media_id>` | `get_media` | JWT+Session+Company |
| GET | `/api/v1/cms/media/<int:media_id>/file` | `get_media_file` | JWT+Session+Company |
| DELETE | `/api/v1/cms/media/<int:media_id>` | `delete_media` | JWT+Session+Company |
| POST/GET/PUT/DELETE | `/api/v1/cms/templates[/<int:template_id>]` | `create/list/get/update/delete_template` | JWT+Session+Company |
| GET | `/api/v1/cms/settings` | `get_settings` | JWT+Session+Company |
| PUT | `/api/v1/cms/settings` | `update_settings` | JWT+Session+Company |
| GET | `/api/v1/public/cms/<string:company_slug>/pages/<string:page_slug>` | `get_public_page` | JWT only (headless public route, no Odoo session — designed for Next.js SSR consumption) |

## Observability — `thedevkitchen_observability/controllers/*`

| Method | Route | Handler | Authentication |
|---|---|---|---|
| POST / OPTIONS | `/api/otel/traces` | `proxy_otlp_traces` / `proxy_otlp_traces_preflight` | none (`cors='*'`, OTLP browser-trace proxy) |
| GET | `/api/v1/test-db-trace` | `test_db_tracing` | none |

## Discrepancies / Findings

- Several endpoints intended for internal/authenticated use are registered with `auth='none'` at the Odoo routing level and rely entirely on the `@require_jwt`/`@require_session`/`@require_company` decorators for protection (this is the intended pattern per ADR-011, since Odoo's native `auth='user'` cookie-session model is incompatible with a stateless JWT-first headless API — not a defect, but worth knowing when reasoning about any single route in isolation).
- A handful of `GET` list endpoints (`/api/v1/leads`, `/api/v1/sales`, `/api/v1/tags`) are fully public (`auth='none'`, no auth decorator, `cors='*'`), which is inconsistent with the otherwise-universal triple-decorator convention used across nearly all other endpoints in the same controllers. This is corroborated by `TECHNICAL_DEBIT.md`'s note about hardcoded `cors='*'`; recommend the team confirm whether these specific public list endpoints are intentional (e.g., a public marketing/leads-capture use case) or an oversight.
- No GraphQL or gRPC surface exists in this codebase.
