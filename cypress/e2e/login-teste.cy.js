describe('Odoo Login Tests', () => {
  const username = Cypress.env('ODOO_USERNAME') || 'admin'
  const password = Cypress.env('ODOO_PASSWORD') || 'admin'

  beforeEach(() => {
    // Visita a página de login antes de cada teste
    cy.visit('/web/login')
  })

  it('Deve realizar login com sucesso', () => {
    // Preenche o campo de email/login
    cy.get('input[name="login"]').type(username)
    
    // Preenche o campo de senha
    cy.get('input[name="password"]').type(password)
    
    // Clica no botão de login
    cy.get('button[type="submit"]').click()
    
    // Verifica se o login foi bem-sucedido
    // Após o login, o Odoo redireciona para /web ou /odoo
    cy.url().should('satisfy', (url) => url.includes('/web') || url.includes('/odoo'))
    
    // Verifica se o menu do usuário está visível (indica login bem-sucedido)
    cy.get('.o_user_menu', { timeout: 10000 }).should('be.visible')
  })

  it('Deve exibir erro com credenciais inválidas', () => {
    // Preenche com credenciais inválidas
    cy.get('input[name="login"]').type('usuario_invalido')
    cy.get('input[name="password"]').type('senha_invalida')
    
    // Clica no botão de login
    cy.get('button[type="submit"]').click()
    
    // Verifica se permanece na página de login
    cy.url().should('include', '/web/login')
    
    // Verifica se exibe mensagem de erro
    cy.get('.alert-danger').should('be.visible')
      .and('contain', 'Wrong login/password')
  })

  it('Deve validar campos obrigatórios', () => {
    // Tenta submeter o formulário sem preencher
    cy.get('button[type="submit"]').click()
    
    // Verifica que ainda está na página de login
    cy.url().should('include', '/web/login')
  })

  it('Deve fazer logout após login bem-sucedido', () => {
    // Realiza o login
    cy.get('input[name="login"]').type(username)
    cy.get('input[name="password"]').type(password)
    cy.get('button[type="submit"]').click()
    
    // Aguarda o carregamento completo
    cy.get('.o_user_menu', { timeout: 10000 }).should('be.visible')
    
    // Clica no menu do usuário
    cy.get('.o_user_menu').click()
    
    // Clica em Logout (pode estar em português ou inglês)
    cy.get('.dropdown-menu').contains(/Log out|Sair/).click()
    
    // Verifica se retornou para a página de login
    cy.url().should('include', '/web/login')
  })
})