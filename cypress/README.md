# Testes Cypress para Odoo

Este diretório contém testes E2E (End-to-End) usando Cypress para o sistema Odoo.

## 📚 Documentação Importante

- **[Comandos Customizados](./COMANDOS_CUSTOMIZADOS.md)** ⭐ **LEIA PRIMEIRO!**
  - `cy.odooLoginSession()` - Login com cache (3x mais rápido!)
  - `cy.odooNavigateTo()` - Navegação direta para menus
  - Boas práticas e exemplos de uso
  - Como migrar testes antigos

## 🧪 Testes Disponíveis

### API Gateway
- **`api-gateway.cy.js`** - Testes de interface (20 testes)
  - Criação/edição de OAuth Applications
  - Gerenciamento de tokens
  - Validações de campos
  - UI/UX

- **`api-gateway-integration.cy.js`** - Testes de integração (12 testes)
  - Fluxo completo: UI → API → UI
  - OAuth 2.0 Client Credentials
  - Revogação de tokens
  - Validações de segurança

### Outros Módulos
- `imoveis-*.cy.js` - Testes do módulo de imóveis
- `login-custom-command.cy.js` - Exemplo de comando customizado

## 🚀 Como Executar

### Pré-requisitos
```bash
# 1. Odoo rodando
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
docker compose up -d

# 2. Módulo api_gateway instalado
docker compose exec odoo odoo -d realestate -i api_gateway --stop-after-init
docker compose restart odoo
```

### Modo Interativo (Recomendado)
```bash
cd /opt/homebrew/var/www/realestate/odoo-docker
npx cypress open
```
Depois selecione o teste desejado.

### Modo Headless (CI/CD)
```bash
# Todos os testes
npx cypress run

# Apenas API Gateway
npx cypress run --spec "cypress/e2e/api-gateway*.cy.js"

# Apenas frontend
npx cypress run --spec "cypress/e2e/api-gateway.cy.js"

# Apenas integração
npx cypress run --spec "cypress/e2e/api-gateway-integration.cy.js"
```

## ✅ Exemplo de Uso

```javascript
describe('Meu Teste', () => {
  beforeEach(() => {
    // ✅ Use cy.odooLoginSession() - MUITO MAIS RÁPIDO!
    cy.odooLoginSession()
  })
  
  it('Deve criar aplicação', () => {
    // ✅ Use cy.odooNavigateTo() - Navegação direta
    cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
    
    cy.get('button.o_list_button_add').click()
    cy.get('input[name="name"]').type('Test App')
    cy.get('button.o_form_button_save').click()
  })
})
```

## 📖 Recursos

- [Comandos Customizados](./COMANDOS_CUSTOMIZADOS.md) - **Leia para testes 3x mais rápidos!**
- [Cypress Docs](https://docs.cypress.io/)
- [Best Practices](https://docs.cypress.io/guides/references/best-practices)

## 🤝 Contribuindo

Ao adicionar novos testes:

1. **Use comandos customizados:**
   ```javascript
   cy.odooLoginSession() // ✅ Ao invés de login manual
   cy.odooNavigateTo(...) // ✅ Ao invés de clicar em menus
   ```

2. **Nomeie descritivamente:**
   ```javascript
   it('Deve criar OAuth Application com nome e descrição', () => {
   ```

3. **Adicione ao README** se criar novos módulos de teste

## 📝 Licença

LGPL-3
