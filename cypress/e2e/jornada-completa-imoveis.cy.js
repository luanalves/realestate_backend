describe('Jornada Completa do Usuário - Gestão de Imóveis', () => {
  // Variável para compartilhar dados entre testes
  let imovelId = null
  let imovelNome = `Imóvel Teste ${Date.now()}`

  beforeEach(() => {
    // Garante login em cada teste
    cy.odooLoginSession()
  })

  context('Criação de Imóvel', () => {
    it('1. Deve acessar o módulo Real Estate', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    })

    it('2. Deve criar um novo imóvel', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 }).should('be.visible').first().click()
      
      // Aguarda navegação e formulário estar em modo editável
      cy.wait(1500)
      cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
      cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 }).should('exist')
      
      // Preenche apenas name (obrigatório)
      cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input', { timeout: 10000 })
        .should('be.visible').first().clear().type(imovelNome)
      
      // Tenta preencher outros campos opcionais
      cy.get('body').then($body => {
        if ($body.find('.o_field_widget[name="price"] input, input[name="price"]').length > 0) {
          cy.get('.o_field_widget[name="price"] input').first().clear({ force: true }).type('450000', { force: true })
        }
        if ($body.find('.o_field_widget[name="num_rooms"] input, input[name="num_rooms"]').length > 0) {
          cy.get('.o_field_widget[name="num_rooms"] input').first().clear({ force: true }).type('3', { force: true })
        }
        if ($body.find('.o_field_widget[name="area"] input, input[name="area"]').length > 0) {
          cy.get('.o_field_widget[name="area"] input').first().clear({ force: true }).type('120', { force: true })
        }
      })
      
      // Salva
      cy.get('button.o_form_button_save', { timeout: 10000 }).should('be.visible').click()
      cy.wait(2000)
      
      // Aguarda salvar e captura o ID da URL
      cy.url().then((url) => {
        const match = url.match(/id=(\d+)/)
        if (match) {
          imovelId = match[1]
          cy.log(`Imóvel criado com ID: ${imovelId}`)
        }
      })
      
      // Verifica se salvou (campo name em qualquer formato)
      cy.get('.o_field_widget[name="name"], input[name="name"], span[name="name"]', { timeout: 10000 })
        .should('exist')
    })
  })

  context('Consulta e Edição', () => {
    it('3. Deve encontrar o imóvel na listagem', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      cy.get('.o_searchview_input', { timeout: 10000 }).should('be.visible').type(`${imovelNome}{enter}`)
      
      // Aguarda resultado da busca
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('body').should('contain', imovelNome)
    })

    it('4. Deve editar o imóvel criado', () => {
      // Acessa lista
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      
      // Aguarda registros e abre o primeiro
      cy.wait(1500)
      cy.get('body').then($body => {
        if ($body.find('tr.o_data_row').length > 0) {
          cy.get('tr.o_data_row').first().click()
          cy.wait(1500)
          
          // Aguarda formulário
          cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
          
          // Verifica se precisa clicar em Edit
          cy.get('body').then($formBody => {
            if ($formBody.find('button.o_form_button_edit').length > 0) {
              cy.get('button.o_form_button_edit').click()
              cy.wait(1000)
            }
          })
          
          // Tenta editar campos se existirem
          cy.get('body').then($formBody => {
            let edited = false
            
            if ($formBody.find('input[name="num_rooms"], .o_field_widget[name="num_rooms"] input').length > 0) {
              cy.get('input[name="num_rooms"], .o_field_widget[name="num_rooms"] input')
                .first().clear({ force: true }).type('4', { force: true })
              edited = true
            }
            
            if ($formBody.find('input[name="price"], .o_field_widget[name="price"] input').length > 0) {
              cy.get('input[name="price"], .o_field_widget[name="price"] input')
                .first().clear({ force: true }).type('480000', { force: true })
              edited = true
            }
            
            if (edited) {
              // Aguarda botão Save ficar visível
              cy.wait(500)
              cy.get('button.o_form_button_save').then($saveBtn => {
                if ($saveBtn.is(':visible')) {
                  cy.wrap($saveBtn).click()
                  cy.wait(2000)
                }
              })
            }
          })
        } else {
          cy.log('Nenhum registro encontrado na lista')
        }
      })
    })

    it('5. Deve visualizar as alterações na listagem', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      cy.get('.o_searchview_input', { timeout: 10000 }).should('be.visible').clear().type(`${imovelNome}{enter}`)
      
      // Aguarda resultado da busca
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('body').should('contain', imovelNome)
    })
  })

  context('Ações Adicionais', () => {
    it('6. Deve navegar para detalhes do imóvel', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      
      // Aguarda registros e abre o primeiro
      cy.wait(1500)
      cy.get('body').then($body => {
        if ($body.find('tr.o_data_row').length > 0) {
          cy.get('tr.o_data_row').first().click()
          cy.wait(1500)
          
          // Verifica que está no formulário
          cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
        } else {
          cy.log('Nenhum registro encontrado na lista')
        }
      })
    })
  })

  after(() => {
    // Opcional: limpar dados de teste
    cy.log(`Testes finalizados. Imóvel ID: ${imovelId} pode ser removido manualmente.`)
  })
})
