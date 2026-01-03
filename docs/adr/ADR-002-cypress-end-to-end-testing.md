# ADR-002: Cypress para Testes E2E e Curl para Testes de API

## Status
**Accepted** - 2025-11-15  
**Amended** - 2025-12-09 (Adicionada seção sobre testes de API REST)

## Context

Durante o desenvolvimento do sistema Odoo (Real Estate Management e API Gateway), identificamos a necessidade de testes automatizados End-to-End (E2E) para garantir:

1. **Qualidade de UI/UX**: Validar que a interface funciona corretamente para usuários finais
2. **Integração Frontend-Backend**: Testar fluxos completos desde a UI até a API
3. **Regressão**: Detectar quebras em funcionalidades existentes ao adicionar novas features
4. **Confiabilidade**: Garantir que APIs REST (especialmente OAuth 2.0) funcionam como esperado
5. **Documentação Viva**: Testes servem como documentação de como o sistema deve funcionar
6. **CI/CD**: Possibilitar automação de testes em pipelines de integração contínua

### Problema Identificado com HttpCase do Odoo

Durante a implementação de testes de API REST, identificamos uma **limitação crítica** do framework `odoo.tests.common.HttpCase`:

- ❌ **HttpCase executa requisições em transações read-only** (somente leitura)
- ❌ **Não persiste dados** durante a execução dos testes
- ❌ **Bloqueia operações INSERT/UPDATE/DELETE** em endpoints de autenticação
- ❌ **Incompatível com OAuth token generation** que precisa gravar na base de dados

**Exemplo de erro:**
```
ERROR: cannot execute INSERT in a read-only transaction
bad query: INSERT INTO "thedevkitchen_oauth_token" ...
```

Isso torna o HttpCase **inadequado para testes E2E de APIs REST** que envolvem autenticação e persistência de dados.

### Alternativas Consideradas

#### Para Testes de UI (E2E):

1. **Selenium WebDriver**
   - Pros: Maduro, suporta múltiplos navegadores
   - Cons: Configuração complexa, testes flaky, lento
   
2. **Playwright**
   - Pros: Moderno, rápido, multi-browser nativo
   - Cons: Comunidade menor, menos exemplos para Odoo
   
3. **Cypress** ✅
   - Pros: Sintaxe simples, debugging excelente, time travel, screenshots/vídeos automáticos
   - Cons: Limitado a Chromium-based browsers (suficiente para nosso caso)

#### Para Testes de API REST:

1. **HttpCase do Odoo** ❌
   - Pros: Nativo do framework, integrado com ambiente de testes
   - Cons: **Executa em transação read-only, não persiste dados, bloqueia INSERT/UPDATE/DELETE**
   
2. **Postman/Newman**
   - Pros: Interface gráfica, fácil de usar
   - Cons: Não versionável facilmente, complexo para automação
   
3. **Pytest com requests**
   - Pros: Flexível, poderoso
   - Cons: Overhead de setup, configuração complexa
   
4. **curl direto** ✅
   - Pros: **Simples, direto, usa a base real, sem limitações de transação**
   - Cons: Menos estruturado que frameworks de teste formais

## Decision

### Para Testes de UI (Cypress)

**Adotamos Cypress como framework oficial para testes E2E de UI** por:

- ✅ Sintaxe JavaScript moderna e intuitiva
- ✅ Excelente experiência de debugging (time travel, screenshots, vídeos)
- ✅ Comandos customizados permitem reutilização de código
- ✅ Sistema de sessões acelera testes (3x mais rápido)
- ✅ Suporta testes de API além de UI
- ✅ Documentação extensa e comunidade ativa
- ✅ Fácil integração com CI/CD (GitHub Actions, GitLab CI)

### Para Testes de API REST (curl)

**Adotamos curl direto para testes E2E de APIs REST** por:

- ✅ **Executa contra a base de dados real** (sem limitação de transação)
- ✅ **Persiste dados normalmente** (INSERT/UPDATE/DELETE funcionam)
- ✅ **Compatível com OAuth token generation** e outros endpoints que escrevem na base
- ✅ **Simples e direto** - sem overhead de frameworks
- ✅ **Fácil debugging** - vê exatamente a requisição e resposta
- ✅ **Reutilizável** - comandos curl podem ser usados em documentação
- ✅ **Execução ocorre diretamente pelo terminal** (copiando comandos documentados), sem wrappers `.sh`

**Importante:** 
- ❌ **NÃO use `odoo.tests.common.HttpCase` para testes de API REST**
- ✅ **NÃO criar arquivos `.sh` para orquestrar os testes de integração**; comandos devem ser executados diretamente no terminal (local ou CI)
- ✅ **HttpCase pode ser usado apenas para testes unitários** de componentes que não precisam persistir dados

## Estrutura de Arquivos

### Testes de UI (Cypress)

**Diretório Principal:**
```
<project-root>/cypress/
```

**Organização:**
```
cypress/
├── README.md                          # Guia de uso e comandos de execução
├── COMANDOS_CUSTOMIZADOS.md         # Documentação completa de comandos
├── e2e/                              # Testes End-to-End
│   ├── api-gateway.cy.js            # Testes de UI do API Gateway (20 testes)
│   ├── api-gateway-integration.cy.js # Testes de integração UI+API (12 testes)
│   ├── exemplo-boas-praticas.cy.js  # Guia de boas práticas
│   ├── imoveis-*.cy.js              # Testes do módulo de imóveis
│   └── login-custom-command.cy.js   # Exemplo de comando customizado
├── fixtures/                         # Dados de teste (JSON)
│   └── example.json
├── support/                          # Comandos customizados e configurações
│   ├── commands.js                  # Comandos reutilizáveis
│   └── e2e.js                       # Configuração global
├── screenshots/                      # Screenshots automáticos em falhas
└── downloads/                        # Downloads durante testes
```

### Testes de API REST (curl)

**Diretórios principais:**
```
18.0/extra-addons/thedevkitchen_apigateway/tests/integration/
├── SECURITY_TEST_SCENARIOS.md       # Lista de cenários e comandos curl
├── test_login_security.sh           # (legado) será migrado para comandos diretos
├── test_logout_security_advanced.py # Testes Python rodando no .venv
└── ...

18.0/extra-addons/quicksol_estate/tests/api/
├── README.md                        # Orientações de execução
├── test_company_isolation_api.py    # Integrações Python (requests)
├── utils.py                         # Loader de variáveis e helpers
└── ...
```

- **Não criar novos scripts `.sh`**: os cenários devem ser descritos em arquivos Markdown e executados manualmente no terminal (local ou CI) copiando/colando os comandos `curl`.
- **Python para utilidades**: quando uma preparação automatizada for necessária (fixtures, sanity checks), use módulos Python executados via `18.0/.venv/bin/python`, reutilizando `utils.py` e mantendo os testes versionáveis.

**Arquivo `.env.example` (commitado no Git):**
```bash
# OAuth Credentials (obter em thedevkitchen.oauth.application)
OAUTH_CLIENT_ID=your_client_id_here
OAUTH_CLIENT_SECRET=your_client_secret_here

# API Configuration
API_BASE_URL=http://localhost:8069

# Test Users (credenciais de usuários de teste)
TEST_USER_COMPANY_A_EMAIL=user_company_a@example.com
TEST_USER_COMPANY_A_PASSWORD=password_here
TEST_USER_COMPANY_B_EMAIL=user_company_b@example.com
TEST_USER_COMPANY_B_PASSWORD=password_here
```

**Arquivo `.env` (NÃO commitado - adicionar ao .gitignore):**
```bash
# OAuth Credentials
OAUTH_CLIENT_ID=client_f0HgaJgLr8lCHOMa3ZKUzA
OAUTH_CLIENT_SECRET=AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt

# API Configuration
API_BASE_URL=http://localhost:8069

# Test Users
TEST_USER_COMPANY_A_EMAIL=user.company1@example.com
TEST_USER_COMPANY_A_PASSWORD=user123
TEST_USER_COMPANY_B_EMAIL=user.company2@example.com
TEST_USER_COMPANY_B_PASSWORD=user123
```

**Fluxo padrão para um cenário documentado:**
```bash
cd 18.0
source .venv/bin/activate                 # garante requests, httpie, jq etc.
export $(grep -v '^#' .env | xargs)       # carrega segredos apenas na sessão atual

# 1) Solicitar token OAuth
TOKEN=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\": \"client_credentials\", \"client_id\": \"$OAUTH_CLIENT_ID\", \"client_secret\": \"$OAUTH_CLIENT_SECRET\"}" \
  | jq -r '.access_token')

# 2) Chamar o endpoint documentado no cenário
curl -i -X GET "$API_BASE_URL/api/v1/properties" \
  -H "Authorization: Bearer $TOKEN" | tee /tmp/response.json
```

Cada cenário descreve claramente o comando `curl`, o status esperado e as validações necessárias (via `jq`, `grep` ou pequenos scripts Python no `.venv`). O terminal passa a ser o único executor — tanto em máquinas locais quanto em pipelines.

## Comandos Customizados

Para maximizar reutilização e performance, criamos comandos customizados:

### 1. `cy.odooLoginSession(username, password)`
Login com cache de sessão (3x mais rápido que login tradicional).

**Uso:**
```javascript
beforeEach(() => {
  cy.odooLoginSession() // Recomendado!
})
```

### 2. `cy.odooLogin(username, password)`
Login simples sem cache.

**Uso:**
```javascript
cy.odooLogin('admin', 'admin')
```

### 3. `cy.odooLogout()`
Logout do sistema.

**Uso:**
```javascript
cy.odooLogout()
```

### 4. `cy.odooNavigateTo(action, model, viewType)`
Navegação direta para menus (evita clicks em cascata).

**Uso:**
```javascript
cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
```

## Padrões de Teste

### Testes de UI (Cypress)

**Estrutura Padrão:**
```javascript
describe('Módulo: Funcionalidade', () => {
  beforeEach(() => {
    cy.odooLoginSession() // Login com sessão persistente
  })

  it('Deve fazer X quando Y', () => {
    // Arrange: Preparar dados
    cy.odooNavigateTo('module.action', 'model.name')
    
    // Act: Executar ação
    cy.get('button.o_list_button_add').click()
    cy.get('input[name="field"]').type('valor')
    
    // Assert: Verificar resultado
    cy.get('.o_field_widget').should('contain', 'valor')
  })
})
```

**Boas Práticas (Cypress):**

✅ **FAÇA:**
- Use `cy.odooLoginSession()` no `beforeEach()`
- Use `cy.odooNavigateTo()` para navegação
- Use URLs relativas (`/web`) ao invés de absolutas
- Aguarde elementos com `.should()` ao invés de `cy.wait()`
- Nomeie testes descritivamente: `'Deve criar aplicação quando...'`

❌ **NÃO FAÇA:**
- Login manual em cada teste (lento!)
- Navegação clicando em menus (frágil!)
- URLs absolutas `http://localhost:8069` (ambiente-específico!)
- `cy.wait(5000)` fixos (instável!)
- Testes dependentes uns dos outros

### Testes de API REST (curl)

**Fluxo Padrão (copiado dos cenários):**
1. Ative o `.venv` (`source 18.0/.venv/bin/activate`) e carregue o `.env`.
2. Execute o comando `curl` descrito no cenário (sempre com `-i` ou `-w "%{http_code}"` para registrar o status).
3. Use `jq`, `python -m json.tool` ou pequenos scripts Python no `.venv` para validar campos específicos.
4. Registre o resultado esperado no próprio cenário (ex.: "HTTP 401 e corpo com `invalid_grant`").

**Exemplo simples (extraído de SECURITY_TEST_SCENARIOS.md):**
```bash
# Login inválido deve retornar 401
TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"password\",\"username\":\"attacker@example.com\",\"password\":\"wrong\"}")
STATUS=$(echo "$TOKEN_RESPONSE" | tail -n1)
BODY=$(echo "$TOKEN_RESPONSE" | sed '$d')
test "$STATUS" -eq 401
echo "$BODY" | jq '.error == "invalid_grant"'
```

**Boas Práticas (curl):**

✅ **FAÇA:**
- ✅ **Use arquivo `.env` para dados sensíveis** (credenciais, senhas)
- ✅ **Adicione `.env` ao .gitignore** (NUNCA commitar credenciais)
- ✅ **Commite `.env.example`** com valores de exemplo/placeholder
- ✅ **Execute tudo dentro do `.venv`** para garantir dependências (`curl`, `jq`, helpers Python)
- Use `jq` para parsing de JSON
- Capture HTTP status code com `-w "\n%{http_code}"` ou `curl -i`
- Documente cada passo no cenário (entrada, resultado esperado, cleanup manual quando necessário)
- Versione apenas os cenários (`.md`) e utilidades Python

❌ **NÃO FAÇA:**
- ❌ **NUNCA hardcode credenciais em comandos** (carregue do `.env`)
- ❌ **NUNCA commite arquivo `.env` com credenciais reais**
- ❌ Criar scripts `.sh` para encapsular os comandos
- ❌ Ignorar status codes HTTP (sempre valide)

### Estrutura dos Diretórios de Testes (Odoo)

Todos os testes Python vivem dentro de `18.0/extra-addons` e seguem uma hierarquia fixa para facilitar a descoberta:

```text
18.0/extra-addons/
├── quicksol_estate/
│   └── tests/
│       ├── *.py                  # testes unitários e helpers base_* para modelos
│       └── api/                  # testes de integração HTTP (usam requests + .env)
├── thedevkitchen_apigateway/
│   └── tests/
│       ├── *.py                  # unitários/serviços/repos
│       └── integration/          # E2E reais contra a API Gateway
└── auditlog/
    └── tests/                    # regressão do módulo terceirizado
```

- `quicksol_estate/tests/api/`: módulos Python (`test_company_isolation_api.py`, `test_property_api*.py`, `run_all_tests.py`) que encapsulam utilidades de preparação/limpeza. Todos dependem de `utils.py` para carregar `18.0/.env` via `python-dotenv`, portanto **execute-os apenas com `18.0/.venv/bin/python`**.
- `quicksol_estate/tests/*.py`: base de fixtures (`base_*.py`) e suites unitárias (`test_agent_unit.py`, `test_validations.py`, etc.) que rodam dentro do Odoo test runner (`./odoo-bin -m quicksol_estate --test-enable`) mas também podem ser chamados via `18.0/.venv/bin/python -m pytest` se configurado.
- `thedevkitchen_apigateway/tests/`: scripts unitários (`test_oauth_application*.py`, `test_middleware.py`, `test_user_auth.py`, etc.) + um helper `run_unit_tests.py` que prepara o ambiente Odoo. O subdiretório `integration/` abriga documentação (`SECURITY_TEST_SCENARIOS.md`) e arquivos Python usados apenas para fixtures; **os testes de integração em si são sequências de comandos `curl` executados diretamente no terminal** (sem novos `.sh`).
- `auditlog/tests/`: cobertura mínima (`test_auditlog.py`, `test_autovacuum.py`) para garantir compatibilidade do módulo de terceiros com nossos patches.

Organize novos testes respeitando essa separação (unitários na raiz `tests/`, integrações HTTP em `tests/api/` ou `tests/integration/`) para que ferramentas e humanos consigam identificar rapidamente o escopo de cada suíte.

### Ambiente de Execução e Dados de Teste

Todo teste de integração que consome a API (scripts Python e **comandos `curl` executados manualmente a partir dos cenários**) **deve usar o ambiente virtual Python documentado na ADR-010**. O `.venv` já está provisionado em `18.0/.venv` com `requests`, `python-dotenv`, `jq` e demais dependências, portanto basta executar os testes assim:

```bash
cd 18.0
source .venv/bin/activate     # ou use .venv/bin/python diretamente
.venv/bin/python extra-addons/quicksol_estate/tests/api/test_user_login.py
```

Os dados sensíveis usados pelos testes (tokens OAuth, usuários das companies de teste, URLs base) **estão centralizados em `18.0/.env`**. Antes de rodar qualquer script, carregue esse arquivo ou copie o `18.0/.env.example` e ajuste os valores. Exemplo:

```bash
cd 18.0
cp .env.example .env   # apenas se ainda não existir
export $(grep -v '^#' .env | xargs)  # torna variáveis disponíveis na sessão atual
```

- ✅ **Nunca reescreva ou versiona esse `.env`** – ele já está ignorado pelo Git e contém tokens reais.
- ✅ **Para pipelines ou novos devs:** basta apontar para `18.0/.env` para reutilizar credenciais sem expor dados nos scripts.
- ✅ **Scripts Python** carregam o `.env` automaticamente via `python-dotenv`, desde que sejam executados com o `python` do `.venv`.
- ❌ Deixe dados de teste na base após execução
- ❌ **NUNCA use `odoo.tests.common.HttpCase` para testes de API REST** (limitação de transação read-only)
- ❌ Criar novos scripts shell para rodar cenários de integração (execute tudo direto no terminal)

## Módulos Testados

### API Gateway
- **Arquivo**: `cypress/e2e/api-gateway.cy.js`
- **Cobertura**: 20 testes de UI
  - Criação/edição de OAuth Applications
  - Gerenciamento de tokens
  - Validações de campos
  - Regeneração de secrets
  
- **Arquivo**: `cypress/e2e/api-gateway-integration.cy.js`
- **Cobertura**: 12 testes de integração
  - OAuth 2.0 Client Credentials flow
  - Geração e validação de tokens
  - Revogação de tokens
  - Validações de segurança

### Imóveis (quicksol_estate)
- **Arquivos**: `cypress/e2e/imoveis-*.cy.js`
- **Cobertura**: Testes de listagem, criação e jornada completa

## Como Executar

### Testes de UI (Cypress)

**Modo Interativo (Desenvolvimento):**
```bash
cd <project-root>
npx cypress open
```

**Modo Headless (CI/CD):**
```bash
# Todos os testes
npx cypress run

# Apenas API Gateway
npx cypress run --spec "cypress/e2e/api-gateway*.cy.js"

# Com vídeo
npx cypress run --video
```

**Pré-requisitos:**
1. Odoo rodando: `docker compose up -d`
2. Módulos instalados: `api_gateway`, `quicksol_estate`
3. Database: `realestate`
4. Usuário padrão: `admin` / `admin`

### Testes de API REST (curl)

**Executar um cenário documentado:**
```bash
cd 18.0
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)

# Abrir SECURITY_TEST_SCENARIOS.md (ou README específico) e copiar o bloco de comandos
# Exemplo: cenário "Login inválido"
curl -i -X POST "$API_BASE_URL/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"grant_type\":\"password\",\"username\":\"attacker@example.com\",\"password\":\"wrong\"}"
```
Cada cenário informa qual resposta esperar e como validar (ex.: `jq '.error == "invalid_grant"'`). Se um cenário exigir limpeza, execute o bloco "Cleanup" descrito no mesmo arquivo ou utilize os helpers Python.

**Automatizar no CI (sem `.sh`):**
```yaml
- name: Run security login scenario
  run: |
    cd 18.0
    source .venv/bin/activate
    export $(grep -v '^#' .env | xargs)
    STATUS=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/api/v1/auth/token" \
      -H "Content-Type: application/json" \
      -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"$OAUTH_CLIENT_ID\",\"client_secret\":\"$OAUTH_CLIENT_SECRET\"}" | tail -n1)
    test "$STATUS" -eq 200
```

**Pré-requisitos:**
1. Odoo rodando: `docker compose up -d`
2. Módulos instalados e atualizados
3. **Arquivo `.env` configurado** com credenciais válidas (`cp .env.example .env`)
4. OAuth Application criada no Odoo
5. `jq` instalado dentro do `.venv` (ou disponível no PATH do CI)
6. Base de dados com dados de teste preparados

**⚠️ IMPORTANTE - Segurança:**
- ✅ O arquivo `.env.example` DEVE ser commitado (sem credenciais reais)
- ❌ O arquivo `.env` NUNCA deve ser commitado (contém credenciais reais)
- ✅ Adicione `.env` ao `.gitignore`
- ✅ Use senhas diferentes para ambientes de produção

## Performance

### Otimização com Sessões (Cypress)
```javascript
// ❌ LENTO: ~30s para 10 testes
beforeEach(() => {
  cy.visit('/web/login')
  cy.get('input[name="login"]').type('admin')
  // ... login manual
})

// ✅ RÁPIDO: ~10s para 10 testes (3x mais rápido!)
beforeEach(() => {
  cy.odooLoginSession()
})
```

### Otimização de Fluxos curl

**✅ Reutilização de Token:**
```bash
# Obter token uma vez
TOKEN=$(get_token)

# Reutilizar em múltiplos testes
curl -H "Authorization: Bearer $TOKEN" ...
curl -H "Authorization: Bearer $TOKEN" ...
```

**✅ Execução Paralela (jobs do CI):**
```bash
# rodar dois cenários simultaneamente (cada um em subshell)
(curl ... cenário A) &
(curl ... cenário B) &
wait
```

## Integração CI/CD

### GitHub Actions (exemplo)

**Para Testes de UI (Cypress):**
```yaml
name: Cypress Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start Odoo
        run: |
          cd 18.0
          docker compose up -d
      - name: Run Tests
        uses: cypress-io/github-action@v5
        with:
          working-directory: .
          spec: cypress/e2e/**/*.cy.js
```

**Para Testes de API (curl):**
```yaml
name: API Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Start Odoo
        run: |
          cd 18.0
          docker compose up -d
          
      - name: Create .env from secrets
        run: |
          cd 18.0/extra-addons/quicksol_estate/tests/api
          echo "OAUTH_CLIENT_ID=${{ secrets.OAUTH_CLIENT_ID }}" >> .env
          echo "OAUTH_CLIENT_SECRET=${{ secrets.OAUTH_CLIENT_SECRET }}" >> .env
          echo "API_BASE_URL=http://localhost:8069" >> .env
          
      - name: Run API Tests (sem .sh)
        run: |
          cd 18.0
          source .venv/bin/activate
          export $(grep -v '^#' .env | xargs)
          TOKEN=$(curl -s -X POST "$API_BASE_URL/api/v1/auth/token" \
            -H "Content-Type: application/json" \
            -d "{\"grant_type\":\"client_credentials\",\"client_id\":\"$OAUTH_CLIENT_ID\",\"client_secret\":\"$OAUTH_CLIENT_SECRET\"}" \
            | jq -r '.access_token')
          # cenário 1
          STATUS=$(curl -s -w "\n%{http_code}" -X GET "$API_BASE_URL/api/v1/properties" \
            -H "Authorization: Bearer $TOKEN" | tail -n1)
          test "$STATUS" -eq 200
          # cenário 2
          RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/api/v1/auth/token" \
            -H "Content-Type: application/json" \
            -d "{\"grant_type\":\"password\",\"username\":\"attacker@example.com\",\"password\":\"wrong\"}")
          test "$(echo "$RESPONSE" | tail -n1)" -eq 401
```

**⚠️ Configuração de Secrets no GitHub:**
1. Acesse: Repository → Settings → Secrets and variables → Actions
2. Adicione os secrets:
   - `OAUTH_CLIENT_ID`
   - `OAUTH_CLIENT_SECRET`
   - Outros dados sensíveis necessários

## Documentação

- **README Principal**: `/cypress/README.md`
- **Comandos Customizados**: `/cypress/COMANDOS_CUSTOMIZADOS.md`
- **Exemplo de Boas Práticas**: `/cypress/e2e/exemplo-boas-praticas.cy.js`

## Consequences

### Positivas
✅ **UI (Cypress):** Testes automatizados garantem qualidade contínua  
✅ **UI (Cypress):** Debugging facilitado com time travel e screenshots  
✅ **UI (Cypress):** Documentação viva do comportamento esperado  
✅ **UI (Cypress):** CI/CD permite validação automática em PRs  
✅ **UI (Cypress):** Comandos customizados aumentam produtividade  
✅ **UI (Cypress):** Performance otimizada (3x mais rápido com sessões)  
✅ **API (curl):** Sem limitações de transação - testa base real  
✅ **API (curl):** Simplicidade - fácil debugging e reutilização  
✅ **API (curl):** Persistência funciona normalmente (INSERT/UPDATE/DELETE)  
✅ **API (curl):** Compatível com OAuth e outros fluxos que escrevem na base  
✅ **API (curl):** Comandos podem ser usados diretamente na documentação  
✅ **Segurança:** Credenciais em variáveis de ambiente (.env) - não commitadas  
✅ **Segurança:** Template (.env.example) facilita setup sem expor dados  
✅ **CI/CD:** GitHub Secrets protege credenciais em pipelines  

### Negativas
⚠️ **UI (Cypress):** Requer manutenção quando UI muda  
⚠️ **UI (Cypress):** Testes podem ser flaky se mal escritos  
⚠️ **UI (Cypress):** Curva de aprendizado inicial para novos desenvolvedores  
⚠️ **API (curl):** Menos estruturado que frameworks de teste formais  
⚠️ **API (curl):** Requer limpeza manual de dados de teste  
⚠️ **API (curl):** Mais verboso que frameworks high-level  
⚠️ **Segurança:** Desenvolvedores precisam configurar `.env` manualmente  

### Mitigações
- **UI:** Documentação completa de boas práticas
- **UI:** Comandos customizados simplificam uso
- **UI:** Exemplo prático (`exemplo-boas-praticas.cy.js`)
- **UI:** Code review obrigatório para novos testes
- **API:** Templates de cenários em Markdown padronizados
- **API:** Funções auxiliares reutilizáveis (`get_token`, `assert_status`)
- **API:** Documentação clara de como executar e limpar
- **API:** ❌ **NUNCA usar HttpCase para APIs REST** - usar apenas curl
- **Segurança:** `.env.example` commitado facilita onboarding
- **Segurança:** Validação de variáveis obrigatórias descrita nos cenários/comandos
- **Segurança:** `.gitignore` previne commit acidental de credenciais

## Próximos Passos

1. ✅ Criar testes para API Gateway (concluído)
2. ✅ Definir padrão curl para testes de API REST (concluído)
3. ⏳ Expandir cobertura para módulo `quicksol_estate`
4. ⏳ Documentar cenários de company isolation em Markdown e remover legados `.sh`
5. ⏳ Integrar com GitHub Actions para CI/CD
6. ⏳ Adicionar testes de performance/carga
7. ⏳ Criar relatórios HTML com Mochawesome (Cypress)

## Referências

- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Cypress Session API](https://docs.cypress.io/api/commands/session)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [curl Manual](https://curl.se/docs/manual.html)
- [jq Manual](https://stedolan.github.io/jq/manual/)

## Histórico de Revisões

| Data       | Versão | Autor  | Mudanças                                                                              |
|------------|--------|--------|---------------------------------------------------------------------------------------|
| 2025-11-15 | 1.0    | Equipe | Criação inicial - Adoção do Cypress                                                  |
| 2025-12-09 | 1.1    | Equipe | Adicionada seção sobre testes de API REST com curl e limitações HttpCase            |
| 2025-12-09 | 1.2    | Equipe | Adicionada seção sobre segurança: variáveis de ambiente, .env, e proteção de credenciais |
| 2025-12-16 | 1.3    | Equipe | Orientações atualizadas: testes de integração usam curl via terminal/.venv, sem scripts `.sh` |

---

**Responsável**: Equipe de Desenvolvimento  
**Revisores**: Tech Lead, QA Lead  
**Data de Aprovação**: 2025-11-15
