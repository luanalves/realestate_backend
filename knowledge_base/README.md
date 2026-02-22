# Odoo Development Knowledge Base

🎯 **Base de conhecimento completa com melhores práticas oficiais do Odoo 19.0**

Esta knowledge base foi criada a partir da documentação oficial do Odoo e contém diretrizes essenciais para desenvolvimento de módulos de alta qualidade.

---

## 📚 Documentação Principal

### 🏗️ Estrutura e Organização
| Documento | Descrição | Tópicos |
|-----------|-----------|---------|
| [📁 Module Structure](01-module-structure.md) | Organização de diretórios e arquivos | `models/`, `views/`, `controllers/`, `security/`, `data/`, `static/` |
| [📝 File Naming Conventions](02-file-naming-conventions.md) | Convenções de nomenclatura | Models, views, controllers, wizards, reports |

### 💻 Código e Padrões
| Documento | Descrição | Tópicos |
|-----------|-----------|---------|
| [🐍 Python Coding Guidelines](03-python-coding-guidelines.md) | Diretrizes de código Python | PEP 8, imports, idioms, builtins |
| [📄 XML Guidelines](04-xml-guidelines.md) | Padrões para arquivos XML | Records, views, actions, menus, herança |
| [⚡ JavaScript Guidelines](05-javascript-guidelines.md) | Convenções JavaScript | OWL, widgets, templates, async/await |
| [🎨 CSS and SCSS Guidelines](06-css-scss-guidelines.md) | Padrões de estilização | Sintaxe, naming, variáveis, mixins |

### 🔧 Práticas de Desenvolvimento
| Documento | Descrição | Tópicos |
|-----------|-----------|---------|
| [🚀 Programming in Odoo](07-programming-in-odoo.md) | Boas práticas específicas do framework | Context, extensibilidade, transações, exceções |
| [🏷️ Symbols and Conventions](08-symbols-conventions.md) | Nomenclatura de variáveis, métodos e classes | Models, fields, methods, ordenação de atributos |
| [🗄️ Database Best Practices](09-database-best-practices.md) | Boas práticas para banco de dados relacional | Normalização, nomenclatura, índices, constraints, migrations |

### 🖥️ Frontend e Infraestrutura
| Documento | Descrição | Tópicos |
|-----------|-----------|---------|
| [🖼️ Frontend & Views](10-frontend-views-odoo18.md) | Diretrizes de views e frontend | Views, templates, OWL, assets |
| [📧 Email Sending Odoo 18](11-email-sending-odoo18.md) | Guia definitivo de envio de emails | mail.template vs mail.mail, inline_template engine, troubleshooting |

---

## 🎯 Guias Rápidos

### ⚡ Quick Reference
**[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Referência rápida com checklists, padrões comuns e atalhos

**Conteúdo:**
- ✅ Checklist de novo módulo
- 🎯 Padrões mais usados
- ⚡ Métodos comuns
- 🛡️ Regras de segurança
- 📊 Campos relacionais
- ⚠️ Regras críticas (fazer/evitar)

### 💡 Practical Examples
**[EXAMPLES.md](EXAMPLES.md)** - Exemplos práticos e completos

**Conteúdo:**
- 📦 Módulo completo (Real Estate)
- 🏗️ Estrutura de diretórios
- 🐍 Models completos com herança
- 📄 Views (form, list, search)
- 🛡️ Segurança (access rights, record rules)
- 🔧 Integration (mail, chatter)

---

## 🚀 Início Rápido

### Para Iniciantes

1. **Entenda a estrutura:**
   - Leia [Module Structure](01-module-structure.md)
   - Leia [File Naming Conventions](02-file-naming-conventions.md)

2. **Aprenda os padrões:**
   - Consulte [Python Guidelines](03-python-coding-guidelines.md)
   - Consulte [XML Guidelines](04-xml-guidelines.md)

3. **Veja exemplos:**
   - Estude [EXAMPLES.md](EXAMPLES.md)
   - Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) como cola

### Para Desenvolvedores Experientes

**Referência rápida por tarefa:**

| Preciso de | Consultar |
|------------|-----------|
| 🏗️ Criar estrutura de módulo | [Module Structure](01-module-structure.md) |
| 📝 Nomear arquivos corretamente | [File Naming](02-file-naming-conventions.md) |
| 🐍 Escrever código Python | [Python Guidelines](03-python-coding-guidelines.md) + [Programming in Odoo](07-programming-in-odoo.md) |
| 📄 Criar views e ações | [XML Guidelines](04-xml-guidelines.md) |
| ⚡ Implementar widgets JS | [JavaScript Guidelines](05-javascript-guidelines.md) |
| 🎨 Estilizar componentes | [CSS/SCSS Guidelines](06-css-scss-guidelines.md) |
| 🏷️ Nomear variáveis/métodos | [Symbols & Conventions](08-symbols-conventions.md) |
| �️ Design de banco de dados | [Database Best Practices](09-database-best-practices.md) |
| �💡 Ver exemplos práticos | [EXAMPLES.md](EXAMPLES.md) |
| ⚡ Consulta rápida | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |

---

## 🔗 Referências Oficiais

- 📖 [Odoo 19.0 Coding Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html)
- 📖 [Odoo 19.0 Developer Documentation](https://www.odoo.com/documentation/19.0/developer.html)
- 🔐 [Security Pitfalls](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#reference-security-pitfalls)
- 🦉 [OWL Framework](https://github.com/odoo/owl)

---

## ⚠️ Regras Críticas

### ❌ NUNCA Faça

1. **`cr.commit()` ou `cr.rollback()`** manualmente (framework gerencia)
2. **Hardcode de credenciais** ou dados sensíveis
3. **Capturar `Exception` genérica** sem especificar tipo
4. **Adicionar bibliotecas minificadas** ao código
5. **Usar seletores `id`** em CSS
6. **Modificar código estável** apenas para aplicar guidelines

### ✅ SEMPRE Faça

1. **Use `filtered`, `mapped`, `sorted`** para iterações
2. **Prefixe módulos** da comunidade (`thedevkitchen_`, `mycompany_`)
3. **Documente código** com docstrings
4. **Organize imports** (stdlib, odoo, addons)
5. **Use savepoints** ao capturar exceções
6. **Siga ADRs do projeto** quando disponíveis

---

## 📊 Estrutura dos Documentos

Cada documento da knowledge base contém:

- 📋 **Introdução** - Conceitos e princípios
- 📝 **Regras e Convenções** - Padrões obrigatórios
- ✅ **Boas Práticas** - O que fazer
- ❌ **Anti-patterns** - O que evitar
- 💡 **Exemplos** - Código real demonstrando uso correto
- 🔗 **Referências** - Links para documentação oficial

---

## 🔄 Atualização e Manutenção

**Última atualização:** 05/02/2026  
**Baseado em:** Odoo 19.0 Official Documentation

**Como manter atualizado:**
1. Revisar documentação oficial periodicamente
2. Atualizar exemplos com novas features
3. Adicionar casos de uso reais do projeto
4. Incorporar feedback da equipe

---

## 💡 Como Usar Esta Knowledge Base

### Durante o Desenvolvimento

1. **Antes de começar:** Consulte [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. **Durante codificação:** Tenha os guias relevantes abertos
3. **Ao criar estrutura:** Siga [Module Structure](01-module-structure.md)
4. **Ao nomear:** Use [Symbols & Conventions](08-symbols-conventions.md)
5. **Para exemplos:** Consulte [EXAMPLES.md](EXAMPLES.md)

### Durante Code Review

1. Verifique se segue [File Naming](02-file-naming-conventions.md)
2. Valide padrões [Python](03-python-coding-guidelines.md) / [XML](04-xml-guidelines.md)
3. Confirme [Symbols & Conventions](08-symbols-conventions.md)
4. Compare com [EXAMPLES.md](EXAMPLES.md)

### Para Novos Membros da Equipe

1. Leia [README.md](README.md) (este arquivo)
2. Estude [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. Pratique com [EXAMPLES.md](EXAMPLES.md)
4. Consulte guias específicos conforme necessário

---

## 🎓 Níveis de Conhecimento

### Iniciante
**Priorize:**
- [Module Structure](01-module-structure.md)
- [File Naming](02-file-naming-conventions.md)
- [EXAMPLES.md](EXAMPLES.md)
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

### Intermediário
**Adicione:**
- [Python Guidelines](03-python-coding-guidelines.md)
- [XML Guidelines](04-xml-guidelines.md)
- [Programming in Odoo](07-programming-in-odoo.md)

### Avançado
**Complete com:**
- [JavaScript Guidelines](05-javascript-guidelines.md)
- [CSS/SCSS Guidelines](06-css-scss-guidelines.md)
- [Symbols & Conventions](08-symbols-conventions.md)

---

## 📞 Suporte e Recursos

- 💬 [Odoo Community Forums](https://www.odoo.com/forum)
- 📧 [Odoo Support](https://odoo.com/help)
- 📚 [Odoo Documentation](https://www.odoo.com/documentation/19.0/)
- 🐙 [Odoo GitHub](https://github.com/odoo/odoo)

---

**Happy Coding! 🚀**
