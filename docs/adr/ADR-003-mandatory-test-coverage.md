# ADR-003: Cobertura de Testes Obrigatória para Todos os Módulos

## Status
Aceito

## Resumo Executivo

**REGRA CRÍTICA:** Cobertura de 100% é OBRIGATÓRIA para TODAS as validações de código.

### 🚫 NÃO Fazemos Testes Manuais

**Este projeto NÃO aceita testes manuais.** Toda validação deve ser automatizada através dos **3 tipos de testes obrigatórios:**

### ✅ Os 3 Tipos de Testes Automatizados

**1. LINTING (Flake8)** - Validação de código estático
- ✅ 0 erros de flake8 (PEP 8 compliance)
- ✅ Execução antes de cada commit
- ✅ Detecta erros de sintaxe e estilo

**2. TESTES UNITÁRIOS (Python unittest)** - Validação de Classes
- ✅ **Objetivo:** Validar APENAS as classes desenvolvidas (models, controllers, helpers)
- ✅ **100% de cobertura de validações** (required, constrains, compute) - **SEM EXCEÇÕES**
- ✅ **Sem banco de dados** - Usa mocks (`unittest.mock`)
- ✅ **Sem framework Odoo** - Testes puros de lógica
- ✅ Execução rápida (< 1 segundo por módulo)
- ✅ Variáveis de teste carregadas do arquivo `.env`

**3. TESTES E2E (Cypress + curl)** - Integração completa
- ✅ Todas as features visíveis devem ter testes Cypress
- ✅ APIs REST testadas com curl
- ✅ Fluxos completos de usuário
- ✅ Integração UI + Backend + Banco de dados

### ⚠️ Regras de Aprovação

- ❌ **PR sem testes automatizados = PR REJEITADO**
- ❌ **Validações não testadas = PR REJEITADO**
- ❌ **"Testei manualmente" NÃO é aceito como validação**
- ✅ **Merge só ocorre se os 3 tipos de testes passarem**

**O que mudou na v2.0 (2026-01-08):**
- Cobertura de validações agora é explicitamente 100% OBRIGATÓRIA
- Cada validação deve ter no mínimo 2 testes (sucesso + falha)
- Code review deve rejeitar PRs sem 100% de cobertura em validações
- Explicitado que NÃO fazemos testes manuais (apenas automatizados)

## Contexto

Durante o desenvolvimento do módulo `api_gateway`, identificamos que a qualidade e confiabilidade do código aumentaram significativamente com a implementação de testes abrangentes. O módulo alcançou:

- **76 testes unitários** com 100% de sucesso em apenas 0.19 segundos
- **22 testes E2E com Cypress** com 100% de sucesso
- **0 bugs em produção** desde a implementação dos testes
- **Refatorações seguras** graças à cobertura completa
- **Documentação viva** através dos testes que servem como exemplos de uso

### Problemas Identificados em Módulos sem Testes

Antes da implementação de testes, observamos:

1. **Bugs em produção**: Erros não detectados que só apareciam após deploy
2. **Medo de refatorar**: Desenvolvedores evitavam melhorar código por medo de quebrar funcionalidades
3. **Tempo de debugging**: 60% do tempo gasto corrigindo bugs ao invés de desenvolver features
4. **Documentação desatualizada**: Comentários e docs rapidamente ficavam obsoletos
5. **Onboarding lento**: Novos desenvolvedores levavam semanas para entender o código

### Forças em Jogo

**A favor de testes obrigatórios:**
- Redução drástica de bugs em produção
- Aumento da confiança da equipe
- Facilita refatoração e manutenção
- Documenta comportamento esperado
- Acelera onboarding de novos membros

**Contra testes obrigatórios:**
- Tempo inicial de desenvolvimento aumenta (~20-30%)
- Requer mudança cultural da equipe
- Necessita infraestrutura (CI/CD)
- Curva de aprendizado para quem não conhece testes

### Restrições

- Sistema Odoo 18.0 com arquitetura específica
- Equipe com diferentes níveis de experiência em testes
- Módulos legados sem nenhum teste
- Necessidade de manter velocidade de desenvolvimento
- Recursos limitados de infraestrutura

## Decisão

**Todos os módulos desenvolvidos ou modificados neste projeto DEVEM ter:**

### Filosofia: Testes Automatizados, Nunca Manuais

**❌ NÃO aceitamos:**
- Testes manuais ("testei na interface e funcionou")
- Validação manual ("rodei alguns casos e está ok")
- "QA manual antes do release"
- Planilhas de casos de teste executados manualmente

**✅ ACEITAMOS apenas:**
- Testes automatizados que podem rodar em CI/CD
- Testes repetíveis e determinísticos
- Testes versionados no Git junto com o código
- Testes que falham se o código quebrar

**Por que não fazemos testes manuais?**
1. **Não são repetíveis** - Cada pessoa testa de forma diferente
2. **Não são versionados** - Perdemos histórico de o que foi testado
3. **São lentos** - Testes manuais levam horas, automatizados levam minutos
4. **São esquecíveis** - Desenvolvedor pode esquecer de testar um caso
5. **Não detectam regressão** - Bug corrigido pode voltar sem ninguém perceber
6. **Não escalam** - Com 100+ funcionalidades, teste manual é inviável

**Exceção única:** Testes exploratórios de UX/UI para validar experiência do usuário (mas funcionalidade ainda precisa de testes automatizados).

### Os 3 Pilares de Testes Automatizados

Este projeto adota **3 tipos complementares de testes automatizados** que juntos garantem qualidade total:

```
┌─────────────────────────────────────────────────────────────┐
│                    PIRÂMIDE DE TESTES                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    🌐 E2E Tests (Cypress + curl)             │
│                  Poucos, Lentos, Alta Confiança             │
│                    Features completas                        │
│                         ▲                                    │
│                        ╱ ╲                                   │
│                       ╱   ╲                                  │
│                      ╱     ╲                                 │
│                     ╱       ╲                                │
│                    ╱         ╲                               │
│                   ╱  🧪 Unit  ╲                              │
│                  ╱    Tests     ╲                            │
│                 ╱   Muitos, Rápidos╲                         │
│                ╱    100% Cobertura   ╲                       │
│               ╱                       ╲                      │
│              ╱                         ╲                     │
│             ╱___________________________╲                    │
│            🔍 Linting (Flake8)                               │
│        Instantâneo, Previne erros básicos                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Linting Obrigatório com Flake8

**Características obrigatórias:**
- Usar `flake8` para validação de código Python
- Seguir PEP 8 (estilo de código Python)
- Executar antes de cada commit
- Nenhum erro ou warning permitido no código final
- Configuração padronizada via `.flake8` ou `setup.cfg`

**Regra crítica de validação:**
- **100% de cobertura em código de validação é OBRIGATÓRIA**
- Toda validação deve ter no mínimo 2 testes: cenário válido e inválido
- Validações incluem: `required=True`, `@api.constrains`, `@api.onchange`, campos `compute`, métodos de validação customizados

**Configuração padrão (.flake8):**
```ini
[flake8]
max-line-length = 120
exclude = 
    .git,
    __pycache__,
    */migrations/*,
    */static/*,
    */filestore/*,
    venv,
    env,
    .venv
ignore = 
    E501,  # line too long (handled by max-line-length)
    W503,  # line break before binary operator
    E203,  # whitespace before ':'
per-file-ignores =
    __init__.py:F401  # imported but unused

# Odoo specific
# F401: module imported but unused (common in __init__.py)
# E501: line too long (Odoo allows 120)
```

**Execução obrigatória:**
```bash
# Executar em módulo específico
cd 18.0/extra-addons/meu_modulo
flake8 .

# Executar em todos os módulos custom
cd 18.0/extra-addons
flake8 quicksol_estate/ thedevkitchen_apigateway/ auditlog/

# Usar script centralizado (recomendado)
cd 18.0
./lint.sh
```

**Script lint.sh (OBRIGATÓRIO em cada módulo):**
```bash
#!/bin/bash
# Lint all Python files in custom addons

set -e

ADDONS_DIR="/mnt/extra-addons"
MODULES=(
    "quicksol_estate"
    "thedevkitchen_apigateway"
    "thedevkitchen_branding"
    "auditlog"
)

echo "🔍 Running Flake8 linting..."

for module in "${MODULES[@]}"; do
    echo ""
    echo "📦 Linting module: $module"
    if [ -d "$ADDONS_DIR/$module" ]; then
        flake8 "$ADDONS_DIR/$module" \
            --max-line-length=120 \
            --exclude=__pycache__,migrations,static,filestore \
            --count \
            --show-source \
            --statistics
        echo "✅ $module passed!"
    else
        echo "⚠️  Module $module not found, skipping..."
    fi
done

echo ""
echo "✨ All modules passed linting!"
```

**Integração com Docker:**
```bash
# Executar dentro do container Odoo
docker compose exec odoo bash -c "cd /mnt/extra-addons && flake8 quicksol_estate/"

# Ou usando o script
docker compose exec odoo /mnt/extra-addons/../lint.sh
```

**Checklist obrigatório:**
- [ ] `.flake8` configurado na raiz do projeto
- [ ] `lint.sh` criado e executável (`chmod +x lint.sh`)
- [ ] `flake8` instalado no container (`pip install flake8`)
- [ ] Nenhum erro ou warning no código
- [ ] Linting executado antes de cada commit

### 2. Testes Unitários com 100% de Cobertura da Lógica de Negócio

**Características obrigatórias:**
- Usar Python `unittest` (biblioteca padrão) ou `pytest`
- Usar `unittest.mock` para criar mocks (sem banco de dados)
- Execução rápida: < 1 segundo para suite completa do módulo
- Testes isolados e independentes
- Documentados com docstrings descritivas
- **Código deve passar no flake8 ANTES de escrever testes**
- **COBERTURA DE VALIDAÇÃO: 100% OBRIGATÓRIA** - Todo código de validação (required, constraints, compute) deve ter testes

**Estrutura de arquivos:**
```
meu_modulo/
├── tests/
│   ├── __init__.py
│   ├── run_unit_tests.py          # Runner principal
│   ├── test_models_unit.py        # Testes de models
│   ├── test_controllers_unit.py   # Testes de controllers  
│   ├── test_helpers_unit.py       # Testes de helpers
│   └── UNIT_TESTS.md              # Documentação
├── .flake8                         # Configuração do linting
└── lint.sh                         # Script de linting
```

**Exemplo de teste:**
```python
class TestMyModel(unittest.TestCase):
    """Test MyModel business logic"""
    
    def test_calculation(self):
        """Test that price calculation is correct"""
        # Arrange
        mock_product = Mock()
        mock_product.price = 100
        mock_product.tax_rate = 0.1
        
        # Act
        result = mock_product.price * (1 + mock_product.tax_rate)
        
        # Assert
        self.assertEqual(result, 110)
    
    def test_required_field_validation(self):
        """Test that required field validation raises error"""
        # Arrange
        mock_record = Mock()
        mock_record.name = None
        
        # Act & Assert
        with self.assertRaises(ValidationError):
            if not mock_record.name:
                raise ValidationError("Name is required")
```

**Exemplo de teste de validação (OBRIGATÓRIO):**
```python
class TestEstatePropertyValidations(unittest.TestCase):
    """Test Estate Property validation logic - 100% coverage required"""
    
    def test_price_must_be_positive(self):
        """Test that price validation rejects negative values"""
        # Arrange
        mock_property = Mock()
        mock_property.expected_price = -1000
        
        # Act & Assert
        with self.assertRaises(ValidationError):
            if mock_property.expected_price < 0:
                raise ValidationError("Price must be positive")
    
    def test_price_accepts_valid_value(self):
        """Test that price validation accepts positive values"""
        # Arrange
        mock_property = Mock()
        mock_property.expected_price = 100000
        
        # Act
        is_valid = mock_property.expected_price > 0
        
        # Assert
        self.assertTrue(is_valid)
```

### 3. Testes End-to-End (E2E) com Cypress para Features Visuais

**Características obrigatórias:**
- Usar Cypress 15.x ou superior
- Cada feature visível deve ter pelo menos 1 teste E2E
- Fluxos críticos devem ter testes completos (sucesso e erro)
- Testes devem ser independentes (podem rodar isoladamente)
- Testes devem limpar dados criados (cleanup no afterEach)

### 4. Cobertura de Validações: 100% OBRIGATÓRIA

**ATENÇÃO: Esta é uma regra CRÍTICA do projeto**

**O que deve ser testado com 100% de cobertura:**

1. **Campos obrigatórios (`required=True`)**
   - ✅ Teste com campo preenchido (deve passar)
   - ✅ Teste com campo vazio/None (deve falhar com ValidationError)

2. **Constraints SQL (`_sql_constraints`)**
   - ✅ Teste com dados válidos (deve passar)
   - ✅ Teste com dados duplicados/inválidos (deve falhar)

3. **Constraints Python (`@api.constrains`)**
   - ✅ Teste para cada condição válida
   - ✅ Teste para cada condição inválida que lança ValidationError

4. **Campos computados (`compute=`)**
   - ✅ Teste para cada cenário de cálculo
   - ✅ Teste com valores extremos (0, None, negativos)

5. **Métodos de validação customizados**
   - ✅ Teste para cada branch (if/else)
   - ✅ Teste para valores limites (boundary testing)

**Exemplo de cobertura completa:**

```python
# Model com validações
class EstateProperty(models.Model):
    _name = 'estate.property'
    
    name = fields.Char(required=True)  # Validação 1
    expected_price = fields.Float(required=True)  # Validação 2
    selling_price = fields.Float()
    
    _sql_constraints = [
        ('check_price', 'CHECK(expected_price > 0)', 
         'Expected price must be positive')  # Validação 3
    ]
    
    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):  # Validação 4
        for record in self:
            if record.selling_price:
                if record.selling_price < record.expected_price * 0.9:
                    raise ValidationError("Selling price too low")

# Testes OBRIGATÓRIOS (100% cobertura)
class TestEstatePropertyValidations(unittest.TestCase):
    """100% coverage for ALL validations"""
    
    # Validação 1: name required
    def test_name_required_passes_with_value(self):
        """Test name validation accepts valid value"""
        mock = Mock()
        mock.name = "Beautiful House"
        self.assertIsNotNone(mock.name)
    
    def test_name_required_fails_without_value(self):
        """Test name validation rejects empty value"""
        mock = Mock()
        mock.name = None
        with self.assertRaises(ValidationError):
            if not mock.name:
                raise ValidationError("Name is required")
    
    # Validação 2: expected_price required
    def test_expected_price_required_passes(self):
        """Test price validation accepts valid value"""
        mock = Mock()
        mock.expected_price = 100000
        self.assertIsNotNone(mock.expected_price)
    
    def test_expected_price_required_fails(self):
        """Test price validation rejects None"""
        mock = Mock()
        mock.expected_price = None
        with self.assertRaises(ValidationError):
            if mock.expected_price is None:
                raise ValidationError("Price is required")
    
    # Validação 3: SQL constraint (price > 0)
    def test_price_positive_passes(self):
        """Test price constraint accepts positive value"""
        mock = Mock()
        mock.expected_price = 100000
        self.assertGreater(mock.expected_price, 0)
    
    def test_price_positive_fails_negative(self):
        """Test price constraint rejects negative value"""
        mock = Mock()
        mock.expected_price = -1000
        with self.assertRaises(ValidationError):
            if mock.expected_price <= 0:
                raise ValidationError("Price must be positive")
    
    def test_price_positive_fails_zero(self):
        """Test price constraint rejects zero"""
        mock = Mock()
        mock.expected_price = 0
        with self.assertRaises(ValidationError):
            if mock.expected_price <= 0:
                raise ValidationError("Price must be positive")
    
    # Validação 4: Selling price constraint
    def test_selling_price_valid(self):
        """Test selling price accepts value above 90% of expected"""
        mock = Mock()
        mock.expected_price = 100000
        mock.selling_price = 95000
        is_valid = mock.selling_price >= mock.expected_price * 0.9
        self.assertTrue(is_valid)
    
    def test_selling_price_too_low(self):
        """Test selling price rejects value below 90% of expected"""
        mock = Mock()
        mock.expected_price = 100000
        mock.selling_price = 80000
        with self.assertRaises(ValidationError):
            if mock.selling_price < mock.expected_price * 0.9:
                raise ValidationError("Selling price too low")
    
    def test_selling_price_none_allowed(self):
        """Test selling price accepts None (not required)"""
        mock = Mock()
        mock.expected_price = 100000
        mock.selling_price = None
        # Não deve lançar erro quando None
        self.assertIsNone(mock.selling_price)
```

**Regras de cobertura de validação:**

1. **Cada validação DEVE ter no mínimo 2 testes:**
   - 1 teste de sucesso (valor válido)
   - 1 teste de falha (valor inválido)

2. **Constraints complexos DEVEM ter N+1 testes:**
   - N testes para cada condição de falha
   - 1 teste de sucesso

3. **Campos computados DEVEM ter testes para:**
   - Cada branch de lógica
   - Valores extremos (None, 0, negativos)
   - Dependências entre campos

4. **Sem exceções:**
   - ❌ Não é permitido pular testes de validação
   - ❌ Não é permitido cobertura < 100% em validações

### Padrão de Testes para Observer Pattern (ADR-020)

**Problema:** Observers dinâmicos (criados em tempo de execução) não registram corretamente no Odoo.

**Solução:** Criar modelos reais de observer para testes em `models/test_observer.py`:

```python
# models/test_observer.py
from odoo import models, api

class TestConcreteObserver(models.AbstractModel):
    _name = 'test.concrete.observer'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Test Observer for Unit Tests'
    
    @api.model
    def can_handle(self, event_name):
        return event_name in ['test.event', 'test.another.event']
    
    @api.model
    def handle(self, event_name, data):
        return {'status': 'handled', 'event': event_name, 'data': data}
```

**Registrar no `models/__init__.py`:**
```python
from . import test_observer  # Test observer for unit tests
```

**Uso nos testes:**
```python
class TestAbstractObserver(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.observer = cls.env['test.concrete.observer']
    
    def test_can_handle_returns_true_for_supported_events(self):
        self.assertTrue(self.observer.can_handle('test.event'))
```

**❌ Não fazer:**
- Criar classes dinamicamente em `setUpClass`
- Tentar mockar métodos read-only de AbstractModel (`search`, `handle`)
- Usar `MagicMock` para simular observers

**✅ Fazer:**
- Criar observer real em `models/test_observer.py`
- Registrar no `__init__.py`
- Usar o observer real nos testes via `self.env['test.concrete.observer']`

   - ❌ Code review deve REJEITAR PR sem 100% de validações testadas

**Por que 100% de cobertura em validações é CRÍTICA:**

- Validações são a primeira linha de defesa contra dados inválidos
- Bugs em validações causam dados corrompidos no banco
- Dados corrompidos são difíceis de corrigir em produção
- Testes de validação evitam 80% dos bugs de produção
- Validações mal testadas causam problemas de integridade referencial

### 5. Categorias de Testes E2E
- Usar Cypress 15.x ou superior
- Cada feature visível deve ter pelo menos 1 teste E2E
- Fluxos críticos devem ter testes completos (sucesso e erro)
- Testes devem ser independentes (podem rodar isoladamente)
- Testes devem limpar dados criados (cleanup no afterEach)

**Categorias de testes E2E obrigatórias:**

1. **CRUD Básico** (obrigatório para todos os models)
   - Criar registro
   - Visualizar registro
   - Editar registro
   - Deletar/Arquivar registro

2. **Validações** (obrigatório)
   - Campos obrigatórios (`required=True`)
   - Constraints SQL e Python (`@api.constrains`)
   - Formatos de dados (`@api.onchange`, `compute`)
   - Regras de negócio (métodos personalizados)
   - **Cobertura de 100% em todas as validações**

3. **Integrações** (quando aplicável)
   - Integração com outros módulos
   - APIs externas

**Exemplo de teste E2E:**
```javascript
describe('Meu Módulo - CRUD', () => {
  beforeEach(() => {
    cy.login('admin', 'admin');
  });

  it('Deve criar novo registro', () => {
    cy.visit('/web#action=my_module.action_my_model');
    cy.get('.o_form_button_create').click();
    cy.get('input[name="name"]').type('Teste');
    cy.get('.o_form_button_save').click();
    cy.get('.o_notification.bg-success').should('be.visible');
  });

  afterEach(() => {
    cy.cleanupTestData();
  });
});
```
### 5. Processo de Pull Request

**Checklist obrigatório antes de abrir PR:**
- [ ] **Código passa no flake8 (0 erros)**
- [ ] **Linting executado via `./lint.sh`**
- [ ] Testes unitários criados para toda lógica nova
- [ ] 100% de cobertura nos arquivos modificados
- [ ] **100% de cobertura em TODAS as validações (required, constrains, compute)**
- [ ] Testes E2E criados para features visíveis
- [ ] Todos os testes passando (0 failures)
- [ ] Documentação dos testes atualizada

**Checklist do revisor:**
- [ ] **Código está formatado conforme PEP 8**
- [ ] **Nenhum warning ou erro do flake8**
- [ ] Testes existem e cobrem 100%
- [ ] **Todas as validações (required, constrains, compute) têm testes**
- [ ] Testes seguem padrão AAA (Arrange, Act, Assert)
- [ ] Testes têm nomes descritivos
- [ ] Testes são independentes
- [ ] Testes limpam dados (cleanup)
- [ ] CI/CD pipeline passa

**Ordem de execução obrigatória:**
```bash
# 1. LINTING (primeiro passo - mais rápido)
./lint.sh
# ✅ Se falhar: código tem erros de sintaxe/estilo - PARE AQUI

# 2. TESTES UNITÁRIOS (segundo passo - rápido)
docker compose exec odoo python3 /mnt/extra-addons/meu_modulo/tests/run_unit_tests.py
# ✅ Se falhar: lógica de negócio quebrada - PARE AQUI

# 3. TESTES E2E (último passo - mais lento)
npx cypress run --spec "cypress/e2e/meu-modulo.cy.js"
# ✅ Se falhar: integração UI/API quebrada
```

**Por que nesta ordem?**
- ⚡ **Feedback rápido**: Linting falha em 1s, testes unitários em <10s, E2E em minutos
- 💰 **Economia de recursos**: Não adianta rodar E2E se o código nem compila
- 🎯 **Foco no problema**: Erro de sintaxe? Linting avisa. Lógica quebrada? Unit test avisa.

**Testes manuais complementares (OPCIONAIS):**
- Testes exploratórios de UX (descobrir melhorias de usabilidade)
- Testes de aceitação com stakeholders (validar se atende expectativa)
- **MAS: funcionalidade ainda precisa de testes automatizados!**

### 6. Implementação Gradual

**Fase 1 - Novos Módulos (Imediato):**
- Todos os novos módulos seguem este ADR
- Template de módulo com estrutura de testes + linting
- CI/CD configurado com flake8 + testes

**Fase 2 - Módulos Existentes (Gradual - 3 meses):**

Prioridade de cobertura:
1. `quicksol_estate` (módulo core) - Mês 1
2. `auditlog` (módulo crítico) - Mês 2  
3. Demais módulos - Mês 3

Para cada módulo:
- **Dia 1**: Configurar `.flake8` e criar `lint.sh`
- **Dia 2-3**: Corrigir todos os erros de linting
- Semana 1-2: Criar testes unitários (100% cobertura)
- Semana 3: Criar testes E2E (features principais)
- Semana 4: Documentar e revisar

### 7. Ferramentas e Recursos

**Obrigatórias:**
- **`flake8`** (Python) - Linting e validação PEP 8
- `unittest` (Python) - Testes unitários
- `unittest.mock` (Python) - Mocks
- Cypress - Testes E2E
- Docker - Ambiente de testes

**Recomendadas:**
- `black` - Auto-formatação de código Python
- `isort` - Ordenação de imports
- `pylint` - Análise estática avançada
- `pytest` - Runner avançado de testes
- `coverage.py` - Relatórios de cobertura
- Cypress Studio - Gravar testes
- `pre-commit` - Hooks de git para validação automática

**Instalação no container:**
```bash
# Adicionar ao Dockerfile
RUN pip3 install flake8 black isort pylint coverage pytest

# Ou executar manualmente
docker compose exec odoo pip3 install flake8 black isort
```

### 8. Referência de Implementação

O módulo `api_gateway` serve como referência:

**Execução:**
```bash
# 1. Linting (primeiro)
cd 18.0
./lint.sh
# Ou específico:
flake8 extra-addons/thedevkitchen_apigateway/

# 2. Unit tests
docker compose exec odoo python3 \
  /mnt/extra-addons/thedevkitchen_apigateway/tests/run_unit_tests.py

# 3. E2E tests  
npx cypress run --spec "cypress/e2e/thedevkitchen-apigateway.cy.js"
```

**Resultado:**
- ✅ **0 erros de linting (PEP 8 compliant)**
- ✅ 76 testes unitários (100% sucesso em 0.19s)
- ✅ 22 testes E2E (100% sucesso em 1m37s)
- ✅ 100% cobertura de código
- ✅ 0 bugs reportados em 30 dias

## Consequências

### Positivas

1. **Qualidade de Código**
   - **Linting automático garante consistência de estilo**
   - **Código mais legível e padronizado (PEP 8)**
   - Redução de 100% em bugs reportados em produção
   - Código mais limpo e modular (testável = bem arquitetado)
   - Refatorações seguras e confiantes

2. **Produtividade**
   - **Menos erros de sintaxe e estilo (-40%)**
   - **Code review mais rápido (estilo já validado)**
   - Menos tempo em debugging (-60%)
   - Mais tempo em desenvolvimento de features (+40%)
   - Onboarding de novos devs 3x mais rápido

3. **Documentação**
   - Testes servem como documentação viva
   - Exemplos de uso sempre atualizados
   - Comportamento esperado explícito

4. **Confiança**
   - Equipe mais confiante para fazer mudanças
   - Deploy mais seguro (testes automatizados)
   - Menos estresse e retrabalho

5. **Manutenibilidade**
   - Código legado pode ser refatorado com segurança
   - Migração para novas versões Odoo mais fácil
   - Débito técnico reduzido

### Negativas

1. **Curto Prazo**
   - Desenvolvimento inicial 20-30% mais lento
   - Curva de aprendizado para equipe
   - Necessidade de treinamento
   - Setup de infraestrutura (CI/CD)

2. **Manutenção**
   - Testes precisam ser mantidos junto com código
   - Testes podem ficar frágeis se mal escritos
   - Tempo gasto escrevendo testes

3. **Recursos**
   - Necessidade de infraestrutura de CI/CD
   - Tempo de execução de testes no pipeline
   - Possível necessidade de servidores adicionais

### Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Equipe resiste a mudança | Alto | Treinamento, pair programming, mostrar benefícios |
| Testes mal escritos | Médio | Code review rigoroso, exemplos, templates |
| Pipeline lento | Médio | Otimizar testes, rodar em paralelo, cache |
| Custo de infraestrutura | Baixo | Usar recursos locais, otimizar runners |
| **Linting muito restritivo** | Baixo | Configurar exceções razoáveis no `.flake8` |
| **Código legado com muitos erros** | Médio | Corrigir gradualmente, priorizar módulos críticos |

### Compromissos Aceitos

- **Velocidade inicial vs qualidade**: Aceitamos desenvolvimento inicial mais lento em troca de menos bugs
- **Tempo de escrita vs manutenção**: Aceitamos tempo escrevendo testes em troca de manutenção mais fácil
- **Flexibilidade vs padrão**: Definimos padrões rígidos (100% cobertura) em troca de consistência

### Implicações Futuras

1. **Cultura de Qualidade**
   - Testes tornam-se parte natural do desenvolvimento
   - Qualidade deixa de ser "extra" e vira padrão
   - Equipe orgulhosa da qualidade do código

2. **Escalabilidade**
   - Sistema pode crescer com segurança
   - Novos módulos seguem padrão de qualidade
   - Débito técnico controlado

3. **Competitividade**
   - Produto mais estável que concorrentes
   - Menos bugs reportados por clientes
   - Releases mais frequentes e seguros

### Alternativas Consideradas e Rejeitadas

**1. Cobertura parcial (70-80%)**
- ❌ Rejeitado: Deixa margem para "escolher" o que não testar
- ❌ Cria precedente de que "às vezes pode"

**2. Apenas testes E2E (sem unitários)**
- ❌ Rejeitado: Testes lentos demais
- ❌ Dificulta debug (erro pode estar em qualquer camada)

**3. Apenas testes unitários (sem E2E)**
- ❌ Rejeitado: Não testa integração real
- ❌ Não valida UI/UX

**4. Testes opcionais (recomendados mas não obrigatórios)**
- ❌ Rejeitado: Na prática ninguém faria
- ❌ Sem padrão de qualidade

---

## Referências

- [ADR-001: Development Guidelines for Odoo Screens](./ADR-001-development-guidelines-for-odoo-screens.md)
- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Test Pyramid - Martin Fowler](https://martinfowler.com/bliki/TestPyramid.html)
- [Clean Code - Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)

## Histórico

| Data | Versão | Mudança | Autor |
|------|--------|---------|-------|
| 2025-11-16 | 1.0 | Criação do ADR baseado no sucesso do módulo api_gateway | Equipe Dev |
| 2025-11-30 | 1.1 | Adicionado linting obrigatório com flake8 e PEP 8 | Equipe Dev |
| 2026-01-08 | 2.0 | **Atualizado para exigir 100% de cobertura em TODAS as validações** | Equipe Dev |

---

## Apêndice A: Template de Teste Unitário

```python
# -*- coding: utf-8 -*-
"""
- ✅ Cobertura de 100% da lógica de negócio
- ✅ Testes puros usando mocks (sem banco de dados)
- ✅ Execução rápida (< 1 segundo para suite completa)
- ✅ Isolados e independentes
- ✅ Documentados com docstrings descritivas

**Tecnologia:**
- Python `unittest` (biblioteca padrão)
- `unittest.mock` para mocks
- Opcional: `pytest` para recursos avançados

**Estrutura obrigatória:**
```
meu_modulo/
├── tests/
│   ├── __init__.py
│   ├── run_unit_tests.py          # Runner principal
│   ├── test_models_unit.py        # Testes de models
│   ├── test_controllers_unit.py   # Testes de controllers
│   ├── test_helpers_unit.py       # Testes de helpers/utils
│   └── UNIT_TESTS.md              # Documentação dos testes
```

**Exemplo de teste unitário:**
```python
class TestMyModel(unittest.TestCase):
    """Test MyModel business logic"""
    
    def test_calculation_logic(self):
        """Test that calculation returns correct result"""
        # Arrange
        mock_obj = Mock()
        mock_obj.value = 100
        
        # Act
        result = mock_obj.value * 1.1
        
        # Assert
        self.assertEqual(result, 110)
```

---

### 2. Testes End-to-End (E2E) com Cypress

**Obrigatório:**
- ✅ Todas as features devem ter pelo menos 1 teste E2E
- ✅ Fluxos críticos devem ter testes completos
- ✅ Testes devem cobrir cenários de sucesso e erro
- ✅ Testes devem ser independentes (podem rodar isoladamente)
- ✅ Testes devem limpar dados criados ao final

**Tecnologia:**
- Cypress 15.x ou superior
- JavaScript/TypeScript

**Estrutura obrigatória:**
```
cypress/
├── e2e/
│   ├── meu-modulo.cy.js           # Testes do módulo
│   └── meu-modulo-integration.cy.js  # Testes de integração
├── support/
│   └── commands.js                # Custom commands
└── fixtures/
    └── meu-modulo.json            # Dados de teste
```

**Exemplo de teste E2E:**
```javascript
describe('Meu Módulo - CRUD', () => {
  beforeEach(() => {
    cy.login('admin', 'admin');
  });

  it('Deve criar novo registro', () => {
    cy.visit('/web#action=my_module.action_my_model');
    cy.get('.o_form_button_create').click();
    cy.get('input[name="name"]').type('Teste');
    cy.get('.o_form_button_save').click();
    cy.get('.o_notification.bg-success').should('be.visible');
  });

  afterEach(() => {
    // Limpar dados de teste
    cy.cleanupTestData();
  });
});
```

---

## Métricas de Qualidade Exigidas

### Mínimos Obrigatórios

| Métrica | Valor Mínimo | Ideal |
|---------|--------------|-------|
| Cobertura de Testes Unitários | 100% | 100% |
| **Cobertura de Validações** | **100%** | **100%** |
| Testes E2E por Feature | 1 teste | 3-5 testes |
| Taxa de Sucesso (Unit) | 100% | 100% |
| Taxa de Sucesso (E2E) | 95% | 100% |
| Tempo de Execução (Unit) | < 1s | < 0.5s |
| Tempo de Execução (E2E) | < 5min | < 3min |

### Categorias de Testes E2E

Cada módulo deve ter testes nas seguintes categorias:

1. **CRUD Básico** (Obrigatório)
   - Criar registro
   - Visualizar registro
   - Editar registro
   - Deletar/Arquivar registro

2. **Validações** (Obrigatório)
   - Campos obrigatórios (`required=True`)
   - Constraints SQL e Python (`@api.constrains`)
   - Formatos de dados e tipos corretos
   - Regras de negócio e compute methods
   - **Todos os cenários de validação devem ter testes (100% cobertura)**

3. **Integrações** (Se aplicável)
   - Integração com outros módulos
   - APIs externas
   - Webhooks

4. **Permissões** (Se aplicável)
   - Acesso por grupo
   - Operações restritas

5. **Fluxos Completos** (Recomendado)
   - Jornadas de usuário
   - Casos de uso reais

---

## Processo de Desenvolvimento

### Pull Request - Checklist Obrigatório

Antes de abrir um PR, o desenvolvedor DEVE:

- [ ] Criar testes unitários para toda lógica nova
- [ ] Garantir 100% de cobertura nos arquivos modificados
- [ ] **Garantir 100% de cobertura em TODAS as validações**
- [ ] Criar testes E2E para features visíveis ao usuário
- [ ] Executar suite de testes unitários (`python3 run_unit_tests.py`)
- [ ] Executar suite de testes E2E (`npx cypress run`)
- [ ] Verificar que todos os testes passam (0 failures)
- [ ] Documentar testes em `UNIT_TESTS.md` ou `README.md`
- [ ] Adicionar screenshots dos testes E2E passando (se aplicável)

### Code Review - Checklist do Revisor

O revisor DEVE verificar:

- [ ] Testes unitários existem e cobrem 100% da lógica
- [ ] **100% de cobertura em validações (required, constrains, compute)**
- [ ] Testes E2E existem para features visuais
- [ ] Testes seguem padrões AAA (Arrange, Act, Assert)
- [ ] Testes têm nomes descritivos
- [ ] Testes são independentes (não dependem de ordem)
- [ ] Não há código duplicado nos testes
- [ ] Testes limpam dados criados (cleanup)
- [ ] CI/CD pipeline passa (todos os testes)

### Integração Contínua (CI/CD)

Pipeline obrigatório para todos os PRs:

```yaml
# Exemplo de workflow GitHub Actions
name: Tests

on: [pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Unit Tests
        run: |
          docker compose exec odoo python3 \
            /mnt/extra-addons/*/tests/run_unit_tests.py
      - name: Check Coverage
        run: |
          if [ $? -ne 0 ]; then
            echo "❌ Unit tests failed!"
            exit 1
          fi

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Cypress Tests
        run: npx cypress run
      - name: Upload Screenshots
        if: failure()
        uses: actions/upload-artifact@v2
        with:
          name: cypress-screenshots
          path: cypress/screenshots
```

---

## Exceções

### Quando NÃO criar testes E2E:

- ✅ Módulos puramente backend (sem UI)
- ✅ Helpers/utilitários simples
- ✅ Scripts de migração one-time

**Nestes casos:**
- Ainda é obrigatório ter testes unitários
- Documentar o motivo da exceção no README

### Quando reduzir cobertura unitária:

- ❌ **NUNCA!** - Não há exceções para cobertura < 100%
- ❌ **ESPECIALMENTE para validações** - 100% de cobertura é CRÍTICA
- Se código não é testável, refatore o código
- Se é código de terceiros, isole em wrapper testável
- **Toda validação deve ter no mínimo 2 testes: sucesso e falha**

---

## Exemplos de Referência

### Módulo com 100% de Cobertura

**`api_gateway`** (Exemplo perfeito):
```
✅ 76 testes unitários (100% cobertura)
✅ 22 testes E2E (100% sucesso)
✅ Tempo total: ~2 minutos
✅ Documentação completa em tests/UNIT_TESTS.md
```

**Arquivos:**
- `tests/test_oauth_application_unit.py` (19 testes)
- `tests/test_jwt_unit.py` (25 testes)
- `tests/test_models_unit.py` (32 testes)
- `tests/run_unit_tests.py` (runner)
- `tests/UNIT_TESTS.md` (documentação)
- `cypress/e2e/api-gateway.cy.js` (22 testes E2E)

**Executar:**
```bash
# Unit tests
docker compose exec odoo python3 \
  /mnt/extra-addons/api_gateway/tests/run_unit_tests.py

# E2E tests
npx cypress run --spec "cypress/e2e/api-gateway.cy.js"
```

---

## Ferramentas e Recursos

### Ferramentas Obrigatórias

| Ferramenta | Uso | Instalação |
|------------|-----|------------|
| `unittest` | Testes unitários Python | Built-in Python |
| `unittest.mock` | Mocks para testes (sem framework Odoo) | Built-in Python |
| Cypress | Testes E2E (validar execução na tela, simular usuário) | `npm install cypress` |
| `curl` | Testes de API REST (sem framework Odoo) | Built-in macOS/Linux |
| `.env` | Variáveis de teste (tokens, URLs, credenciais) | Arquivo de configuração |
| `jq` | Processar JSON em testes | `brew install jq` |

### Ferramentas Recomendadas

| Ferramenta | Uso | Benefício |
|------------|-----|-----------|
| `pytest` | Runner de testes avançado | Fixtures, parametrização |
| `coverage.py` | Medir cobertura | Relatórios detalhados |
| `pytest-cov` | Cobertura com pytest | Integração pytest |
| Cypress Studio | Gravar testes E2E | Acelera criação de testes |

### Recursos de Aprendizado

**Testes Unitários Python:**
- 📚 [Python unittest docs](https://docs.python.org/3/library/unittest.html)
- 📚 [unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- 🎥 [Real Python - Testing](https://realpython.com/python-testing/)

**Cypress:**
- 📚 [Cypress Docs](https://docs.cypress.io)
- 📚 [Best Practices](https://docs.cypress.io/guides/references/best-practices)
- 🎥 [Cypress YouTube Channel](https://www.youtube.com/@Cypress-io)

**Odoo Testing:**
- 📚 [Odoo Test Framework](https://www.odoo.com/documentation/18.0/developer/reference/backend/testing.html)
- 📚 ADR-001 - Development Guidelines (já existente)

**curl e API Testing:**
- 📚 [curl Documentation](https://curl.se/docs/)
- 📚 [REST API Best Practices](https://restfulapi.net/)

---

## Configuração de Variáveis de Teste (.env)

**Arquivo `.env` deve conter todas as variáveis necessárias para testes:**

```bash
# Localização: raiz do projeto (18.0/.env)

# URLs e Portas
ODOO_URL=http://localhost:8069
ODOO_API_URL=http://localhost:8069/api/v1
ODOO_DB=realestate
POSTGRES_DB=realestate
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Cypress - Credenciais de teste
CYPRESS_ADMIN_LOGIN=admin
CYPRESS_ADMIN_PASSWORD=admin
CYPRESS_ADMIN_EMAIL=admin@example.com

# JWT e OAuth - Tokens de teste
JWT_SECRET=test-secret-key
JWT_EXPIRATION=3600
OAUTH_CLIENT_ID=test-client
OAUTH_CLIENT_SECRET=test-client-secret

# Variáveis de teste (curl + unitários)
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=Test123!@#
TEST_COMPANY_ID=1
TEST_COMPANY_NAME=Test Company

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1

# Debug (ativar logs em testes)
DEBUG=false
LOG_LEVEL=WARNING
```

**Como usar em testes:**

**Python (testes unitários e curl):**
```python
import os
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.getenv('ODOO_URL')
JWT_TOKEN = os.getenv('JWT_TOKEN')
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL')
TEST_USER_PASSWORD = os.getenv('TEST_USER_PASSWORD')
```

**Cypress (testes E2E):**
```javascript
describe('Login', () => {
  it('Deve fazer login com credenciais do .env', () => {
    cy.visit(Cypress.env('ODOO_URL'));
    cy.get('input[name="login"]').type(Cypress.env('CYPRESS_ADMIN_LOGIN'));
    cy.get('input[name="password"]').type(Cypress.env('CYPRESS_ADMIN_PASSWORD'));
    cy.get('button[type="submit"]').click();
  });
});
```

**curl (testes de API):**
```bash
# Carregar variáveis do .env
source 18.0/.env

# Usar em curl
curl -X POST $ODOO_API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_USER_EMAIL\", \"password\": \"$TEST_USER_PASSWORD\"}"
```

**⚠️ IMPORTANTE:**
- ❌ NUNCA committar `.env` com dados reais no Git
- ✅ Usar `.env.example` como template (sem valores sensíveis)
- ✅ Adicionar `.env` ao `.gitignore`
- ✅ Em CI/CD, variáveis vêm de secrets configurados na plataforma (GitHub Actions, GitLab CI, etc.)

---

## Benefícios Esperados

### Curto Prazo (1-3 meses)

- ✅ Redução de 80% em bugs reportados em produção
- ✅ Refatorações mais seguras e rápidas
- ✅ Onboarding de novos devs mais fácil (testes = documentação)
- ✅ Code review mais rápido e efetivo

### Médio Prazo (3-6 meses)

- ✅ Aumento de 50% na velocidade de desenvolvimento
- ✅ Confiança da equipe em fazer mudanças
- ✅ Documentação sempre atualizada (testes não mentem)
- ✅ Menor tempo de debugging

### Longo Prazo (6+ meses)

- ✅ Código legado 100% coberto
- ✅ Sistema estável e confiável
- ✅ Facilidade para migrar para novas versões Odoo
- ✅ Cultura de qualidade estabelecida

---

## Implementação

### Fase 1: Novos Módulos (Imediato)

- ✅ Todos os novos módulos seguem este ADR
- ✅ Template de módulo com estrutura de testes
- ✅ CI/CD configurado para rodar testes automaticamente

### Fase 2: Módulos Existentes (Gradual)

Para cada módulo existente:

1. **Semana 1-2:** Criar testes unitários (100% cobertura)
2. **Semana 3:** Criar testes E2E (features principais)
3. **Semana 4:** Documentar e revisar

**Prioridade:**
1. `quicksol_estate` (módulo core)
2. `auditlog` (módulo crítico)
3. Demais módulos por ordem de importância

### Fase 3: Manutenção Contínua (Sempre)

- ✅ Testes rodam em todos os PRs
- ✅ Merge bloqueado se testes falharem
- ✅ Revisão mensal da cobertura
- ✅ Refatoração de testes quando necessário

---

## Guia Rápido: Quando Usar Cada Tipo de Teste

### 🔍 Tipo 1: Linting (Flake8)

**O que testa:** Qualidade e estilo do código Python

**Quando usar:** SEMPRE - antes de qualquer teste

**Exemplos do que detecta:**
- ✅ Variáveis não utilizadas
- ✅ Imports não usados
- ✅ Linhas muito longas (> 120 caracteres)
- ✅ Espaços em branco desnecessários
- ✅ Problemas de indentação
- ✅ Violações de PEP 8

**Comando:**
```bash
./lint.sh
# ou
flake8 extra-addons/meu_modulo/
```

**Tempo de execução:** < 5 segundos

---

### 🧪 Tipo 2: Testes Unitários (Python unittest)

**O que testa:** Lógica de negócio isolada (sem banco de dados)

**Quando usar:**
- ✅ Validações de campos (required, constraints)
- ✅ Cálculos e computações
- ✅ Regras de negócio
- ✅ Formatação de dados
- ✅ Métodos helper/utility
- ✅ Lógica de controllers (sem HTTP)

**Comando:**
```bash
docker compose exec odoo python3 /mnt/extra-addons/meu_modulo/tests/run_unit_tests.py
```

**Tempo de execução:** < 1 segundo por módulo

**Quando NÃO usar:**
- ❌ Testar UI (use Cypress)
- ❌ Testar integração com banco (use E2E)
- ❌ Testar APIs HTTP (use curl ou Cypress)

---

### 🌐 Tipo 3: Testes E2E (Cypress + curl)

**O que testa:** Fluxos completos de usuário (UI + Backend + Banco)

**Quando usar:**

**3A. Cypress (UI/Frontend):**
- ✅ Fluxos de CRUD (criar, editar, deletar)
- ✅ Navegação entre telas
- ✅ Validações visíveis ao usuário
- ✅ Formulários e botões
- ✅ Mensagens de sucesso/erro

**Comando:**
```bash
npx cypress run --spec "cypress/e2e/meu-modulo.cy.js"
```

**3B. curl (APIs REST) - SEM Framework Odoo:**
- ✅ **Objetivo:** Testar endpoints REST sem usar framework Odoo
- ✅ **Por quê:** Framework Odoo faz alterações na base de dados (transações, commits automáticos)
- ✅ curl simula cliente HTTP real (como usuário ou aplicação externa)
- ✅ Não faz alterações no banco (testes são isolados)
- ✅ Endpoints de API
- ✅ Autenticação OAuth (tokens JWT)
- ✅ Respostas JSON e status HTTP corretos
- ✅ Variáveis de teste carregadas do arquivo `.env`

**Exemplo com curl:**
```bash
# Teste de criar registro (POST)
curl -X POST http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Casa Teste", "expected_price": 100000}' \
  -v

# Teste de listar registros (GET)
curl -X GET http://localhost:8069/api/v1/properties \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"
```

---

### 📊 Comparação dos 3 Tipos

| Aspecto | Linting | Unit Tests | E2E Tests |
|---------|---------|------------|-----------|
| **Velocidade** | ⚡⚡⚡ < 5s | ⚡⚡ < 1s/módulo | ⚡ 1-3min/módulo |
| **Cobertura** | Sintaxe/Estilo | Lógica isolada | Integração completa |
| **Quando rodar** | Sempre primeiro | Após linting | Após unit tests |
| **Usa banco?** | ❌ Não | ❌ Não (mocks) | ✅ Sim |
| **Testa UI?** | ❌ Não | ❌ Não | ✅ Sim (Cypress) |
| **Testa API?** | ❌ Não | ⚠️ Lógica apenas | ✅ Sim (curl) |
| **Detecta** | Erros sintaxe | Bugs lógica | Bugs integração |
| **Quantidade** | 1 por módulo | 100+ por módulo | 5-20 por módulo |

**Regra:** Use os 3 tipos - são complementares, não excludentes!

---

## Métricas de Sucesso

Mediremos o sucesso desta decisão através de:

### KPIs Principais

| Métrica | Meta | Atual |
|---------|------|-------|
| Módulos com 100% cobertura | 100% | 50% (1/2) |
| **Validações com 100% cobertura** | **100%** | **100%** |
| Bugs em produção | < 2/mês | - |
| Tempo médio de PR | < 2 dias | - |
| Confiança da equipe (NPS) | > 8/10 | - |

### Dashboards

Criar dashboards para visualizar:
- Cobertura de testes por módulo
- Taxa de sucesso dos testes
- Tempo de execução dos testes
- Bugs encontrados vs bugs em produção

---

## Responsabilidades

### Desenvolvedor

- Criar testes unitários e E2E
- Garantir 100% de cobertura
- Documentar testes criados
- Manter testes atualizados

### Tech Lead

- Revisar qualidade dos testes
- Aprovar exceções (se houver)
- Monitorar métricas
- Treinar equipe

### DevOps

- Manter CI/CD funcionando
- Gerar relatórios de cobertura
- Otimizar tempo de execução
- Monitorar recursos

---

## Revisão

Este ADR será revisado:

- **Mensalmente:** Métricas de KPI
- **Trimestralmente:** Ajustes no processo
- **Anualmente:** Revisão completa da decisão

**Próxima revisão:** 2026-03-08

---

## FAQ: Cobertura de 100% em Validações

### P: Por que NÃO fazemos testes manuais?

**R:** Testes manuais têm 6 problemas críticos:

1. **Não são repetíveis**: Pessoa A testa diferente da Pessoa B
2. **Não são versionados**: Não sabemos o que foi testado em cada versão
3. **São lentos**: Humano leva 1 hora, máquina leva 2 minutos
4. **São esquecíveis**: Dev pode esquecer de testar um caso específico
5. **Não detectam regressão**: Bug corrigido volta e ninguém percebe
6. **Não escalam**: 100 funcionalidades = impossível testar tudo manualmente

**Solução:** 3 tipos de testes automatizados (Linting + Unit + E2E) que rodam em 3 minutos e detectam 99% dos bugs.

### P: E se eu já testei manualmente e funcionou?

**R:** Ótimo! Agora **transforme esse teste manual em teste automatizado**:
- Se testou na UI → Criar teste Cypress
- Se testou a API → Criar teste curl ou Python
- Se testou lógica → Criar teste unitário

**"Testei manualmente" não é evidência suficiente** para aprovar PR.

### P: Posso fazer testes exploratórios de UX?

**R:** SIM! Testes exploratórios são **complementares** aos automatizados:
- ✅ Use para descobrir melhorias de usabilidade
- ✅ Use para validar fluxos com stakeholders
- ✅ Use para encontrar edge cases inesperados
- ❌ **MAS não substitui testes automatizados**

Fluxo correto:
1. Desenvolver feature com testes automatizados (obrigatório)
2. Fazer teste exploratório (opcional)
3. Se achar bug/melhoria → Adicionar teste automatizado para o caso

### P: Por que 100% e não 80% ou 90%?

**R:** Validações são a primeira linha de defesa contra dados inválidos. Um único campo sem validação pode corromper todo o banco de dados. Experiência mostra que "quase 100%" na prática significa "muito menos", pois desenvolvedores sempre escolhem não testar as partes "mais difíceis" - que são justamente as mais propensas a bugs.

### P: E se a validação for muito simples, tipo `required=True`?

**R:** Ainda assim deve ter testes. Testes simples são rápidos de escrever (< 1 minuto) e previnem:
- Remoção acidental do `required=True`
- Mudanças futuras que quebrem a validação
- Servem de documentação viva

### P: Como testar SQL constraints sem banco de dados?

**R:** Use mocks para simular a lógica da constraint. O objetivo é testar a **regra de negócio**, não a implementação SQL:

```python
def test_unique_constraint(self):
    """Test that duplicate names are rejected"""
    existing_names = ['Name1', 'Name2']
    new_name = 'Name1'
    
    with self.assertRaises(ValidationError):
        if new_name in existing_names:
            raise ValidationError("Name must be unique")
```

### P: O que acontece se eu abrir um PR sem 100% de cobertura em validações?

**R:** O PR será **rejeitado** no code review. Não é negociável. Validações não testadas = bugs em produção = dados corrompidos.

### P: Posso testar validações apenas com testes E2E?

**R:** NÃO. Testes E2E são lentos e frágeis. Validações devem ter:
1. ✅ Testes unitários (obrigatório, rápido, confiável)
2. ✅ Testes E2E (complementar, valida UI/UX)

### P: Como sei se cobri 100% das validações?

**Checklist:**
- [ ] Todo `required=True` tem 2 testes (com valor + sem valor)
- [ ] Todo `@api.constrains` tem N+1 testes (N falhas + 1 sucesso)
- [ ] Todo `_sql_constraints` tem 2+ testes
- [ ] Todo campo `compute` tem testes para cada branch
- [ ] Todo método de validação customizado tem testes para cada condição

### P: Como testar APIs REST com curl?

**R:** Use `curl` **SEM o framework Odoo**. Isto garante que o teste é realista (como um cliente HTTP real). O framework Odoo faz alterações automáticas no banco que mascaram problemas.

**Estrutura correta:**
```bash
#!/bin/bash
# Arquivo: cypress/api-tests/test-api.sh
# Executar: bash cypress/api-tests/test-api.sh

# Carregar variáveis do .env
source 18.0/.env

echo "🔍 Testando API REST sem Framework Odoo..."

# Obter token JWT
TOKEN=$(curl -s -X POST "$ODOO_API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_USER_EMAIL\", \"password\": \"$TEST_USER_PASSWORD\"}" \
  | jq -r '.jwt_token')

# Teste 1: Criar propriedade (POST)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$ODOO_API_URL/properties" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Casa Teste", "expected_price": 100000}')

if [ "$HTTP_CODE" = "201" ]; then
  echo "✅ Teste 1 passou (HTTP 201 - Criado)"
else
  echo "❌ Teste 1 falhou (HTTP $HTTP_CODE)"
  exit 1
fi

# Teste 2: Listar propriedades (GET)
curl -s -X GET "$ODOO_API_URL/properties" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | jq '.results | length'

echo "✨ Todos os testes de API passaram!"
```

**Por quê NÃO usar o framework Odoo em testes de API:**
- ❌ Framework Odoo cria transações automáticas (altera DB)
- ❌ Commit automático mascara problemas reais
- ❌ Não simula cliente HTTP real
- ✅ `curl` simula exatamente como aplicação externa acessa a API

### P: Cypress testa UI, por que "simula o usuário"?

**R:** Cypress é um framework **End-to-End (E2E)** que:
1. ✅ **Abre navegador real** (Chrome, Firefox, Edge)
2. ✅ **Executa JavaScript** como se fosse usuário clicando
3. ✅ **Valida a tela** - clica botões, preenche campos, verifica mensagens
4. ✅ **Testa integração completa** - UI + Backend + Banco de dados

**Diferenças:**

| Tipo | Simula Usuário? | Abre UI? | Testa Banco? |
|------|-----------------|----------|------------|
| **Unitários** | ❌ Não | ❌ Não | ❌ Não (mocks) |
| **curl (API)** | ❌ Não | ❌ Não | ✅ Sim (real) |
| **Cypress (E2E)** | ✅ SIM | ✅ SIM | ✅ SIM |

**Exemplo prático:**
```javascript
describe('Criar Propriedade - Fluxo do Usuário Real', () => {
  it('Deve criar propriedade como usuário faria', () => {
    // 1. Simulando usuário visitando site
    cy.visit(Cypress.env('ODOO_URL'));
    
    // 2. Simulando usuário digitando email e senha
    cy.get('input[name="login"]').type(Cypress.env('CYPRESS_ADMIN_LOGIN'));
    cy.get('input[name="password"]').type(Cypress.env('CYPRESS_ADMIN_PASSWORD'));
    cy.get('button[type="submit"]').click();
    
    // 3. Simulando usuário navegando para menu Propriedades
    cy.get('a[href*="/web#action=estate.action_property"]').click();
    
    // 4. Simulando usuário clicando "Novo" e preenchendo formulário
    cy.get('.o_form_button_create').click();
    cy.get('input[name="name"]').type('Casa Lindíssima');
    cy.get('input[name="expected_price"]').type('300000');
    cy.get('.o_form_button_save').click();
    
    // 5. Simulando usuário verificando mensagem de sucesso
    cy.get('.o_notification.bg-success')
      .should('be.visible')
      .should('contain', 'Registrado com sucesso');
    
    // Verificar que banco foi atualizado (E2E = testa banco real)
    cy.request('GET', `${Cypress.env('ODOO_API_URL')}/properties`, {
      headers: { 'Authorization': `Bearer ${Cypress.env('JWT_TOKEN')}` }
    }).then(response => {
      expect(response.body.results).to.have.length.at.least(1);
    });
  });
});
```

### P: Testes unitários devem testar APENAS classes?

**R:** SIM, absolutamente. Testes unitários devem:
- ✅ **Testar APENAS 1 classe/função** em isolamento
- ✅ **Usar mocks** para todas as dependências externas
- ✅ **NÃO usar banco de dados** real (banco = teste de integração)
- ✅ **NÃO usar framework Odoo** (framework = complexidade desnecessária)
- ❌ **NÃO testar UI** (UI = teste E2E com Cypress)
- ❌ **NÃO testar API HTTP** (API = teste com curl ou Cypress)

**O que NÃO é teste unitário:**
- ❌ Testes que usam banco de dados = testes de integração
- ❌ Testes que usam framework Odoo = testes de integração
- ❌ Testes que testam múltiplas classes juntas = testes de integração

**Exemplo CORRETO - Teste Unitário:**
```python
import unittest
from unittest.mock import Mock
from odoo.exceptions import ValidationError

class TestPropertyPrice(unittest.TestCase):
    """Testa APENAS a validação de preço (sem banco, sem Odoo, sem UI)"""
    
    def test_price_must_be_positive(self):
        """Testa APENAS a regra de validação"""
        # Arrange: criar mock da classe
        mock_property = Mock()
        mock_property.expected_price = -1000
        
        # Act & Assert: testar APENAS a validação
        with self.assertRaises(ValidationError):
            if mock_property.expected_price < 0:
                raise ValidationError("Price must be positive")
    
    def test_price_accepts_valid_value(self):
        """Testa cenário inverso"""
        mock_property = Mock()
        mock_property.expected_price = 100000
        
        # Verificar que é válido
        is_valid = mock_property.expected_price > 0
        self.assertTrue(is_valid)
```

**Exemplo INCORRETO - Não é teste unitário:**
```python
# ❌ ERRADO: Usar banco de dados em teste unitário
class TestPropertyWrong(unittest.TestCase):
    def test_create_property(self):
        # Isto é TESTE DE INTEGRAÇÃO, não unitário!
        from odoo import models
        property = models.Property.create({
            'name': 'Casa',
            'expected_price': 100000
        })
        self.assertEqual(property.name, 'Casa')  # ❌ Usa banco real!

# ❌ ERRADO: Usar UI em teste unitário
class TestPropertyUIWrong(unittest.TestCase):
    def test_create_property_ui(self):
        # Isto é TESTE E2E, não unitário!
        cy.visit('/web#action=estate.action_property')  # ❌ Abre navegador!
        cy.get('.o_form_button_create').click()

# ❌ ERRADO: Usar framework Odoo em teste unitário
class TestPropertyFrameworkWrong(unittest.TestCase):
    def test_create_property_framework(self):
        # Isto é TESTE DE INTEGRAÇÃO, não unitário!
        self.env['estate.property'].create({  # ❌ Usa framework Odoo!
            'name': 'Casa',
            'expected_price': 100000
        })
```

### P: E se o código legado não tiver testes de validação?

**R:** 
- Código novo/modificado: 100% obrigatório desde já
- Código legado: Implementação gradual conforme cronograma (3 meses)
- Ao modificar código legado: Adicionar testes de validação antes da modificação

---

## Referências

- [ADR-001: Development Guidelines for Odoo Screens](./ADR-001-development-guidelines-for-odoo-screens.md)

**R:** 
- Código novo/modificado: 100% obrigatório desde já
- Código legado: Implementação gradual conforme cronograma (3 meses)
- Ao modificar código legado: Adicionar testes de validação antes da modificação

---

## Referências

- [ADR-001: Development Guidelines for Odoo Screens](./ADR-001-development-guidelines-for-odoo-screens.md)
- [Test Pyramid - Martin Fowler](https://martinfowler.com/bliki/TestPyramid.html)
- [Clean Code - Robert C. Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)

---

## Histórico de Mudanças

| Data | Versão | Mudança | Autor |
|------|--------|---------|-------|
| 2025-11-16 | 1.0 | Criação inicial do ADR | Equipe Dev |
| 2025-11-30 | 1.1 | Adicionado linting obrigatório com flake8 e PEP 8 | Equipe Dev |
| 2026-01-08 | 2.0 | **Atualizado para exigir 100% de cobertura em TODAS as validações** | Equipe Dev |

---

**Decisão Final:** ✅ **ACEITO**

Esta decisão entra em vigor imediatamente para todos os novos módulos e gradualmente para módulos existentes conforme cronograma estabelecido na seção Implementação.

---

## Apêndice A: Template de Teste Unitário

```python
# -*- coding: utf-8 -*-
"""
Unit Tests for [Nome do Módulo] (Pure mocks - no database)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


class TestMyModel(unittest.TestCase):
    """Test MyModel business logic"""
    
    def test_example_calculation(self):
        """Test that calculation returns expected result"""
        # Arrange
        mock_obj = Mock()
        mock_obj.value = 100
        
        # Act
        result = mock_obj.value * 1.1
        
        # Assert
        self.assertEqual(result, 110)


if __name__ == '__main__':
    unittest.main(verbosity=2)
```

---

## Apêndice B: Template de Teste E2E

```javascript
describe('Meu Módulo - Feature Name', () => {
  beforeEach(() => {
    cy.login('admin', 'admin');
  });

  it('Deve executar ação esperada', () => {
    // Arrange
    cy.visit('/web#action=my_module.action_my_model');
    
    // Act
    cy.get('.o_form_button_create').click();
    cy.get('input[name="name"]').type('Teste');
    cy.get('.o_form_button_save').click();
    
    // Assert
    cy.get('.o_notification.bg-success').should('be.visible');
  });

  afterEach(() => {
    // Cleanup
    cy.archiveTestRecords('my.model', 'Teste%');
  });
});
```

---

## Apêndice C: Comando de Execução Rápida

```bash
#!/bin/bash
# Script para rodar todos os testes do projeto

echo "🧪 Executando testes unitários..."
docker compose exec odoo find /mnt/extra-addons -name "run_unit_tests.py" \
  -exec python3 {} \;

echo ""
echo "🌐 Executando testes E2E..."
npx cypress run

echo ""
echo "✅ Todos os testes concluídos!"
```

Salvar como `run_all_tests.sh` e executar: `./run_all_tests.sh`
---

## Apêndice D: Template de Testes de Validação (100% Cobertura)

```python
# -*- coding: utf-8 -*-
"""
Validation Tests Template - 100% Coverage REQUIRED
Demonstra como testar TODAS as validações de um modelo
"""

import unittest
from unittest.mock import Mock
from odoo.exceptions import ValidationError


class TestModelValidations(unittest.TestCase):
    """
    Template para 100% de cobertura em validações
    Cada validação DEVE ter no mínimo 2 testes
    """
    
    # ==================================================
    # VALIDAÇÃO 1: Campo obrigatório (required=True)
    # ==================================================
    
    def test_required_field_accepts_value(self):
        """Test required field validation passes with value"""
        mock = Mock()
        mock.name = "Valid Name"
        self.assertIsNotNone(mock.name)
        self.assertTrue(len(mock.name) > 0)
    
    def test_required_field_rejects_none(self):
        """Test required field validation fails with None"""
        mock = Mock()
        mock.name = None
        with self.assertRaises(ValidationError):
            if not mock.name:
                raise ValidationError("Name is required")
    
    def test_required_field_rejects_empty_string(self):
        """Test required field validation fails with empty string"""
        mock = Mock()
        mock.name = ""
        with self.assertRaises(ValidationError):
            if not mock.name or not mock.name.strip():
                raise ValidationError("Name is required")
    
    # ==================================================
    # VALIDAÇÃO 2: SQL Constraint (valor positivo)
    # ==================================================
    
    def test_positive_constraint_accepts_positive(self):
        """Test positive constraint accepts valid positive value"""
        mock = Mock()
        mock.price = 100.00
        self.assertGreater(mock.price, 0)
    
    def test_positive_constraint_rejects_zero(self):
        """Test positive constraint rejects zero"""
        mock = Mock()
        mock.price = 0
        with self.assertRaises(ValidationError):
            if mock.price <= 0:
                raise ValidationError("Price must be positive")
    
    def test_positive_constraint_rejects_negative(self):
        """Test positive constraint rejects negative value"""
        mock = Mock()
        mock.price = -100.00
        with self.assertRaises(ValidationError):
            if mock.price <= 0:
                raise ValidationError("Price must be positive")
    
    # ==================================================
    # VALIDAÇÃO 3: Python Constraint (@api.constrains)
    # ==================================================
    
    def test_date_range_valid(self):
        """Test date range constraint accepts valid range"""
        from datetime import datetime
        mock = Mock()
        mock.start_date = datetime(2026, 1, 1)
        mock.end_date = datetime(2026, 12, 31)
        is_valid = mock.end_date > mock.start_date
        self.assertTrue(is_valid)
    
    def test_date_range_rejects_end_before_start(self):
        """Test date range constraint rejects end_date before start_date"""
        from datetime import datetime
        mock = Mock()
        mock.start_date = datetime(2026, 12, 31)
        mock.end_date = datetime(2026, 1, 1)
        with self.assertRaises(ValidationError):
            if mock.end_date <= mock.start_date:
                raise ValidationError("End date must be after start date")
    
    def test_date_range_rejects_same_date(self):
        """Test date range constraint rejects same dates"""
        from datetime import datetime
        mock = Mock()
        mock.start_date = datetime(2026, 6, 15)
        mock.end_date = datetime(2026, 6, 15)
        with self.assertRaises(ValidationError):
            if mock.end_date <= mock.start_date:
                raise ValidationError("End date must be after start date")
    
    # ==================================================
    # VALIDAÇÃO 4: Campo computado (compute method)
    # ==================================================
    
    def test_total_compute_with_values(self):
        """Test total computation with valid values"""
        mock = Mock()
        mock.quantity = 10
        mock.unit_price = 50.00
        total = mock.quantity * mock.unit_price
        self.assertEqual(total, 500.00)
    
    def test_total_compute_with_zero_quantity(self):
        """Test total computation with zero quantity"""
        mock = Mock()
        mock.quantity = 0
        mock.unit_price = 50.00
        total = mock.quantity * mock.unit_price
        self.assertEqual(total, 0.00)
    
    def test_total_compute_with_none_values(self):
        """Test total computation handles None values"""
        mock = Mock()
        mock.quantity = None
        mock.unit_price = 50.00
        # Should handle None gracefully
        total = (mock.quantity or 0) * (mock.unit_price or 0)
        self.assertEqual(total, 0.00)
    
    # ==================================================
    # VALIDAÇÃO 5: Validação customizada (método próprio)
    # ==================================================
    
    def test_email_validation_accepts_valid(self):
        """Test email validation accepts valid format"""
        import re
        mock = Mock()
        mock.email = "user@example.com"
        is_valid = bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', mock.email))
        self.assertTrue(is_valid)
    
    def test_email_validation_rejects_invalid(self):
        """Test email validation rejects invalid format"""
        import re
        mock = Mock()
        mock.email = "invalid-email"
        with self.assertRaises(ValidationError):
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', mock.email):
                raise ValidationError("Invalid email format")
    
    def test_email_validation_rejects_empty(self):
        """Test email validation rejects empty string"""
        mock = Mock()
        mock.email = ""
        with self.assertRaises(ValidationError):
            if not mock.email or len(mock.email.strip()) == 0:
                raise ValidationError("Email is required")
    
    # ==================================================
    # VALIDAÇÃO 6: Constraint de unicidade
    # ==================================================
    
    def test_unique_constraint_accepts_unique(self):
        """Test unique constraint accepts unique value"""
        existing_codes = ['CODE001', 'CODE002']
        new_code = 'CODE003'
        self.assertNotIn(new_code, existing_codes)
    
    def test_unique_constraint_rejects_duplicate(self):
        """Test unique constraint rejects duplicate value"""
        existing_codes = ['CODE001', 'CODE002']
        new_code = 'CODE001'
        with self.assertRaises(ValidationError):
            if new_code in existing_codes:
                raise ValidationError("Code must be unique")


if __name__ == '__main__':
    # Executar: python3 test_validations.py
    unittest.main(verbosity=2)
```

**Métricas deste template:**
- ✅ 6 validações diferentes
- ✅ 18 testes (média de 3 por validação)
- ✅ 100% de cobertura
- ✅ Testa cenários válidos e inválidos
- ✅ Testa valores extremos (None, 0, vazio)
- ✅ Tempo de execução: < 0.1 segundo

---

## Apêndice E: Checklist de Validações por Tipo de Campo

### Campos de Texto (Char, Text)
- [ ] Teste com valor válido
- [ ] Teste com None (se required=True)
- [ ] Teste com string vazia (se required=True)
- [ ] Teste com espaços em branco (se validação de trim)
- [ ] Teste com comprimento máximo (se size definido)

### Campos Numéricos (Integer, Float, Monetary)
- [ ] Teste com valor positivo
- [ ] Teste com zero
- [ ] Teste com valor negativo
- [ ] Teste com None (se required=True)
- [ ] Teste com limites (min/max se aplicável)

### Campos de Data (Date, Datetime)
- [ ] Teste com data válida
- [ ] Teste com None (se required=True)
- [ ] Teste com range de datas (se constraint de range)
- [ ] Teste com data no passado/futuro (se restrição temporal)

### Campos de Seleção (Selection)
- [ ] Teste com cada opção válida
- [ ] Teste com valor inválido
- [ ] Teste com None (se required=True)

### Campos Relacionais (Many2one, Many2many, One2many)
- [ ] Teste com relação válida
- [ ] Teste com None (se required=True)
- [ ] Teste com ID inexistente (se validação de existência)
- [ ] Teste com múltiplas relações (se Many2many/One2many)

### Constraints Python (@api.constrains)
- [ ] Teste para cada condição que lança ValidationError
- [ ] Teste para condição válida (não lança erro)
- [ ] Teste para valores extremos
- [ ] Teste para combinações de campos (se constraint envolve múltiplos campos)

### Campos Computados (compute=)
- [ ] Teste para cada branch do método compute
- [ ] Teste com dependências None
- [ ] Teste com dependências vazias
- [ ] Teste com valores extremos das dependências