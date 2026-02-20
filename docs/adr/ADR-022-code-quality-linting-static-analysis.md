# ADR-022: Qualidade de Código, Linting e Análise Estática

## Status
**Aceito** - 2026-02-05

## Contexto

Durante o desenvolvimento do projeto, identificamos que a qualidade do código pode variar significativamente entre desenvolvedores e ao longo do tempo. Embora tenhamos ADRs sobre testes (ADR-003), padrões de desenvolvimento Odoo (ADR-001) e nomenclatura (ADR-004), ainda não há uma definição clara sobre ferramentas automatizadas de qualidade de código.

### Problemas Identificados

1. **Inconsistência de estilo**: Diferentes desenvolvedores seguem estilos diferentes
2. **Code smells não detectados**: Código duplicado, funções muito longas, alta complexidade
3. **Falta de documentação**: Docstrings ausentes ou incompletos
4. **Imports desorganizados**: Ordem e agrupamento inconsistentes
5. **Problemas detectados apenas em code review**: Tempo desperdiçado com issues triviais
6. **Dívida técnica crescente**: Sem métricas objetivas para medir qualidade

### Restrições

- O projeto usa **Odoo 18.0** (Python 3.10+)
- Desenvolvimento em containers Docker
- CI/CD usando GitHub Actions (ou similar)
- Equipe trabalha em macOS, Linux e Windows
- Tempo de execução de CI deve ser razoável (< 10 minutos)

## Decisão

Adotamos um conjunto de ferramentas automatizadas para garantir qualidade de código consistente em todo o projeto.

### 1. Ferramentas Obrigatórias

#### Python

| Ferramenta | Propósito | Configuração |
|------------|-----------|--------------|
| **black** | Formatação automática de código | `line-length = 100` |
| **isort** | Organização de imports | Compatível com black |
| **flake8** | Linting (PEP 8, erros, code smells) | Integrado com black |
| **pylint** | Análise estática profunda | Específico para Odoo |
| **mypy** | Type checking estático | Modo gradual (não-strict) |

#### XML/Views (Novo - 2026-02-08)

| Ferramenta | Propósito | Localização |
|------------|-----------|-------------|
| **lint_xml.py** | Detecta erros de views Odoo 18.0 | `18.0/lint_xml.py` |
| **lint_xml.sh** | Wrapper shell para XML linter | `18.0/lint_xml.sh` |

**Erros detectados pelo XML linter:**
- ❌ `<tree>` deprecated (usar `<list>`)
- ❌ `attrs` deprecated (usar atributos diretos)
- ❌ `column_invisible` com expressões Python (causa OwlError)
- ❌ `ref()` em action context
- ⚠️ Views sem nome/modelo definido

**Documentação:** Ver `18.0/LINT_XML_README.md`

### 2. Configuração Padrão

#### **pyproject.toml** (configuração centralizada)

```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
  | migrations
  | __pycache__
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
skip_glob = ["*/migrations/*", "*/__pycache__/*"]

[tool.pylint.messages_control]
disable = [
    "C0103",  # invalid-name (Odoo usa _name, _inherit)
    "C0114",  # missing-module-docstring
    "R0903",  # too-few-public-methods (models Odoo)
    "W0212",  # protected-access (_name é padrão Odoo)
]

[tool.pylint.format]
max-line-length = 100

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
# Modo gradual - não forçar tipos em todo código legacy
check_untyped_defs = false
disallow_untyped_defs = false
```

#### **.flake8** (não suporta pyproject.toml)

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist,
    migrations,
    *.egg-info
per-file-ignores =
    __init__.py: F401
```

### 3. Pre-commit Hooks

Criar arquivo `.pre-commit-config.yaml` na raiz do projeto:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        name: isort (python)

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-merge-conflict
```

**Instalação**:
```bash
# Instalar pre-commit
pip install pre-commit

# Instalar hooks no repositório
pre-commit install

# Executar em todos os arquivos (primeira vez)
pre-commit run --all-files
```

### 4. CI/CD Pipeline

Adicionar ao GitHub Actions (`.github/workflows/code-quality.yml`):

```yaml
name: Code Quality

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install black isort flake8 pylint mypy
      
      - name: Run black
        run: black --check --diff 18.0/extra-addons/
      
      - name: Run isort
        run: isort --check-only --diff 18.0/extra-addons/
      
      - name: Run flake8
        run: flake8 18.0/extra-addons/
      
      - name: Run pylint
        run: |
          pylint 18.0/extra-addons/ --rcfile=pyproject.toml --exit-zero
      
      - name: Run mypy
        run: mypy 18.0/extra-addons/ --config-file=pyproject.toml
      
      - name: Lint XML Views
        run: |
          cd 18.0
          docker compose up -d odoo
          docker compose exec -T odoo python3 /mnt/extra-addons/../lint_xml.py /mnt/extra-addons/
```

**Python:**
- ✅ **Black passou**: Código formatado automaticamente
- ✅ **Isort passou**: Imports organizados
- ✅ **Flake8 passou**: Sem erros de linting (score 10/10)
- ✅ **Pylint score ≥ 8.0/10**: Qualidade mínima aceitável

**XML/Views:**
- ✅ **XML Linter passou**: Sem erros de views Odoo 18.0
- ✅ **Sem `<tree>` tags**: Usar `<list>` instead
- ✅ **Sem `attrs`**: Usar atributos diretos
- ✅ **Sem `column_invisible` com expressões**: Usar `optional`

**Geral:**
Antes de aprovar um PR, verificar:

- ✅ **Black passou**: Código formatado automaticamente
- ✅ **Isort passou**: Imports organizados
- ✅ **Flake8 passou**: Sem erros de linting (score 10/10)
- ✅ **Pylint score ≥ 8.0/10**: Qualidade mínima aceitável
- ✅ **Docstrings obrigatórios**:
  - Todos os métodos públicos
  - Todas as classes
  - Módulos principais
- ✅ **Complexidade ciclomática ≤ 10** por função
- ✅ **Funções ≤ 50 linhas** (guideline, não hard limit)
- ✅ **Testes passando** (ver ADR-003)

#### **Docstrings Obrigatórios**

Seguir padrão Google Style:

```python
def calculate_commission(self, sale_value, commission_rate):
    """Calculate agent commission based on sale value.

    Args:
        sale_value (float): Total value of the property sale.
        commission_rate (float): Commission percentage (0-100).

    Returns:
        float: Calculated commission amount.

    Raises:
        ValidationError: If sale_value or commission_rate is invalid.

    Example:
        >>> self.calculate_commission(100000.0, 5.0)
        5000.0
    """
    if sale_value <= 0:
        raise ValidationError("Sale value must be positive")
    if not 0 <= commission_rate <= 100:
        raise ValidationError("Commission rate must be between 0 and 100")
    
    return sale_value * (commission_rate / 100)
```

### 6. Exceções e Casos Especiais

#### **Código Odoo Legacy**
- Não é obrigatório refatorar código de módulos core do Odoo
- Apenas nosso código customizado (`thedevkitchen_*`) deve seguir as regras

#### **Arquivos Gerados**
Ignorar (já configurado):
- `migrations/`
- `__pycache__/`
- `.pyc` files
- `build/`, `dist/`

#### **Pylint - Desabilitar com justificativa**
Quando inevitável:
```python
# pylint: disable=broad-except
# Justificativa: Precisamos capturar qualquer exceção do Odoo neste contexto
try:
    self.env['model'].create(vals)
except Exception as e:
    _logger.error("Failed to create record: %s", e)
```

### 7. Integração com VS Code

Recomendado adicionar ao `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true
  } lint-xml

# Formatar código automaticamente
format:
	black 18.0/extra-addons/
	isort 18.0/extra-addons/

# Verificar qualidade Python (sem modificar)
lint:
	black --check --diff 18.0/extra-addons/
	isort --check-only --diff 18.0/extra-addons/
	flake8 18.0/extra-addons/
	pylint 18.0/extra-addons/ --exit-zero

# Verificar XML views
lint-xml:
	cd 18.0 && ./lint_xml.sh extra-addons/

# Verificar tudo antes de commit
check-quality: lint lint-xml
	@echo "Running tests..."
	cd 18.0 && ./run_all_tests.sh
	@echo "✅ All quality checks passed!"
```

**Uso:**
```bash
# Antes de commitar
make format        # Formata código automaticamente
make lint          # Verifica problemas Python
make lint-xml      # Verifica problemas XML/Views
make check-quality # Roda tudo (lint + lint-xml
	@echo "✅ All quality checks passed!"
```

**Uso:**
```bash
# Antes de commitar
make format        # Formata código automaticamente
make lint          # Verifica problemas
make check-quality # Roda tudo (lint + testes)
```

## Consequências

### Positivas

✅ **Qualidade consistente**: Todo código segue o mesmo padrão, independente do desenvolvedor

✅ **Code review mais rápido**: Issues triviais são detectadas automaticamente
etecção precoce de erros Odoo 18.0**: XML linter previne erros de runtime no browser

✅ **Documentação melhor**: Docstrings obrigatórios melhoram compreensão do código

✅ **Refatoração segura**: Ferramentas detectam quebras não intencionais

✅ **Métricas objetivas**: Pylint score fornece KPI de qualidade

✅ **CI/CD confiável**: Builds não passam com código de baixa qualidade

✅ **Compliance Odoo 18.0**: Garante compatibilidade com versão atual
✅ **Refatoração segura**: Ferramentas detectam quebras não intencionais

✅ **Métricas objetivas**: Pylint score fornece KPI de qualidade

✅ **CI/CD confiável**: Builds não passam com código de baixa qualidade

### Negativas

⚠️ **Curva de aprendizado inicial**: Desenvolvedores precisam aprender ferramentas

⚠️ **Tempo de CI aumenta**: ~2-3 minutos extras por build (aceitável)

⚠️ **Falsos positivos ocasionais**: Pylint pode reclamar de padrões Odoo válidos

⚠️ **Configuração inicial trabalhosa**: Setup das ferramentas e configs

⚠️ **Resistência de desenvolvedores**: Alguns podem achar "burocrático"

### Mitigações

- **Documentação clara**: README com setup e comandos
- **Pre-commit hooks**: Feedback imediato antes de commit
- **Exceções documentadas**: Casos onde é OK desabilitar regras
- **Graduação**: Começar com avisos, depois tornar obrigatório
- **Treinamento**: Sessões sobre as ferramentas

### Código Legacy

Para código existente (`quicksol_estate` antigo):

1.**XML Linter falha** | ❌ CI falha - PR bloqueado |
|  **Não bloquear**: Continuar trabalhando normalmente
2. **Gradual cleanup**: Aplicar formatação ao modificar arquivos
3. **Boy Scout Rule**: "Deixe o código melhor do que encontrou"
4. **Sprint de limpeza**: Dedicar tempo para refatoração periódica

### Impacto em PRs, **XML linter**

**NOVO comportamento de PRs:**

| Situação | Resultado |
|----------|-----------|
| Black falha | ❌ CI falha - PR bloqueado |
| Isort falha | ❌ CI falha - PR bloqueado |
| Flake8 falha | ❌ CI falha - PR bloqueado |
| Pylint < 8.0 | ⚠️ Aviso (não bloqueia ainda) |
| Mypy falha | ⚠️ Aviso (não bloqueia ainda) |
| Testes falham | ❌ CI falha - PR bloqueado (ADR-003) |

**Transição:**
- **Fase 1 (primeiros 30 dias)**: Todos em modo "aviso"
- **Fase 2 (após 30 dias)**: Black, isort, flake8 bloqueiam PRs
- **Fase 3 (após 60 dias)**: Pylint com score mínimo 8.0 bloqueia PRs

## Relação com Outras ADRs

Esta ADR complementa:
- **ADR-001**: Padrões de desenvolvimento Odoo (estrutura, camadas)
- **ADR-003**: Testes obrigatórios (qualidade através de testes)
- **ADR-004**: Nomenclatura padronizada (convenções de nomes)

**Juntas formam o "tripé de qualidade":**
1. **ADR-001**: Como estruturar o código
2. **ADR-003**: Como garantir que funciona (testes)
3. **ADR-004**: Como nomear (convenções)
4. **ADR-022**: Como manter limpo (linting e análise estática)

## Code Documentation Philosophy (Emenda 2026-02-20)

### Decisão: Priorizar Código Auto-Explicativo sobre Docstrings Extensivas

**Status**: Aceito - 2026-02-20

#### Contexto

Durante revisão de código em 2026-02-20, identificamos que docstrings extensivas podem:
1. Ficar desatualizadas mais rápido que o código
2. Adicionar ruído visual ao código
3. Duplicar informações que já estão claras pelo código bem escrito
4. Criar falsa sensação de segurança ("está documentado, então está correto")

A filosofia de **Clean Code** prega que "código que precisa de comentários para ser entendido não é um bom código".

#### Princípios Adotados

**1. Código Auto-Explicativo é a Documentação Principal**

✅ **PREFERIR** (código claro):
```python
def strip_non_digits(document: str) -> str:
    """Remove formatting, keeping only digits."""
    return re.sub(r'[^0-9]', '', document)

CPF_LENGTH = 11  # Brazilian individual tax ID
CNPJ_LENGTH = 14  # Brazilian company tax ID

def is_cpf(document: str) -> bool:
    return len(document) == CPF_LENGTH and _checksum_valid(document)
```

❌ **EVITAR** (docstring extensa com informações óbvias):
```python
def normalize_document(document):
    """
    Strip all non-digit characters from a document string (CPF or CNPJ).
    
    This function takes a document string that may contain formatting
    characters like dots, dashes, and slashes, and returns only the
    numeric digits. This is useful for standardizing document formats
    before validation or storage.
    
    Args:
        document (str): CPF/CNPJ with or without formatting. Can be
                       formatted as XXX.XXX.XXX-XX (CPF) or 
                       XX.XXX.XXX/XXXX-XX (CNPJ), or just digits.
        
    Returns:
        str: A string containing only numeric digits (0-9). If the input
             is empty or None, returns an empty string.
        
    Example:
        >>> normalize_document('123.456.789-01')
        '12345678901'
        >>> normalize_document('12.345.678/0001-95')
        '12345678000195'
        >>> normalize_document('')
        ''
        
    Note:
        This function does not validate the document format or checksum.
        Use validate_document() or is_cpf()/is_cnpj() for validation.
    """
    if not document:
        return ''
    return re.sub(r'[^0-9]', '', document)
```

**2. Quando Usar Docstrings (Exceções)**

✅ **Docstrings OBRIGATÓRIAS apenas para**:
- **Regras de negócio não-óbvias** (ex: validação CRECI varia por estado)
- **Comportamentos contra-intuitivos** (ex: context flags que bypassam validação)
- **APIs públicas** que serão consumidas por outros módulos/equipes
- **Formatos específicos do domínio brasileiro** (ex: CRECI/SP 123456 vs CRECI-RJ 12345)

✅ **Formato Minimalista** (1 linha quando possível):
```python
def validate_creci(creci: str, state_code: Optional[str] = None) -> bool:
    """Brazilian broker license. Format: CRECI/SP 123456 (varies by state)."""
    # Implementation...

def write(self, vals):
    """Override to validate transitions. Context flags: cron_expire, lease_terminate."""
    # Implementation...
```

**3. Type Hints > Docstrings para Tipos**

✅ **PREFERIR** type hints explícitos:
```python
from typing import Optional, Literal

DocumentType = Literal['cpf', 'cnpj']

def validate_document(document: str, doc_type: Optional[DocumentType] = None) -> bool:
    """Validates CPF (11 digits) or CNPJ (14 digits)."""
    pass
```

❌ **EVITAR** documentar tipos em docstrings quando type hints já existem:
```python
def validate_document(document, doc_type=None):
    """Validate a document.
    
    Args:
        document (str): The document string  # ❌ Redundante com type hint
        doc_type (str, optional): Either 'cpf' or 'cnpj'  # ❌ Redundante
    
    Returns:
        bool: True if valid  # ❌ Redundante
    """
```

**4. Constants e Inline Comments para Regras de Negócio**

✅ **PREFERIR** constants com comments inline:
```python
# Valid CRECI formats by state (Brazilian real estate broker license)
CRECI_PATTERN_SP = r'CRECI[/-]?SP\s*\d{6}'  # São Paulo: 6 digits
CRECI_PATTERN_RJ = r'CRECI[/-]?RJ\s*\d{5}'  # Rio de Janeiro: 5 digits
CRECI_PATTERN_MG = r'CRECI[/-]?MG\s*\d{5}'  # Minas Gerais: 5 digits

VALID_TRANSITIONS = {
    'draft': ['active'],
    'active': ['terminated'],  # 'expired' only via cron
    'terminated': [],
    'expired': [],
}
```

#### Arquivos Afetados (2026-02-20)

Os seguintes arquivos tiveram docstrings extensivas removidas seguindo esta filosofia:

- ✅ `models/agent.py` - Removido cabeçalho de módulo (ADRs já documentadas em `/docs/adr/`)
- ✅ `models/profile.py` - Removido cabeçalho extenso (informação desatualizada: dizia 9 tipos, agora são 10)
- ✅ `models/lease.py` - Removidas docstrings de `write()` e `_cron_expire_leases()` (comportamento agora via inline comments)
- ✅ `utils/validators.py` - Removidas docstrings extensivas de 10 funções (código + type hints são auto-explicativos)

**Justificativa**: 
- Código Python 3.10+ com type hints é auto-documentado
- Nomes de funções/variáveis são descritivos (`strip_non_digits` vs `normalize_document`)
- Constants explicam regras de negócio sem docstrings (`CPF_LENGTH = 11  # Brazilian individual tax ID`)
- Inline comments para casos específicos (ex: `# São Paulo: 6 digits`)
- Reduz manutenção (docstrings ficam desatualizadas, código não)

#### Pylint Configuration Update

Desabilitar checagem de docstrings obrigatórias:

```toml
[tool.pylint.messages_control]
disable = [
    "C0103",  # invalid-name (Odoo usa _name, _inherit)
    "C0114",  # missing-module-docstring
    "C0115",  # missing-class-docstring (NEW - 2026-02-20)
    "C0116",  # missing-function-docstring (NEW - 2026-02-20)
    "R0903",  # too-few-public-methods (models Odoo)
    "W0212",  # protected-access (_name é padrão Odoo)
]
```

**Pre-commit**: Remover `flake8-docstrings` de `additional_dependencies`:

```yaml
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        # Removido: additional_dependencies: [flake8-docstrings]
```

#### Trade-offs

**Vantagens**:
- ✅ Código mais limpo e conciso
- ✅ Menos manutenção (docstrings não ficam desatualizadas)
- ✅ Força boas práticas de nomenclatura e type hints
- ✅ Desenvolvedores leem o código, não apenas docstrings

**Desvantagens**:
- ❌ Curva de aprendizado para código de domínio brasileiro (CRECI, CPF, CNPJ)
- ❌ Menos exemplos inline de uso
- ❌ IDEs mostram menos ajuda contextual (solved by type hints)

**Mitigação**:
- ADRs documentam decisões arquiteturais e regras de negócio
- Type hints fornecem informação de tipos
- Constants documentam valores mágicos e regras
- Inline comments para casos específicos de domínio

---

## Referências

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Clean Code: A Handbook of Agile Software Craftsmanship](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882) - Robert C. Martin
- [Odoo Development Guidelines](https://www.odoo.com/documentation/18.0/developer/reference/guidelines.html)

---

## Changelog

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.2 | 2026-02-20 | **Emenda**: Priorizar código auto-explicativo sobre docstrings extensivas. Removidas docstrings de `agent.py`, `profile.py`, `lease.py`, `validators.py`. Desabilitar pylint C0115, C0116. Filosofia Clean Code adotada. |
| 1.1 | 2026-02-08 | Adicionado XML linter para views Odoo 18.0 |
| 1.0 | 2026-02-05 | Versão inicial com Python linters |

## Próximos Passos

1. ✅ Criar arquivos de configuração (`pyproject.toml`, `.flake8`)
2. ✅ Instalar pre-commit hooks
3. ✅ Configurar CI/CD pipeline
4. ⏳ Rodar formatação em código existente (uma vez)
5. ⏳ Treinar equipe nas ferramentas
6. ⏳ Monitorar métricas de qualidade (Pylint score trend)
7. ⏳ Ajustar regras baseado em feedback da equipe
