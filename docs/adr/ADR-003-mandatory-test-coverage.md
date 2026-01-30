# ADR-003: Cobertura de Testes Obrigatória para Todos os Módulos

## Status
**Accepted** - 2025-11-16  
**Amended** - 2026-01-22 (v3.0 - Simplificado)

## Context

Durante o desenvolvimento do sistema, identificamos que a qualidade e confiabilidade do código aumentam significativamente com a implementação de testes automatizados.

### Problemas Identificados em Módulos sem Testes

1. **Bugs em produção**: Erros não detectados que só apareciam após deploy
2. **Medo de refatorar**: Desenvolvedores evitavam melhorar código
3. **Tempo de debugging**: Maior parte do tempo gasto corrigindo bugs
4. **Onboarding lento**: Novos desenvolvedores levavam semanas para entender o código

### Limitação do Framework de Testes do Odoo

O framework `odoo.tests.common.HttpCase` **não persiste dados** no banco de dados durante a execução dos testes:

- ❌ Executa requisições em transações read-only
- ❌ Bloqueia operações INSERT/UPDATE/DELETE
- ❌ Incompatível com OAuth token generation
- ❌ Quebra jornadas de teste que dependem de dados persistidos

**Por isso, utilizamos curl para testes de API** - ele executa contra a instância real do Odoo, persistindo dados normalmente.

### ⚠️ NUNCA use JSON-RPC em testes

Endpoints REST deste projeto **NÃO usam formato JSON-RPC**. Envie JSON direto no body:

```json
// ✅ CORRETO - JSON direto
{"email": "user@example.com", "password": "secret"}

// ❌ ERRADO - wrapper JSON-RPC (NÃO usar)
{"jsonrpc": "2.0", "method": "call", "params": {...}}
```

## Decision

**Todos os módulos desenvolvidos ou modificados neste projeto DEVEM ter cobertura de testes automatizados.**

### Regra Fundamental: Testes Automatizados, Nunca Manuais

| ❌ NÃO Aceitamos | ✅ Aceitamos Apenas |
|------------------|---------------------|
| Testes manuais ("testei na interface") | Testes automatizados |
| Validação manual ("rodei alguns casos") | Testes repetíveis e determinísticos |
| Planilhas de casos de teste manuais | Testes versionados no Git |

**Exceção única:** Testes exploratórios de UX/UI (mas funcionalidade ainda precisa de testes automatizados).

### Os 2 Tipos de Testes Obrigatórios

| Tipo | Ferramenta | Objetivo |
|------|------------|----------|
| **Unitário** | Python unittest + mock | Lógica isolada, validações, cálculos (SEM banco) |
| **E2E** | Cypress (UI) / curl (API) | Fluxos completos (COM banco) |

### Dados de Teste

**Credenciais e configurações de teste devem estar no arquivo `18.0/.env`** (não versionado no Git).

Testes E2E devem ler variáveis de ambiente do `.env` - **nunca hardcode credenciais no código de teste**.

### Ordem de Execução Obrigatória

```bash
# 1. UNITÁRIOS (rápido, sem dependências)
docker compose exec odoo python3 /mnt/extra-addons/quicksol_estate/tests/run_unit_tests.py

# 2. E2E - API (curl contra Odoo rodando)
./tests/api/run_api_tests.sh

# 3. E2E - UI (Cypress)
npx cypress run --spec "cypress/e2e/*.cy.js"
```

**Por que nesta ordem?** Feedback rápido: unitários falham em segundos, E2E em minutos.

---

## Testes Unitários

### Quando usar

| Cenário | Exemplo |
|---------|---------|
| Campos obrigatórios | `required=True` |
| Constraints Python | `@api.constrains` |
| Campos computados | `compute=` |
| Validação de formato | CRECI, CPF, email |
| Cálculos | Comissão, preços |
| Helpers/utils | Formatadores, parsers |
| Regras de negócio | Services, validators |

### Características

- **SEM banco de dados** - usa `unittest.mock`
- **SEM framework Odoo** - testes puros de lógica Python
- **Rápido** - execução em segundos
- **Padrão PEP 8** - código seguindo convenções Python

---

## Testes E2E

### UI/UX com Cypress

| Cenário |
|---------|
| Fluxos completos de usuário |
| CRUD via interface |
| Validações de formulários |
| Navegação entre telas |

### API com curl

| Cenário |
|---------|
| Endpoints REST |
| Autenticação OAuth |
| CRUD via API |
| Validações de payload |

**Por que curl?** O HttpCase do Odoo não persiste dados no banco, impossibilitando testes de jornadas completas.

---

## Regra de Ouro

```
Pergunta: "Precisa de banco de dados para testar?"
   │
   ├─ NÃO → Teste Unitário (mock)
   │
   └─ SIM → Teste E2E (Cypress ou curl)
```

---

## Cobertura de Validações (100% OBRIGATÓRIA)

Cada validação DEVE ter no mínimo **2 testes**:

| Teste | Objetivo |
|-------|----------|
| Sucesso | Valor válido passa |
| Falha | Valor inválido lança `ValidationError` |

### O que deve ter 100% de cobertura

| Tipo | Testes Obrigatórios |
|------|---------------------|
| `required=True` | Campo preenchido passa, campo vazio falha |
| `@api.constrains` | Cada condição válida e inválida |
| `_sql_constraints` | Dados válidos passam, duplicados/inválidos falham |
| `compute=` | Cada branch do cálculo, valores extremos |
| Métodos de validação | Cada if/else, boundary testing |

---

## Estrutura de Arquivos

```
meu_modulo/
├── tests/
│   ├── __init__.py
│   ├── run_unit_tests.py      # Runner unitários
│   ├── test_*_unit.py         # Testes unitários
│   └── api/
│       └── test_*.sh          # Testes curl

cypress/
└── e2e/
    └── meu-modulo.cy.js       # Testes E2E UI
```

---

## Checklist de PR

### Desenvolvedor (antes de abrir PR)

- [ ] Testes unitários criados para lógica nova
- [ ] 100% cobertura em validações (required, constrains, compute)
- [ ] Testes E2E para features visíveis (UI ou API)
- [ ] Todos os testes passando

### Revisor (code review)

- [ ] Validações têm testes de sucesso E falha
- [ ] Testes seguem padrão AAA (Arrange, Act, Assert)
- [ ] Testes são independentes (não dependem de ordem)

---

## Exceções

### Quando NÃO criar testes E2E

- Módulos puramente backend (sem UI nem API exposta)
- Helpers/utilitários simples
- Scripts de migração one-time

**Ainda obrigatório:** Testes unitários

### Quando reduzir cobertura unitária

- **NUNCA para validações** - 100% é obrigatório
- Se código não é testável → refatore o código
- Se é código de terceiros → isole em wrapper testável

---

## Consequences

### Positivas

1. **Qualidade**: Redução de bugs em produção
2. **Produtividade**: Menos tempo em debugging
3. **Confiança**: Refatorações seguras
4. **Manutenibilidade**: Código mais fácil de evoluir

### Negativas

1. **Curto prazo**: Desenvolvimento inicial mais lento
2. **Manutenção**: Testes precisam ser mantidos junto com código

### Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Equipe resiste a mudança | Treinamento, pair programming |
| Testes mal escritos | Code review rigoroso |

---

## Alternativas Consideradas e Rejeitadas

| Alternativa | Motivo da Rejeição |
|-------------|-------------------|
| HttpCase do Odoo para APIs | Não persiste dados, quebra jornadas de teste |
| Cobertura parcial (70-80%) | Deixa margem para "escolher" o que não testar |
| Apenas testes E2E | Testes lentos demais, dificulta debug |
| Apenas testes unitários | Não testa integração real |
| Testes opcionais | Na prática ninguém faria |

---

## Referências

- [ADR-001: Development Guidelines for Odoo Screens](./ADR-001-development-guidelines-for-odoo-screens.md)
- [ADR-002: Cypress E2E Testing](./ADR-002-cypress-end-to-end-testing.md)
- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Test Pyramid - Martin Fowler](https://martinfowler.com/bliki/TestPyramid.html)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)

---

## Histórico

| Data | Versão | Mudança | Autor |
|------|--------|---------|-------|
| 2025-11-16 | 1.0 | Criação do ADR | Equipe Dev |
| 2025-11-30 | 1.1 | Detalhamento de tipos de teste | Equipe Dev |
| 2026-01-08 | 2.0 | 100% cobertura em validações obrigatória | Equipe Dev |
| 2026-01-22 | 3.0 | Simplificado: 2 tipos de teste (unitário + E2E) | Equipe Dev |
