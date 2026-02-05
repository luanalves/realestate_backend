# JavaScript Guidelines - Diretrizes de Código JavaScript

## Static Files Organization (Organização de Arquivos Estáticos)

O servidor Odoo serve estaticamente todos os arquivos em `static/`, prefixados com o nome do addon.

**Exemplo:**
```
addons/web/static/src/js/some_file.js
→ Acessível em: your-odoo-server.com/web/static/src/js/some_file.js
```

### Estrutura Padrão

```
my_module/
└── static/
    ├── lib/                    # Bibliotecas JavaScript externas
    │   └── jquery/
    │       ├── jquery.js
    │       └── jquery.min.js
    ├── src/                    # Código fonte
    │   ├── js/                 # JavaScript
    │   │   └── tours/          # Tours de usuário (tutoriais)
    │   ├── scss/               # SCSS
    │   ├── css/                # CSS compilado
    │   └── xml/                # QWeb templates para JS
    ├── img/                    # Imagens
    └── fonts/                  # Fontes
```

### Detalhamento dos Diretórios

#### `static/lib/`
Bibliotecas JavaScript de terceiros, em subpastas:
```
static/lib/
├── jquery/
│   ├── jquery.js
│   └── jquery.min.js
├── bootstrap/
│   ├── bootstrap.js
│   └── bootstrap.css
└── moment/
    └── moment.js
```

#### `static/src/`
Código fonte genérico do módulo:

**`static/src/js/`** - Arquivos JavaScript
```
static/src/js/
├── components/
│   ├── dialog.js
│   └── modal.js
├── widgets/
│   ├── calendar.js
│   └── kanban.js
└── tours/              # Tours de usuário (tutoriais)
    └── home_tour.js
```

**`static/src/xml/`** - QWeb templates renderizados em JS
```
static/src/xml/
├── dialog_templates.xml
└── widget_templates.xml
```

**`static/src/scss/`** - Arquivos SCSS
```
static/src/scss/
├── components/
│   ├── _dialog.scss
│   └── _modal.scss
└── main.scss
```

**`static/src/css/`** - CSS compilado

#### `static/tests/`
Arquivos relacionados a testes:

```
static/tests/
└── tours/              # Testes de tours (não tutoriais)
    ├── test_flow_1.js
    └── test_flow_2.js
```

## JavaScript Coding Guidelines

### 1. Use Strict

**Recomendado** para todos os arquivos JavaScript:

```javascript
'use strict';

// Seu código aqui
```

### 2. Use a Linter

Use ferramentas como:
- **JSHint**
- **ESLint**
- **Prettier**

### 3. Never Add Minified Libraries

❌ **NUNCA** adicione bibliotecas JavaScript minificadas:

```
❌ Ruim:
static/lib/library/library.min.js

✅ Bom:
static/lib/library/library.js
```

**Motivo:** 
- Dificulta debugging
- Dificulta manutenção
- Odoo tem processo próprio de minificação

### 4. Use PascalCase for Classes

Use **PascalCase** para declaração de classes:

```javascript
// ✅ Correto
class DialogWidget {
    constructor() {
        this.name = 'Dialog';
    }
    
    open() {
        // ...
    }
}

// ✅ Correto
class KanbanView extends AbstractView {
    // ...
}
```

### 5. Estrutura de um Widget Odoo

```javascript
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class MyCustomWidget extends Component {
    static template = "my_module.MyCustomWidget";
    static props = {
        value: { type: String, optional: true },
    };

    setup() {
        // Initialization
    }

    async willStart() {
        // Async initialization
    }

    onClick() {
        // Event handler
    }
}

registry.category("fields").add("my_custom_widget", MyCustomWidget);
```

### 6. Organização de Código

#### Um Componente por Arquivo

```
static/src/js/
├── activity_widget.js       # Widget de atividade
├── calendar_widget.js       # Widget de calendário
└── kanban_renderer.js       # Renderer do kanban
```

#### Naming de Arquivos

- **PascalCase para classes:** Refletido no nome do arquivo
- **snake_case para arquivos:** `activity_widget.js`, `kanban_view.js`

### 7. Templates QWeb para JS

Templates devem estar em arquivos XML separados:

```xml
<!-- static/src/xml/dialog_templates.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="my_module.DialogWidget" owl="1">
        <div class="o_dialog">
            <div class="o_dialog_header">
                <h3><t t-esc="props.title"/></h3>
            </div>
            <div class="o_dialog_body">
                <t t-slot="default"/>
            </div>
        </div>
    </t>
</templates>
```

### 8. Comentários e Documentação

```javascript
/**
 * Widget personalizado para exibir atividades
 * 
 * @extends Component
 */
export class ActivityWidget extends Component {
    static template = "my_module.ActivityWidget";
    
    /**
     * Inicializa o widget
     * @override
     */
    setup() {
        super.setup();
        this.activities = [];
    }
    
    /**
     * Carrega atividades do servidor
     * 
     * @returns {Promise<Array>} Lista de atividades
     */
    async loadActivities() {
        const data = await this.orm.call(
            'mail.activity',
            'search_read',
            [[], ['id', 'summary', 'date_deadline']]
        );
        return data;
    }
}
```

### 9. Async/Await

Use **async/await** em vez de Promises diretas:

```javascript
// ✅ Bom - async/await
async loadData() {
    try {
        const result = await this.orm.call(
            'res.partner',
            'search_read',
            [[], ['name', 'email']]
        );
        this.partners = result;
    } catch (error) {
        console.error('Failed to load partners:', error);
    }
}

// ❌ Evite - Promise chains
loadData() {
    this.orm.call('res.partner', 'search_read', [[], ['name', 'email']])
        .then(result => {
            this.partners = result;
        })
        .catch(error => {
            console.error('Failed to load partners:', error);
        });
}
```

### 10. Event Handlers

```javascript
export class MyWidget extends Component {
    static template = "my_module.MyWidget";
    
    setup() {
        // Use arrow functions para manter 'this'
        this.onButtonClick = this.onButtonClick.bind(this);
    }
    
    /**
     * Handler para clique no botão
     * 
     * @param {Event} ev - Evento de clique
     */
    onButtonClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        
        // Lógica do handler
        this.doSomething();
    }
}
```

## Exemplo Completo: Widget Customizado

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Widget para gerenciar tags de produtos
 * 
 * Permite adicionar, remover e pesquisar tags
 */
export class ProductTagWidget extends Component {
    static template = "my_module.ProductTagWidget";
    static props = {
        productId: Number,
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        this.state = useState({
            tags: [],
            isLoading: false,
        });
        
        this.loadTags();
    }

    /**
     * Carrega tags do produto
     */
    async loadTags() {
        this.state.isLoading = true;
        try {
            const tags = await this.orm.call(
                'product.product',
                'read',
                [[this.props.productId], ['tag_ids']]
            );
            this.state.tags = tags[0].tag_ids || [];
        } catch (error) {
            this.notification.add(
                'Failed to load tags',
                { type: 'danger' }
            );
        } finally {
            this.state.isLoading = false;
        }
    }

    /**
     * Adiciona nova tag
     * 
     * @param {Event} ev - Evento de clique
     */
    async onAddTag(ev) {
        ev.preventDefault();
        
        if (this.props.readonly) {
            return;
        }
        
        // Lógica para adicionar tag
        // ...
    }

    /**
     * Remove tag
     * 
     * @param {Number} tagId - ID da tag a remover
     */
    async onRemoveTag(tagId) {
        if (this.props.readonly) {
            return;
        }
        
        try {
            await this.orm.write(
                'product.product',
                [this.props.productId],
                { tag_ids: [[3, tagId]] }  // Command para remover
            );
            await this.loadTags();
            
            this.notification.add(
                'Tag removed successfully',
                { type: 'success' }
            );
        } catch (error) {
            this.notification.add(
                'Failed to remove tag',
                { type: 'danger' }
            );
        }
    }
}

// Registrar widget
registry.category("fields").add("product_tag_widget", ProductTagWidget);
```

## Checklist

### ✅ Fazer

- Use `'use strict';`
- Use linter (ESLint, JSHint)
- PascalCase para classes
- Um componente por arquivo
- Documentar com JSDoc
- Usar async/await
- Templates em arquivos XML separados
- Nomear arquivos com snake_case

### ❌ Evitar

- Bibliotecas minificadas
- Código sem documentação
- Promise chains (use async/await)
- Código sem organização
- Múltiplos componentes em um arquivo

## Referências

- [Odoo JavaScript Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#javascript)
- [JavaScript Coding Guidelines (GitHub Wiki)](https://github.com/odoo/odoo/wiki/Javascript-coding-guidelines)
- [OWL Documentation](https://github.com/odoo/owl)
- [JavaScript References](https://www.odoo.com/documentation/19.0/developer/reference/frontend/javascript_reference.html)
