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

#### 1. **MODULAR ARCHITECTURE**
- Create subfolders for complex functionalities with multiple components
- Example structure: `company/` containing `(models/, views/, tests/, controllers/, data/, security/)`
- Maintain clear separation between MVC layers

#### 2. **MANDATORY LAYERS**
- ✅ **Models**: Field definitions, validations, business methods
- ✅ **Views**: XML forms, lists, search, kanban (following Odoo layout standards)
- ✅ **Controllers**: APIs/endpoints when needed
- ✅ **Tests**: Unit tests for all validations and methods
- ✅ **Security**: User groups, permissions, record rules
- ✅ **Data**: Initial data, demo data, configurations

#### 3. **DATA DIRECTORY STANDARDS**
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

#### 4. **SECURITY DIRECTORY STANDARDS**
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

#### 5. **VALIDATION REQUIREMENTS**
- All required fields must have proper validation
- Implement `@api.constrains` for business rules
- Format validations (email, CNPJ, phone, etc.)
- Clear, translated error messages

#### 6. **INTERFACE STANDARDS**
- **FOLLOW Odoo layout patterns** (don't replicate external designs exactly)
- Use native components: `<form>`, `<tree>`, `<search>`, `<kanban>`
- Apply Odoo CSS classes: `oe_title`, `oe_edit_only`, etc.
- Organize complex forms with tabs: `<notebook><page>`

#### 7. **INTERNATIONALIZATION (i18n)**
- All code in English (variables, methods, comments)
- Create Portuguese translations file
- Translate: labels, help texts, error messages, menu items
- Translate demo data when applicable

#### 8. **DATABASE DESIGN**
- Define fields with correct types
- Create indexes when necessary
- Proper relationships: Many2one, One2many, Many2many
- Consider performance for large data volumes

#### 9. **TESTING REQUIREMENTS**
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
```

### **Implementation Template**

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
- **Project**: Real Estate Management System (Odoo 18.0)
- **Module**: quicksol_estate

---
**Note**: This ADR should be updated when guidelines evolve or new requirements emerge.