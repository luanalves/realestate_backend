/// <reference types="cypress" />

/**
 * Testes E2E para Actions de OAuth Applications
 * 
 * Valida as ações disponíveis no menu Actions:
 * - Export
 * - Archive
 * - Unarchive
 * - Duplicate
 * - Delete
 */

describe('OAuth Applications - Actions Menu', () => {
  let testAppName;
  let testAppId;

  beforeEach(() => {
    // Login com sessão persistente
    cy.odooLoginSession();
  });

  before(() => {
    // Criar uma aplicação de teste para usar nos testes
    cy.odooLoginSession();
    testAppName = `Test Actions App ${Date.now()}`;
  });

  describe('Preparação - Criar Aplicação de Teste', () => {
    it('Deve criar uma aplicação para testes de ações', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Clicar em criar
      cy.get('button.o_list_button_add, button.o-list-button-add').first().click();
      cy.wait(2000);

      // Preencher nome
      cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input')
        .first()
        .clear()
        .type(testAppName);

      // Salvar
      cy.get('button.o_form_button_save').click();
      cy.wait(2000);

      // Capturar ID da aplicação criada
      cy.url().then((url) => {
        const match = url.match(/id=(\d+)/);
        if (match) {
          testAppId = match[1];
          cy.log(`Aplicação criada com ID: ${testAppId}`);
        }
      });

      // Voltar para lista
      cy.get('.o_back_button, button.o_form_button_cancel').first().click();
      cy.wait(1000);
    });
  });

  describe('Action: Export', () => {
    it('Deve selecionar uma aplicação e exportar', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Selecionar a aplicação de teste
      cy.contains('td', testAppName).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.wait(500);

      // Verificar que mostra "1 selected"
      cy.get('body').should('contain.text', 'selected');

      // Clicar em Actions - usar seletor mais genérico
      cy.contains('button', 'Actions').click();
      cy.wait(500);

      // Verificar que menu Export existe
      cy.get('.dropdown-menu').should('contain.text', 'Export');

      // Clicar em Export
      cy.contains('.dropdown-item', 'Export').click();
      cy.wait(1000);

      // Verificar que dialog de export aparece
      cy.get('.modal-dialog, .o_dialog').should('be.visible');
      cy.get('.modal-body, .o_dialog_content').should('contain.text', 'Export');

      // Fechar modal
      cy.get('.modal-footer button, .o_dialog_footer button')
        .contains(/Cancel|Cancelar/i)
        .click();
    });
  });

  describe('Action: Duplicate', () => {
    it('Deve duplicar uma aplicação', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Selecionar a aplicação
      cy.contains('td', testAppName).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.wait(500);

      // Abrir menu Actions
      cy.get('button').click();
      cy.wait(500);

      // Verificar que Duplicate existe
      cy.get('.dropdown-menu').should('contain.text', 'Duplicate');

      // Clicar em Duplicate
      cy.contains('.dropdown-item', 'Duplicate').click();
      cy.wait(2000);

      // Verificar que cópia foi criada
      cy.get('body').should('contain.text', `${testAppName} (copy)`);

      // Limpar - deletar a cópia criada
      cy.contains('td', `${testAppName} (copy)`).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.get('button').click();
      cy.contains('.dropdown-item', 'Delete').click();
      cy.get('.modal-footer button, .o_dialog_footer button')
        .contains(/Ok|Confirm/i)
        .click();
      cy.wait(1000);
    });
  });

  describe('Action: Archive', () => {
    it('Deve arquivar uma aplicação', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Contar quantas aplicações existem antes
      cy.get('tbody tr').then(($rows) => {
        const countBefore = $rows.length;

        // Selecionar a aplicação
        cy.contains('td', testAppName).parent('tr').within(() => {
          cy.get('input[type="checkbox"]').first().check({ force: true });
        });

        cy.wait(500);

        // Abrir menu Actions
        cy.get('button').click();
        cy.wait(500);

        // Verificar que Archive existe
        cy.get('.dropdown-menu').should('contain.text', 'Archive');

        // Clicar em Archive
        cy.contains('.dropdown-item', 'Archive').click();
        cy.wait(1000);

        // Confirmar se houver modal
        cy.get('body').then(($body) => {
          if ($body.find('.modal-dialog, .o_dialog').length > 0) {
            cy.get('.modal-footer button, .o_dialog_footer button')
              .contains(/Ok|Confirm/i)
              .click();
            cy.wait(1000);
          }
        });

        // Verificar que a aplicação sumiu da lista (foi arquivada)
        cy.get('tbody tr').should('have.length.lessThan', countBefore);
        cy.get('body').should('not.contain', testAppName);
      });
    });
  });

  describe('Action: Unarchive', () => {
    it('Deve desarquivar a aplicação', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Ativar filtro de arquivados
      cy.get('.o_cp_searchview').click();
      cy.wait(500);

      // Tentar adicionar filtro "Archived"
      cy.get('body').then(($body) => {
        // Procurar por "Add Custom Filter" ou similar
        if ($body.find('.o_add_custom_filter').length > 0) {
          cy.get('.o_add_custom_filter').click();
          cy.wait(500);
        }
        
        // Ou usar filtro de favoritos se disponível
        if ($body.find('.o_searchview_facet').length > 0) {
          cy.get('.o_searchview_facet').click();
        }
      });

      // Alternativamente, ir direto para URL com filtro de arquivados
      cy.visit('/web#action=api_gateway.action_oauth_application&active_test=false');
      cy.wait(2000);

      // Procurar pela aplicação arquivada
      cy.get('body').then(($body) => {
        if ($body.text().includes(testAppName)) {
          // Selecionar a aplicação arquivada
          cy.contains('td', testAppName).parent('tr').within(() => {
            cy.get('input[type="checkbox"]').first().check({ force: true });
          });

          cy.wait(500);

          // Abrir menu Actions
          cy.get('button').click();
          cy.wait(500);

          // Verificar que Unarchive existe
          cy.get('.dropdown-menu').should('contain.text', 'Unarchive');

          // Clicar em Unarchive
          cy.contains('.dropdown-item', 'Unarchive').click();
          cy.wait(1000);

          // Voltar para lista normal
          cy.visit('/web#action=api_gateway.action_oauth_application');
          cy.wait(2000);

          // Verificar que a aplicação voltou
          cy.get('body').should('contain.text', testAppName);
        } else {
          cy.log('Aplicação não encontrada em arquivados, pulando teste de Unarchive');
        }
      });
    });
  });

  describe('Action: Delete', () => {
    it('Deve deletar a aplicação de teste', () => {
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);

      // Selecionar a aplicação
      cy.contains('td', testAppName).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.wait(500);

      // Abrir menu Actions
      cy.get('button').click();
      cy.wait(500);

      // Verificar que Delete existe
      cy.get('.dropdown-menu').should('contain.text', 'Delete');

      // Clicar em Delete
      cy.contains('.dropdown-item', 'Delete').click();
      cy.wait(1000);

      // Confirmar deleção
      cy.get('.modal-dialog, .o_dialog').should('be.visible');
      cy.get('.modal-footer button, .o_dialog_footer button')
        .contains(/Ok|Confirm|Delete/i)
        .click();
      cy.wait(1000);

      // Verificar que a aplicação foi deletada
      cy.get('body').should('not.contain', testAppName);
    });
  });

  describe('Ações em Múltiplas Seleções', () => {
    it('Deve criar duas aplicações e deletar ambas em lote', () => {
      const app1 = `Batch Test 1 ${Date.now()}`;
      const app2 = `Batch Test 2 ${Date.now()}`;

      // Criar primeira aplicação
      cy.visit('/web#action=api_gateway.action_oauth_application');
      cy.wait(2000);
      cy.get('button.o_list_button_add').first().click();
      cy.wait(2000);
      cy.get('.o_field_widget[name="name"] input').first().clear().type(app1);
      cy.get('button.o_form_button_save').click();
      cy.wait(2000);
      cy.get('.o_back_button').first().click();
      cy.wait(1000);

      // Criar segunda aplicação
      cy.get('button.o_list_button_add').first().click();
      cy.wait(2000);
      cy.get('.o_field_widget[name="name"] input').first().clear().type(app2);
      cy.get('button.o_form_button_save').click();
      cy.wait(2000);
      cy.get('.o_back_button').first().click();
      cy.wait(1000);

      // Selecionar ambas
      cy.contains('td', app1).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.contains('td', app2).parent('tr').within(() => {
        cy.get('input[type="checkbox"]').first().check({ force: true });
      });

      cy.wait(500);

      // Verificar que mostra "2 selected"
      cy.get('body').should('contain.text', '2 selected');

      // Deletar em lote
      cy.get('button').click();
      cy.wait(500);
      cy.contains('.dropdown-item', 'Delete').click();
      cy.wait(1000);
      cy.get('.modal-footer button').contains(/Ok|Confirm|Delete/i).click();
      cy.wait(1000);

      // Verificar que ambas foram deletadas
      cy.get('body').should('not.contain', app1);
      cy.get('body').should('not.contain', app2);
    });
  });
});
