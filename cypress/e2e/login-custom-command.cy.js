describe('Exemplo de uso do comando customizado odooLogin', () => {
  it('Deve fazer login usando o comando customizado', () => {
    // Usa o comando customizado para fazer login
    cy.odooLogin()
    
    // Verifica se está logado
    cy.url().should('satisfy', (url) => url.includes('/web') || url.includes('/odoo'))
    cy.get('.o_user_menu').should('be.visible')
    
    // Faz logout usando o comando customizado
    cy.odooLogout()
  })

  it('Deve fazer login com credenciais específicas', () => {
    // Usa o comando customizado com credenciais específicas
    cy.odooLogin('admin', 'admin')
    
    // Verifica se está logado
    cy.url().should('satisfy', (url) => url.includes('/web') || url.includes('/odoo'))
    cy.get('.o_user_menu').should('be.visible')
  })

  it('Deve navegar após login', () => {
    // Faz login
    cy.odooLogin()
    
    // Aguarda o carregamento completo - verifica se está na interface do Odoo
    cy.get('.o_main_navbar', { timeout: 10000 }).should('be.visible')
    
    // Verifica que o menu de usuário está presente
    cy.get('.o_user_menu').should('be.visible')
  })
})
