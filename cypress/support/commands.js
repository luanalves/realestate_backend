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
 * Comando customizado para fazer logout do Odoo
 */
Cypress.Commands.add('odooLogout', () => {
  cy.get('.o_user_menu').click()
  cy.get('.dropdown-menu').contains(/Log out|Sair/).click()
  cy.url().should('include', '/web/login')
})