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
RESPONSE=$(curl -s -X POST "$BASE_URL/api/endpoint" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"data": "value"}')
```

3. **Asserções:**
```bash
if [[ "$RESPONSE" == *"expected"* ]]; then
  echo "✅ PASS"
else
  echo "❌ FAIL"
  exit 1
fi
```

## 📁 Convenções de Nomenclatura

- **Unitários:** `test_*_unit.py` (ex: `test_property_validations_unit.py`)
- **E2E Cypress:** `*.cy.js` (ex: `imoveis-fluxo-completo.cy.js`)
- **E2E Shell:** `test_*.sh` (ex: `test_us1_s1_owner_login.sh`)

## 🔍 Verificação de Cobertura

Quando criar um teste, sempre verifique se:

1. ✅ O teste está no diretório correto
2. ✅ Segue o template do projeto
3. ✅ Usa credenciais do `.env` (não hardcoded)
4. ✅ Tem comando de execução documentado
5. ✅ Está alinhado com a ADR-003

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
