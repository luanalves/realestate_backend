/// <reference types="cypress" />

describe('API Gateway - Integração Completa (Front + API)', () => {
  let clientId = '';
  let clientSecret = '';

  before(() => {
    // Login usando comando customizado
    cy.odooLoginSession();

    // Criar nova OAuth Application
    cy.visit('/web#action=api_gateway.action_oauth_application&model=oauth.application&view_type=list');
    cy.wait(2000);

    cy.get('button.o_list_button_add, button.o-kanban-button-new').first().click();
    cy.wait(1000);

    const appName = `Cypress Integration Test ${Date.now()}`;
    cy.get('input[name="name"]').clear().type(appName);
    cy.get('textarea[name="description"]').clear().type('Aplicação para teste de integração completo');
    cy.get('button.o_form_button_save').click();
    cy.wait(2000);

    // Capturar Client ID e Secret
    cy.get('input[name="client_id"]').invoke('val').then((val) => {
      clientId = val;
      cy.log('Client ID:', clientId);
    });

    cy.get('input[name="client_secret"]').invoke('val').then((val) => {
      clientSecret = val;
      cy.log('Client Secret:', clientSecret);
    });
  });

  it('1. Deve obter access token via API OAuth 2.0', () => {
    cy.then(() => {
      expect(clientId).to.not.be.empty;
      expect(clientSecret).to.not.be.empty;
    });

    // Fazer requisição OAuth 2.0 (Client Credentials)
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
      },
      failOnStatusCode: false,
    }).then((response) => {
      cy.log('Response Status:', response.status);
      cy.log('Response Body:', JSON.stringify(response.body));

      // Verificar resposta OAuth 2.0
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('access_token');
      expect(response.body).to.have.property('token_type', 'Bearer');
      expect(response.body).to.have.property('expires_in');
      expect(response.body).to.have.property('refresh_token');

      // Salvar token para próximos testes
      cy.wrap(response.body.access_token).as('accessToken');
      cy.wrap(response.body.refresh_token).as('refreshToken');
    });
  });

  it('2. Deve validar token gerado no frontend', function () {
    // Aguardar um pouco para garantir que o token foi salvo no banco
    cy.wait(2000);

    // Navegar para Active Tokens
    cy.visit('/web#action=api_gateway.action_oauth_token&model=oauth.token&view_type=list');
    cy.wait(2000);

    // Verificar que token aparece na lista
    cy.get('table.o_list_table tbody tr').should('have.length.greaterThan', 0);

    // Verificar que access token está visível (parcialmente)
    cy.get('body').should('contain', this.accessToken.substring(0, 20));
  });

  it('3. Deve validar detalhes do token no frontend', function () {
    // Navegar para tokens
    cy.visit(`/web#action=api_gateway.action_oauth_token&model=oauth.token&view_type=list`);
    cy.wait(2000);

    // Abrir primeiro token
    cy.get('tr.o_data_row').first().click();
    cy.wait(1000);

    // Verificar campos
    cy.get('body').should('contain', 'Bearer');
    cy.get('.o_field_widget[name="expires_at"]').should('exist');
    cy.get('.o_field_widget[name="is_expired"]').should('exist');
  });

  it('4. Deve revogar token via API', function () {
    // Revogar token
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/revoke`,
      form: true,
      body: {
        token: this.accessToken,
      },
      failOnStatusCode: false,
    }).then((response) => {
      cy.log('Revoke Response:', JSON.stringify(response.body));

      // RFC 7009: Always return success
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('success', true);
    });
  });

  it('5. Deve verificar token revogado no frontend', function () {
    cy.wait(2000);

    // Login
    cy.visit(`/web/login`);
    cy.get('input[name="login"]').clear().type(username);
    cy.get('input[name="password"]').clear().type(password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/web');
    cy.wait(2000);

    // Navegar para tokens
    cy.visit(`/web#action=api_gateway.action_oauth_token&model=oauth.token&view_type=list`);
    cy.wait(2000);

    // Filtrar tokens revogados
    cy.get('body').then($body => {
      // Procurar por linhas em vermelho (decoration-danger)
      const revokedRows = $body.find('tr.text-danger');
      if (revokedRows.length > 0) {
        cy.log(`Encontrados ${revokedRows.length} tokens revogados`);
      }
    });
  });

  it('6. Deve testar regeneração de secret', () => {
    // Login
    cy.visit(`/web/login`);
    cy.get('input[name="login"]').clear().type(username);
    cy.get('input[name="password"]').clear().type(password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/web');
    cy.wait(2000);

    // Navegar para aplicação criada
    cy.visit(`/web#action=api_gateway.action_oauth_application&model=oauth.application&view_type=list`);
    cy.wait(2000);

    // Filtrar pela aplicação de teste
    cy.get('tr.o_data_row').contains('Cypress Integration Test').click();
    cy.wait(1000);

    // Capturar secret antigo
    cy.get('input[name="client_secret"]').invoke('val').as('oldSecret');

    // Clicar em Regenerate Secret
    cy.get('button').contains('Regenerate Secret').click();
    cy.wait(500);

    // Confirmar
    cy.get('.modal-footer button.btn-primary, .modal-footer button').contains('OK').click();
    cy.wait(2000);

    // Verificar que secret mudou
    cy.get('input[name="client_secret"]').invoke('val').then(function (newSecret) {
      expect(newSecret).to.not.eq(this.oldSecret);
      cy.log('Secret regenerado com sucesso');
    });
  });

  it('7. Deve falhar ao usar secret antigo', function () {
    // Tentar obter token com secret antigo (deve falhar)
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret, // Secret antigo
      },
      failOnStatusCode: false,
    }).then((response) => {
      cy.log('Response:', JSON.stringify(response.body));

      // Deve falhar com 400 ou 401
      expect(response.status).to.be.oneOf([400, 401]);
      expect(response.body).to.have.property('error');
    });
  });

  it('8. Deve validar grant_type inválido', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'authorization_code', // Não suportado
        client_id: clientId,
        client_secret: clientSecret,
      },
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.eq(400);
      expect(response.body).to.have.property('error', 'unsupported_grant_type');
    });
  });

  it('9. Deve validar client_id ausente', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_secret: clientSecret,
      },
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.eq(400);
      expect(response.body).to.have.property('error', 'invalid_request');
    });
  });

  it('10. Deve validar client_secret ausente', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_id: clientId,
      },
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.eq(400);
      expect(response.body).to.have.property('error', 'invalid_request');
    });
  });

  it('11. Deve validar credenciais inválidas', () => {
    cy.request({
      method: 'POST',
      url: `/api/v1/auth/token`,
      form: true,
      body: {
        grant_type: 'client_credentials',
        client_id: 'invalid_id',
        client_secret: 'invalid_secret',
      },
      failOnStatusCode: false,
    }).then((response) => {
      expect(response.status).to.eq(400);
      expect(response.body).to.have.property('error', 'invalid_client');
    });
  });

  it('12. Deve validar aplicação desativada', () => {
    // Login
    cy.visit(`/web/login`);
    cy.get('input[name="login"]').clear().type(username);
    cy.get('input[name="password"]').clear().type(password);
    cy.get('button[type="submit"]').click();
    cy.url().should('include', '/web');
    cy.wait(2000);

    // Navegar para aplicação
    cy.visit(`/web#action=api_gateway.action_oauth_application&model=oauth.application&view_type=list`);
    cy.wait(2000);

    cy.get('tr.o_data_row').contains('Cypress Integration Test').click();
    cy.wait(1000);

    // Capturar novo secret
    cy.get('input[name="client_secret"]').invoke('val').then((newSecret) => {
      // Desativar aplicação
      cy.get('button.o_form_button_edit').click();
      cy.wait(500);
      cy.get('input[name="active"]').click();
      cy.get('button.o_form_button_save').click();
      cy.wait(2000);

      // Tentar obter token (deve falhar)
      cy.request({
        method: 'POST',
        url: `/api/v1/auth/token`,
        form: true,
        body: {
          grant_type: 'client_credentials',
          client_id: clientId,
          client_secret: newSecret,
        },
        failOnStatusCode: false,
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_client');
      });
    });
  });
});
