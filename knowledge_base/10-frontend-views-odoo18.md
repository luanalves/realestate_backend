# Frontend & Views Guidelines - Odoo 18.0

## Overview

Este documento define as boas práticas e padrões obrigatórios para desenvolvimento de interfaces (views) no Odoo 18.0. Todas as views devem seguir estas diretrizes para garantir compatibilidade, performance e manutenibilidade.

## Table of Contents

1. [View Types & Best Practices](#view-types--best-practices)
2. [Odoo 18.0 Breaking Changes](#odoo-180-breaking-changes)
3. [List Views (tree)](#list-views-tree)
4. [Form Views](#form-views)
5. [Search Views](#search-views)
6. [Kanban Views](#kanban-views)
7. [Common Patterns](#common-patterns)
8. [Frontend Validation](#frontend-validation)
9. [Testing Requirements](#testing-requirements)

---

## View Types & Best Practices

### Standard View Naming Convention

```xml
<!-- Pattern: view_[model]_[type] -->
<record id="view_commission_rule_list" model="ir.ui.view">
    <field name="name">real.estate.commission.rule.list</field>
    <field name="model">real.estate.commission.rule</field>
    ...
</record>
```

**Types:**
- `list` - List/Tree view
- `form` - Form view
- `search` - Search filters
- `kanban` - Kanban board
- `calendar` - Calendar view
- `pivot` - Pivot table
- `graph` - Chart/Graph

---

## Odoo 18.0 Breaking Changes

### 🚨 CRITICAL: Changes from Odoo 17

#### 1. NO MORE `attrs` attribute ❌

```xml
<!-- ❌ WRONG (Odoo 17 and earlier) -->
<field name="sale_price" attrs="{'invisible': [('status', '=', 'rented')]}"/>
<field name="status" attrs="{'readonly': [('state', '=', 'sold')]}"/>

<!-- ✅ CORRECT (Odoo 18.0+) -->
<field name="sale_price" invisible="status == 'rented'"/>
<field name="status" readonly="state == 'sold'"/>
```

#### 2. Use `<list>` instead of `<tree>` ⚠️

```xml
<!-- ❌ WRONG -->
<record id="view_property_tree" model="ir.ui.view">
    <field name="arch" type="xml">
        <tree>
            <field name="name"/>
        </tree>
    </field>
</record>

<!-- ✅ CORRECT -->
<record id="view_property_list" model="ir.ui.view">
    <field name="arch" type="xml">
        <list>
            <field name="name"/>
        </list>
    </field>
</record>
```

#### 3. NO `ref()` in action context ❌

```xml
<!-- ❌ WRONG -->
<record id="action_users" model="ir.actions.act_window">
    <field name="context">{'default_groups_id': ref('group_user')}</field>
</record>

<!-- ✅ CORRECT - Use XML ID directly or avoid ref() -->
<record id="action_users" model="ir.actions.act_window">
    <field name="context">{}</field>
</record>
```

---

## List Views (tree)

### Basic Structure

```xml
<record id="view_entity_list" model="ir.ui.view">
    <field name="name">entity.model.list</field>
    <field name="model">entity.model</field>
    <field name="arch" type="xml">
        <list string="Entities" decoration-muted="not active">
            <field name="name"/>
            <field name="status"/>
            <field name="active"/>
        </list>
    </field>
</record>
```

### Column Visibility: `optional` vs `column_invisible`

#### 🚨 CRITICAL RULE: DO NOT use `column_invisible` with Python expressions

**Problem:** Python expressions in `column_invisible` are **NOT evaluated in the frontend**, causing runtime errors like:

```
OwlError: Can not evaluate python expression: (bool(structure_type != 'percentage'))
Error: Name 'structure_type' is not defined
```

#### ❌ WRONG - Causes Frontend Errors

```xml
<list string="Commission Rules">
    <field name="structure_type"/>
    <!-- ❌ This WILL FAIL - Python expression not available in frontend -->
    <field name="percentage" column_invisible="structure_type != 'percentage'"/>
    <field name="fixed_amount" column_invisible="structure_type != 'fixed'"/>
</list>
```

#### ✅ CORRECT - Use `optional` attribute

```xml
<list string="Commission Rules">
    <field name="structure_type"/>
    <!-- ✅ Users can show/hide columns via UI -->
    <field name="percentage" optional="show"/>
    <field name="fixed_amount" optional="show"/>
    <field name="description" optional="hide"/>
</list>
```

**`optional` values:**
- `show` - Column visible by default, user can hide
- `hide` - Column hidden by default, user can show
- (omit attribute) - Column always visible, user cannot hide

#### ✅ ALTERNATIVE - Use computed field for complex logic

If conditional visibility is **critical** for business logic:

```python
# In model
@api.depends('structure_type')
def _compute_show_percentage(self):
    for record in self:
        record.show_percentage = record.structure_type == 'percentage'

show_percentage = fields.Boolean(compute='_compute_show_percentage', store=False)
```

```xml
<list string="Commission Rules">
    <field name="show_percentage" column_invisible="1"/>  <!-- Hidden helper field -->
    <field name="percentage" column_invisible="not show_percentage"/>
</list>
```

### Decorations (Row Colors)

```xml
<list string="Properties" 
      decoration-danger="state == 'cancelled'"
      decoration-success="state == 'sold'"
      decoration-muted="not active"
      decoration-warning="urgent">
    <field name="state" column_invisible="1"/>  <!-- Required for decoration -->
    <field name="active" column_invisible="1"/>
    <field name="urgent" column_invisible="1"/>
    <field name="name"/>
</list>
```

**Available decorations:**
- `decoration-bf` - Bold font
- `decoration-it` - Italic font
- `decoration-danger` - Red text
- `decoration-info` - Blue text
- `decoration-muted` - Gray text
- `decoration-primary` - Primary color
- `decoration-success` - Green text
- `decoration-warning` - Orange text

### Editable Lists

```xml
<list string="Order Lines" editable="bottom">
    <field name="product_id"/>
    <field name="quantity"/>
    <field name="price"/>
</list>
```

**Options:**
- `editable="top"` - New row at top
- `editable="bottom"` - New row at bottom
- (omit) - Non-editable list

---

## Form Views

### Basic Structure with Groups

```xml
<record id="view_entity_form" model="ir.ui.view">
    <field name="name">entity.model.form</field>
    <field name="model">entity.model</field>
    <field name="arch" type="xml">
        <form string="Entity">
            <header>
                <button name="action_confirm" string="Confirm" type="object" class="oe_highlight"/>
                <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,done"/>
            </header>
            <sheet>
                <group>
                    <group name="left" string="Basic Info">
                        <field name="name"/>
                        <field name="date"/>
                    </group>
                    <group name="right" string="Details">
                        <field name="status"/>
                        <field name="amount"/>
                    </group>
                </group>
            </sheet>
        </form>
    </field>
</record>
```

### Conditional Field Visibility

```xml
<!-- ✅ CORRECT - Use invisible with Python expression -->
<form>
    <group>
        <field name="structure_type"/>
        <field name="percentage" 
               invisible="structure_type != 'percentage'" 
               required="structure_type == 'percentage'"/>
        <field name="fixed_amount" 
               invisible="structure_type != 'fixed'" 
               required="structure_type == 'fixed'"/>
    </group>
</form>
```

**Works in form views because:**
- Form views evaluate expressions in the frontend context
- The field values are available in the same form scope

### Readonly and Required Conditions

```xml
<field name="sale_price" readonly="state == 'sold'"/>
<field name="agent_id" required="status == 'active'"/>
<field name="notes" invisible="internal_only"/>
```

---

## Search Views

### Filters and Group By

```xml
<record id="view_entity_search" model="ir.ui.view">
    <field name="name">entity.model.search</field>
    <field name="model">entity.model</field>
    <field name="arch" type="xml">
        <search string="Search Entities">
            <!-- Searchable fields -->
            <field name="name"/>
            <field name="agent_id"/>
            
            <!-- Filters -->
            <filter string="Active" name="active" domain="[('active', '=', True)]"/>
            <filter string="Archived" name="archived" domain="[('active', '=', False)]"/>
            
            <separator/>
            
            <!-- Date filters -->
            <filter string="This Month" name="this_month" 
                    domain="[('date', '&gt;=', context_today().strftime('%Y-%m-01'))]"/>
            
            <!-- Group By -->
            <group expand="0" string="Group By">
                <filter string="Agent" name="group_agent" context="{'group_by': 'agent_id'}"/>
                <filter string="Status" name="group_status" context="{'group_by': 'status'}"/>
            </group>
        </search>
    </field>
</record>
```

---

## Kanban Views

### Basic Kanban

```xml
<record id="view_entity_kanban" model="ir.ui.view">
    <field name="name">entity.model.kanban</field>
    <field name="model">entity.model</field>
    <field name="arch" type="xml">
        <kanban default_group_by="stage_id">
            <field name="name"/>
            <field name="stage_id"/>
            <templates>
                <t t-name="card">
                    <div class="oe_kanban_card">
                        <div class="oe_kanban_content">
                            <field name="name"/>
                            <div>
                                <field name="agent_id"/>
                            </div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

**Note:** Odoo 18.0 prefers `<t t-name="card">` over the deprecated `t-name="kanban-box"`.

---

## Common Patterns

### 1. Multi-Tenancy Display

Always include company indicator when multi-tenant:

```xml
<list>
    <field name="company_id" groups="base.group_multi_company"/>
</list>
```

### 2. Active/Archive Pattern

```xml
<form>
    <header>
        <field name="active" widget="boolean_button" 
               options="{'terminology': 'active'}"/>
    </header>
</form>

<list decoration-muted="not active">
    <field name="active"/>
</list>
```

### 3. Chatter (Messages & Activities)

```xml
<form>
    <sheet>
        <!-- Form content -->
    </sheet>
    
    <!-- Chatter at bottom -->
    <div class="oe_chatter">
        <field name="message_follower_ids"/>
        <field name="activity_ids"/>
        <field name="message_ids"/>
    </div>
</form>
```

### 4. Action Buttons

```xml
<header>
    <button name="action_confirm" string="Confirm" 
            type="object" 
            class="oe_highlight"
            invisible="state != 'draft'"/>
    <button name="action_cancel" string="Cancel" 
            type="object"
            confirm="Are you sure you want to cancel?"/>
    <field name="state" widget="statusbar" 
           statusbar_visible="draft,confirmed,done"/>
</header>
```

---

## Frontend Validation

### MANDATORY Validation Checklist

Before committing any view changes, **ALWAYS** verify:

#### ✅ Browser Console Check

```bash
# 1. Start Odoo
docker compose up -d

# 2. Open browser DevTools (F12)
# 3. Navigate to your new menu/view
# 4. Check Console tab for errors

# ❌ Common errors to watch for:
# - "Can not evaluate python expression"
# - "Name 'field_name' is not defined"
# - "OwlError"
# - Any JavaScript errors
```

#### ✅ Manual View Testing

```markdown
**Test Procedure:**

1. [ ] Menu loads without "Oops!" error dialog
2. [ ] List view displays correctly
3. [ ] All columns render (no missing headers)
4. [ ] Form view opens without errors
5. [ ] Search filters work
6. [ ] Create new record works
7. [ ] Edit existing record works
8. [ ] No JavaScript console errors
```

#### ✅ Multi-Browser Testing

Test on:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if on macOS)

---

## Testing Requirements

### Unit Tests (Python)

**Not applicable for views.** Views don't have unit tests.

### Integration Tests (Python)

Test view definitions exist and are valid:

```python
# tests/test_views.py
from odoo.tests.common import TransactionCase

class TestCommissionRuleViews(TransactionCase):
    
    def test_list_view_defined(self):
        """Verify list view is properly defined"""
        view = self.env.ref('quicksol_estate.view_commission_rule_list')
        self.assertTrue(view.exists())
        self.assertEqual(view.model, 'real.estate.commission.rule')
    
    def test_form_view_defined(self):
        """Verify form view is properly defined"""
        view = self.env.ref('quicksol_estate.view_commission_rule_form')
        self.assertTrue(view.exists())
```

### E2E Tests (Cypress) - MANDATORY ⚠️

**Every new view MUST have E2E test verifying:**

```javascript
// cypress/e2e/views/commission_rules.cy.js
describe('Commission Rules Views', () => {
  before(() => {
    // Setup: Login
    cy.login('admin', 'admin')
  })

  describe('List View', () => {
    it('should load commission rules menu without errors', () => {
      cy.visit('/web#action=quicksol_estate.action_commission_rule')
      
      // ✅ Critical: No error dialog
      cy.contains('Oops!').should('not.exist')
      
      // ✅ List view loads
      cy.get('.o_list_view').should('be.visible')
      
      // ✅ Expected columns visible
      cy.contains('th', 'Agent').should('be.visible')
      cy.contains('th', 'Transaction Type').should('be.visible')
    })

    it('should display commission rules data', () => {
      cy.visit('/web#action=quicksol_estate.action_commission_rule')
      
      // Verify data loads
      cy.get('.o_list_view tbody tr').should('have.length.greaterThan', 0)
    })
  })

  describe('Form View', () => {
    it('should open form view without errors', () => {
      cy.visit('/web#action=quicksol_estate.action_commission_rule')
      
      // Click first record
      cy.get('.o_list_view tbody tr').first().click()
      
      // Form loads
      cy.get('.o_form_view').should('be.visible')
      cy.contains('Oops!').should('not.exist')
    })

    it('should show conditional fields correctly', () => {
      cy.visit('/web#action=quicksol_estate.action_commission_rule')
      cy.get('.o_list_view tbody tr').first().click()
      
      // Select percentage type
      cy.get('[name="structure_type"]').select('percentage')
      cy.get('[name="percentage"]').should('be.visible')
      cy.get('[name="fixed_amount"]').should('not.be.visible')
      
      // Select fixed type
      cy.get('[name="structure_type"]').select('fixed')
      cy.get('[name="percentage"]').should('not.be.visible')
      cy.get('[name="fixed_amount"]').should('be.visible')
    })
  })

  describe('Search View', () => {
    it('should filter results correctly', () => {
      cy.visit('/web#action=quicksol_estate.action_commission_rule')
      
      // Apply filter
      cy.get('.o_searchview_input').type('percentage{enter}')
      
      // Results filtered
      cy.get('.o_list_view tbody tr').should('have.length.lessThan', 10)
    })
  })
})
```

### E2E Test Naming Convention

```
cypress/e2e/views/[model_name].cy.js
cypress/e2e/views/[feature_name]_[view_type].cy.js
```

**Examples:**
- `cypress/e2e/views/commission_rules.cy.js`
- `cypress/e2e/views/properties_kanban.cy.js`
- `cypress/e2e/views/leads_list.cy.js`

---

## Error Prevention Checklist

### Before Committing View Code

```markdown
## View Development Checklist

### Development Phase
- [ ] Used `<list>` instead of `<tree>`
- [ ] Used `invisible="expression"` instead of `attrs`
- [ ] Used `optional="show|hide"` for column visibility
- [ ] NO `column_invisible` with Python expressions
- [ ] All decoration fields included in view (column_invisible="1")
- [ ] Multi-tenancy field included: `company_id`
- [ ] Active/Archive pattern implemented correctly

### Testing Phase
- [ ] Manual test: Menu loads without "Oops!" error
- [ ] Manual test: List view displays correctly
- [ ] Manual test: Form view opens and saves
- [ ] Browser console: No JavaScript errors
- [ ] Cypress E2E test created and passing
- [ ] Test covers: view loading, data display, interactions

### Code Review Phase
- [ ] View follows naming conventions
- [ ] XML is properly formatted
- [ ] Comments explain complex logic
- [ ] Documentation updated (if new patterns)
```

---

## Quick Reference

### View Attributes Summary

| Attribute | Usage | Odoo Version | Notes |
|-----------|-------|--------------|-------|
| `attrs` | ❌ Deprecated | Odoo ≤17 | Use direct attributes instead |
| `invisible` | ✅ Form views | Odoo 18+ | Boolean expression |
| `readonly` | ✅ All views | All | Boolean expression |
| `required` | ✅ All views | All | Boolean expression |
| `column_invisible` | ⚠️ Limited | All | Only static boolean or computed field |
| `optional` | ✅ List views | Odoo 14+ | `show` or `hide` |

### When to Use What

```python
# List View Column Visibility
optional="show"           # ✅ Best: User-controlled, no errors
optional="hide"           # ✅ Good: Hidden by default, user can show
column_invisible="1"      # ✅ OK: Permanently hidden helper field
column_invisible="field"  # ⚠️ Limited: Only with boolean computed field
column_invisible="expr"   # ❌ NEVER: Causes frontend errors

# Form View Field Visibility
invisible="expression"    # ✅ Perfect: Evaluated in form context
readonly="expression"     # ✅ Perfect: Dynamic readonly state
required="expression"     # ✅ Perfect: Dynamic required validation
```

---

## Resources

### Internal Documentation
- [ADR-001: Development Guidelines for Odoo Screens](../docs/adr/ADR-001-development-guidelines-for-odoo-screens.md)
- [04-xml-guidelines.md](04-xml-guidelines.md)
- [ADR-003: Mandatory Test Coverage](../docs/adr/ADR-003-mandatory-test-coverage.md)

### External References
- [Odoo 18.0 Views Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/views.html)
- [Odoo 18.0 Migration Guide](https://www.odoo.com/documentation/18.0/developer/howtos/upgrade_scripts.html)

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-08 | Initial document creation with Odoo 18.0 patterns |

---

**Last Updated:** 2026-02-08  
**Maintainer:** DevKitchen Team  
**Status:** Active
