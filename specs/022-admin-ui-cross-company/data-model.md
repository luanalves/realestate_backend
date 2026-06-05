# Data Model: Admin UI — Cross-Company Access for System Admin

**Feature**: 022-admin-ui-cross-company  
**Date**: 2026-06-03

## No New Entities

This feature introduces **no new Odoo models** and **no database schema changes**. All changes are either:
- Additions to existing `ir.rule` data (record rules — rows in the `ir_rule` table, managed by Odoo module upgrade)
- One Python controller code change
- Documentation files

---

## Affected Models (by record rule override)

The following models gain a new `ir.rule` record assigned to `base.group_system` with `domain_force=[(1,'=',1)]`. This is purely data configuration — no model field changes.

### Module: `quicksol_estate`

| Model (technical name) | XML id for override | Ref in CSV |
|---|---|---|
| `real.estate.property` | `rule_admin_all_properties` | `model_real_estate_property` |
| `real.estate.agent` | `rule_admin_all_agents` | `model_real_estate_agent` |
| `real.estate.lease` | `rule_admin_all_leases` | `model_real_estate_lease` |
| `real.estate.sale` | `rule_admin_all_sales` | `model_real_estate_sale` |
| `real.estate.agent.property.assignment` | `rule_admin_all_assignments` | `model_real_estate_agent_property_assignment` |
| `real.estate.commission.rule` | `rule_admin_all_commission_rules` | `model_real_estate_commission_rule` |
| `real.estate.commission.transaction` | `rule_admin_all_commission_transactions` | `model_real_estate_commission_transaction` |
| `real.estate.lease.renewal.history` | `rule_admin_all_lease_renewal_history` | `model_real_estate_lease_renewal_history` |
| `thedevkitchen.estate.profile` | `rule_admin_all_profiles` | `model_thedevkitchen_estate_profile` |
| `real.estate.proposal` | `rule_proposal_admin_all` | `model_real_estate_proposal` |
| `real.estate.service` | `rule_service_admin_all` | `model_real_estate_service` |
| `real.estate.service.tag` | `rule_service_tag_admin_all` | `model_real_estate_service_tag` |
| `real.estate.service.source` | `rule_service_source_admin_all` | `model_real_estate_service_source` |
| `thedevkitchen.service.settings` | `rule_service_settings_admin_all` | `model_thedevkitchen_service_settings` |

### Module: `thedevkitchen_cms`

| Model (technical name) | XML id for override |
|---|---|
| `thedevkitchen.cms.page` | `rule_cms_page_admin_all` |
| `thedevkitchen.cms.media` | `rule_cms_media_admin_all` |
| `thedevkitchen.cms.settings` | `rule_cms_settings_admin_all` |

### Module: `thedevkitchen_estate_goals`

| Model (technical name) | XML id for override |
|---|---|
| `thedevkitchen.estate.goal` | `rule_estate_goal_admin_all` |

### Module: `thedevkitchen_estate_credit_check`

| Model (technical name) | XML id for override |
|---|---|
| `thedevkitchen.estate.credit.check` | `rule_credit_check_admin_all` |

### Module: `thedevkitchen_user_onboarding`

| Model (technical name) | XML id for override |
|---|---|
| `thedevkitchen.password.token` | `rule_password_token_admin_all` |

---

## Record Rule Pattern (canonical)

```xml
<record id="rule_admin_all_{entity}" model="ir.rule">
    <field name="name">System Admin: All {Entity} (Cross-Company)</field>
    <field name="model_id" ref="model_{underscore_name}"/>
    <field name="domain_force">[(1, '=', 1)]</field>
    <field name="groups" eval="[(4, ref('base.group_system'))]"/>
</record>
```

**Key semantics**:
- `domain_force=[(1,'=',1)]`: always-true domain — returns all records regardless of company
- `groups=[(4, ref('base.group_system'))]`: rule only applies to users in `base.group_system`
- Odoo OR-union: this rule combined with any narrower rule resolves to "see everything" for System Admin

---

## Affected Behaviors (not model fields)

### `res.users` — login endpoint guard

The `login()` method in `user_auth_controller.py` will evaluate `user.has_group('base.group_system')` and return HTTP 401 + audit log if true. This is **controller logic only** — the `res.users` model is unchanged.

### `ir.ui.menu` — `menu_real_estate_lead`

The `groups` attribute gains `base.group_system`. This is an XML data update — no model change.
