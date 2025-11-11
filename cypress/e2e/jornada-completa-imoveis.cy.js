describe('Jornada Completa do Usuário - Gestão de Imóveis', () => {
  // Variável para compartilhar dados entre testes
  let imovelId = null
  let imovelNome = `Imóvel Teste ${Date.now()}`

  before(() => {
    // Login uma vez no início
    cy.odooLoginSession()
  })

  context('Criação de Imóvel', () => {
    it('1. Deve acessar o módulo Real Estate', () => {
      cy.visit('/web')
      cy.contains('Real Estate').click()
      cy.url().should('include', 'model=estate.property')
    })

    it('2. Deve criar um novo imóvel', () => {
      cy.contains('Real Estate').click()
      cy.get('.o_list_button_add').click()
      
      // Preenche dados básicos
      cy.get('input[name="name"]').type(imovelNome)
      cy.get('input[name="expected_price"]').type('450000')
      cy.get('input[name="bedrooms"]').type('3')
      cy.get('input[name="living_area"]').type('120')
      
      // Salva
      cy.get('.o_form_button_save').click()
      
      // Aguarda salvar e captura o ID da URL
      cy.url().should('include', 'id=')
      cy.url().then((url) => {
        const match = url.match(/id=(\d+)/)
        if (match) {
          imovelId = match[1]
          cy.log(`Imóvel criado com ID: ${imovelId}`)
        }
      })
      
      // Verifica se salvou
      cy.contains(imovelNome).should('be.visible')
    })
  })

  context('Consulta e Edição', () => {
    it('3. Deve encontrar o imóvel na listagem', () => {
      cy.contains('Real Estate').click()
      cy.get('.o_searchview_input').type(`${imovelNome}{enter}`)
      
      // Verifica se apareceu na lista
      cy.contains(imovelNome).should('be.visible')
      cy.contains('450,000').should('be.visible')
    })

    it('4. Deve editar o imóvel criado', () => {
      // Busca pelo nome
      cy.contains('Real Estate').click()
      cy.get('.o_searchview_input').clear().type(`${imovelNome}{enter}`)
      
      // Abre o registro
      cy.contains(imovelNome).click()
      
      // Entra em modo edição
      cy.get('.o_form_button_edit').click()
      
      // Altera dados
      cy.get('input[name="bedrooms"]').clear().type('4')
      cy.get('input[name="expected_price"]').clear().type('480000')
      
      // Salva
      cy.get('.o_form_button_save').click()
      
      // Verifica se salvou
      cy.get('input[name="bedrooms"]').should('have.value', '4')
    })

    it('5. Deve visualizar as alterações na listagem', () => {
      cy.contains('Real Estate').click()
      cy.get('.o_searchview_input').clear().type(`${imovelNome}{enter}`)
      
      // Verifica o novo preço
      cy.contains('480,000').should('be.visible')
    })
  })

  context('Ações Adicionais', () => {
    it('6. Deve adicionar uma foto ao imóvel', () => {
      cy.contains('Real Estate').click()
      cy.contains(imovelNome).click()
      
      // Navega para aba de fotos (ajustar seletor conforme seu módulo)
      cy.contains('Photos').click()
      
      // Adiciona foto
      cy.get('.o_field_x2many_list_row_add a').click()
      
      // Upload de arquivo (exemplo)
      // cy.get('input[type="file"]').attachFile('casa-exemplo.jpg')
    })

    it('7. Deve arquivar o imóvel', () => {
      cy.contains('Real Estate').click()
      cy.contains(imovelNome).click()
      
      // Clica em Ação > Arquivar (ajustar conforme seu Odoo)
      cy.get('.o_cp_action_menus button').click()
      cy.contains('Archive').click()
      
      // Confirma
      cy.get('.modal').contains('Ok').click()
      
      // Verifica que saiu da view
      cy.url().should('include', 'model=estate.property')
      cy.url().should('not.include', `id=${imovelId}`)
    })
  })

  after(() => {
    // Opcional: limpar dados de teste
    cy.log(`Testes finalizados. Imóvel ID: ${imovelId} pode ser removido manualmente.`)
  })
})
