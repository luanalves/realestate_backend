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

| Ferramenta | Propósito | Configuração |
|------------|-----------|--------------|
| **black** | Formatação automática de código | `line-length = 100` |
| **isort** | Organização de imports | Compatível com black |
| **flake8** | Linting (PEP 8, erros, code smells) | Integrado com black |
| **pylint** | Análise estática profunda | Específico para Odoo |
| **mypy** | Type checking estático | Modo gradual (não-strict) |

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
```

### 5. Regras de Qualidade Obrigatórias

#### **Code Review Checklist**

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
  }
}
```

### 8. Comando Make para Qualidade

Adicionar ao `Makefile` na raiz do projeto:

```makefile
.PHONY: lint format check-quality

# Formatar código automaticamente
format:
	black 18.0/extra-addons/
	isort 18.0/extra-addons/

# Verificar qualidade (sem modificar)
lint:
	black --check --diff 18.0/extra-addons/
	isort --check-only --diff 18.0/extra-addons/
	flake8 18.0/extra-addons/
	pylint 18.0/extra-addons/ --exit-zero

# Verificar tudo antes de commit
check-quality: lint
	@echo "Running tests..."
	cd 18.0 && ./run_all_tests.sh
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

✅ **Menos bugs**: Análise estática detecta problemas antes de produção

✅ **Onboarding facilitado**: Novos desenvolvedores seguem padrões claros

✅ **Documentação melhor**: Docstrings obrigatórios melhoram compreensão do código

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

1. **Não bloquear**: Continuar trabalhando normalmente
2. **Gradual cleanup**: Aplicar formatação ao modificar arquivos
3. **Boy Scout Rule**: "Deixe o código melhor do que encontrou"
4. **Sprint de limpeza**: Dedicar tempo para refatoração periódica

### Impacto em PRs

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

## Referências

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Black - The Uncompromising Code Formatter](https://black.readthedocs.io/)
- [Pylint - Code Analysis for Python](https://pylint.org/)
- [Flake8 - Your Tool For Style Guide Enforcement](https://flake8.pycqa.org/)
- [Odoo Development Guidelines](https://www.odoo.com/documentation/18.0/developer/reference/guidelines.html)

## Próximos Passos

1. ✅ Criar arquivos de configuração (`pyproject.toml`, `.flake8`)
2. ✅ Instalar pre-commit hooks
3. ✅ Configurar CI/CD pipeline
4. ⏳ Rodar formatação em código existente (uma vez)
5. ⏳ Treinar equipe nas ferramentas
6. ⏳ Monitorar métricas de qualidade (Pylint score trend)
7. ⏳ Ajustar regras baseado em feedback da equipe
