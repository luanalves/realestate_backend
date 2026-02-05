# Programming in Odoo - Programação Específica do Framework

## Princípios Gerais

- ❌ **Evite** criar generators e decorators: use apenas os fornecidos pela API do Odoo
- ✅ **Use** métodos como `filtered`, `mapped`, `sorted` para facilitar leitura e performance

## 1. Propagate the Context (Propagar o Contexto)

### O que é o Context?

O context é um `frozendict` que **não pode ser modificado**. Para chamar um método com contexto diferente, use `with_context`:

```python
# Substituir todo o contexto
records.with_context(new_context).do_stuff()

# Adicionar/sobrescrever valores no contexto
records.with_context(**additional_context).do_other_stuff()
```

### ⚠️ Warning: Side Effects Perigosos

Passar parâmetros no context pode ter **efeitos colaterais perigosos**.

**Problema:** Os valores são propagados automaticamente, causando comportamentos inesperados.

#### Exemplo de Problema

```python
# Se você criar com default_my_field no context:
self.with_context(default_my_field='value').create({...})

# PROBLEMA: Todos os objetos criados durante essa operação
# que tenham um campo my_field receberão esse valor padrão!
# Isso inclui sale.order.line, produtos, etc.
```

### ✅ Boas Práticas para Context

1. **Escolha nomes descritivos e específicos**
2. **Prefixe com o nome do módulo** para isolar impacto
3. **Exemplo do módulo `mail`:**
   - `mail_create_nosubscribe`
   - `mail_notrack`
   - `mail_notify_user_signature`

```python
# ✅ Bom - nome específico e prefixado
self.with_context(mail_create_nosubscribe=True).create({...})

# ❌ Ruim - nome genérico
self.with_context(no_subscribe=True).create({...})
```

## 2. Think Extendable (Pense em Extensibilidade)

### Princípio da Responsabilidade Única

Funções e métodos **não devem conter muita lógica**:
- ✅ Muitos métodos pequenos e simples
- ❌ Poucos métodos grandes e complexos

**Regra prática:** Divida um método quando ele tem **mais de uma responsabilidade**.

Referência: [Single Responsibility Principle](http://en.wikipedia.org/wiki/Single_responsibility_principle)

### Evite Hardcoding de Lógica de Negócio

Hardcoding impede que o módulo seja facilmente estendido por submódulos.

#### ❌ Exemplo Ruim - Lógica Hardcoded

```python
def action(self):
    ...  # método longo
    # Domain complexo hardcoded - difícil de estender
    partners = self.env['res.partner'].search([
        ('active', '=', True),
        ('customer', '=', True),
        ('country_id.code', '=', 'BR')
    ])
    # Critério arbitrário hardcoded
    emails = partners.filtered(lambda r: r.email and '@' in r.email).mapped('email')
```

#### ⚠️ Exemplo Melhor, Mas Ainda Não Ideal

```python
def action(self):
    ...
    partners = self._get_partners()
    emails = partners._get_emails()

# Problema: Para modificar a lógica, precisa duplicar código
```

#### ✅ Exemplo Ideal - Máxima Extensibilidade

```python
def action(self):
    ...
    partners = self.env['res.partner'].search(self._get_partner_domain())
    emails = partners.filtered(lambda r: r._filter_partners()).mapped('email')

def _get_partner_domain(self):
    """Retorna o domain para buscar partners.
    
    Override este método para customizar a busca.
    """
    return [
        ('active', '=', True),
        ('customer', '=', True),
        ('country_id.code', '=', 'BR')
    ]

def _filter_partners(self):
    """Verifica se partner deve ser incluído.
    
    Override este método para customizar o filtro.
    
    Returns:
        bool: True se partner deve ser incluído
    """
    return self.email and '@' in self.email
```

**Nota:** O código acima é extensível ao extremo para fins de exemplo. Um **trade-off** deve ser feito entre extensibilidade e legibilidade.

### Nomenclatura de Funções

Funções pequenas e bem nomeadas são o ponto de partida para:
- ✅ Código legível
- ✅ Código manutenível  
- ✅ Documentação clara

**Aplica-se também a:** classes, arquivos, módulos e packages.

Referência: [Cyclomatic Complexity](http://en.wikipedia.org/wiki/Cyclomatic_complexity)

## 3. Never Commit the Transaction (Nunca Commit Manual)

### ⚠️ REGRA CRÍTICA

**Você NUNCA deve chamar `cr.commit()` ou `cr.rollback()` você mesmo**, A MENOS QUE tenha explicitamente criado seu próprio cursor de banco de dados!

### Como o Framework Funciona

O framework Odoo fornece o contexto transacional para todas as chamadas RPC:

```python
def execute(self, db_name, uid, obj, method, *args, **kw):
    db, pool = pooler.get_db_and_pool(db_name)
    # Cria cursor de transação
    cr = db.cursor()
    try:
        res = pool.execute_cr(cr, uid, obj, method, *args, **kw)
        cr.commit()  # Tudo OK, commit automático
    except Exception:
        cr.rollback()  # Erro, rollback atômico
        raise
    finally:
        cr.close()  # Sempre fecha cursor
    return res
```

### Consequências de `cr.commit()` Manual

Se você chamar `cr.commit()` manualmente, **alta chance de quebrar o sistema**:

1. **Dados inconsistentes** - Perda de dados
2. **Workflows dessincronizados** - Documentos travados permanentemente
3. **Testes poluídos** - Testes não podem fazer rollback limpo

### Quando NÃO Precisa de `cr.commit()`

❌ Você NÃO precisa de `cr.commit()` nos seguintes casos:

- No método `_auto_init()` de models.Model
- Em relatórios
- Em métodos models.TransientModel (wizards)
- Em qualquer método normal de modelo

### Quando É Permitido (Raríssimo)

✅ Apenas quando você **explicitamente criar seu próprio cursor**:

```python
# Situação rara - você criou o cursor
new_cr = self.env.registry.cursor()
try:
    # Faça operações
    new_cr.commit()
except Exception:
    new_cr.rollback()
    raise
finally:
    new_cr.close()
```

**E você DEVE:**
- Tratar casos de erro
- Fazer rollback apropriado
- Fechar o cursor quando terminar

## 4. Avoid Catching Exceptions (Evite Capturar Exceções)

### Princípio

- ✅ Capture **apenas exceções específicas**
- ❌ Evite blocos try-catch muito amplos
- ✅ Limite o escopo do try-catch o máximo possível

Exceções não capturadas serão **logadas e tratadas apropriadamente** pelo framework.

### ❌ Exemplo Ruim

```python
try:
    do_something()
except Exception as e:
    # Se capturamos ValidationError, não fizemos rollback
    # e deixamos o ORM em estado indefinido!
    _logger.warning(e)
```

### ✅ Use Savepoints

Para ações agendadas (scheduled actions), use **savepoints** para isolar sua função:

```python
try:
    with self.env.cr.savepoint():
        do_stuff()
except ValidationError:
    # Exceção específica
    handle_validation_error()
except AccessError:
    # Outra exceção específica
    handle_access_error()
```

**Savepoints:**
- Flush computações ao entrar no bloco
- Rollback correto em caso de exceções

### ⚠️ Warning: Performance de Savepoints

- Após **64 savepoints** em uma única transação, PostgreSQL fica lento
- Se o servidor tem réplicas, savepoints têm overhead grande
- **Se processar em loop:** limite o tamanho do batch
- **Muitos registros:** considere usar scheduled job

Referência: [Scheduled Actions (ir.cron)](https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#reference-actions-cron)

## 5. Filtered, Mapped, Sorted

Use os métodos do framework Odoo para facilitar leitura e performance:

```python
# ✅ Bom - legível e eficiente
active_partners = partners.filtered(lambda p: p.active)
partner_names = partners.mapped('name')
sorted_partners = partners.sorted(key=lambda p: p.name)

# ✅ Ainda melhor - sem lambda quando possível
partner_names = partners.mapped('name')
partner_emails = partners.mapped('email')

# ❌ Evite loops quando pode usar filtered/mapped
names = []
for partner in partners:
    names.append(partner.name)
```

## Resumo das Regras

| Regra | ✅ Fazer | ❌ Evitar |
|-------|---------|-----------|
| **Context** | Nomes específicos e prefixados | Nomes genéricos |
| **Extensibilidade** | Métodos pequenos e focados | Lógica hardcoded |
| **Transações** | Deixar framework gerenciar | `cr.commit()` manual |
| **Exceções** | Específicas e com savepoint | `except Exception` genérico |
| **Iterações** | `filtered`, `mapped`, `sorted` | Loops manuais |

## Referências

- [Odoo Programming Guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html#programming-in-odoo)
- [Security Pitfalls](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#reference-security-pitfalls)
- [Scheduled Actions](https://www.odoo.com/documentation/19.0/developer/reference/backend/actions.html#reference-actions-cron)
