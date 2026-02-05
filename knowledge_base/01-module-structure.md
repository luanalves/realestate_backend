# Module Structure - Estrutura de Módulos Odoo

## Diretórios Principais

Um módulo Odoo é organizado em diretórios importantes que contêm a lógica de negócio:

### Diretórios Obrigatórios

```
addons/my_module/
├── __init__.py
├── __manifest__.py
├── models/              # Definição dos modelos
├── views/               # Views e templates
├── controllers/         # Controladores HTTP (rotas)
├── data/               # Dados demo e data XML
├── security/           # Regras de segurança e acesso
└── static/             # Assets web (CSS, JS, imagens)
    ├── src/
    │   ├── css/
    │   ├── js/
    │   ├── scss/
    │   └── xml/
    ├── img/
    └── lib/
```

### Diretórios Opcionais

```
├── wizard/             # Modelos transientes e suas views
├── report/             # Relatórios imprimíveis e SQL views
└── tests/              # Testes Python
```

## Descrição dos Diretórios

### `models/`
Contém a definição dos modelos de negócio (classes Python que herdam de `models.Model`).

**Organização:**
- Um arquivo por modelo principal
- Modelos herdados em arquivos separados
- Nome do arquivo = nome do modelo principal

**Exemplo:**
```
models/
├── __init__.py
├── plant_nursery.py     # Modelo principal
├── plant_order.py       # Outro modelo principal
└── res_partner.py       # Herança de modelo Odoo
```

### `views/`
Contém as views do backend e templates do portal/website.

**Convenções:**
- Views do backend: `<model>_views.xml`
- Templates (QWeb): `<model>_templates.xml`
- Menus principais (opcional): `<module>_menus.xml`

**Exemplo:**
```
views/
├── plant_nursery_menus.xml
├── plant_nursery_views.xml
├── plant_nursery_templates.xml
├── plant_order_views.xml
└── plant_order_templates.xml
```

### `controllers/`
Contém os controladores HTTP (endpoints/rotas).

**Convenções:**
- Arquivo principal: `<module_name>.py`
- Herança de outros módulos: `<inherited_module>.py`
- ❌ Evitar `main.py` (convenção antiga)

**Exemplo:**
```
controllers/
├── __init__.py
├── plant_nursery.py
└── portal.py           # Herança de portal/controllers/portal.py
```

### `security/`
Contém regras de segurança, grupos de usuários e controle de acesso.

**Arquivos principais:**
- `ir.model.access.csv` - Direitos de acesso
- `<module>_groups.xml` - Grupos de usuários
- `<model>_security.xml` - Regras de registro (record rules)

**Exemplo:**
```
security/
├── ir.model.access.csv
├── plant_nursery_groups.xml
├── plant_nursery_security.xml
└── plant_order_security.xml
```

### `data/`
Dados de demonstração e dados iniciais do módulo.

**Convenções:**
- Dados demo: `<model>_demo.xml`
- Dados de produção: `<model>_data.xml`

**Exemplo:**
```
data/
├── plant_nursery_data.xml
├── plant_nursery_demo.xml
└── mail_data.xml
```

### `static/`
Assets estáticos (JavaScript, CSS, imagens, bibliotecas).

**Estrutura:**
```
static/
├── src/
│   ├── js/              # JavaScript
│   │   └── tours/       # Tours de usuário (tutoriais)
│   ├── scss/            # SCSS
│   ├── css/             # CSS compilado
│   └── xml/             # Templates QWeb para JS
├── img/                 # Imagens
└── lib/                 # Bibliotecas externas
    └── external_lib/
```

### `wizard/`
Modelos transientes (wizards) e suas views.

**Convenção:**
- `<transient>.py` - Modelo transiente
- `<transient>_views.xml` - Views do wizard

**Exemplo:**
```
wizard/
├── make_plant_order.py
└── make_plant_order_views.xml
```

### `report/`
Relatórios (SQL views e relatórios imprimíveis).

**Tipos:**
1. **Relatórios estatísticos** (SQL views):
   - `<model>_report.py` - Python/SQL view
   - `<model>_report_views.xml` - Views do relatório

2. **Relatórios imprimíveis** (QWeb):
   - `<model>_reports.xml` - Actions, paperformat
   - `<model>_templates.xml` - Templates XML do relatório

**Exemplo:**
```
report/
├── __init__.py
├── plant_order_report.py
├── plant_order_report_views.xml
├── plant_order_reports.xml
└── plant_order_templates.xml
```

### `tests/`
Testes automatizados Python.

**Estrutura recomendada:**
```
tests/
├── __init__.py
├── test_plant_nursery.py
└── test_plant_order.py
```

## Árvore Completa de Exemplo

```
addons/plant_nursery/
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
│   ├── __init__.py
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
│   │   ├── my_little_kitten.png
│   │   └── troll.jpg
│   ├── lib/
│   │   └── external_lib/
│   └── src/
│       ├── js/
│       │   ├── widget_a.js
│       │   └── widget_b.js
│       ├── scss/
│       │   ├── widget_a.scss
│       │   └── widget_b.scss
│       └── xml/
│           ├── widget_a.xml
│           └── widget_b.xml
├── views/
│   ├── plant_nursery_menus.xml
│   ├── plant_nursery_views.xml
│   ├── plant_nursery_templates.xml
│   ├── plant_order_views.xml
│   ├── plant_order_templates.xml
│   └── res_partner_views.xml
└── wizard/
    ├── make_plant_order.py
    └── make_plant_order_views.xml
```

## Regras Importantes

### ⚠️ Nomenclatura de Arquivos
- Apenas `[a-z0-9_]` (minúsculas, números e underscore)
- Sem caracteres especiais ou espaços

### ⚠️ Permissões de Arquivos
- Pastas: `755`
- Arquivos: `644`

### ⚠️ Prefixo de Módulo (Comunidade)
Para módulos desenvolvidos pela comunidade, use um prefixo como o nome da sua empresa:
```
thedevkitchen_estate
mycompany_crm_extension
```

## Referências

- [Odoo Module Structure](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#module-structure)
- Exemplo real: [Plant Nursery](https://github.com/tivisse/odoodays-2018/tree/master/plant_nursery)
