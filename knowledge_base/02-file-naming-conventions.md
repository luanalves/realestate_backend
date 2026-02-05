# File Naming Conventions - Convenções de Nomenclatura de Arquivos

## Princípios Gerais

A nomenclatura de arquivos é crucial para encontrar informações rapidamente em todos os addons Odoo. Esta seção explica como nomear arquivos em um módulo Odoo padrão.

## Regras Básicas

### ✅ Caracteres Permitidos
- Apenas `[a-z0-9_]` (minúsculas, números e underscore)
- **NUNCA** use espaços ou caracteres especiais

### ✅ Formato Geral
```
<model_name>_<type>.extension
```

## Models (Python)

### Regra Principal
Divida a lógica de negócio por conjuntos de modelos pertencentes a um mesmo modelo principal. Cada conjunto fica em um arquivo nomeado com base no modelo principal.

### Convenções

**1. Modelo único:**
```python
# Arquivo: plant_nursery.py
class PlantNursery(models.Model):
    _name = 'plant.nursery'
```

**2. Múltiplos modelos:**
```
models/
├── plant_nursery.py    # Primeiro modelo principal
├── plant_order.py      # Outro modelo principal
└── res_partner.py      # Modelo Odoo herdado
```

**3. Modelos herdados:**
Cada modelo herdado deve estar em seu próprio arquivo para facilitar o entendimento.

```python
# Arquivo: res_partner.py
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    nursery_id = fields.Many2one('plant.nursery')
```

## Security (Segurança)

Três arquivos principais devem ser usados:

### 1. Access Rights
```
security/ir.model.access.csv
```
Definição de direitos de acesso (CRUD permissions).

### 2. User Groups
```
security/<module>_groups.xml
```
Definição de grupos de usuários.

### 3. Record Rules
```
security/<model>_security.xml
```
Regras de registro (filtros de domínio).

### Exemplo Completo
```
security/
├── ir.model.access.csv
├── plant_nursery_groups.xml
├── plant_nursery_security.xml
└── plant_order_security.xml
```

## Views (Visualizações)

### Backend Views
Views do backend devem ser divididas como os models e com sufixo `_views.xml`.

**Views incluem:** list, form, kanban, activity, graph, pivot, etc.

```
views/
├── plant_nursery_views.xml
├── plant_order_views.xml
└── res_partner_views.xml
```

### Menus (Opcional)
Menus principais não vinculados a ações específicas podem ser extraídos para:
```
views/<module>_menus.xml
```

### Templates (Portal/Website)
Templates QWeb para portal/website são colocados em arquivos separados:
```
views/<model>_templates.xml
```

### Exemplo Completo
```
views/
├── plant_nursery_menus.xml       # Menus principais (opcional)
├── plant_nursery_views.xml       # Views backend
├── plant_nursery_templates.xml   # Templates portal
├── plant_order_views.xml
└── plant_order_templates.xml
```

## Data (Dados)

Divida por propósito (demo ou data) e modelo principal.

### Convenções
- Dados de produção: `<model>_data.xml`
- Dados de demonstração: `<model>_demo.xml`

### Exemplo
```
data/
├── plant_nursery_data.xml
├── plant_nursery_demo.xml
└── mail_data.xml              # Dados relacionados ao mail
```

## Controllers (Controladores)

### Arquivo Principal
Geralmente todos os controladores pertencem a um único arquivo:
```
controllers/<module_name>.py
```

### Herança
Para herdar controlador de outro módulo:
```
controllers/<inherited_module_name>.py
```

### ❌ Convenção Antiga (Evitar)
```
controllers/main.py  # DEPRECATED - use <module_name>.py
```

### Exemplo
```
controllers/
├── plant_nursery.py
└── portal.py          # Herdando portal/controllers/portal.py
```

## Static Files (Arquivos Estáticos)

### JavaScript
Cada componente em seu próprio arquivo com nome significativo.

```
static/src/js/
├── activity.js        # Widget de atividade
├── widget_a.js
└── widget_b.js
```

**Subdiretorios** podem ser criados para estruturar o 'package':
```
static/src/js/
├── components/
│   ├── dialog.js
│   └── modal.js
└── widgets/
    ├── calendar.js
    └── kanban.js
```

### Templates JS (XML Estático)
```
static/src/xml/
├── widget_a.xml
└── widget_b.xml
```

### SCSS/CSS
Mesma lógica do JavaScript:
```
static/src/scss/
├── widget_a.scss
└── widget_b.scss
```

### ⚠️ Imagens e Bibliotecas
**NUNCA** linke dados externos (URLs). Copie para o codebase:

```
static/
├── img/
│   ├── logo.png
│   └── banner.jpg
└── lib/
    └── external_library/
        ├── lib.js
        └── lib.css
```

## Wizards (Assistentes)

Nomenclatura igual aos models Python:

```
wizard/
├── <transient>.py
└── <transient>_views.xml
```

### Exemplo
```
wizard/
├── make_plant_order.py
└── make_plant_order_views.xml
```

## Reports (Relatórios)

### Statistical Reports (SQL Views)
```
report/
├── <model>_report.py
└── <model>_report_views.xml
```

### Printable Reports (QWeb)
```
report/
├── <model>_reports.xml       # Actions, paperformat
└── <model>_templates.xml     # Templates XML
```

### Exemplo Completo
```
report/
├── plant_order_report.py
├── plant_order_report_views.xml
├── plant_order_reports.xml
└── plant_order_templates.xml
```

## Tabela de Referência Rápida

| Tipo | Padrão de Nomenclatura | Exemplo |
|------|------------------------|---------|
| **Model** | `<model_name>.py` | `plant_nursery.py` |
| **Inherited Model** | `<inherited_model>.py` | `res_partner.py` |
| **Access Rights** | `ir.model.access.csv` | `ir.model.access.csv` |
| **Groups** | `<module>_groups.xml` | `plant_nursery_groups.xml` |
| **Security Rules** | `<model>_security.xml` | `plant_nursery_security.xml` |
| **Backend Views** | `<model>_views.xml` | `plant_nursery_views.xml` |
| **Templates** | `<model>_templates.xml` | `plant_nursery_templates.xml` |
| **Menus** | `<module>_menus.xml` | `plant_nursery_menus.xml` |
| **Production Data** | `<model>_data.xml` | `plant_nursery_data.xml` |
| **Demo Data** | `<model>_demo.xml` | `plant_nursery_demo.xml` |
| **Controller** | `<module_name>.py` | `plant_nursery.py` |
| **Inherited Controller** | `<module>.py` | `portal.py` |
| **Wizard** | `<transient>.py` | `make_plant_order.py` |
| **Wizard Views** | `<transient>_views.xml` | `make_plant_order_views.xml` |
| **SQL Report** | `<model>_report.py` | `plant_order_report.py` |
| **Report Views** | `<model>_report_views.xml` | `plant_order_report_views.xml` |
| **Report Actions** | `<model>_reports.xml` | `plant_order_reports.xml` |
| **Report Templates** | `<model>_templates.xml` | `plant_order_templates.xml` |
| **JavaScript** | `<component>.js` | `widget_calendar.js` |
| **SCSS** | `<component>.scss` | `widget_calendar.scss` |
| **JS Templates** | `<component>.xml` | `widget_calendar.xml` |

## Boas Práticas

### ✅ Fazer
- Usar nomes descritivos e significativos
- Manter consistência em todo o módulo
- Seguir o padrão `<model>_<type>.extension`
- Um propósito por arquivo

### ❌ Evitar
- Nomes genéricos (`utils.py`, `helpers.py`, `common.py`)
- Misturar múltiplos modelos em um arquivo (exceto relacionados)
- Arquivos muito grandes (refatore em arquivos menores)
- Caracteres especiais ou espaços

## Exemplo Real: Plant Nursery

```
plant_nursery/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── plant_nursery.py
│   └── portal.py
├── data/
│   ├── plant_nursery_data.xml
│   ├── plant_nursery_demo.xml
│   └── mail_data.xml
├── models/
│   ├── __init__.py
│   ├── plant_nursery.py
│   ├── plant_order.py
│   └── res_partner.py
├── report/
│   ├── plant_order_report.py
│   ├── plant_order_report_views.xml
│   ├── plant_order_reports.xml
│   └── plant_order_templates.xml
├── security/
│   ├── ir.model.access.csv
│   ├── plant_nursery_groups.xml
│   ├── plant_nursery_security.xml
│   └── plant_order_security.xml
├── static/
│   ├── img/
│   ├── lib/
│   └── src/
│       ├── js/
│       ├── scss/
│       └── xml/
├── views/
│   ├── plant_nursery_menus.xml
│   ├── plant_nursery_views.xml
│   ├── plant_nursery_templates.xml
│   ├── plant_order_views.xml
│   └── plant_order_templates.xml
└── wizard/
    ├── make_plant_order.py
    └── make_plant_order_views.xml
```

## Referências

- [Odoo File Naming](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#file-naming)
- [Plant Nursery Example](https://github.com/tivisse/odoodays-2018/tree/master/plant_nursery)
