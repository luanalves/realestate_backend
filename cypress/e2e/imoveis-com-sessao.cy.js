describe('Imóveis - Testes com Sessão Persistente', () => {
  beforeEach(() => {
    // Usa cy.session para manter o login entre os testes
    // Muito mais rápido que fazer login toda vez!
    cy.odooLoginSession()
  })

  it('Deve navegar para listagem de imóveis', () => {
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
  })

  it('Deve criar novo imóvel rapidamente', () => {
    // Garante sessão ativa
    cy.odooLoginSession()
    
    // Já está logado por causa da sessão
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 }).should('be.visible').first().click()
    
    // Aguarda navegação e formulário estar em modo editável
    cy.wait(1500)
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 }).should('exist')
    
    // Usa seletor mais flexível para o campo name
    cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input', { timeout: 10000 })
      .should('be.visible')
      .first()
      .clear()
      .type('Casa Teste Sessão')
  })

  it('Deve buscar imóveis sem fazer login novamente', () => {
    // Sessão ainda está ativa!
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    cy.get('.o_searchview_input', { timeout: 10000 }).should('be.visible')
  })
})
