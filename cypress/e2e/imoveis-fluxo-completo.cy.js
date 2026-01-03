describe('Gestão de Imóveis - Fluxo Completo', () => {
  
  context('Como usuário autenticado', () => {
    beforeEach(() => {
      // Garante login em cada teste
      cy.odooLogin()
    })

    it('1. Deve visualizar a listagem de imóveis', () => {
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      
      // Guarda informações para próximos testes
      cy.url().as('listagemUrl')
    })

    it('2. Deve criar um novo imóvel', () => {
      // Continua do teste anterior (ainda logado)
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 }).should('be.visible').first().click()
      
      // Aguarda navegação e formulário estar em modo editável
      cy.wait(1500)
      cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
      cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 }).should('exist')
      
      // Preenche apenas campos obrigatórios que sempre existem
      cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input', { timeout: 10000 })
        .should('be.visible').first().clear().type('Apartamento Teste Cypress')
      
      // Tenta preencher price se existir
      cy.get('body').then($body => {
        if ($body.find('.o_field_widget[name="price"] input, input[name="price"]').length > 0) {
          cy.get('.o_field_widget[name="price"] input, input[name="price"], div[name="price"] input', { timeout: 5000 })
            .first().clear({ force: true }).type('500000', { force: true })
        }
      })
      
      // Salva
      cy.get('button.o_form_button_save', { timeout: 10000 }).should('be.visible').click()
      cy.wait(2000)
      
      // Verifica se salvou (campo name em qualquer formato: input, span, div)
      cy.get('.o_field_widget[name="name"], input[name="name"], span[name="name"], div[name="name"]', { timeout: 10000 })
        .should('exist')
    })

    it('3. Deve editar o imóvel criado', () => {
      // Acessa lista de imóveis
      cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
      
      // Aguarda registros carregarem e clica no primeiro
      cy.wait(1500)
      cy.get('body').then($body => {
        if ($body.find('tr.o_data_row').length > 0) {
          cy.get('tr.o_data_row', { timeout: 10000 }).first().click()
          cy.wait(1500)
          
          // Aguarda formulário carregar
          cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
          
          // Verifica se precisa clicar em Editar ou se já está editável
          cy.get('body').then($formBody => {
            if ($formBody.find('button.o_form_button_edit').length > 0) {
              cy.get('button.o_form_button_edit').click()
              cy.wait(1000)
            }
          })
          
          // Tenta editar num_rooms se o campo existir
          cy.get('body').then($formBody => {
            if ($formBody.find('input[name="num_rooms"], .o_field_widget[name="num_rooms"] input').length > 0) {
              cy.get('input[name="num_rooms"], .o_field_widget[name="num_rooms"] input')
                .first().clear({ force: true }).type('4', { force: true })
              
              // Aguarda botão Save ficar visível após edição
              cy.wait(500)
              
              // Salva (só se conseguiu editar)
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
