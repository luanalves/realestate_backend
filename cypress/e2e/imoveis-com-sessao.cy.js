describe('Imóveis - Testes com Sessão Persistente', () => {
  beforeEach(() => {
    // Usa cy.session para manter o login entre os testes
    // Muito mais rápido que fazer login toda vez!
    cy.odooLoginSession()
  })

  it('Deve navegar para listagem de imóveis', () => {
    cy.contains('Real Estate').click()
    cy.get('.o_list_view').should('be.visible')
  })

  it('Deve criar novo imóvel rapidamente', () => {
    // Já está logado por causa da sessão
    cy.contains('Real Estate').click()
    cy.get('.o_list_button_add').click()
    cy.get('input[name="name"]').type('Casa Teste Sessão')
  })

  it('Deve buscar imóveis sem fazer login novamente', () => {
    // Sessão ainda está ativa!
    cy.contains('Real Estate').click()
    cy.get('.o_searchview_input').should('be.visible')
  })
})
