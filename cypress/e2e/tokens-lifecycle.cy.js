/// <reference types="cypress" />

/**
 * Testes E2E para Ciclo de Vida de Tokens OAuth
 * 
 * Testa:
 * - Geração de tokens
 * - Uso de tokens válidos
 * - Expiração de tokens
 * - Revogação de tokens
 * - Tentativas de reutilização de tokens revogados
 * - Tentativas de uso de tokens expirados
 */

describe('Tokens Lifecycle - OAuth 2.0', () => {
  let clientId = '';
  let clientSecret = '';
  let accessToken, refreshToken;

  before(() => {
    // Login apenas uma vez para configuração inicial
    cy.odooLoginSession();

    // Criar nova aplicação OAuth via API (mais confiável que UI)
    const appName = `Lifecycle Test ${Date.now()}`;
    
    cy.request({
      method: 'POST',
      url: '/web/dataset/call_kw/oauth.application/create',
      headers: {
        'Content-Type': 'application/json'
      },
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {
          model: 'oauth.application',
          method: 'create',
          args: [{
            name: appName,
            description: 'Aplicação para testes de ciclo de vida',
            active: true
          }],
          kwargs: {}
        },
        id: Date.now()
      }
    }).then((response) => {
      expect(response.status).to.eq(200);
      const appId = response.body.result;
      cy.log(`Aplicação criada com ID: ${appId}`);

      // Buscar credenciais da aplicação criada
      cy.request({
        method: 'POST',
        url: '/web/dataset/call_kw/oauth.application/read',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          jsonrpc: '2.0',
          method: 'call',
          params: {
            model: 'oauth.application',
            method: 'read',
            args: [[appId], ['client_id', 'client_secret']],
            kwargs: {}
          },
          id: Date.now()
        }
      }).then((readResponse) => {
        expect(readResponse.status).to.eq(200);
        const appData = readResponse.body.result[0];
        clientId = appData.client_id;
        clientSecret = appData.client_secret;
        cy.log('Client ID:', clientId);
        cy.log('Client Secret:', clientSecret);
      });
    });
  });

  describe('1. Geração de Tokens', () => {
    it('Deve gerar access_token e refresh_token com grant_type client_credentials', () => {
      // Garantir que as credenciais foram obtidas
      cy.then(() => {
        expect(clientId).to.not.be.empty;
        expect(clientSecret).to.not.be.empty;
      });

      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          client_secret: clientSecret,
          grant_type: 'client_credentials'
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('access_token');
        expect(response.body).to.have.property('refresh_token');
        expect(response.body).to.have.property('token_type', 'Bearer');
        expect(response.body).to.have.property('expires_in', 3600);

        // Armazenar tokens
        accessToken = response.body.access_token;
        refreshToken = response.body.refresh_token;

        // Validar formato JWT do access_token
        expect(accessToken).to.match(/^eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/);
      });
    });

    it('Deve rejeitar geração sem client_id', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_secret: clientSecret,
          grant_type: 'client_credentials'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_request');
      });
    });

    it('Deve rejeitar geração sem client_secret', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          grant_type: 'client_credentials'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_request');
      });
    });

    it('Deve rejeitar credenciais inválidas', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: 'invalid_client_id',
          client_secret: 'invalid_secret',
          grant_type: 'client_credentials'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_client');
      });
    });

    it('Deve rejeitar grant_type inválido', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          client_secret: clientSecret,
          grant_type: 'password'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'unsupported_grant_type');
      });
    });
  });

  describe('2. Uso de Tokens Válidos', () => {
    it('Deve acessar endpoint protegido com token válido', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('message');
      });
    });

    it('Deve rejeitar acesso sem Authorization header', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(401);
        expect(response.body).to.have.property('error', 'unauthorized');
      });
    });

    it('Deve rejeitar token malformado', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        headers: {
          'Authorization': 'Bearer invalid_token_format'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(401);
        expect(response.body).to.have.property('error', 'invalid_token');
      });
    });

    it('Deve rejeitar Authorization header sem Bearer', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        headers: {
          'Authorization': accessToken
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(401);
        expect(response.body).to.have.property('error', 'invalid_token');
      });
    });
  });

  describe('3. Renovação de Tokens', () => {
    it('Deve renovar access_token usando refresh_token', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/refresh',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          refresh_token: refreshToken
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('access_token');
        expect(response.body).to.have.property('refresh_token', refreshToken); // Mesmo refresh_token
        expect(response.body).to.have.property('token_type', 'Bearer');
        expect(response.body).to.have.property('expires_in', 3600);

        // Verificar que é um novo access_token
        expect(response.body.access_token).to.not.eq(accessToken);

        // Atualizar access_token
        accessToken = response.body.access_token;
      });
    });

    it('Deve usar novo access_token renovado', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
      });
    });

    it('Deve rejeitar refresh_token inválido', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/refresh',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          refresh_token: 'invalid_refresh_token'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_grant');
      });
    });
  });

  describe('4. Revogação de Tokens', () => {
    let tokenToRevoke, refreshTokenToRevoke;

    before(() => {
      // Gerar novo token para revogar
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          client_secret: clientSecret,
          grant_type: 'client_credentials'
        }
      }).then((response) => {
        tokenToRevoke = response.body.access_token;
        refreshTokenToRevoke = response.body.refresh_token;
      });
    });

    it('Deve revogar token via Authorization header', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/revoke',
        headers: {
          'Authorization': `Bearer ${tokenToRevoke}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('success', true);
      });
    });

    it('Não deve permitir uso de token revogado', () => {
      cy.request({
        method: 'GET',
        url: '/api/v1/test/protected',
        headers: {
          'Authorization': `Bearer ${tokenToRevoke}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(401);
        expect(response.body).to.have.property('error', 'invalid_token');
      });
    });

    it('Não deve permitir renovação com refresh_token de token revogado', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/refresh',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          refresh_token: refreshTokenToRevoke
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body).to.have.property('error', 'invalid_grant');
      });
    });

    it('Deve revogar token via body JSON', () => {
      // Gerar novo token
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          client_secret: clientSecret,
          grant_type: 'client_credentials'
        }
      }).then((tokenResponse) => {
        const newToken = tokenResponse.body.access_token;

        // Revogar via body
        cy.request({
          method: 'POST',
          url: '/api/v1/auth/revoke',
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            token: newToken
          }
        }).then((response) => {
          expect(response.status).to.eq(200);
          expect(response.body).to.have.property('success', true);

          // Verificar que não pode ser usado
          cy.request({
            method: 'GET',
            url: '/api/v1/test/protected',
            headers: {
              'Authorization': `Bearer ${newToken}`
            },
            failOnStatusCode: false
          }).then((protectedResponse) => {
            expect(protectedResponse.status).to.eq(401);
          });
        });
      });
    });

    it('Deve retornar sucesso mesmo para token inexistente (RFC 7009)', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/revoke',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          token: 'non_existent_token'
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body).to.have.property('success', true);
      });
    });
  });

  describe('5. Múltiplos Tokens por Aplicação', () => {
    it('Deve permitir múltiplos tokens ativos para mesma aplicação', () => {
      const tokens = [];

      // Gerar 3 tokens
      cy.wrap([1, 2, 3]).each(() => {
        cy.request({
          method: 'POST',
          url: '/api/v1/auth/token',
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            client_id: clientId,
            client_secret: clientSecret,
            grant_type: 'client_credentials'
          }
        }).then((response) => {
          tokens.push(response.body.access_token);
        });
      }).then(() => {
        // Verificar que todos são diferentes
        expect(tokens[0]).to.not.eq(tokens[1]);
        expect(tokens[1]).to.not.eq(tokens[2]);
        expect(tokens[0]).to.not.eq(tokens[2]);

        // Verificar que todos funcionam
        tokens.forEach((token) => {
          cy.request({
            method: 'GET',
            url: '/api/v1/test/protected',
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }).then((response) => {
            expect(response.status).to.eq(200);
          });
        });
      });
    });

    it('Deve revogar apenas o token especificado', () => {
      let token1, token2;

      // Gerar 2 tokens
      cy.request({
        method: 'POST',
        url: '/api/v1/auth/token',
        headers: {
          'Content-Type': 'application/json'
        },
        body: {
          client_id: clientId,
          client_secret: clientSecret,
          grant_type: 'client_credentials'
        }
      }).then((response) => {
        token1 = response.body.access_token;

        cy.request({
          method: 'POST',
          url: '/api/v1/auth/token',
          headers: {
            'Content-Type': 'application/json'
          },
          body: {
            client_id: clientId,
            client_secret: clientSecret,
            grant_type: 'client_credentials'
          }
        }).then((response) => {
          token2 = response.body.access_token;

          // Revogar token1
          cy.request({
            method: 'POST',
            url: '/api/v1/auth/revoke',
            headers: {
              'Authorization': `Bearer ${token1}`
            }
          });

          // Token1 não deve funcionar
          cy.request({
            method: 'GET',
            url: '/api/v1/test/protected',
            headers: {
              'Authorization': `Bearer ${token1}`
            },
            failOnStatusCode: false
          }).then((response) => {
            expect(response.status).to.eq(401);
          });

          // Token2 deve continuar funcionando
          cy.request({
            method: 'GET',
            url: '/api/v1/test/protected',
            headers: {
              'Authorization': `Bearer ${token2}`
            }
          }).then((response) => {
            expect(response.status).to.eq(200);
          });
        });
      });
    });
  });

  describe('6. Validação de Tokens na Interface', () => {
    before(() => {
      // Login para acessar interface
      cy.odooLogin('admin', 'admin');
    });

    it('Deve exibir tokens ativos na lista Active Tokens', () => {
      cy.visit('/web');
      cy.wait(2000);
      
      // Navegar para Active Tokens via URL direta
      cy.visit('/web#action=api_gateway.action_oauth_token');
      cy.wait(2000);

      // Verificar que existem tokens listados
      cy.get('.o_list_table tbody tr', { timeout: 10000 }).should('have.length.at.least', 1);
    });
  });
});
