describe('Listagem de Imóveis', () => {
  beforeEach(() => {
    // Faz login antes de cada teste
    cy.odooLogin()
  })

  it('Deve visualizar a listagem de imóveis', () => {
    // Navega para o menu de imóveis
    cy.contains('Real Estate').click()
    
    // Verifica se está na view de lista
    cy.get('.o_list_view').should('be.visible')
    cy.url().should('include', '/web')
    
    // Verifica se há registros ou mensagem de "sem dados"
    cy.get('body').then(($body) => {
      if ($body.find('.o_list_table').length > 0) {
        cy.get('.o_list_table').should('be.visible')
      } else {
        cy.contains('No records').should('be.visible')
      }
    })
  })

  it('Deve abrir o formulário de novo imóvel', () => {
    // Já está logado por causa do beforeEach
    cy.contains('Real Estate').click()
    
    // Clica no botão de criar
    cy.get('.o_list_button_add').click()
    
    // Verifica se abriu o formulário
    cy.get('.o_form_view').should('be.visible')
    cy.url().should('include', 'model=estate.property')
  })

  it('Deve filtrar imóveis disponíveis', () => {
    cy.contains('Real Estate').click()
    
    // Usa os filtros do Odoo
    cy.get('.o_searchview_input').type('Disponível{enter}')
    
    // Verifica se o filtro foi aplicado
    cy.get('.o_facet_value').should('contain', 'Disponível')
  })

  afterEach(() => {
    // Opcional: fazer logout após cada teste
    // cy.odooLogout()
  })
})
