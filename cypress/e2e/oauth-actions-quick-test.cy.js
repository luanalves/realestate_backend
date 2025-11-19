/// <reference types="cypress" />

/**
 * Teste Rápido: Validar Actions Menu de OAuth Applications
 */

describe('OAuth Applications - Quick Actions Test', () => {
  const testAppName = `Actions Test ${Date.now()}`;

  before(() => {
    cy.odooLoginSession();
  });

  it('Deve validar todas as ações disponíveis no menu', () => {
    // 1. Criar uma aplicação de teste
    cy.visit('/web#action=api_gateway.action_oauth_application');
    cy.wait(2000);

    cy.get('button.o_list_button_add').first().click();
    cy.wait(2000);

    cy.get('.o_field_widget[name="name"] input').first().clear().type(testAppName);
    cy.get('button.o_form_button_save').click();
    cy.wait(2000);

    cy.get('.o_back_button').first().click();
    cy.wait(1000);

    // 2. Selecionar a aplicação criada
    cy.contains('td', testAppName).parent('tr').within(() => {
      cy.get('input[type="checkbox"]').first().check({ force: true });
    });
    cy.wait(500);

    // 3. Abrir menu Actions e verificar opções
    cy.get('button').contains('Actions').click();
    cy.wait(500);

    // 4. Verificar que TODAS as ações existem
    const expectedActions = ['Export', 'Archive', 'Unarchive', 'Duplicate', 'Delete'];
    
    cy.get('.dropdown-menu').within(() => {
      expectedActions.forEach((action) => {
        cy.log(`Verificando ação: ${action}`);
        // Usar should para garantir que está visível
        cy.contains('.dropdown-item', action, { matchCase: false }).should('exist');
      });
    });

    // 5. Fechar menu clicando fora
    cy.get('body').click(0, 0);
    cy.wait(500);

    // 6. Testar Delete (limpar dados)
    cy.contains('td', testAppName).parent('tr').within(() => {
      cy.get('input[type="checkbox"]').first().check({ force: true });
    });
    
    cy.get('button').contains('Actions').click();
    cy.contains('.dropdown-item', 'Delete').click();
    cy.wait(1000);
    
    cy.get('.modal-footer button, .o_dialog_footer button')
      .contains(/Ok|Confirm|Delete/i)
      .click();
    cy.wait(1000);

    // Verificar que foi deletada
    cy.get('body').should('not.contain', testAppName);
  });
});
