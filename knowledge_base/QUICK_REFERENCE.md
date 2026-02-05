# Quick Reference - Referência Rápida

## 🚀 Início Rápido

| Preciso de | Consultar |
|------------|-----------|
| Estrutura de diretórios | [Module Structure](01-module-structure.md) |
| Como nomear arquivos | [File Naming](02-file-naming-conventions.md) |
| Padrões Python | [Python Guidelines](03-python-coding-guidelines.md) |
| Padrões XML | [XML Guidelines](04-xml-guidelines.md) |
| Padrões JavaScript | [JavaScript Guidelines](05-javascript-guidelines.md) |
| Padrões CSS/SCSS | [CSS/SCSS Guidelines](06-css-scss-guidelines.md) |
| Como escrever código Odoo | [Programming in Odoo](07-programming-in-odoo.md) |
| Nomenclatura de variáveis/métodos | [Symbols & Conventions](08-symbols-conventions.md) |

## 📋 Checklist de Novo Módulo

### 1. Estrutura Básica
```
my_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── my_model.py
├── views/
│   └── my_model_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── my_module_groups.xml
└── data/
    └── my_model_data.xml
```

### 2. Nomenclatura
- [ ] Módulo: `thedevkitchen_<name>` ou `<company>_<name>`
- [ ] Modelo: `thedevkitchen.<category>.<entity>` (singular)
- [ ] Arquivos: `[a-z0-9_]` apenas

### 3. Python
- [ ] Imports organizados (stdlib, odoo, addons)
- [ ] Classes em PascalCase
- [ ] Variáveis em underscore_lowercase
- [ ] Docstrings em métodos públicos

### 4. XML
- [ ] IDs seguem padrão: `<model>_<type>`
- [ ] Views: `<model>_view_<type>`
- [ ] Actions: `<model>_action`
- [ ] Menus: `<model>_menu`

### 5. Segurança
- [ ] `ir.model.access.csv` criado
- [ ] Grupos definidos em `<module>_groups.xml`
- [ ] Record rules em `<model>_security.xml`

## 🎯 Padrões Mais Usados

### Model Declaration
```python
class MyModel(models.Model):
    _name = 'my.module.model'
    _description = 'Model Description'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    line_ids = fields.One2many('my.module.line', 'parent_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
```

### View XML
```xml
<record id="my_model_view_form" model="ir.ui.view">
    <field name="name">my.module.model.view.form</field>
    <field name="model">my.module.model</field>
    <field name="arch" type="xml">
        <form>
            <sheet>
                <group>
                    <field name="name"/>
                    <field name="partner_id"/>
                </group>
            </sheet>
        </form>
    </field>
</record>
```

### Action + Menu
```xml
<record id="my_model_action" model="ir.actions.act_window">
    <field name="name">My Models</field>
    <field name="res_model">my.module.model</field>
    <field name="view_mode">list,form</field>
</record>

<menuitem id="my_model_menu" 
          name="My Models"
          action="my_model_action"
          sequence="10"/>
```

## ⚡ Métodos Comuns

### Compute Field
```python
total = fields.Float(compute='_compute_total', store=True)

@api.depends('line_ids.amount')
def _compute_total(self):
    for record in self:
        record.total = sum(record.line_ids.mapped('amount'))
```

### Onchange
```python
@api.onchange('partner_id')
def _onchange_partner_id(self):
    if self.partner_id:
        self.email = self.partner_id.email
```

### Constraint
```python
@api.constrains('date_start', 'date_end')
def _check_dates(self):
    for record in self:
        if record.date_start > record.date_end:
            raise ValidationError("Invalid dates!")
```

### Action Method
```python
def action_confirm(self):
    self.ensure_one()
    self.state = 'confirmed'
    return True
```

## 🛡️ Regras de Segurança

### Access Rights (ir.model.access.csv)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model.user,model_my_module_model,base.group_user,1,1,1,0
access_my_model_manager,my.model.manager,model_my_module_model,my_module_group_manager,1,1,1,1
```

### Record Rule
```xml
<record id="my_model_rule_user" model="ir.rule">
    <field name="name">My Model: User Access</field>
    <field name="model_id" ref="model_my_module_model"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

## 📊 Relational Fields

| Tipo | Definição | Uso |
|------|-----------|-----|
| **Many2one** | `partner_id = fields.Many2one('res.partner')` | Um parceiro |
| **One2many** | `line_ids = fields.One2many('sale.line', 'order_id')` | Múltiplas linhas |
| **Many2many** | `tag_ids = fields.Many2many('product.tag')` | Múltiplas tags |

## 🔍 Search & Filter

### Search Method
```python
# Buscar todos ativos
records = self.env['my.model'].search([('active', '=', True)])

# Com limite
records = self.env['my.model'].search([], limit=10)

# Com ordenação
records = self.env['my.model'].search([], order='name desc')
```

### Filtered, Mapped, Sorted
```python
# Filtered
active_partners = partners.filtered(lambda p: p.active)

# Mapped
names = partners.mapped('name')

# Sorted
sorted_partners = partners.sorted(key=lambda p: p.name)
```

## ⚠️ Regras Críticas

### ❌ NUNCA Faça

1. **`cr.commit()` ou `cr.rollback()`** manualmente (framework gerencia)
2. **Hardcode de credenciais** ou dados sensíveis
3. **Capturar `Exception` genérica** sem especificar tipo
4. **Adicionar bibliotecas minificadas** ao código
5. **Usar seletores `id`** em CSS
6. **Criar variáveis temporárias** desnecessárias

### ✅ SEMPRE Faça

1. **Use `filtered`, `mapped`, `sorted`** para iterações
2. **Prefixe módulos** da comunidade (`thedevkitchen_`, `mycompany_`)
3. **Documente código** com docstrings
4. **Organize imports** (stdlib, odoo, addons)
5. **Use savepoints** ao capturar exceções
6. **Nomes significativos** para variáveis e métodos

## 📚 Recursos

### Documentação Oficial
- [Odoo 19.0 Coding Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html)
- [Odoo 19.0 Developer Docs](https://www.odoo.com/documentation/19.0/developer.html)
- [Security Pitfalls](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#reference-security-pitfalls)

### Python
- [PEP 8](https://pep8.org/)
- [Python Built-ins](http://docs.python.org/library/functions.html)

### Frontend
- [OWL Framework](https://github.com/odoo/owl)
- [SASS Documentation](https://sass-lang.com/documentation)
- [CSS Variables (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

### Design Patterns
- [Single Responsibility Principle](http://en.wikipedia.org/wiki/Single_responsibility_principle)
- [Cyclomatic Complexity](http://en.wikipedia.org/wiki/Cyclomatic_complexity)

## 🔖 Atalhos

| Tarefa | Comando/Ação |
|--------|--------------|
| Criar modelo | Adicionar classe em `models/` |
| Criar view | Adicionar XML em `views/` |
| Adicionar menu | Tag `<menuitem>` em XML |
| Criar ação | `<record model="ir.actions.act_window">` |
| Adicionar acesso | Linha em `ir.model.access.csv` |
| Adicionar grupo | XML em `security/<module>_groups.xml` |
| Record rule | XML em `security/<model>_security.xml` |
| Template QWeb | Tag `<template>` em XML |
| Widget JS | Classe em `static/src/js/` |
| SCSS | Arquivo em `static/src/scss/` |

## 💡 Dicas Pro

1. **Use GitHub Copilot/AI** mas revise sempre o código gerado
2. **Leia ADRs do projeto** antes de implementar features
3. **Siga padrões existentes** quando modificar código
4. **Teste localmente** antes de commit
5. **Use linters** (pylint, eslint, stylelint)
6. **Documente decisões** técnicas importantes
7. **Peça code review** de colegas experientes
8. **Mantenha commits atômicos** e bem descritos

---

**Última atualização:** 05/02/2026  
**Baseado em:** Odoo 19.0 Official Documentation
