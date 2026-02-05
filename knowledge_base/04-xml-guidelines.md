# XML Guidelines - Diretrizes para Arquivos XML

## Format (Formato)

### Regra Básica: Use `<record>`

Para declarar um registro em XML, a notação `<record>` é recomendada:

### Estrutura de um Record

```xml
<record id="view_id" model="ir.ui.view">
    <field name="name">view.name</field>
    <field name="model">object_name</field>
    <field name="priority" eval="16"/>
    <field name="arch" type="xml">
        <list>
            <field name="my_field_1"/>
            <field name="my_field_2" string="My Label" widget="statusbar" 
                   statusbar_visible="draft,sent,progress,done"/>
        </list>
    </field>
</record>
```

### Regras de Formatação

1. **Atributo `id` antes de `model`**
2. **Para campos (`<field>`):**
   - Atributo `name` primeiro
   - Valor no conteúdo da tag OU no atributo `eval`
   - Outros atributos (`widget`, `options`, etc.) ordenados por importância
3. **Agrupe registros por modelo** (quando possível)
4. **Tag `<data>` apenas para dados não-atualizáveis** (`noupdate=1`)

### Tag `<data>` com noupdate

```xml
<odoo>
    <data noupdate="1">
        <!-- Dados que não serão atualizados em upgrades -->
        <record id="demo_data_1" model="res.partner">
            <field name="name">Demo Partner</field>
        </record>
    </data>
</odoo>
```

**Ou diretamente na tag `<odoo>`:**

```xml
<odoo noupdate="1">
    <!-- Todos os dados não serão atualizados -->
    <record id="demo_data_1" model="res.partner">
        <field name="name">Demo Partner</field>
    </record>
</odoo>
```

## Custom Tags (Syntactic Sugar)

Odoo suporta tags customizadas que funcionam como atalhos:

### 1. `<menuitem>`

Atalho para declarar `ir.ui.menu`:

```xml
<menuitem 
    id="menu_sale_order" 
    name="Sales Orders"
    parent="sale.menu_sale"
    action="action_orders"
    sequence="10"/>
```

**Preferível a:**
```xml
<record id="menu_sale_order" model="ir.ui.menu">
    <field name="name">Sales Orders</field>
    <field name="parent_id" ref="sale.menu_sale"/>
    <field name="action" ref="action_orders"/>
    <field name="sequence">10</field>
</record>
```

### 2. `<template>`

Atalho para declarar QWeb View (requer apenas a seção `arch`):

```xml
<template id="portal_my_home" name="My Portal">
    <t t-call="portal.portal_layout">
        <div class="container">
            <h1>Welcome to My Portal</h1>
        </div>
    </t>
</template>
```

**Preferível a:**
```xml
<record id="portal_my_home" model="ir.ui.view">
    <field name="name">My Portal</field>
    <field name="type">qweb</field>
    <field name="arch" type="xml">
        <t t-call="portal.portal_layout">
            <div class="container">
                <h1>Welcome to My Portal</h1>
            </div>
        </t>
    </field>
</record>
```

## XML IDs and Naming (IDs e Nomenclatura)

### Security, View and Action

**Padrões obrigatórios:**

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| **Menu** | `<model_name>_menu` | `sale_order_menu` |
| **Submenu** | `<model_name>_menu_<action>` | `sale_order_menu_report` |
| **View** | `<model_name>_view_<type>` | `sale_order_view_form` |
| **Action (principal)** | `<model_name>_action` | `sale_order_action` |
| **Action (específica)** | `<model_name>_action_<detail>` | `sale_order_action_cancel` |
| **Window Action** | `<model_name>_action_view_<type>` | `sale_order_action_view_calendar` |
| **Group** | `<module>_group_<name>` | `sales_group_manager` |
| **Rule** | `<model_name>_rule_<group>` | `sale_order_rule_user` |

### Exemplos Completos

#### Views
```xml
<!-- Form View -->
<record id="sale_order_view_form" model="ir.ui.view">
    <field name="name">sale.order.view.form</field>
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <form>...</form>
    </field>
</record>

<!-- Kanban View -->
<record id="sale_order_view_kanban" model="ir.ui.view">
    <field name="name">sale.order.view.kanban</field>
    <field name="model">sale.order</field>
    <field name="arch" type="xml">
        <kanban>...</kanban>
    </field>
</record>
```

#### Actions
```xml
<!-- Action Principal -->
<record id="sale_order_action" model="ir.actions.act_window">
    <field name="name">Sales Orders</field>
    <field name="res_model">sale.order</field>
    <field name="view_mode">list,form,kanban</field>
</record>

<!-- Action Específica -->
<record id="sale_order_action_cancel" model="ir.actions.act_window">
    <field name="name">Cancelled Orders</field>
    <field name="res_model">sale.order</field>
    <field name="domain">[('state', '=', 'cancel')]</field>
</record>
```

#### Menus
```xml
<!-- Menu Principal -->
<menuitem 
    id="sale_order_menu_root"
    name="Sales"
    sequence="5"/>

<!-- Submenu -->
<menuitem 
    id="sale_order_menu_action"
    name="Orders"
    parent="sale_order_menu_root"
    action="sale_order_action"
    sequence="10"/>
```

#### Security
```xml
<!-- Group -->
<record id="sales_group_manager" model="res.groups">
    <field name="name">Sales Manager</field>
</record>

<!-- Record Rule -->
<record id="sale_order_rule_user" model="ir.rule">
    <field name="name">Sale Order User Rule</field>
    <field name="model_id" ref="model_sale_order"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('sales_group_user'))]"/>
</record>

<record id="sale_order_rule_company" model="ir.rule">
    <field name="name">Sale Order Multi-Company</field>
    <field name="model_id" ref="model_sale_order"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

### Nome do Campo `name`

O campo `name` deve ser **idêntico ao XML ID** com underscores substituídos por pontos:

```xml
<!-- XML ID: sale_order_view_form -->
<record id="sale_order_view_form" model="ir.ui.view">
    <!-- name: sale.order.view.form -->
    <field name="name">sale.order.view.form</field>
    ...
</record>
```

**Para actions:** Use naming descritivo (é usado como display name):

```xml
<record id="sale_order_action" model="ir.actions.act_window">
    <field name="name">Sales Orders</field>  <!-- Nome descritivo -->
    ...
</record>
```

## Inheriting XML (Herança de Views)

### XML ID de Views Herdadas

Use o **mesmo ID** do registro original (será prefixado automaticamente pelo módulo):

```xml
<!-- Módulo original: sale -->
<record id="sale_order_view_form" model="ir.ui.view">
    <field name="name">sale.order.view.form</field>
    ...
</record>

<!-- Módulo que herda: sale_custom -->
<!-- XML ID final: sale_custom.sale_order_view_form -->
<record id="sale_order_view_form" model="ir.ui.view">
    <field name="name">sale.order.view.form.inherit.sale_custom</field>
    <field name="inherit_id" ref="sale.sale_order_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='partner_id']" position="after">
            <field name="custom_field"/>
        </xpath>
    </field>
</record>
```

### Nomenclatura de Herança

Adicione sufixo `.inherit.{details}` ao nome para facilitar compreensão:

```xml
<field name="name">sale.order.view.form.inherit.sale_custom</field>
```

**Estrutura:**
- `sale.order.view.form` - View original
- `.inherit` - Indica herança
- `.sale_custom` - Módulo que está herdando

### Primary Views (Views Primárias)

Views primárias **não requerem** o sufixo inherit:

```xml
<record id="sale_order_view_form" model="ir.ui.view">
    <field name="name">sale.order.view.form.sale_custom</field>
    <field name="inherit_id" ref="sale.sale_order_view_form"/>
    <field name="mode">primary</field>
    <field name="arch" type="xml">
        <!-- Completamente nova view baseada na original -->
    </field>
</record>
```

## Resumo de Boas Práticas

### ✅ Fazer

- Usar `<record>` para declarações
- Colocar `id` antes de `model`
- Campo `name` primeiro em `<field>`
- Agrupar registros por modelo
- Seguir padrões de nomenclatura
- Usar `<menuitem>` e `<template>` quando apropriado
- Nome do campo `name` = XML ID com pontos
- Mesmo ID para views herdadas
- Sufixo `.inherit.{module}` para heranças

### ❌ Evitar

- XML IDs genéricos ou sem padrão
- Misturar diferentes modelos sem organização
- Usar `<data>` desnecessariamente
- Nomes de views sem seguir o padrão
- Views herdadas com IDs diferentes

## Referências

- [Odoo XML Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#xml-files)
- [QWeb Documentation](https://www.odoo.com/documentation/19.0/developer/reference/frontend/qweb.html)
