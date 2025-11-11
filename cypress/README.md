# Testes E2E com Cypress - Odoo Real Estate

## 📋 Pré-requisitos

- Node.js 20.x instalado
- Odoo rodando em `http://localhost:8069`
- Credenciais de acesso configuradas

## 🚀 Como executar os testes

### 1. Certifique-se que o Odoo está rodando

```bash
cd 18.0
docker compose up -d
```

### 2. Execute os testes em modo interativo

```bash
npm run cypress:open
```

Ou usando npx diretamente:

```bash
npx cypress open
```

### 3. Execute os testes em modo headless

```bash
npm run cypress:run
```

## 📁 Estrutura dos Testes

```
cypress/
├── e2e/
│   ├── login-teste.cy.js           # Testes completos de login
│   └── login-custom-command.cy.js  # Exemplos usando comandos customizados
├── fixtures/
│   └── example.json                # Dados de teste
├── support/
│   ├── commands.js                 # Comandos customizados
│   └── e2e.js                      # Configurações globais
└── cypress.config.js               # Configuração do Cypress
```

## 🧪 Testes Disponíveis

### login-teste.cy.js

Contém 4 testes principais:

1. **Login com sucesso** - Testa login com credenciais válidas
2. **Erro com credenciais inválidas** - Verifica mensagens de erro
3. **Validação de campos obrigatórios** - Testa campos vazios
4. **Logout após login** - Testa o fluxo completo de login/logout

### login-custom-command.cy.js

Demonstra o uso dos comandos customizados:
- `cy.odooLogin()` - Login rápido
- `cy.odooLogout()` - Logout rápido

## 🔐 Credenciais

As credenciais padrão estão configuradas em `cypress.env.json`:

```json
{
  "ODOO_USERNAME": "admin",
  "ODOO_PASSWORD": "admin",
  "ODOO_BASE_URL": "http://localhost:8069"
}
```

Para usar credenciais diferentes, edite o arquivo `cypress.env.json`.

## 🛠️ Comandos Customizados

### cy.odooLogin(username, password)

Realiza login no Odoo de forma simplificada.

```javascript
// Login com credenciais padrão (admin/admin)
cy.odooLogin()

// Login com credenciais específicas
cy.odooLogin('outro_usuario', 'outra_senha')
```

### cy.odooLoginSession(username, password)

Realiza login com sessão persistente (muito mais rápido para múltiplos testes).

```javascript
// Mantém o login entre os testes
beforeEach(() => {
  cy.odooLoginSession()
})
```

### cy.odooLogout()

Realiza logout do Odoo.

```javascript
cy.odooLogout()
```

## 🔗 Conectando Testes

### Opção 1: Testes Independentes (Recomendado)

Cada teste começa do zero, garantindo isolamento:

```javascript
describe('Listagem de Imóveis', () => {
  beforeEach(() => {
    cy.odooLogin() // Login antes de cada teste
  })

  it('Deve visualizar a listagem', () => {
    cy.contains('Real Estate').click()
    cy.get('.o_list_view').should('be.visible')
  })

  it('Deve criar novo imóvel', () => {
    // Já está logado por causa do beforeEach
    cy.contains('Real Estate').click()
    cy.get('.o_list_button_add').click()
  })
})
```

### Opção 2: Testes Conectados (Fluxo)

Testes dependem uns dos outros, executam em sequência:

```javascript
describe('Fluxo Completo', () => {
  let imovelId
  
  before(() => {
    cy.odooLoginSession() // Login uma vez
  })

  it('1. Criar imóvel', () => {
    // ... código ...
    cy.url().then((url) => {
      imovelId = url.match(/id=(\d+)/)[1]
    })
  })

  it('2. Editar imóvel', () => {
    // Usa o imovelId do teste anterior
    cy.visit(`/web#id=${imovelId}&model=estate.property`)
  })
})
```

### Opção 3: Sessões (Performance)

Mantém login entre testes para execução mais rápida:

```javascript
describe('Testes Rápidos', () => {
  beforeEach(() => {
    cy.odooLoginSession() // Reutiliza sessão
  })

  // Testes executam muito mais rápido!
})
```

## 📝 Exemplo de Teste

```javascript
describe('Meu Teste', () => {
  it('Deve acessar o sistema', () => {
    // Faz login
    cy.odooLogin()
    
    // Navega para algum lugar
    cy.visit('/web#menu_id=123')
    
    // Faz suas verificações
    cy.get('.o_form_view').should('be.visible')
    
    // Faz logout
    cy.odooLogout()
  })
})
```

## 🔍 Seletores Úteis do Odoo

- `.o_user_menu` - Menu do usuário
- `.o_apps` - Menu de aplicativos
- `.o_form_view` - Visualização de formulário
- `.o_list_view` - Visualização de lista
- `.o_kanban_view` - Visualização kanban
- `input[name="login"]` - Campo de login
- `input[name="password"]` - Campo de senha
- `button[type="submit"]` - Botão de submit

## 📊 Relatórios

Os relatórios de execução são salvos em:
- Screenshots: `cypress/screenshots/`
- Vídeos: `cypress/videos/`

## ⚙️ Configurações

O arquivo `cypress.config.js` contém as configurações principais:

- `baseUrl`: URL base do Odoo
- `viewportWidth`: Largura da viewport (1280px)
- `viewportHeight`: Altura da viewport (720px)
- `defaultCommandTimeout`: Timeout padrão (10000ms)

## 🐛 Troubleshooting

### Erro: "Timed out retrying"

- Verifique se o Odoo está rodando
- Aumente o timeout no `cypress.config.js`
- Verifique se a URL está correta

### Erro: "Element not visible"

- Use `{ timeout: 10000 }` para aguardar elementos
- Verifique se o seletor CSS está correto
- Use `cy.wait()` se necessário

### Testes passam no modo interativo mas falham no headless

- Adicione esperas explícitas com `cy.wait()`
- Use `cy.get('.elemento', { timeout: 10000 })`
- Verifique a velocidade de execução
