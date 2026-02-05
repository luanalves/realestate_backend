# Python Coding Guidelines - Diretrizes de Código Python

## ⚠️ Security Warning

**SEMPRE leia a seção [Security Pitfalls](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html#reference-security-pitfalls) para escrever código seguro!**

## PEP 8 Options

### Regras que Podem Ser Ignoradas

Odoo tenta respeitar o padrão Python (PEP 8), mas algumas regras podem ser ignoradas:

- **E501:** line too long (linha muito longa)
- **E301:** expected 1 blank line, found 0
- **E302:** expected 2 blank lines, found 1

**Recomendação:** Use um linter (pylint, flake8) para ajudar a identificar problemas.

## Imports

### Ordem de Importação

Os imports devem ser organizados em **3 grupos**, cada um alfabeticamente ordenado:

```python
# 1: Bibliotecas externas Python (stdlib)
import base64
import re
import time
from datetime import datetime

# 2: Imports de submódulos Odoo
from odoo import Command, _, api, fields, models  # Alfabeticamente
from odoo.fields import Domain
from odoo.tools.safe_eval import safe_eval as eval

# 3: Imports de addons Odoo (raramente, apenas se necessário)
from odoo.addons.web.controllers.main import login_redirect
from odoo.addons.website.models.website import slug
```

### ✅ Boas Práticas
- Um import por linha (para bibliotecas externas)
- Ordem alfabética dentro de cada grupo
- Linha em branco separando os 3 grupos

### ❌ Evitar
```python
# Ruim - tudo misturado
from odoo import models, fields
import datetime
from odoo.addons.website import slug
import base64
```

## Idiomatics of Programming (Python)

### 1. Favor Legibilidade

**SEMPRE favoreça legibilidade** sobre concisão ou uso de features/idiomas da linguagem.

### 2. Não Use `.clone()`

```python
# ❌ Ruim
new_dict = my_dict.clone()
new_list = old_list.clone()

# ✅ Bom
new_dict = dict(my_dict)
new_list = list(old_list)
```

### 3. Python Dictionary

#### Criação

```python
# -- Criação de dict vazio
my_dict = {}           # ✅ Preferido
my_dict2 = dict()      # ✅ OK

# -- Criação com valores
# ❌ Ruim
my_dict = {}
my_dict['foo'] = 3
my_dict['bar'] = 4

# ✅ Bom
my_dict = {'foo': 3, 'bar': 4}
```

#### Atualização

```python
# ❌ Ruim
my_dict['foo'] = 3
my_dict['bar'] = 4
my_dict['baz'] = 5

# ✅ Bom
my_dict.update(foo=3, bar=4, baz=5)
my_dict = dict(my_dict, **my_dict2)
```

### 4. Variáveis Significativas

Use nomes de variáveis/classes/métodos significativos.

```python
# ❌ Ruim - variável temporária desnecessária
schema = kw['schema']
params = {'schema': schema}

# ✅ Bom - mais simples
params = {'schema': kw['schema']}
```

### 5. Múltiplos Return Points

Múltiplos pontos de retorno são OK quando tornam o código mais simples:

```python
# ❌ Um pouco complexo e com variável temporária redundante
def axes(self, axis):
    axes = []
    if type(axis) == type([]):
        axes.extend(axis)
    else:
        axes.append(axis)
    return axes

# ✅ Mais claro
def axes(self, axis):
    if type(axis) == type([]):
        return list(axis)  # clone the axis
    else:
        return [axis]  # single-element list
```

### 6. Conheça os Builtins

Você deve ter entendimento básico de todos os Python builtins:
[http://docs.python.org/library/functions.html](http://docs.python.org/library/functions.html)

```python
# ❌ Muito redundante
value = my_dict.get('key', None)

# ✅ Bom
value = my_dict.get('key')
```

**Importante:** `if 'key' in my_dict` e `if my_dict.get('key')` têm significados muito diferentes!

### 7. List/Dict Comprehensions

Use comprehensions para tornar o código mais legível:

```python
# ❌ Não muito bom
cube = []
for i in res:
    cube.append((i['id'], i['name']))

# ✅ Melhor
cube = [(i['id'], i['name']) for i in res]
```

### 8. Collections são Booleanos

Em Python, coleções têm valor "boolean-ish":
- **Falsy** quando vazias
- **Truthy** quando contêm itens

```python
bool([]) is False
bool([1]) is True
bool([False]) is True  # Lista contém item!
```

```python
# ❌ Ruim
if len(some_collection):
    do_something()

# ✅ Bom
if some_collection:
    do_something()
```

### 9. Itere sobre Iteráveis

```python
# ❌ Cria lista temporária desnecessária
for key in my_dict.keys():
    "do something..."

# ✅ Melhor
for key in my_dict:
    "do something..."

# ✅ Acessando key e value
for key, value in my_dict.items():
    "do something..."
```

### 10. Use dict.setdefault

```python
# ❌ Mais longo... mais difícil de ler
values = {}
for element in iterable:
    if element not in values:
        values[element] = []
    values[element].append(other_value)

# ✅ Melhor... use dict.setdefault
values = {}
for element in iterable:
    values.setdefault(element, []).append(other_value)
```

## Documentação

### Docstrings e Comentários

- ✅ Docstring em métodos
- ✅ Comentários simples para partes complexas do código
- ✅ Código auto-explicativo é melhor que comentários

```python
def compute_price(self):
    """
    Calcula o preço total incluindo impostos e descontos.
    
    Returns:
        float: Preço total calculado
    """
    # Aplicar desconto progressivo para grandes volumes
    if self.quantity > 100:
        discount = 0.15
    else:
        discount = 0.05
    
    return self.unit_price * self.quantity * (1 - discount)
```

## Links Úteis

- [Idiomatic Python](https://david.goodger.org/projects/pycon/2007/idiomatic/handout.html) - Um pouco desatualizado, mas relevante
- [PEP 8 - Style Guide](https://pep8.org/)
- [Python Built-in Functions](http://docs.python.org/library/functions.html)

## Próximos Passos

Continue lendo:
- [Programming in Odoo](07-programming-in-odoo.md) - Práticas específicas do framework
- [Symbols and Conventions](08-symbols-conventions.md) - Nomenclatura de variáveis e métodos
