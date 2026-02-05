# CSS and SCSS Guidelines - Diretrizes de CSS e SCSS

## Syntax and Formatting (Sintaxe e Formatação)

### Exemplo Base

```scss
.o_foo, .o_foo_bar, .o_baz {
    height: $o-statusbar-height;

    .o_qux {
        height: $o-statusbar-height * 0.5;
    }
}

.o_corge {
    background: $o-list-footer-bg-color;
}
```

### Regras de Formatação

1. **Indentação:** 4 espaços, sem tabs
2. **Largura:** Máximo de 80 caracteres por linha
3. **Chave de abertura `{`:** Espaço vazio após o último seletor
4. **Chave de fechamento `}`:** Em sua própria linha
5. **Declarações:** Uma por linha
6. **Whitespace:** Uso significativo de espaços em branco

#### Configurações Stylelint Sugeridas

```json
{
  "indentation": 4,
  "max-line-length": 80,
  "block-opening-brace-space-before": "always",
  "block-closing-brace-newline-before": "always",
  "declaration-block-semicolon-newline-after": "always"
}
```

## Properties Order (Ordem das Propriedades)

Ordene propriedades de "fora para dentro", começando com `position` e terminando com regras decorativas (`font`, `filter`, etc.).

### Exemplo Completo

```scss
.o_element {
    // 1. Variáveis SCSS e CSS no topo
    $-inner-gap: $border-width + $legend-margin-bottom;
    
    --element-margin: 1rem;
    --element-size: 3rem;
    
    // Linha em branco separando variáveis de outras declarações
    
    // 2. Posicionamento
    @include o-position-absolute(1rem);
    position: absolute;
    top: 0;
    left: 0;
    z-index: 100;
    
    // 3. Box model
    display: block;
    width: calc(var(--element-size) + #{$-inner-gap});
    height: var(--element-size);
    margin: var(--element-margin);
    padding: 1rem;
    
    // 4. Bordas
    border: 0;
    border-radius: 4px;
    
    // 5. Background
    background: blue;
    
    // 6. Texto
    color: white;
    font-size: 1rem;
    line-height: 1.5;
    
    // 7. Outros
    filter: blur(2px);
    transform: scale(1.1);
}
```

### Ordem Recomendada

1. **Variáveis** (SCSS e CSS)
2. **Positioning** (`position`, `top`, `left`, `z-index`)
3. **Box Model** (`display`, `width`, `height`, `margin`, `padding`)
4. **Borders** (`border`, `border-radius`)
5. **Background** (`background-*`)
6. **Typography** (`font-*`, `line-height`, `color`)
7. **Visual Effects** (`filter`, `transform`, `opacity`)
8. **Outros**

## Naming Conventions (Convenções de Nomenclatura)

### Regra Fundamental

✅ **Evite seletores `id`**, prefixe classes com `o_<module_name>`:

```scss
// ✅ Bom
.o_sale_order_line { }
.o_website_forum_post { }
.o_kanban_view { }

// ❌ Evite
#sale_order_line { }
.sale_order_line { }  // Sem prefixo
```

**Exceção:** Webclient usa apenas prefixo `o_`:
```scss
.o_form_view { }
.o_list_view { }
```

### Abordagem "Grandchild" (Neto)

Evite criar classes hiper-específicas. Opte pela abordagem "Grandchild":

#### ❌ Não Faça

```html
<div class="o_element_wrapper">
    <div class="o_element_wrapper_entries">
        <span class="o_element_wrapper_entries_entry">
            <a class="o_element_wrapper_entries_entry_link">Entry</a>
        </span>
    </div>
</div>
```

```scss
.o_element_wrapper { }
.o_element_wrapper_entries { }
.o_element_wrapper_entries_entry { }
.o_element_wrapper_entries_entry_link { }  // Muito específico!
```

#### ✅ Faça

```html
<div class="o_element_wrapper">
    <div class="o_element_entries">
        <span class="o_element_entry">
            <a class="o_element_link">Entry</a>
        </span>
    </div>
</div>
```

```scss
.o_element_wrapper { }
.o_element_entries { }
.o_element_entry { }
.o_element_link { }  // Mais compacto e manutenível
```

**Benefícios:**
- Mais compacto
- Facilita manutenção
- Limita necessidade de renomear quando DOM muda

## SCSS Variables (Variáveis SCSS)

### Convenção Padrão

```
$o-[root]-[element]-[property]-[modifier]
```

**Componentes:**
- **`$o-`** - Prefixo obrigatório
- **`[root]`** - Nome do componente ou módulo
- **`[element]`** - Identificador opcional para elementos internos
- **`[property]`** - Propriedade/comportamento definido
- **`[modifier]`** - Modificador opcional

### Exemplos

```scss
// Variáveis globais
$o-block-color: #333;
$o-block-title-color: #000;
$o-block-title-color-hover: #555;

// Componente específico
$o-kanban-card-width: 300px;
$o-kanban-card-padding: 1rem;
$o-kanban-card-bg-color: white;
$o-kanban-card-bg-color-hover: #f5f5f5;

// Elemento interno
$o-form-field-height: 32px;
$o-form-field-border-color: #ccc;
$o-form-label-color: #555;
```

## SCSS Variables (Scoped) - Variáveis de Escopo

Variáveis declaradas dentro de blocos (não acessíveis externamente).

### Convenção

```
$-[variable_name]
```

### Exemplo

```scss
.o_element {
    $-inner-gap: compute-something;
    
    margin-right: $-inner-gap;
    
    .o_element_child {
        margin-right: $-inner-gap * 0.5;
    }
}
```

**Referência:** [Variables scope (SASS Documentation)](https://sass-lang.com/documentation/variables#scope)

## SCSS Mixins and Functions

### Convenção

```
o-[name]
```

Use **nomes descritivos**. Para funções, use **verbos no imperativo** (`get`, `make`, `apply`).

Argumentos opcionais seguem convenção de variáveis de escopo: `$-[argument]`

### Exemplos

#### Mixin

```scss
@mixin o-avatar($-size: 1.5em, $-radius: 100%) {
    width: $-size;
    height: $-size;
    border-radius: $-radius;
    overflow: hidden;
}

// Uso
.o_user_avatar {
    @include o-avatar(2em, 50%);
}
```

#### Function

```scss
@function o-invert-color($-color, $-amount: 100%) {
    $-inverse: change-color($-color, $-hue: hue($-color) + 180);
    @return mix($-inverse, $-color, $-amount);
}

// Uso
.o_button_primary {
    background: $o-brand-primary;
    color: o-invert-color($o-brand-primary);
}
```

**Referências:**
- [Mixins (SASS Documentation)](https://sass-lang.com/documentation/at-rules/mixin)
- [Functions (SASS Documentation)](https://sass-lang.com/documentation/at-rules/function)

## CSS Variables (Variáveis CSS)

### Uso em Odoo

CSS variables são **estritamente relacionadas ao DOM** - usadas para adaptações contextuais.

### Convenção (BEM)

```
--[root]__[element]-[property]--[modifier]
```

**Componentes:**
- **`[root]`** - Nome do componente ou módulo
- **`[element]`** - Identificador opcional para elementos internos
- **`[property]`** - Propriedade/comportamento
- **`[modifier]`** - Modificador opcional

### Exemplo

```scss
.o_kanban_record {
    --KanbanRecord-width: 300px;
    --KanbanRecord__picture-border: 1px solid #ccc;
    --KanbanRecord__picture-border--active: 2px solid blue;
}

// Adaptar componente em outro contexto
.o_form_view {
    --KanbanRecord-width: 250px;
    --KanbanRecord__picture-border: 2px solid #999;
    --KanbanRecord__picture-border--active: 3px solid green;
}
```

## CSS vs SCSS Variables

### Diferenças Principais

| Característica | SCSS Variables | CSS Variables |
|----------------|----------------|---------------|
| **Compilação** | Compiladas (imperativas) | Incluídas no output (declarativas) |
| **Uso** | Design system global | Adaptações contextuais |
| **Escopo** | Tempo de compilação | Runtime (DOM) |
| **Performance** | Mais rápido | Levemente mais lento |

**Referência:** [CSS/SCSS Differences (SASS Documentation)](https://sass-lang.com/documentation/variables#:~:text=CSS%20variables%20are%20included%20in,use%20will%20stay%20the%20same)

### Estratégia em Odoo

1. **SCSS** para design system (cores, tamanhos, breakpoints)
2. **CSS** para variações contextuais (temas, adaptações)

### Exemplo Completo

```scss
// secondary_variables.scss
$o-component-color: $o-main-text-color;
$o-dashboard-color: $o-info;

// component.scss
.o_component {
    // Fallback para variável SCSS
    color: var(--MyComponent-color, #{$o-component-color});
}

// dashboard.scss
.o_dashboard {
    // Override contextual
    --MyComponent-color: #{$o-dashboard-color};
}
```

## The `:root` Pseudo-class

### Regra em Odoo

❌ **Normalmente NÃO use** `:root` para definir CSS variables na UI do Odoo.

**Motivo:** Gerenciamos design system globalmente via SCSS.

### Exceções

Apenas em casos específicos:
- Templates compartilhados entre bundles
- Componentes que precisam de contexto global
- Casos onde SCSS não é adequado

## Use of CSS Variables (Uso de Variáveis CSS)

### Princípio

CSS variables são usadas para **adaptações contextuais**, não para gerenciar design system global.

### Exemplo Correto

```scss
// my_component.scss
.o_MyComponent {
    // Define propriedades com fallbacks
    color: var(--MyComponent-color, #313131);
    background: var(--MyComponent-bg, white);
}

// my_dashboard.scss
.o_MyDashboard {
    // Adapta componente neste contexto apenas
    --MyComponent-color: #017e84;
    --MyComponent-bg: #f0f0f0;
}
```

**Referência:** [CSS Variables (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)

## Resumo - Checklist

### ✅ Fazer

- 4 espaços de indentação
- Máximo 80 caracteres por linha
- Ordenar propriedades (fora para dentro)
- Prefixar classes com `o_<module>`
- Usar abordagem "Grandchild"
- SCSS variables para design system
- CSS variables para adaptações contextuais
- Nomear variáveis de forma descritiva

### ❌ Evitar

- Seletores `id`
- Classes sem prefixo `o_`
- Classes hiper-específicas
- Usar `:root` desnecessariamente
- Tabs (use 4 espaços)
- Linhas muito longas (>80 chars)
- CSS variables para design system global

## Exemplo Completo: Componente

```scss
// _kanban_card.scss

// ========== Variáveis SCSS (Design System) ==========
$o-kanban-card-width: 300px;
$o-kanban-card-padding: 1rem;
$o-kanban-card-bg: white;
$o-kanban-card-border-color: #ddd;

// ========== Mixin ==========
@mixin o-kanban-card-hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
}

// ========== Componente ==========
.o_kanban_record {
    // Variáveis CSS (contextuais)
    --KanbanCard-bg: #{$o-kanban-card-bg};
    --KanbanCard-border: 1px solid #{$o-kanban-card-border-color};
    
    // Posicionamento
    position: relative;
    
    // Box model
    display: flex;
    flex-direction: column;
    width: $o-kanban-card-width;
    padding: $o-kanban-card-padding;
    margin: 0.5rem;
    
    // Bordas
    border: var(--KanbanCard-border);
    border-radius: 4px;
    
    // Background
    background: var(--KanbanCard-bg);
    
    // Visual effects
    transition: all 0.2s ease;
    
    // Estados
    &:hover {
        @include o-kanban-card-hover;
    }
    
    // Elementos internos
    .o_kanban_card_header {
        margin-bottom: 1rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .o_kanban_card_body {
        flex: 1;
        color: #555;
    }
}

// ========== Adaptações Contextuais ==========
.o_dashboard {
    // Adaptar kanban card no dashboard
    --KanbanCard-bg: #f5f5f5;
    --KanbanCard-border: 2px solid #017e84;
}
```

## Referências

- [Odoo CSS/SCSS Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#css-and-scss)
- [SASS Documentation](https://sass-lang.com/documentation)
- [CSS Variables (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties)
- [BEM Methodology](http://getbem.com/)
