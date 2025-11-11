describe('Gestão de Imóveis - Fluxo Completo', () => {
  
  context('Como usuário autenticado', () => {
    before(() => {
      // Login uma vez antes de todos os testes deste contexto
      cy.odooLogin()
    })

    it('1. Deve visualizar a listagem de imóveis', () => {
      cy.contains('Real Estate').click()
      cy.get('.o_list_view').should('be.visible')
      
      // Guarda informações para próximos testes
      cy.url().as('listagemUrl')
    })

    it('2. Deve criar um novo imóvel', () => {
      // Continua do teste anterior (ainda logado)
      cy.contains('Real Estate').click()
      cy.get('.o_list_button_add').click()
      
      // Preenche o formulário
      cy.get('input[name="name"]').type('Apartamento Teste Cypress')
      cy.get('input[name="expected_price"]').type('500000')
      cy.get('input[name="bedrooms"]').type('3')
      
      // Salva
      cy.get('.o_form_button_save').click()
      
      // Verifica se salvou
      cy.contains('Apartamento Teste Cypress').should('be.visible')
    })

    it('3. Deve editar o imóvel criado', () => {
      // Busca pelo imóvel criado no teste anterior
      cy.contains('Real Estate').click()
      cy.get('.o_searchview_input').type('Apartamento Teste Cypress{enter}')
      
      // Abre o registro
      cy.contains('Apartamento Teste Cypress').click()
      
      // Edita
      cy.get('.o_form_button_edit').click()
      cy.get('input[name="bedrooms"]').clear().type('4')
      cy.get('.o_form_button_save').click()
      
      // Verifica a alteração
      cy.get('input[name="bedrooms"]').should('have.value', '4')
    })

    after(() => {
      // Opcional: limpar dados de teste
      // cy.odooLogout()
    })
  })

  context('Como usuário não autenticado', () => {
    it('Deve redirecionar para login ao tentar acessar imóveis', () => {
      cy.visit('/web')
      cy.url().should('include', '/web/login')
    })
  })
})
