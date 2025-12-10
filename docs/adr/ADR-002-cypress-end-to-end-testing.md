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
- ✅ **Automação possível** com scripts shell

**Importante:** 
- ❌ **NÃO use `odoo.tests.common.HttpCase` para testes de API REST**
- ✅ **USE curl direto ou scripts shell** para validar APIs
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

**Diretório Principal:**
```
<module>/tests/api/
```

**Organização:**
```
quicksol_estate/tests/api/
├── .env.example                      # Template de variáveis de ambiente (commitado)
├── .env                              # Variáveis de ambiente reais (GITIGNORED)
├── test_company_isolation.sh        # Script com testes de isolamento de empresa
├── test_master_data_api.sh          # Script com testes de Master Data
├── test_property_api.sh              # Script com testes de CRUD de propriedades
└── README.md                         # Documentação de como executar

⚠️ IMPORTANTE: Dados sensíveis (credenciais OAuth, senhas) DEVEM estar em .env (gitignored)
```

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

**Estrutura de Script de Teste (exemplo):**
```bash
#!/bin/bash
# test_company_isolation.sh - Testes de isolamento de empresa via API

set -e  # Parar em caso de erro

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Erro: Arquivo .env não encontrado!"
    echo "Copie .env.example para .env e configure as credenciais."
    exit 1
fi

# Validar variáveis obrigatórias
if [ -z "$OAUTH_CLIENT_ID" ] || [ -z "$OAUTH_CLIENT_SECRET" ]; then
    echo "❌ Erro: OAUTH_CLIENT_ID e OAUTH_CLIENT_SECRET são obrigatórios!"
    exit 1
fi

# Função auxiliar para obter token
get_token() {
    curl -s -X POST "$API_BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{
            \"grant_type\": \"client_credentials\",
            \"client_id\": \"$OAUTH_CLIENT_ID\",
            \"client_secret\": \"$OAUTH_CLIENT_SECRET\"
        }" | jq -r '.access_token'
}

# Test 1: Listar propriedades com isolamento de empresa
echo "Test 1: User A vê apenas propriedades da Company A"
TOKEN=$(get_token)
RESPONSE=$(curl -s -X GET "$API_BASE_URL/api/v1/properties" \
    -H "Authorization: Bearer $TOKEN")
echo "$RESPONSE" | jq .

# Test 2: Tentar criar propriedade em outra empresa
echo "Test 2: User A não pode criar propriedade na Company B"
# ... mais testes
```

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

**Estrutura Padrão:**
```bash
#!/bin/bash
# test_feature_name.sh - Descrição dos testes

set -e  # Parar em caso de erro

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Erro: Arquivo .env não encontrado!"
    echo "Copie .env.example para .env e configure as credenciais."
    exit 1
fi

# Validar variáveis obrigatórias
required_vars=("OAUTH_CLIENT_ID" "OAUTH_CLIENT_SECRET" "API_BASE_URL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Erro: Variável $var é obrigatória!"
        exit 1
    fi
done

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Função para obter token OAuth
get_token() {
    curl -s -X POST "$API_BASE_URL/api/v1/auth/token" \
        -H "Content-Type: application/json" \
        -d "{
            \"grant_type\": \"client_credentials\",
            \"client_id\": \"$OAUTH_CLIENT_ID\",
            \"client_secret\": \"$OAUTH_CLIENT_SECRET\"
        }" | jq -r '.access_token'
}

# Função para assertar resposta
assert_status() {
    local expected=$1
    local actual=$2
    local test_name=$3
    
    if [ "$actual" -eq "$expected" ]; then
        echo -e "${GREEN}✓${NC} $test_name"
    else
        echo -e "${RED}✗${NC} $test_name (Expected: $expected, Got: $actual)"
        exit 1
    fi
}

# Setup
echo "=== Setup ==="
TOKEN=$(get_token)

# Test 1
echo ""
echo "=== Test 1: Descrição ==="
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_BASE_URL/api/v1/endpoint" \
    -H "Authorization: Bearer $TOKEN")
STATUS=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

assert_status 200 "$STATUS" "Deve retornar 200"
echo "$BODY" | jq .

# Cleanup
echo ""
echo "=== Cleanup ==="
# ... limpar dados de teste se necessário
```

**Boas Práticas (curl):**

✅ **FAÇA:**
- ✅ **Use arquivo `.env` para dados sensíveis** (credenciais, senhas)
- ✅ **Adicione `.env` ao .gitignore** (NUNCA commitar credenciais)
- ✅ **Commite `.env.example`** com valores de exemplo/placeholder
- ✅ **Valide variáveis obrigatórias** no início do script
- Use `jq` para parsing de JSON
- Capture HTTP status code com `-w "\n%{http_code}"`
- Adicione cores para facilitar visualização (verde=sucesso, vermelho=erro)
- Use `set -e` para parar em caso de erro
- Documente cada teste com comentários
- Faça cleanup ao final

❌ **NÃO FAÇA:**
- ❌ **NUNCA hardcode credenciais no script** (use variáveis de ambiente)
- ❌ **NUNCA commite arquivo `.env` com credenciais reais**
- ❌ Ignore status codes HTTP (sempre valide)
- ❌ Deixe dados de teste na base após execução
- ❌ **NUNCA use `odoo.tests.common.HttpCase` para testes de API REST** (limitação de transação read-only)

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

**Executar um script de teste:**
```bash
cd 18.0/extra-addons/quicksol_estate/tests/api

# Primeira vez: copiar template de configuração
cp .env.example .env

# Editar .env com suas credenciais reais
nano .env  # ou vim, code, etc.

# Executar o script
chmod +x test_company_isolation.sh
./test_company_isolation.sh
```

**Executar todos os scripts de teste:**
```bash
cd 18.0/extra-addons/quicksol_estate/tests/api
for script in test_*.sh; do
    echo "Running $script..."
    ./"$script"
done
```

**Pré-requisitos:**
1. Odoo rodando: `docker compose up -d`
2. Módulos instalados e atualizados
3. **Arquivo `.env` configurado** com credenciais válidas:
   ```bash
   cp .env.example .env
   # Editar .env com credenciais reais
   ```
4. OAuth Application criada no Odoo
5. `jq` instalado: `brew install jq` (macOS) ou `apt install jq` (Linux)
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

### Otimização de Scripts curl

**✅ Reutilização de Token:**
```bash
# Obter token uma vez
TOKEN=$(get_token)

# Reutilizar em múltiplos testes
curl -H "Authorization: Bearer $TOKEN" ...
curl -H "Authorization: Bearer $TOKEN" ...
```

**✅ Execução Paralela:**
```bash
# Executar múltiplos scripts em paralelo
./test_script1.sh &
./test_script2.sh &
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
          
      - name: Run API Tests
        run: |
          cd 18.0/extra-addons/quicksol_estate/tests/api
          chmod +x test_*.sh
          for script in test_*.sh; do
            ./"$script"
          done
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
- **API:** Templates de scripts padronizados
- **API:** Funções auxiliares reutilizáveis (`get_token`, `assert_status`)
- **API:** Documentação clara de como executar e limpar
- **API:** ❌ **NUNCA usar HttpCase para APIs REST** - usar apenas curl
- **Segurança:** `.env.example` commitado facilita onboarding
- **Segurança:** Validação de variáveis obrigatórias nos scripts
- **Segurança:** `.gitignore` previne commit acidental de credenciais

## Próximos Passos

1. ✅ Criar testes para API Gateway (concluído)
2. ✅ Definir padrão curl para testes de API REST (concluído)
3. ⏳ Expandir cobertura para módulo `quicksol_estate`
4. ⏳ Criar scripts shell para testes de company isolation
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

---

**Responsável**: Equipe de Desenvolvimento  
**Revisores**: Tech Lead, QA Lead  
**Data de Aprovação**: 2025-11-15
