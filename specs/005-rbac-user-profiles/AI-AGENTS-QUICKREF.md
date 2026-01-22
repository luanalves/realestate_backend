# AI Test Agents - Quick Reference

**Updated**: 2026-01-22  
**Feature**: RBAC User Profiles (Spec 005)

## 🚀 Processo Fluido (3 comandos)

```bash
# 1. Gerar tasks (se necessário)
@speckit.tasks 005-rbac-user-profiles

# 2. Gerar TODOS os testes automaticamente
@speckit.tests 005-rbac-user-profiles

# 3. Implementar código
@speckit.implement 005-rbac-user-profiles
```

**É só isso!** O `@speckit.tests` gera tudo automaticamente.

## Workflow Visual

```
@speckit.tasks → @speckit.tests → @speckit.implement → Validação
     │                │                  │
     ▼                ▼                  ▼
  tasks.md      Test Files          Code Files
               (auto-generated)   (TDD approach)
```

## O que @speckit.tests faz

1. ✅ Lê spec.md → extrai TODOS os acceptance scenarios
2. ✅ Aplica "Regra de Ouro" (precisa de banco? SIM→E2E, NÃO→Unit)
3. ✅ Gera código (curl/bash, Cypress, ou unittest)
4. ✅ Cria arquivos nas localizações corretas
5. ✅ Marca tasks de teste como [X] completas
6. ✅ Faz handoff para @speckit.implement

## Tipos de Teste (ADR-003)

| Tipo | Quando usar | Tool | Precisa DB? |
|------|-------------|------|-------------|
| **Unitário** | Validações, cálculos, lógica | unittest.mock | ❌ |
| **E2E API** | OAuth, CRUD, multi-tenancy | curl/bash | ✅ |
| **E2E UI** | Fluxos de usuário, navegação | Cypress | ✅ |

## Estrutura de Arquivos Gerada

```
realestate_backend/
├── integration_tests/              # @speckit.tests gera
│   ├── test_us1_s1_owner_login.sh
│   ├── test_us1_s2_owner_crud.sh
│   ├── test_us1_s3_multitenancy.sh
│   └── run_all_tests.sh           # Executa todos
│
├── cypress/e2e/                   # @speckit.tests gera
│   └── test_us2_s2_profile_menus.cy.js
│
└── 18.0/extra-addons/quicksol_estate/tests/unit/
    └── test_*_unit.py             # @speckit.tests gera
```

## Comandos de Execução

```bash
# Verificar Odoo rodando
curl -s http://localhost:8069/web/database/selector | head -3

# Executar todos os testes
bash integration_tests/run_all_tests.sh

# Executar teste específico
bash integration_tests/test_us1_s1_owner_login.sh

# Cypress
npm run cypress:run
```

## Troubleshooting

| Problema | Solução |
|----------|---------|
| 401 Unauthorized | Verificar `18.0/.env` |
| Connection refused | `cd 18.0 && docker compose up -d` |
| Teste não executa | `chmod +x integration_tests/*.sh` |

## Links

- [Guia Completo](AI-TEST-GENERATION.md)
- [ADR-003: Test Coverage](../../docs/adr/ADR-003-mandatory-test-coverage.md)
- [Tasks.md](tasks.md)
- [Spec.md](spec.md)
