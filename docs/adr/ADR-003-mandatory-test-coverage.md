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

### 🔐 Endpoints de Autenticação Disponíveis

**Use APENAS os endpoints existentes - NÃO crie novos sistemas de autenticação.**

| Endpoint | Arquivo | Tipo | Uso Recomendado | Status |
|----------|---------|------|-----------------|--------|
| `/api/v1/auth/token` | `auth_controller.py` | OAuth2 `client_credentials` | ✅ **PREFERENCIAL** para testes E2E (curl) | Ativo |
| `/api/v1/users/login` | `user_auth_controller.py` | JSON-RPC | ⚠️ **EVITAR** (legado) | Ativo |

**Como obter token OAuth2:**

```bash
# 1. Credenciais estão em 18.0/.env
OAUTH_CLIENT_ID=client_xxx
OAUTH_CLIENT_SECRET=secret_yyy

# 2. Request token
curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "'$OAUTH_CLIENT_ID'",
    "client_secret": "'$OAUTH_CLIENT_SECRET'"
  }'

# 3. Use token
curl -X GET http://localhost:8069/api/v1/owners \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Helper disponível:**
```bash
# integration_tests/lib/get_token.sh
source lib/get_token.sh
TOKEN=$(get_oauth_token)
```

### ⚠️ NUNCA use JSON-RPC em novos testes

Endpoints REST deste projeto **NÃO usam formato JSON-RPC**. Envie JSON direto no body:

```json
// ✅ CORRETO - JSON direto (REST)
{"email": "user@example.com", "password": "secret"}

// ❌ ERRADO - wrapper JSON-RPC (EVITAR - apenas legado)
{"jsonrpc": "2.0", "method": "call", "params": {...}}
```

**Por que evitar JSON-RPC?**
- ❌ Não é padrão REST
- ❌ Dificulta integração com ferramentas
- ❌ Adiciona camada de complexidade desnecessária
- ✅ Usar REST puro (preferência do projeto)

## Decision

**Todos os módulos desenvolvidos ou modificados neste projeto DEVEM ter cobertura de testes automatizados.**

### 🎯 Princípio Arquitetural Fundamental

**OS TESTES DEVEM SE ADAPTAR À APLICAÇÃO, NÃO O CONTRÁRIO.**

| ❌ ERRADO | ✅ CORRETO |
|-----------|------------|
| Criar novos endpoints só para testes | Usar endpoints existentes nos testes |
| Modificar middleware para testes passarem | Adaptar testes ao middleware existente |
| Criar sistema paralelo de autenticação | Usar OAuth2 já implementado |
| Duplicar código para facilitar testes | Testes devem usar infraestrutura real |

**Justificativa:**
- Testes que forçam mudanças na aplicação geram débito técnico
- Código duplicado aumenta manutenção
- Sistemas paralelos criam inconsistências
- Testes devem validar o comportamento REAL do sistema

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

**REGRA CRÍTICA: Dados sensíveis SEMPRE no arquivo `18.0/.env`** (não versionado no Git).

#### ✅ O que DEVE estar no .env

- Credenciais de usuários (admin, manager, agent, owner)
- Senhas e tokens
- Company IDs de teste
- URLs de serviços
- Chaves de API

#### ❌ O que NÃO deve estar hardcoded no código

- Qualquer senha ou token
- Dados reais de usuários
- Informações sensíveis da empresa

#### 📋 Regras de Dados de Teste

1. **Credenciais de usuários**: Ler do `.env` - **nunca hardcode**
2. **CNPJ**: Sempre usar formato válido brasileiro (14 dígitos, com validação de dígitos verificadores)
   - ✅ Correto: `12.345.678/0001-95` (formato válido)
   - ❌ Errado: `12345678000195`, `11111111111111`, `00000000000000`
3. **Login de Admin**: **NÃO usar em testes de API** - criar usuários específicos para cada perfil (manager, agent, owner)
   - ✅ Correto: Login como `TEST_USER_MANAGER` do `.env`
   - ❌ Errado: Login como `admin` em teste de permissões de agent

#### Exemplo de .env para testes

```bash
# 18.0/.env
TEST_DATABASE=realestate
TEST_BASE_URL=http://localhost:8069

# Credenciais por perfil
TEST_USER_ADMIN=admin
TEST_PASSWORD_ADMIN=admin

TEST_USER_OWNER=owner_test
TEST_PASSWORD_OWNER=owner123

TEST_USER_MANAGER=manager_test  
TEST_PASSWORD_MANAGER=manager123

TEST_USER_AGENT=agent_test
TEST_PASSWORD_AGENT=agent123

# Dados de teste
TEST_COMPANY_ID=1
TEST_CNPJ=12.345.678/0001-95
```

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
## Boas Práticas de Dados de Teste

### 1. Formato de CNPJ

**SEMPRE use CNPJs válidos** nos testes (com dígitos verificadores corretos):

```python
# ✅ CORRETO - CNPJ válido
cnpj = "12.345.678/0001-95"

# ❌ ERRADO - CNPJs inválidos
cnpj = "11111111111111"  # Repetição de dígitos
cnpj = "00000000000000"  # Zeros
cnpj = "12345678000195"  # Sem formatação
```

**Por quê?** Validações de CNPJ (ADR-012) devem funcionar corretamente em testes.

### 2. Não Usar Login de Admin em Testes de API

**NUNCA teste permissões de usuários usando login de admin**:

```bash
# ❌ ERRADO - Testar permissões de agent usando admin
curl -X POST "$BASE_URL/api/v1/auth/token" \
  -d '{"username":"admin","password":"admin"}'

# ✅ CORRETO - Usar usuário específico do perfil
curl -X POST "$BASE_URL/api/v1/auth/token" \
  -d '{"username":"${TEST_USER_AGENT}","password":"${TEST_PASSWORD_AGENT}"}'
```

**Por quê?** 
- Admin tem permissões irrestritas (bypassa RBAC)
- Testes de permissões devem validar o perfil correto
- Esconde bugs de controle de acesso

**Quando usar admin?**
- Apenas em testes de configuração/setup inicial
- Criação de dados de teste (companies, configurações)
- Testes específicos de funcionalidades administrativas

### 3. Dados Sensíveis no .env

**Estrutura do .env para testes**:

```bash
# 18.0/.env

# Database
TEST_DATABASE=realestate
TEST_BASE_URL=http://localhost:8069

# === Credenciais por Perfil ===

# Admin (apenas para setup)
TEST_USER_ADMIN=admin
TEST_PASSWORD_ADMIN=admin

# Owner (usuário dono da imobiliária)
TEST_USER_OWNER=owner_test
TEST_PASSWORD_OWNER=owner_secure_123
TEST_OWNER_EMAIL=owner@test.com

# Manager (gerente)
TEST_USER_MANAGER=manager_test
TEST_PASSWORD_MANAGER=manager_secure_123
TEST_MANAGER_EMAIL=manager@test.com

# Agent (corretor)
TEST_USER_AGENT=agent_test
TEST_PASSWORD_AGENT=agent_secure_123
TEST_AGENT_EMAIL=agent@test.com

# Prospector (prospector)
TEST_USER_PROSPECTOR=prospector_test
TEST_PASSWORD_PROSPECTOR=prospector_secure_123

# === Dados de Teste ===

# Company
TEST_COMPANY_ID=1
TEST_COMPANY_NAME=Imobiliária Teste Ltda
TEST_CNPJ=12.345.678/0001-95

# Outros
TEST_TIMEOUT=30
TEST_API_VERSION=v1
```

**Regras**:
1. **Nunca versione o .env** - está no `.gitignore`
2. **Use senhas diferentes para cada perfil** - simula ambiente real
3. **Documente variáveis necessárias** - em README ou .env.example
4. **Mantenha consistência** - mesmos nomes em todos os testes

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
| 2026-02-05 | 3.1 | Adicionadas boas práticas: CNPJ válido, não usar admin em testes de API, dados sensíveis no .env | Equipe Dev |
