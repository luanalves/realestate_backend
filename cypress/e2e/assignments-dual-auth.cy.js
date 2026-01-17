/// <reference types="cypress" />

/**
 * E2E Test: Assignments Domain - Dual Authentication Validation
 * 
 * Tests:
 * - T081: Reject request without bearer token
 * - T082: Reject request without session_id
 * - T083: Accept request with valid bearer + session
 * - T084: Reject request with different User-Agent (fingerprint validation)
 * 
 * Feature: 002-dual-auth-remaining-endpoints
 * Phase: 3 - E2E Tests
 */

describe('Assignments Domain - Dual Authentication', () => {
  let accessToken;
  let sessionId;
  const testUserAgent = 'CypressTest/1.0 (E2E Testing)';
  const differentUserAgent = 'DifferentClient/2.0 (Attack Simulation)';
  
  const baseUrl = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069';
  const clientId = Cypress.env('OAUTH_CLIENT_ID') || 'client_EEQix5KVT6JsSUARsdUGnw';
  const clientSecret = Cypress.env('OAUTH_CLIENT_SECRET') || 'Xu5l7zL9Je6HKcx6EbJJiLwy9JAA0QHozcDE37TGjjC5skPEWfkigZPouqTWzDBG';
  const testEmail = Cypress.env('TEST_USER_A_EMAIL') || 'joao@imobiliaria.com';
  const testPassword = Cypress.env('TEST_USER_A_PASSWORD') || 'test123';

  before(() => {
    cy.log('🔐 Phase 1: Get OAuth Token');
    
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/auth/token`,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': testUserAgent
      },
      body: {
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret
      }
    }).then((response) => {
      expect(response.status).to.eq(200);
      accessToken = response.body.access_token;
      cy.log(`✅ OAuth token obtained`);
    });

    cy.log('👤 Phase 2: User Login (Get Session)');
    
    cy.then(() => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/users/login`,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
          'User-Agent': testUserAgent,
          'Accept-Language': 'pt-BR'
        },
        body: {
          jsonrpc: '2.0',
          method: 'call',
          params: {
            email: testEmail,
            password: testPassword
          }
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        sessionId = response.body.result.session_id;
        cy.log(`✅ Session obtained`);
        
        expect(sessionId.length).to.be.gte(60);
        expect(sessionId.length).to.be.lte(100);
      });
    });
  });

  after(() => {
    cy.log('🚪 Cleanup: Logging out');
    
    cy.then(() => {
      if (sessionId && accessToken) {
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/users/logout`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'User-Agent': testUserAgent
          },
          body: {
            jsonrpc: '2.0',
            method: 'call',
            params: {
              session_id: sessionId
            }
          },
          failOnStatusCode: false
        });
      }
    });
  });

  describe('T081: Reject request without bearer token', () => {
    it('should return 401 when bearer token is missing', () => {
      cy.then(() => {
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/assignments`,
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': testUserAgent
            // ❌ Missing Authorization header
          },
          body: {
            jsonrpc: '2.0',
            method: 'call',
            params: {
              session_id: sessionId,
              agent_id: 1,
              property_id: 1
            }
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Authorization header is required');
          
          cy.log('✅ T081 PASS: Request rejected without bearer token');
        });
      });
    });
  });

  describe('T082: Reject request without session_id', () => {
    it('should return 401 when session_id is missing', () => {
      cy.then(() => {
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/assignments`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'User-Agent': testUserAgent
          },
          body: {
            jsonrpc: '2.0',
            method: 'call',
            params: {
              // ❌ Missing session_id
              agent_id: 1,
              property_id: 1
            }
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Session required');
          
          cy.log('✅ T082 PASS: Request rejected without session_id');
        });
      });
    });
  });

  describe('T083: Accept request with valid bearer + session', () => {
    it('should authenticate with valid bearer token and session_id', () => {
      cy.then(() => {
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/assignments`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'User-Agent': testUserAgent,
            'Accept-Language': 'pt-BR'
          },
          body: {
            jsonrpc: '2.0',
            method: 'call',
            params: {
              session_id: sessionId,
              agent_id: 1,
              property_id: 1
            }
          },
          failOnStatusCode: false
        }).then((response) => {
          // Accept 200/201 (success) or 400/404 (business logic error - but auth passed)
          expect([200, 201, 400, 404, 422]).to.include(response.status);
          
          if ([200, 201].includes(response.status)) {
            expect(response.body).to.have.property('result');
            cy.log('✅ T083 PASS: Valid request accepted (assignment created)');
          } else {
            expect(response.body).to.have.property('error');
            cy.log('✅ T083 PASS: Auth succeeded (business error is expected)');
          }
        });
      });
    });
  });

  describe('T084: Reject request with different User-Agent', () => {
    it('should return 401 when User-Agent differs from login', () => {
      cy.then(() => {
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/assignments`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'User-Agent': differentUserAgent,  // ❌ Different from login
            'Accept-Language': 'pt-BR'
          },
          body: {
            jsonrpc: '2.0',
            method: 'call',
            params: {
              session_id: sessionId,
              agent_id: 1,
              property_id: 1
            }
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Session validation failed');
          
          cy.log('✅ T084 PASS: Fingerprint validation rejected different User-Agent');
        });
      });
    });
  });
});
