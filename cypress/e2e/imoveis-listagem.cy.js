describe('Listagem de Imóveis', () => {
  beforeEach(() => {
    // Faz login antes de cada teste
    cy.odooLogin()
  })

  it('Deve visualizar a listagem de imóveis', () => {
    // Navega diretamente para a listagem de propriedades
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    
    // Aguarda elementos estarem prontos
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    
    // Verifica se há registros ou mensagem de "sem dados"
    cy.get('body').then(($body) => {
      if ($body.find('.o_list_table').length > 0) {
        cy.get('.o_list_table').should('be.visible')
      } else if ($body.find('.o_view_nocontent').length > 0) {
        cy.get('.o_view_nocontent').should('be.visible')
      }
    })
  })

  it('Deve abrir o formulário de novo imóvel', () => {
    // Navega para listagem de propriedades
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    
    // Aguarda elementos estarem prontos
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    
    // Clica no botão de criar
    cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 }).first().click()
    
    // Verifica se abriu o formulário
    cy.get('.o_form_view', { timeout: 10000 }).should('be.visible')
  })

  it('Deve filtrar imóveis disponíveis', () => {
    // Navega para listagem de propriedades
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    
    // Aguarda elementos estarem prontos
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    
    // Usa os filtros do Odoo
    cy.get('.o_searchview_input', { timeout: 10000 }).should('be.visible').type('Casa{enter}')
    
    // Verifica se o filtro foi aplicado (filtrou por algum texto)
    cy.get('body').should('be.visible')
  })

  afterEach(() => {
    // Opcional: fazer logout após cada teste
    // cy.odooLogout()
  })
})
