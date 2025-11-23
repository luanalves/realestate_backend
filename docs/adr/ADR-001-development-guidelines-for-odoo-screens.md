# ADR-001: Development Guidelines for Odoo Screens and Features

## Status
**Accepted** - 2025-10-14

## Context

During the development of the Real Estate Management System using Odoo 18.0, we needed to establish consistent guidelines for creating and modifying screens/features. The team required a structured approach that ensures:

1. **Code Quality**: Maintainable, readable, and well-organized code
2. **Architecture Consistency**: Following Odoo best practices and MVC patterns
3. **Internationalization**: Proper i18n support for Portuguese translations
4. **Testing Coverage**: Comprehensive unit tests for all functionality
5. **Security**: Proper access controls and data isolation
6. **Data Management**: Consistent demo data and configuration setup

## Decision

We adopt a comprehensive development prompt that standardizes the creation/modification of Odoo features. This prompt serves as a reference guide for all team members when implementing new functionality.

## Development Guidelines

### **Project Context**
```
Projeto: Sistema de Gestão Imobiliária (Real Estate Management)
Framework: Odoo 18.0
Database: PostgreSQL (realestate)
Diretório de trabalho: 18.0/extra-addons/quicksol_estate/
```

### **Core Development Principles**

#### 1. **DIRECTORY STRUCTURE (CRITICAL)**
⚠️ **IMPORTANT**: DO NOT create subdirectories by functionality!

**CORRECT Structure** (Use this):
```
quicksol_estate/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── property.py
│   ├── agent.py
│   ├── company.py
│   └── tenant.py
├── views/
│   ├── property_views.xml
│   ├── agent_views.xml
│   └── real_estate_menus.xml
├── security/
│   ├── groups.xml
│   ├── ir.model.access.csv
│   └── record_rules.xml
├── data/
│   ├── property_type_data.xml
│   └── company_data.xml
├── tests/
│   ├── __init__.py
│   └── test_property.py
└── i18n/
    └── pt_BR.po
```

**WRONG Structure** (Avoid this):
```
❌ quicksol_estate/
   ├── property/        # DON'T CREATE SUBDIRECTORIES BY FEATURE!
   │   ├── models/
   │   ├── views/
   │   └── data/
   ├── agent/
   │   ├── models/
   │   └── views/
```

**Why?**
- Odoo expects flat structure in module root
- Import system works better with flat structure
- Manifest file references are simpler
- Avoids circular import issues

#### 2. **MANDATORY LAYERS**
- ✅ **Models**: Field definitions, validations, business methods
- ✅ **Views**: XML forms, lists, search, kanban (following Odoo layout standards)
- ✅ **Controllers**: APIs/endpoints when needed
- ✅ **Tests**: Unit tests for all validations and methods
- ✅ **Security**: User groups, permissions, record rules
- ✅ **Data**: Initial data, demo data, configurations

#### 3. **ODOO 18.0 SPECIFIC REQUIREMENTS** ⚠️

##### **Breaking Changes from Odoo 17:**

**A) Views: NO MORE `attrs` attribute**
```xml
<!-- ❌ WRONG (Odoo 17 and earlier) -->
<field name="sale_price" attrs="{'invisible': [('status', '=', 'rented')]}"/>
<field name="status" attrs="{'readonly': [('state', '=', 'sold')]}"/>

<!-- ✅ CORRECT (Odoo 18.0+) -->
<field name="sale_price" invisible="status == 'rented'"/>
<field name="status" readonly="state == 'sold'"/>
```

**B) Views: Use `<list>` instead of `<tree>`**
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

**C) Actions: NO `ref()` in context**
```xml
<!-- ❌ WRONG -->
<record id="action_users" model="ir.actions.act_window">
    <field name="context">{'default_groups_id': ref('group_user')}</field>
</record>

<!-- ✅ CORRECT -->
<record id="action_users" model="ir.actions.act_window">
    <field name="context">{}</field>
</record>
```

**D) Docker: MUST set DB_NAME**
```yaml
# docker-compose.yml
services:
  odoo:
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
      - DB_NAME=realestate  # ✅ REQUIRED for Odoo 18.0
```

#### 4. **MODEL IMPORT ORDER** ⚠️

**CRITICAL**: Import auxiliary/helper models BEFORE main models

```python
# models/__init__.py

# ✅ CORRECT ORDER
from . import property_auxiliary  # Import FIRST (contains PropertyImage, PropertyPurpose)
from . import property            # Import SECOND (uses PropertyImage)
from . import agent
from . import tenant

# ❌ WRONG ORDER (causes "Field does not exist" errors)
from . import property            # Uses PropertyImage but it's not loaded yet!
from . import property_auxiliary  # Loaded too late
```

**Why?** When `property.py` references `PropertyImage`, that model must already be loaded in the registry.

#### 5. **AVOID DUPLICATION** ⚠️

**Single Source of Truth for:**

**A) Security Groups:**
- Keep only ONE security file: `security/groups.xml` OR `security/real_estate_security.xml`
- Choose one naming convention: `group_property_*` OR `group_real_estate_*` and stick to it
- ❌ DON'T create both `property_groups.xml` AND `real_estate_security.xml`

**B) Menus:**
- Keep only ONE main menu file: `views/real_estate_menus.xml`
- ❌ DON'T create separate menu files per model (e.g., `property_menus.xml`, `agent_menus.xml`)
- ❌ DON'T create NEW top-level menus (menu without parent)
- ✅ ALL submenus MUST reference the existing parent menu ID

**CRITICAL**: Always extend the existing "Real Estate" menu, never create a new one!

```xml
<!-- ✅ CORRECT: Extending existing Real Estate menu -->
<odoo>
    <!-- Main menu already exists, don't recreate it! -->
    <!-- Just add submenus that reference it -->
    
    <menuitem id="menu_real_estate_property" 
              name="Properties" 
              parent="menu_real_estate_root"  <!-- Reference existing parent -->
              sequence="10" 
              action="action_property"/>
              
    <menuitem id="menu_real_estate_agent" 
              name="Agents" 
              parent="menu_real_estate_root"  <!-- Same parent -->
              sequence="20" 
              action="action_agent"/>
</odoo>

<!-- ❌ WRONG: Creating a new top-level menu -->
<odoo>
    <!-- DON'T DO THIS! -->
    <menuitem id="menu_property_management" 
              name="Property Management"   <!-- New top-level menu! -->
              sequence="15"/>
    
    <menuitem id="menu_properties" 
              name="Properties" 
              parent="menu_property_management"  <!-- Wrong parent -->
              action="action_property"/>
</odoo>
```

**Why?**
- Keeps navigation consistent
- Avoids menu duplication
- All features in one place
- Easier for users to find functionality

**C) Actions:**
- One action per view: `action_property`, `action_agent`, etc.
- Menu references must match action IDs exactly
- Update menu when changing action ID

#### 6. **DATA FILE MANAGEMENT**

**A) Use `noupdate="1"` for demo data:**
```xml
<odoo>
    <data noupdate="1">
        <record id="property_type_apartment" model="real.estate.property.type">
            <field name="name">Apartment</field>
        </record>
    </data>
</odoo>
```

**B) Handle existing data:**
- Check database for existing records before loading
- Use `<data noupdate="1">` to prevent duplicates
- If data exists, temporarily disable in manifest:
```python
'data': [
    # 'data/property_type_data.xml',  # Temporarily disabled - duplicate data
],
```

#### 8. **DATA DIRECTORY STANDARDS**
- Create realistic and useful demo data
- Include initial configuration data (types, categories, etc.)
- Follow naming pattern: `[model_name]_data.xml`
- Examples: `company_data.xml`, `property_type_data.xml`
- Use proper references: `ref="base.br"` for Brazil country
- Include varied data for comprehensive testing

**Example Data Structure:**
```xml
<record id="company_quicksol_real_estate" model="thedevkitchen.estate.company">
    <field name="name">Quicksol Real Estate</field>
    <field name="cnpj">12.345.678/0001-90</field>
    <field name="country_id" ref="base.br"/>
</record>
```

#### 9. **SECURITY DIRECTORY STANDARDS**
- Define user groups with appropriate access levels
- Create record rules for multi-company data isolation
- Configure CRUD permissions per group
- Maintain `ir.model.access.csv` with all permissions

**Example Security Structure:**
```xml
<!-- User Groups -->
<record id="group_real_estate_user" model="res.groups">
    <field name="name">Real Estate User</field>
    <field name="category_id" ref="category_real_estate"/>
</record>

<!-- Access Rules -->
<record id="rule_property_multi_company" model="ir.rule">
    <field name="name">Property Multi-Company Rule</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">['|', ('company_ids', '=', False), ('company_ids', 'in', user.company_ids.ids)]</field>
</record>
```

#### 10. **VALIDATION REQUIREMENTS**
- All required fields must have proper validation
- Implement `@api.constrains` for business rules
- Format validations (email, CNPJ, phone, etc.)
- Clear, translated error messages

#### 11. **INTERFACE STANDARDS**
- **FOLLOW Odoo layout patterns** (don't replicate external designs exactly)
- Use native components: `<form>`, `<list>`, `<search>`, `<kanban>`
- Apply Odoo CSS classes: `oe_title`, `oe_edit_only`, etc.
- Organize complex forms with tabs: `<notebook><page>`

#### 12. **INTERNATIONALIZATION (i18n)**
- All code in English (variables, methods, comments)
- Create Portuguese translations file
- Translate: labels, help texts, error messages, menu items
- Translate demo data when applicable

#### 13. **DATABASE DESIGN**
- Define fields with correct types
- Create indexes when necessary
- Proper relationships: Many2one, One2many, Many2many
- Consider performance for large data volumes

#### 14. **TESTING REQUIREMENTS**
- Test creation, editing, validations
- Test error scenarios
- Test demo data loading
- Test permissions and access rules
- Mock external dependencies
- Minimum 80% test coverage

### **File Structure Standard**

```
[module]/
├── [functionality]/
│   ├── models/
│   │   ├── __init__.py
│   │   └── [model_name].py
│   ├── views/
│   │   ├── [model_name]_views.xml
│   │   └── [model_name]_menus.xml
│   ├── controllers/
│   │   ├── __init__.py
│   │   └── [controller_name].py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_[model_name].py
│   │   └── base_[model_name]_test.py
│   ├── security/
│   │   ├── [model_name]_groups.xml
│   │   ├── [model_name]_rules.xml
│   │   └── ir.model.access.csv
│   ├── data/
│   │   ├── [model_name]_data.xml
│   │   ├── [model_name]_demo.xml
│   │   └── [config_name]_config.xml
│   └── i18n/
│       └── pt_BR.po
```

### **Manifest Update Standards**

Include new files in correct order:
```python
'data': [
    'security/groups.xml',
    'security/ir.model.access.csv',
    'security/record_rules.xml',
    'data/property_type_data.xml',
    'data/company_data.xml',
    'views/model_views.xml',
    'views/menus.xml',
],
'demo': [
    'data/demo_users.xml',
],
```

### **Development Workflow**

#### Standard Commands:
```bash
# Navigate to working directory
cd 18.0

# Update module (includes new data and security)
docker compose exec odoo odoo -u quicksol_estate -d realestate --stop-after-init

# Run tests including data
docker compose exec odoo odoo --test-tags quicksol_estate -d realestate --stop-after-init

# Verify loaded data
docker compose exec odoo odoo shell -d realestate
# >>> env['thedevkitchen.estate.company'].search([])

# Force restart after updates
docker compose restart odoo

# Check logs for errors
docker compose logs -f odoo --tail=50
```

### **Lessons Learned from Real Implementation** 🎓

#### **Problem 1: Wrong Directory Structure**
**Issue**: Created `quicksol_estate/property/models/` subdirectory
**Error**: Import failures, models not loading
**Solution**: Use flat structure - all models in `quicksol_estate/models/`
**Learning**: Odoo requires flat module structure, not nested by feature

#### **Problem 2: Odoo 18.0 `attrs` Deprecation**
**Issue**: Used `attrs={'invisible': [...]}`  
**Error**: `Since 17.0, the 'attrs' and 'states' attributes are no longer used`
**Solution**: Use inline modifiers: `invisible="condition"`
**Learning**: Always check Odoo version changelog for breaking changes

#### **Problem 3: Using `<tree>` instead of `<list>`**
**Issue**: Views defined with `<tree>` tag
**Error**: Deprecation warnings
**Solution**: Replace all `<tree>` with `<list>` in Odoo 18.0
**Learning**: View type names changed in Odoo 18.0

#### **Problem 4: Wrong Action References in Menus**
**Issue**: Menu references `action_property` but action ID is `action_property_enhanced`
**Error**: `External ID not found: quicksol_estate.action_property`
**Solution**: Synchronize menu action references with actual action IDs
**Learning**: Keep ID naming consistent and update all references

#### **Problem 5: Duplicate Security Groups**
**Issue**: Both `real_estate_security.xml` and `property_groups.xml` with different group names
**Error**: Broken references, inconsistent permissions
**Solution**: Keep only ONE security file, use consistent naming
**Learning**: Single source of truth for security definitions

#### **Problem 6: Duplicate Menu Files & Creating New Top-Level Menus**
**Issue**: Both `real_estate_menus.xml` and `property_menus.xml` creating menus, plus creating new top-level menu instead of extending existing
**Error**: 
- Duplicate menus in navigation
- Multiple "Real Estate" sections
- Navigation confusion for users
**Solution**: 
- Consolidate into single menu file (`real_estate_menus.xml`)
- Always use `parent="menu_real_estate_root"` for submenus
- Never create new top-level menus without parent
**Learning**: 
- One main menu file per module with all submenus
- **CRITICAL**: Always extend existing menu structure, never create parallel menus
- All features must be under the same parent menu for consistency

#### **Problem 7: Missing DB_NAME in Docker**
**Issue**: Docker not configured with database name
**Error**: `FATAL: database "odoo" does not exist`
**Solution**: Add `DB_NAME=realestate` to docker-compose.yml environment
**Learning**: Odoo 18.0 requires explicit database configuration

#### **Problem 8: Wrong Model Import Order**
**Issue**: Imported `property.py` before `property_auxiliary.py`
**Error**: `Field 'sequence' does not exist` (PropertyImage not loaded)
**Solution**: Import auxiliary models BEFORE models that use them
**Learning**: Python module import order matters for model registry

#### **Problem 9: Using `ref()` in Action Context**
**Issue**: Action context with `ref('quicksol_estate.group_user')`
**Error**: `Name 'ref' is not defined`
**Solution**: Remove `ref()` from action contexts (only works in XML)
**Learning**: `ref()` is XML-only, doesn't work in client-side contexts

#### **Problem 10: Duplicate Data with `noupdate="1"`**
**Issue**: Reloading data that already exists in database
**Error**: `duplicate key value violates unique constraint`
**Solution**: Use `noupdate="1"` or temporarily disable in manifest
**Learning**: Check database before loading demo data, use proper data flags

#### **Problem 11: Unwanted Menu Items**
**Issue**: Extra "Users" submenu from `res_users_views.xml`
**Error**: Menu clutter, not in original design
**Solution**: Remove unnecessary `<menuitem>` definitions
**Learning**: Only create menus that are explicitly required

### **Quick Troubleshooting Checklist** ✅

Before committing code, verify:
- [ ] Flat directory structure (no feature subdirectories)
- [ ] No `attrs` in views (use inline modifiers)
- [ ] All `<tree>` changed to `<list>`
- [ ] Menu action references match action IDs
- [ ] Only ONE security groups file
- [ ] Only ONE main menu file
- [ ] **All submenus use parent="menu_real_estate_root" (never create new top-level menus)**
- [ ] `DB_NAME` set in docker-compose.yml
- [ ] Auxiliary models imported first in `__init__.py`
- [ ] No `ref()` in action contexts
- [ ] Data files use `noupdate="1"` when appropriate
- [ ] All XML IDs are unique and consistent
- [ ] Tested with `odoo -u module_name --stop-after-init`

## Consequences

When implementing new features, follow this response structure:

```
## 🎯 Analysis of Print/HTML
[Description of identified elements]

## 🏗️ Proposed Architecture
[Complete folder structure and organization]

## 💾 Database Models  
[Field definitions and relationships]

## 📊 Demo Data and Configuration
[XML files with realistic data]

## 🔒 Security and Access Control
[Groups, permissions, record rules]

## 🖼️ Views and Interface
[XML layouts following Odoo standards]

## 🧪 Unit Tests
[Test cases for models, data and security]

## 🌐 Internationalization
[Complete PT-BR translation files]

## ⚙️ Deployment Commands
[Steps to apply all changes]
```

## Consequences

### **Positive:**
- **Consistency**: All team members follow the same development patterns
- **Quality**: Comprehensive testing and validation requirements ensure robust code
- **Maintainability**: Clear organization and documentation standards
- **Scalability**: Modular architecture supports project growth
- **User Experience**: Proper i18n support for Portuguese users
- **Security**: Standardized access control implementation

### **Negative:**
- **Initial Learning Curve**: Team members need time to learn the comprehensive guidelines
- **Development Time**: Following all guidelines may initially slow development
- **Overhead**: More files and structure to maintain

### **Mitigation:**
- Provide training sessions on the guidelines
- Create code templates and examples
- Regular code reviews to ensure adherence
- Gradual implementation allowing team adaptation

## References

- [Odoo Official Documentation](https://www.odoo.com/documentation/18.0/)
- [Odoo Development Guidelines](https://www.odoo.com/documentation/18.0/developer/reference/guidelines.html)
- [Python PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [ADR Template by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)

## Author
- **Created by**: Development Team
- **Date**: 2025-10-14
- **Last Updated**: 2025-10-14
- **Project**: Real Estate Management System (Odoo 18.0)
- **Module**: quicksol_estate

## Revision History
- **2025-10-14 (v1.0)**: Initial ADR creation
- **2025-10-14 (v2.0)**: Added critical lessons learned from implementation:
  - Fixed directory structure guidelines (flat structure required)
  - Added Odoo 18.0 breaking changes section
  - Added model import order requirements
  - Added duplication prevention guidelines
  - Added troubleshooting checklist
  - Added 11 real-world problems and solutions
- **2025-10-14 (v2.1)**: Enhanced menu guidelines:
  - **CRITICAL**: Never create new top-level menus
  - Always extend existing "Real Estate" menu with parent reference
  - Added detailed examples of correct vs wrong menu structure
  - Updated Problem #6 to include top-level menu creation issue
  - Added menu parent verification to checklist

---
**Note**: This ADR is a living document and should be updated when guidelines evolve or new requirements emerge. All team members should review changes and provide feedback.