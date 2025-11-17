# Comandos Customizados Cypress para Odoo

Este documento descreve os comandos customizados disponíveis para facilitar a escrita de testes E2E no Odoo.

## Comandos Disponíveis

### 1. `cy.odooLogin(username, password)`

Faz login no Odoo de forma simples.

**Parâmetros:**
- `username` (opcional): Nome de usuário. Padrão: `'admin'`
- `password` (opcional): Senha. Padrão: `'admin'`

**Quando usar:**
- Testes isolados que não se beneficiam de cache de sessão
- Testes que precisam fazer login/logout múltiplas vezes

**Exemplo:**
```javascript
describe('Meu Teste', () => {
  it('Deve fazer login', () => {
    cy.odooLogin()
    // ... resto do teste
  })
  
  it('Deve fazer login com credenciais específicas', () => {
    cy.odooLogin('usuario', 'senha123')
    // ... resto do teste
  })
})
```

---

### 2. `cy.odooLoginSession(username, password)` ⭐ **RECOMENDADO**

Faz login no Odoo com **sessão persistente** entre testes.

**Parâmetros:**
- `username` (opcional): Nome de usuário. Padrão: `'admin'`
- `password` (opcional): Senha. Padrão: `'admin'`

**Quando usar:**
- **SEMPRE** que possível em `beforeEach()`
- Testes que não precisam fazer logout
- Suítes de teste que compartilham o mesmo usuário

**Vantagens:**
- ✅ **Muito mais rápido**: Login é feito apenas uma vez
- ✅ **Cache de sessão**: Reutiliza cookies entre testes
- ✅ **Menos requisições**: Economiza recursos do servidor

**Exemplo:**
```javascript
describe('API Gateway Tests', () => {
  beforeEach(() => {
    // Login com sessão persistente - MUITO MAIS RÁPIDO!
    cy.odooLoginSession()
  })
  
  it('Teste 1', () => {
    // Já está logado automaticamente
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
  })
  
  it('Teste 2', () => {
    // Também já está logado (reutiliza sessão)
    cy.odooNavigateTo('api_gateway.action_oauth_token', 'oauth.token')
  })
})
```

---

### 3. `cy.odooLogout()`

Faz logout do Odoo.

**Quando usar:**
- Testes que precisam validar comportamento após logout
- Testes que precisam trocar de usuário

**Exemplo:**
```javascript
it('Deve fazer logout', () => {
  cy.odooLogin()
  cy.odooLogout()
  cy.url().should('include', '/web/login')
})
```

---

### 4. `cy.odooNavigateTo(action, model, viewType)` 🆕

Navega para um menu/action específico do Odoo.

**Parâmetros:**
- `action` (obrigatório): Nome da action (ex: `'api_gateway.action_oauth_application'`)
- `model` (obrigatório): Nome do modelo (ex: `'oauth.application'`)
- `viewType` (opcional): Tipo de view. Padrão: `'list'`
  - Valores possíveis: `'list'`, `'form'`, `'kanban'`, `'graph'`, etc.

**Vantagens:**
- ✅ Navegação direta sem clicar em menus
- ✅ Mais rápido e confiável
- ✅ Menos dependente da estrutura de menus

**Exemplo:**
```javascript
describe('OAuth Applications', () => {
  beforeEach(() => {
    cy.odooLoginSession()
  })
  
  it('Deve listar aplicações', () => {
    // Navega diretamente para a lista
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
    cy.get('.o_list_view').should('be.visible')
  })
  
  it('Deve listar tokens', () => {
    // Navega para tokens
    cy.odooNavigateTo('api_gateway.action_oauth_token', 'oauth.token')
    cy.get('table.o_list_table').should('exist')
  })
})
```

---

## Boas Práticas

### ✅ DO (Faça)

**1. Use `cy.odooLoginSession()` em `beforeEach()`**
```javascript
describe('Testes', () => {
  beforeEach(() => {
    cy.odooLoginSession() // ✅ Rápido e eficiente
  })
})
```

**2. Use `cy.odooNavigateTo()` para navegação**
```javascript
it('Teste', () => {
  cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application') // ✅ Direto
})
```

**3. Use URLs relativas**
```javascript
cy.visit('/web#menu_id=123') // ✅ Funciona em qualquer ambiente
```

**4. Aguarde elementos importantes**
```javascript
cy.get('.o_list_view', { timeout: 10000 }).should('be.visible') // ✅ Robusto
```

---

### ❌ DON'T (Não Faça)

**1. Não faça login manual em cada teste**
```javascript
// ❌ LENTO e repetitivo
beforeEach(() => {
  cy.visit('/web/login')
  cy.get('input[name="login"]').type('admin')
  cy.get('input[name="password"]').type('admin')
  cy.get('button[type="submit"]').click()
})

// ✅ RÁPIDO e limpo
beforeEach(() => {
  cy.odooLoginSession()
})
```

**2. Não use URLs absolutas**
```javascript
cy.visit('http://localhost:8069/web') // ❌ Só funciona em localhost
cy.visit('/web') // ✅ Funciona em qualquer ambiente
```

**3. Não navegue clicando em menus se pode ir direto**
```javascript
// ❌ LENTO e frágil
cy.contains('Configurações').click()
cy.contains('Técnico').click()
cy.contains('API Gateway').click()

// ✅ RÁPIDO e confiável
cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
```

**4. Não use `cy.wait(5000)` sem necessidade**
```javascript
cy.wait(5000) // ❌ Tempo fixo desnecessário
cy.get('.o_list_view').should('be.visible') // ✅ Aguarda o necessário
```

---

## Comparação de Performance

### Teste SEM comandos customizados:
```javascript
describe('Teste Lento', () => {
  it('Teste 1', () => {
    cy.visit('/web/login')
    cy.get('input[name="login"]').type('admin')
    cy.get('input[name="password"]').type('admin')
    cy.get('button[type="submit"]').click()
    cy.wait(2000)
    cy.visit('/web#action=...')
    // ... teste
  })
  
  it('Teste 2', () => {
    cy.visit('/web/login') // Login novamente!
    cy.get('input[name="login"]').type('admin')
    cy.get('input[name="password"]').type('admin')
    cy.get('button[type="submit"]').click()
    cy.wait(2000)
    cy.visit('/web#action=...')
    // ... teste
  })
})
// ⏱️ Tempo total: ~30 segundos (faz login 2x)
```

### Teste COM comandos customizados:
```javascript
describe('Teste Rápido', () => {
  beforeEach(() => {
    cy.odooLoginSession() // Login uma vez, reutiliza sessão
  })
  
  it('Teste 1', () => {
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
    // ... teste
  })
  
  it('Teste 2', () => {
    cy.odooNavigateTo('api_gateway.action_oauth_token', 'oauth.token')
    // ... teste
  })
})
// ⏱️ Tempo total: ~10 segundos (faz login 1x, reutiliza)
// 🚀 3x MAIS RÁPIDO!
```

---

## Exemplos Reais

### Exemplo 1: Criar OAuth Application
```javascript
describe('OAuth Applications', () => {
  beforeEach(() => {
    cy.odooLoginSession()
  })
  
  it('Deve criar aplicação', () => {
    // Navegar para lista
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
    
    // Criar
    cy.get('button.o_list_button_add').click()
    cy.get('input[name="name"]').type('Minha App')
    cy.get('button.o_form_button_save').click()
    
    // Validar
    cy.get('.o_field_widget[name="name"]').should('contain', 'Minha App')
  })
})
```

### Exemplo 2: Testar API OAuth 2.0
```javascript
describe('OAuth 2.0 API', () => {
  let clientId, clientSecret
  
  before(() => {
    cy.odooLoginSession()
    
    // Criar aplicação via UI
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
    cy.get('button.o_list_button_add').click()
    cy.get('input[name="name"]').type('Test App')
    cy.get('button.o_form_button_save').click()
    
    // Capturar credenciais
    cy.get('input[name="client_id"]').invoke('val').then(val => {
      clientId = val
    })
    cy.get('input[name="client_secret"]').invoke('val').then(val => {
      clientSecret = val
    })
  })
  
  it('Deve obter token', () => {
    cy.request({
      method: 'POST',
      url: '/api/v1/auth/token',
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
      }
    }).then(response => {
      expect(response.status).to.eq(200)
      expect(response.body).to.have.property('access_token')
    })
  })
})
```

---

## Migrando Testes Antigos

Se você tem testes antigos que fazem login manualmente, migre para comandos customizados:

### Antes:
```javascript
describe('Teste Antigo', () => {
  beforeEach(() => {
    cy.visit('http://localhost:8069/web/login')
    cy.get('input[name="login"]').clear().type('admin')
    cy.get('input[name="password"]').clear().type('admin')
    cy.get('button[type="submit"]').click()
    cy.url().should('include', '/web')
    cy.wait(2000)
  })
  
  it('Teste', () => {
    cy.visit('http://localhost:8069/web#action=123')
    cy.wait(2000)
    // ... teste
  })
})
```

### Depois:
```javascript
describe('Teste Novo', () => {
  beforeEach(() => {
    cy.odooLoginSession() // 🚀 Muito mais rápido!
  })
  
  it('Teste', () => {
    cy.odooNavigateTo('module.action_name', 'model.name')
    // ... teste
  })
})
```

---

## Troubleshooting

### Problema: "Session não funciona"
**Solução:** Limpar cache de sessão:
```bash
npx cypress run --config-file=false
```

### Problema: "Timeout em login"
**Solução:** Aumentar timeout:
```javascript
cy.get('.o_user_menu', { timeout: 15000 }).should('be.visible')
```

### Problema: "Navegação não funciona"
**Solução:** Verificar se action existe:
```javascript
// Verificar action no Odoo:
// Settings → Technical → Actions → Window Actions
cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
```

---

## Referências

- [Cypress Session API](https://docs.cypress.io/api/commands/session)
- [Cypress Custom Commands](https://docs.cypress.io/api/cypress-api/custom-commands)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)

## Contribuindo

Ao criar novos comandos customizados:

1. Adicione em `cypress/support/commands.js`
2. Documente aqui com exemplos
3. Adicione JSDoc comments no código
4. Teste em múltiplos cenários

---

**Dica Final:** Use sempre `cy.odooLoginSession()` em `beforeEach()` para testes 3x mais rápidos! 🚀
