/// <reference types="cypress" />

/**
 * E2E Test: Performance Domain - Dual Authentication Validation
 * 
 * Tests:
 * - T091: Reject request without bearer token
 * - T092: Reject request without session_id
 * - T093: Accept request with valid bearer + session
 * - T094: Reject request with different User-Agent (fingerprint validation)
 * 
 * Feature: 002-dual-auth-remaining-endpoints
 * Phase: 3 - E2E Tests
 */

describe('Performance Domain - Dual Authentication', () => {
  let accessToken;
  let sessionId;
  let testAgentId;
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

    // Get an agent ID for testing
    cy.then(() => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/agents?limit=1`,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
          'X-Openerp-Session-Id': sessionId,
          'User-Agent': testUserAgent,
          'Accept-Language': 'pt-BR'
        },
        failOnStatusCode: false
      }).then((response) => {
        if (response.status === 200 && response.body.result) {
          const agents = response.body.result.agents || response.body.result.items || [];
          if (agents.length > 0) {
            testAgentId = agents[0].id;
            cy.log(`✅ Using agent ID: ${testAgentId}`);
          } else {
            testAgentId = 1; // Fallback ID for testing
            cy.log(`⚠️ No agents found, using fallback ID: ${testAgentId}`);
          }
        } else {
          testAgentId = 1;
          cy.log(`⚠️ Could not fetch agents, using fallback ID: ${testAgentId}`);
        }
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

  describe('T091: Reject request without bearer token', () => {
    it('should return 401 when bearer token is missing', () => {
      cy.then(() => {
        cy.request({
          method: 'GET',
          url: `${baseUrl}/api/v1/agents/${testAgentId}/performance`,
          headers: {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': sessionId,
            'User-Agent': testUserAgent
            // ❌ Missing Authorization header
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Authorization header is required');
          
          cy.log('✅ T091 PASS: Request rejected without bearer token');
        });
      });
    });
  });

  describe('T092: Reject request without session_id', () => {
    it('should return 401 when session_id is missing', () => {
      cy.then(() => {
        cy.request({
          method: 'GET',
          url: `${baseUrl}/api/v1/agents/${testAgentId}/performance`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'User-Agent': testUserAgent
            // ❌ Missing X-Openerp-Session-Id header
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Session required');
          
          cy.log('✅ T092 PASS: Request rejected without session_id');
        });
      });
    });
  });

  describe('T093: Accept request with valid bearer + session', () => {
    it('should return 200 with valid bearer token and session_id', () => {
      cy.then(() => {
        cy.request({
          method: 'GET',
          url: `${baseUrl}/api/v1/agents/${testAgentId}/performance`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'X-Openerp-Session-Id': sessionId,
            'User-Agent': testUserAgent,
            'Accept-Language': 'pt-BR'
          },
          failOnStatusCode: false
        }).then((response) => {
          // Accept 200 (found) or 404 (not found - but auth passed)
          expect([200, 404]).to.include(response.status);
          
          if (response.status === 200) {
            expect(response.body).to.have.property('result');
            cy.log('✅ T093 PASS: Valid request accepted (performance metrics found)');
          } else {
            expect(response.body).to.have.property('error');
            cy.log('✅ T093 PASS: Auth succeeded (agent not found is expected)');
          }
        });
      });
    });
  });

  describe('T094: Reject request with different User-Agent', () => {
    it('should return 401 when User-Agent differs from login', () => {
      cy.then(() => {
        cy.request({
          method: 'GET',
          url: `${baseUrl}/api/v1/agents/${testAgentId}/performance`,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
            'X-Openerp-Session-Id': sessionId,
            'User-Agent': differentUserAgent,  // ❌ Different from login
            'Accept-Language': 'pt-BR'
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(401);
          expect(response.body).to.have.property('error');
          expect(response.body.error.message).to.include('Session validation failed');
          
          cy.log('✅ T094 PASS: Fingerprint validation rejected different User-Agent');
        });
      });
    });
  });
});
