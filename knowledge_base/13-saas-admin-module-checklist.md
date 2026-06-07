# KB-013: SaaS Admin Module Checklist — Record Rule Overrides

**Reference**: [ADR-029 — SaaS Admin Channel Separation](../docs/adr/ADR-029-saas-admin-channel-separation.md)  
**Applies to**: Every new Odoo module that adds `ir.rule` records with company isolation

---

## The Rule

> Every new module that introduces `ir.rule` records with a company-filtering domain
> (`company_id in ...`, `company_id = user.company_id.id`, etc.) **MUST** also include a
> corresponding `base.group_system` cross-company override rule.

**Why**: Odoo's OR-union rule evaluation means the `[(1,'=',1)]` rule for `base.group_system`
overrides all narrower rules for that user. Without it, the System Admin is silently locked out
of data from companies other than their own in the Odoo web UI.

---

## Checklist for New Module Authors

When creating a new `thedevkitchen_*` module with record rules:

### 1. Identify company-filtering rules

```bash
# Find all rules with company-based domain in your new module
grep -r "company_id" path/to/your-module/security/*.xml
```

Every model with a company-filtering rule needs a System Admin override.

### 2. Add `base.group_system` override rules

For each affected model, add the canonical override pattern. Place it in a `noupdate="0"` block:

```xml
<!-- Feature 022 / ADR-029: SaaS Admin cross-company override -->
<data noupdate="0">
    <record id="rule_admin_all_{entity}" model="ir.rule">
        <field name="name">System Admin: All {Entity} (Cross-Company)</field>
        <field name="model_id" ref="model_{underscore_model_name}"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[(4, ref('base.group_system'))]"/>
    </record>
</data>
```

### 3. Choose the correct placement strategy

| Existing file structure | Correct placement |
|---|---|
| `<data noupdate="1">` only | Add a NEW `<data noupdate="0">` block **after** the existing block, inside `<odoo>` |
| `<data noupdate="0">` only | Append the override record **inside** the existing `<data>` block |
| Multiple `<data>` blocks | Append inside any existing `noupdate="0"` block, or add a new one |

**Never** add `noupdate="0"` records inside a `noupdate="1"` block.

### 4. Name the override records consistently

Follow this naming pattern for discoverability:

```
rule_admin_all_{entity}
```

Examples:
- `rule_admin_all_properties`
- `rule_admin_all_leases`
- `rule_admin_all_commission_transactions`
- `rule_cms_page_admin_all` (alternative accepted — module-prefixed)

### 5. Verify model XML ID

The `model_id` ref must exactly match the model's XML ID in the `ir.model` table.
Verify by checking the existing `ir.model.access.csv` in your module:

```csv
access_id,name,model_id:id,group_id:id,...
access_foo_owner,Owner: Foo,model_thedevkitchen_foo,...
```

Use `model_thedevkitchen_foo` as the `ref` value.

---

## PR Review Checklist

Before approving a PR that adds a new module with record rules:

- [ ] Every model with a company-filtering `ir.rule` has a corresponding `rule_admin_all_*` record
- [ ] The override record uses `domain_force=[(1, '=', 1)]`
- [ ] The override record is assigned to `base.group_system` via `eval="[(4, ref('base.group_system'))]"`
- [ ] The override record is in a `noupdate="0"` block (never inside `noupdate="1"`)
- [ ] The model XML ID in the `ref` attribute matches the CSV model ID
- [ ] Module upgrade (`-u module_name`) applies the new rules without errors

---

## Anti-Patterns to Avoid

❌ **Putting overrides inside a `noupdate="1"` block** — they will not re-apply on upgrade  
❌ **Using `sudo()` in controllers** to work around the lack of an admin override rule (ADR-011 violation)  
❌ **Skipping the override "temporarily"** — creates an operational blind spot immediately on deployment  
❌ **Using a company-specific domain** (`company_id = 1`) instead of `[(1,'=',1)]`  

---

## Quick Reference

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- existing company-filtering rules — DO NOT MODIFY -->
        <record id="rule_my_model_company" model="ir.rule">
            <field name="domain_force">[('company_id', 'in', company_ids)]</field>
            ...
        </record>
    </data>

    <!-- ADR-029: SaaS Admin cross-company overrides — applied on every upgrade -->
    <data noupdate="0">
        <record id="rule_admin_all_my_model" model="ir.rule">
            <field name="name">System Admin: All My Model (Cross-Company)</field>
            <field name="model_id" ref="model_thedevkitchen_my_model"/>
            <field name="domain_force">[(1, '=', 1)]</field>
            <field name="groups" eval="[(4, ref('base.group_system'))]"/>
        </record>
    </data>
</odoo>
```

---

## Related Entries

- [KB-012 — Deploy New Module](12-deploy-new-module.md)
- [KB-009 — Database Best Practices](09-database-best-practices.md)
- [ADR-029 — SaaS Admin Channel Separation](../docs/adr/ADR-029-saas-admin-channel-separation.md)
