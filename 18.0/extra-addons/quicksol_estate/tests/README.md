# Estrutura de Testes - quicksol_estate

**Reorganizado**: 2026-01-22  
**Padrão**: ADR-003 Mandatory Test Coverage

## 📂 Estrutura de Diretórios

```
tests/
├── __init__.py                 # Inicializa pacote de testes
├── base_*.py                   # Classes base para testes
│
├── unit/                       # ✅ Testes Unitários (unittest.mock)
│   ├── __init__.py
│   ├── run_unit_tests.py      # Runner para executar todos os testes unitários
│   ├── test_agent_unit.py
│   ├── test_company_unit.py
│   ├── test_utils_unit.py
│   └── test_*_unit.py
│
├── integration/                # ✅ Testes de Integração (TransactionCase)
│   ├── __init__.py
│   ├── test_rbac_*.py         # Testes de RBAC (Owner, Agent, Manager, etc)
│   ├── test_commission_*.py   # Testes de comissões
│   ├── test_validations.py    # Testes de validações com banco
│   └── test_*_integration.py
│
├── observers/                  # ✅ Testes de Observers (EventBus)
│   ├── __init__.py
│   ├── test_event_bus.py
│   ├── test_abstract_observer.py
│   └── test_*_observer.py
│
├── api/                        # ✅ Testes de API (TransactionCase)
│   ├── __init__.py
│   ├── test_oauth.py
│   ├── test_property_api.py
│   └── test_*_api.py
│
└── validate_phase7.py          # Script de validação de fase
```

## 🎯 Tipos de Testes

### 1. Testes Unitários (`unit/`)

**Framework**: `unittest` + `unittest.mock`  
**Banco de dados**: ❌ NÃO  
**Odoo framework**: ❌ NÃO

**O que testar:**
- Validações de campo (`required`, `constraints`)
- Cálculos e lógica de negócio
- Helpers e utils
- Formatadores e parsers

**Executar:**
```bash
cd 18.0/extra-addons/quicksol_estate/tests/unit
python3 run_unit_tests.py
```

**Características:**
- ⚡ Rápido (< 1 segundo)
- 🔒 Isolado (sem dependências externas)
- 🎯 Testa uma função/método por vez

---

### 2. Testes de Integração (`integration/`)

**Framework**: `odoo.tests.common.TransactionCase`  
**Banco de dados**: ✅ SIM (Odoo test DB)  
**Odoo framework**: ✅ SIM

**O que testar:**
- RBAC (record rules, ACLs)
- Validações que dependem do ORM
- Constraints SQL
- Observers e event bus
- Models e relacionamentos

**Executar:**
```bash
cd 18.0
docker compose run --rm odoo odoo \
  --test-enable \
  --test-tags=quicksol_estate \
  --stop-after-init
```

**Características:**
- 🐢 Mais lento (segundos a minutos)
- 🔗 Testa interações entre componentes
- 💾 Usa banco de dados de teste (rollback automático)

---

### 3. Testes de Observers (`observers/`)

**Framework**: `odoo.tests.common.TransactionCase`  
**Banco de dados**: ✅ SIM  

**O que testar:**
- Event emission
- Observer registration
- Event handling
- Async event queuing

**Executar:** (mesmo comando dos testes de integração)

---

### 4. Testes de API (`api/`)

**Framework**: `odoo.tests.common.TransactionCase`  
**Banco de dados**: ✅ SIM

**O que testar:**
- Endpoints REST internos
- OAuth token validation
- Payload serialization
- Response formatting

**⚠️ Limitação:** TransactionCase não persiste dados (read-only transactions).  
**Para testes E2E de API reais, use:** `integration_tests/` na raiz do repo.

---

## 🚀 Ordem de Execução

```bash
# 1. Linting (PRIMEIRO)
./lint.sh

# 2. Testes Unitários (rápido, sem banco)
cd 18.0/extra-addons/quicksol_estate/tests/unit
python3 run_unit_tests.py

# 3. Testes de Integração (Odoo framework + banco)
cd 18.0
docker compose run --rm odoo odoo \
  --test-enable \
  --test-tags=quicksol_estate \
  --stop-after-init

# 4. Testes E2E de API (curl/bash - na raiz do repo)
cd integration_tests
bash run_all_tests.sh

# 5. Testes E2E de UI (Cypress)
npm run cypress:run
```

## 📍 Onde colocar novos testes?

| Teste | Localização |
|-------|-------------|
| Validação de campo obrigatório | `unit/test_*_unit.py` |
| Cálculo de comissão | `unit/test_commission_unit.py` |
| Record rule de RBAC | `integration/test_rbac_*.py` |
| Observer reage a evento | `observers/test_*_observer.py` |
| Endpoint REST funciona | `api/test_*_api.py` |
| Jornada completa de usuário | `integration_tests/test_*.sh` (raiz) |
| Fluxo de UI/UX | `cypress/e2e/*.cy.js` (raiz) |

## ❌ Anti-Patterns

### NÃO faça isso:

```python
# ❌ ERRADO - Teste unitário com banco de dados
from odoo.tests.common import TransactionCase

class TestCommissionCalculation(TransactionCase):  # Deveria ser unittest.TestCase
    def test_split_30_70(self):
        # Testando lógica pura não precisa de banco
        result = calculate_split(1000, 0.30)
        self.assertEqual(result, (300, 700))
```

### ✅ Faça isso:

```python
# ✅ CORRETO - Teste unitário puro
import unittest

class TestCommissionCalculation(unittest.TestCase):
    def test_split_30_70(self):
        result = calculate_split(1000, 0.30)
        self.assertEqual(result, (300, 700))
```

## 📚 Referências

- [ADR-003: Mandatory Test Coverage](../../../../docs/adr/ADR-003-mandatory-test-coverage.md)
- [ADR-002: Cypress E2E Testing](../../../../docs/adr/ADR-002-cypress-end-to-end-testing.md)
- [Tasks.md - Test Structure](../../../../specs/005-rbac-user-profiles/tasks.md)

## 🔄 Migração de Testes Antigos

Se você encontrar testes na raiz de `tests/` (não em subpastas), mova-os:

```bash
# TransactionCase → integration/
mv tests/test_rbac_*.py tests/integration/

# unittest.mock → unit/
mv tests/test_*_unit.py tests/unit/

# Observer tests → observers/
mv tests/test_*_observer.py tests/observers/
```
