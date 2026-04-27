# Test Strategy Instructions

**Auto-aplicável:** Este arquivo é lido automaticamente pelo GitHub Copilot quando você trabalha com arquivos de teste.

## 🎯 Objetivo

Garantir que **todos os testes** sigam a estratégia definida na ADR-003.

## 📖 Referência Obrigatória

**SEMPRE consulte:**
- `docs/adr/ADR-003-mandatory-test-coverage.md` - Estratégia oficial de testes

## 🧪 Tipos de Testes (ADR-003)

Este projeto usa **APENAS 2 tipos de testes**:

### 1. Testes Unitários (Python unittest + mock)
- **Localização:** `18.0/extra-addons/*/tests/unit/`
- **Framework:** Python `unittest` + `unittest.mock`
- **Quando usar:** Lógica isolada que **NÃO precisa** de banco de dados
- **Exemplos:**
  - Validações de campos (`required`, `@api.constrains`)
  - Cálculos e transformações de dados
  - Lógica de negócio pura (helpers, utils)
- **Template:** `18.0/extra-addons/quicksol_estate/tests/unit/test_property_validations_unit.py`

### 2. Testes E2E (End-to-End)
- **Cypress (UI/UX):**
  - **Localização:** `cypress/e2e/`
  - **Quando usar:** Fluxos de usuário via interface
  - **Exemplo:** `cypress/e2e/imoveis-fluxo-completo.cy.js`
  
- **curl/shell (API):**
  - **Localização:** `integration_tests/`
  - **Quando usar:** Endpoints REST/API
  - **Exemplo:** `integration_tests/test_us1_s1_owner_login.sh`

## ⚡ Regra de Ouro

```
"Este teste precisa de banco de dados real?"
  → NÃO  = Teste Unitário (com mock)
  → SIM  = Teste E2E (Cypress ou curl)
```

## 🚫 O que NÃO fazer

❌ Criar testes com `HttpCase` do Odoo (não persiste dados)
❌ Usar fixtures complexas em testes unitários
❌ Mockar bancos de dados em E2E (use o real)
❌ Hardcoded credentials (use `18.0/.env`)
❌ **NUNCA usar formato JSON-RPC** em testes de API (wrapper `{"jsonrpc": "2.0", "method": "call", "params": {...}}`)
❌ **CNPJs inválidos** - sempre use formato válido brasileiro (14 dígitos com validação)
❌ **Login de admin em testes de API** - use usuários específicos por perfil (manager, agent, owner)
❌ **Dados sensíveis hardcoded** - sempre no .env

### ⚠️ IMPORTANTE: JSON-RPC NÃO é suportado

Endpoints REST deste projeto usam **JSON direto** no body:

```json
// ✅ CORRETO
{"email": "user@example.com", "password": "secret"}

// ❌ ERRADO - NÃO usar wrapper JSON-RPC
{"jsonrpc": "2.0", "method": "call", "params": {"email": "...", "password": "..."}}
```

## ✅ Regras ao Criar/Modificar Testes

### Para Testes Unitários:

1. **Estrutura de arquivo obrigatória:**
```python
import unittest
from unittest.mock import MagicMock, patch

class TestPropertyValidations(unittest.TestCase):
    def setUp(self):
        # Setup com mocks
        pass
    
    def test_agent_id_required(self):
        # Teste isolado
        pass

if __name__ == '__main__':
    unittest.main()
```

2. **Use mocks para dependências externas:**
   - `@patch('odoo.models.Model')` para models
   - `MagicMock()` para objetos complexos
   - Nunca acesse o banco de dados real

3. **Comando de execução no docstring:**
```python
"""
Run: docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/unit/test_example.py
"""
```

### Para Testes E2E (Cypress):

1. **Use comandos customizados:**
```javascript
cy.loginAsOwner()       // Login com credenciais do .env
cy.loginAsManager()
cy.loginAsAgent()
cy.apiLogin(username, password)  // Login direto via API
```

2. **Estrutura recomendada:**
```javascript
describe('Fluxo Completo: [Cenário]', () => {
  beforeEach(() => {
    // Setup do teste
  })

  it('deve [ação esperada]', () => {
    // Arrange
    // Act
    // Assert
  })
})
```

3. **Credenciais do .env:**
```javascript
// ✅ CORRETO
const username = Cypress.env('OWNER_USERNAME')

// ❌ ERRADO
const username = 'owner'
```

### Para Testes E2E (shell/curl):

1. **Load .env automaticamente:**
```bash
#!/bin/bash
set -e
source "$(dirname "$0")/../18.0/.env"
```

2. **Estrutura de teste:**
```bash
echo "🧪 Test: [Cenário]"

# ✅ CORRETO - Usar variáveis do .env
RESPONSE=$(curl -s -X POST "$BASE_URL/api/endpoint" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"data": "value"}')

# ❌ ERRADO - Hardcode de credenciais
RESPONSE=$(curl -s -X POST "http://localhost:8069/api/endpoint" \
  -H "Authorization: Bearer hardcoded_token" \
  -d '{"username": "admin"}')
```

3. **Dados de teste válidos:**
```bash
# ✅ CORRETO - CNPJ válido do .env
CNPJ="${TEST_CNPJ}"  # 12.345.678/0001-95

# ❌ ERRADO - CNPJ inválido hardcoded
CNPJ="11111111111111"
```

4. **Login por perfil:**
```bash
# ✅ CORRETO - Usar usuário específico do perfil
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -d "{\"username\":\"${TEST_USER_AGENT}\",\"password\":\"${TEST_PASSWORD_AGENT}\"}" \
  | jq -r '.access_token')

# ❌ ERRADO - Usar admin em teste de permissões
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')
```

5. **Asserções:**
```bash
if [[ "$RESPONSE" == *"expected"* ]]; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
  exit 1
fi
```

## 📁 Convenções de Nomenclatura

### 1. Testes Unitários (`tests/unit/`)

| Elemento | Padrão | Exemplo |
|----------|--------|---------|
| **Arquivo** | `test_{domínio}_unit.py` | `test_property_validations_unit.py` |
| **Classe** | `Test{Domínio}(unittest.TestCase)` ou subclasse de base | `TestPropertyValidationsUnit` |
| **Método** | `test_{ação}_{condição}` | `test_agent_email_validation_valid` |
| **Docstring** | `"""FR-XXX: Descrição do que está sendo testado."""` | `"""FR-004: Proposal value must be positive."""` |

> ✅ O sufixo `_unit` é **obrigatório** — diferencia do diretório `integration/`.

```python
# ✅ CORRETO
# tests/unit/test_proposal_validations_unit.py
class TestProposalValidationsUnit(unittest.TestCase):
    def test_proposal_value_positive(self):
        """FR-004: Proposal value must be positive."""
        ...

# ❌ ERRADO — sufixo ausente
# tests/unit/test_proposal_validations.py
class TestProposalValidations(TransactionCase):
    ...
```

---

### 2. Testes de Integração (`tests/integration/`)

| Elemento | Padrão | Exemplo |
|----------|--------|---------|
| **Arquivo** | `test_{domínio}.py` | `test_proposal_create.py` |
| **Arquivo (categoria)** | `test_{categoria}_{domínio}.py` | `test_rbac_manager.py` |
| **Arquivo base** | `base_{feature}_test.py` | `base_proposal_test.py` |
| **Classe** | `Test{Domínio}(TransactionCase)` | `TestProposalCreate` |
| **Classe (base)** | `Base{Feature}Test(TransactionCase)` | `BaseProposalTest` |
| **Método** | `test_{ação}_{condição}` | `test_create_draft_when_no_active_proposal` |
| **Docstring** | `"""US{N}/FR-{N}: Descrição."""` | `"""US1/FR-001: First proposal goes to draft."""` |
| **Tags** | `@tagged('post_install', '-at_install', '{categoria}', '{domínio}')` | `@tagged('post_install', '-at_install', 'proposal', 'proposal_create')` |

> ✅ Sem sufixo no arquivo — o diretório `integration/` já comunica o tipo.  
> ❌ Nunca use `_integration` no nome do arquivo (ex: `test_rbac_owner_integration.py` → `test_rbac_owner.py`).

```python
# ✅ CORRETO
# tests/integration/test_proposal_create.py
@tagged('post_install', '-at_install', 'proposal', 'proposal_create')
class TestProposalCreate(BaseProposalTest):
    def test_create_draft_when_no_active_proposal(self):
        """US1/FR-001: First proposal for a property goes to draft."""
        ...

# ❌ ERRADO — sufixo desnecessário
# tests/integration/test_proposal_create_integration.py
class TestProposalCreateIntegration(TransactionCase):
    ...
```

---

### 3. Testes E2E Shell (`integration_tests/`)

| Elemento | Padrão | Exemplo |
|----------|--------|---------|
| **Arquivo** | `test_{us}{N}_{sN}_{descrição}.sh` | `test_us1_s1_owner_login.sh` |
| **Teste inline** | `echo "🧪 Test: {Cenário}"` | `echo "🧪 Test: Owner login"` |

---

### 4. Testes E2E Cypress (`cypress/e2e/`)

| Elemento | Padrão | Exemplo |
|----------|--------|---------|
| **Arquivo** | `{domínio}-{fluxo}.cy.js` | `imoveis-fluxo-completo.cy.js` |
| **describe** | `'Fluxo Completo: {Cenário}'` | `'Fluxo Completo: Criação de Imóvel'` |
| **it** | `'deve {ação esperada}'` | `'deve criar imóvel com dados válidos'` |

---

### Resumo Visual

```
tests/
  unit/
    test_{domínio}_unit.py          ← sufixo _unit obrigatório
    base_{feature}_test.py          ← base sem sufixo
  integration/
    test_{domínio}.py               ← sem sufixo
    test_{categoria}_{domínio}.py   ← prefixo de categoria
    base_{feature}_test.py          ← classe base compartilhada

integration_tests/
    test_{us}{N}_{sN}_{descrição}.sh

cypress/e2e/
    {domínio}-{fluxo}.cy.js
```

## 🔍 Verificação de Cobertura

Quando criar um teste, sempre verifique se:

1. ✅ O teste está no diretório correto
2. ✅ Segue o template do projeto
3. ✅ Usa credenciais do `.env` (não hardcoded)
4. ✅ **CNPJ está em formato válido** (14 dígitos com validação)
5. ✅ **Não usa login de admin** em testes de permissões de API
6. ✅ **Dados sensíveis estão no .env** (nunca no código)
7. ✅ Tem comando de execução documentado
8. ✅ Está alinhado com a ADR-003

## 📚 Recursos Úteis

- **ADR-003:** `docs/adr/ADR-003-mandatory-test-coverage.md`
- **Templates unitários:** `18.0/extra-addons/quicksol_estate/tests/unit/`
- **Cypress custom commands:** `cypress/support/commands.js`
- **Status dos testes:** `integration_tests/STATUS.md`

## 💡 Quando Pedir Ajuda

Se você está escrevendo um teste e não tem certeza qual tipo usar:

1. Consulte a ADR-003
2. Use o prompt `test-strategy.prompt.md` para análise detalhada
3. Verifique testes similares no projeto

---

**Nota:** Esta instruction é aplicada automaticamente pelo Copilot. Para análise detalhada de estratégia, use o prompt `.github/prompts/test-strategy.prompt.md`.
