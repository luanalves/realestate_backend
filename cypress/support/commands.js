// ***********************************************
// Custom Commands for Odoo Testing
// ***********************************************

/**
 * Comando customizado para fazer login no Odoo
 * @param {string} username - Nome de usuário (padrão: 'admin')
 * @param {string} password - Senha (padrão: 'admin')
 * 
 * Exemplo de uso:
 * cy.odooLogin()
 * cy.odooLogin('admin', 'admin')
 */
Cypress.Commands.add('odooLogin', (username = 'admin', password = 'admin') => {
  cy.visit('/web/login')
  cy.get('input[name="login"]').type(username)
  cy.get('input[name="password"]').type(password)
  cy.get('button[type="submit"]').click()
  cy.get('.o_user_menu', { timeout: 10000 }).should('be.visible')
})

/**
 * Comando customizado para fazer login com sessão persistente
 * Mantém o login entre os testes para melhor performance
 * 
 * RECOMENDADO: Use este comando em beforeEach() para testes mais rápidos
 * 
 * Exemplo de uso:
 * beforeEach(() => {
 *   cy.odooLoginSession()
 * })
 */
Cypress.Commands.add('odooLoginSession', (username = 'admin', password = 'admin') => {
  cy.session([username, password], () => {
    cy.visit('/web/login')
    cy.get('input[name="login"]').type(username)
    cy.get('input[name="password"]').type(password)
    cy.get('button[type="submit"]').click()
    cy.get('.o_user_menu', { timeout: 10000 }).should('be.visible')
  })
  // Após restaurar a sessão, navega para a home
  cy.visit('/web')
})

/**
 * Comando customizado para fazer logout do Odoo
 */
Cypress.Commands.add('odooLogout', () => {
  cy.get('.o_user_menu').click()
  cy.get('.dropdown-menu').contains(/Log out|Sair/).click()
  cy.url().should('include', '/web/login')
})

/**
 * Comando customizado para navegar para menu do Odoo
 * @param {string} action - Nome da action (ex: 'api_gateway.action_oauth_application')
 * @param {string} model - Nome do modelo (ex: 'oauth.application')
 * @param {string} viewType - Tipo de view (padrão: 'list')
 * 
 * Exemplo de uso:
 * cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
 * cy.odooNavigateTo('api_gateway.action_oauth_token', 'oauth.token', 'form')
 */
Cypress.Commands.add('odooNavigateTo', (action, model, viewType = 'list') => {
  cy.visit(`/web#action=${action}&model=${model}&view_type=${viewType}`)
  cy.wait(1500) // Aguardar carregamento
})