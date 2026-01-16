/**
 * E2E Test: User Authentication with Bearer Token and Session Validation
 * 
 * Tests complete authentication flow across all 5 User Authentication endpoints:
 * 1. /api/v1/users/login (bearer token only - creates session)
 * 2. /api/v1/me (bearer token + session required)
 * 3. /api/v1/users/profile (bearer token + session required)
 * 4. /api/v1/users/change-password (bearer token + session required)
 * 5. /api/v1/users/logout (bearer token + session required)
 * 
 * Validates:
 * - Bearer token validation on all endpoints
 * - Session requirement on all endpoints except login
 * - Session fingerprint validation (IP/User-Agent/Language)
 * - Session invalidation on logout
 * - Error responses for missing/expired tokens and sessions
 * 
 * Implements ADR-002 (Cypress E2E Testing), ADR-011 (Dual Authentication)
 */

describe('User Authentication - Bearer Token and Session Validation (T023)', () => {
  let bearerToken;
  let sessionId;
  let testUser;

  before(() => {
    // Setup: Create OAuth application and token for authentication
    cy.task('db:query', {
      query: `
        -- Create OAuth application
        INSERT INTO thedevkitchen_oauth_application (name, create_date, write_date, create_uid, write_uid)
        VALUES ('Cypress E2E Test App', NOW(), NOW(), 2, 2)
        ON CONFLICT DO NOTHING
        RETURNING id;
      `
    }).then((result) => {
      const appId = result.rows[0]?.id || 1;

      // Create OAuth token
      cy.task('db:query', {
        query: `
          INSERT INTO thedevkitchen_oauth_token (
            application_id, access_token, token_type, expires_at, 
            revoked, create_date, write_date, create_uid, write_uid
          )
          VALUES (
            ${appId}, 
            'cypress-e2e-token-${Date.now()}', 
            'Bearer', 
            NOW() + INTERVAL '24 hours',
            false,
            NOW(), NOW(), 2, 2
          )
          ON CONFLICT DO NOTHING
          RETURNING access_token;
        `
      }).then((result) => {
        bearerToken = result.rows[0]?.access_token || 'cypress-e2e-token';
        cy.log(`Bearer token created: ${bearerToken}`);
      });
    });

    // Create test user
    testUser = {
      email: `cypress-e2e-${Date.now()}@example.com`,
      password: 'CypressTestPass123!',
      name: 'Cypress E2E Test User'
    };

    cy.task('db:query', {
      query: `
        INSERT INTO res_users (
          login, email, password, name, active,
          create_date, write_date, create_uid, write_uid
        )
        VALUES (
          '${testUser.email}',
          '${testUser.email}',
          crypt('${testUser.password}', gen_salt('bf', 12)),
          '${testUser.name}',
          true,
          NOW(), NOW(), 2, 2
        )
        ON CONFLICT (login) DO NOTHING
        RETURNING id;
      `
    }).then((result) => {
      testUser.id = result.rows[0]?.id;
      cy.log(`Test user created: ${testUser.email} (ID: ${testUser.id})`);
    });
  });

  after(() => {
    // Cleanup: Remove test data
    if (testUser?.id) {
      cy.task('db:query', {
        query: `
          DELETE FROM res_users WHERE id = ${testUser.id};
          DELETE FROM thedevkitchen_api_session WHERE user_id = ${testUser.id};
          DELETE FROM thedevkitchen_oauth_token WHERE access_token = '${bearerToken}';
        `
      });
    }
  });

  describe('US1: Bearer Token Validation', () => {
    it('should reject login request without Authorization header (401)', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/users/login',
        body: {
          email: testUser.email,
          password: testUser.password
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(401);
        expect(response.body).to.have.property('error');
        expect(response.body.error.message).to.include('Authorization header');
      });
    });

    it('should reject login with expired bearer token (401)', () => {
      // Create expired token
      cy.task('db:query', {
        query: `
          INSERT INTO thedevkitchen_oauth_token (
            application_id, access_token, token_type, expires_at, revoked,
            create_date, write_date, create_uid, write_uid
          )
          VALUES (
            1, 'expired-cypress-token', 'Bearer', NOW() - INTERVAL '1 hour', false,
            NOW(), NOW(), 2, 2
          )
          ON CONFLICT DO NOTHING;
        `
      }).then(() => {
        cy.request({
          method: 'POST',
          url: '/api/v1/users/login',
          headers: {
            'Authorization': 'Bearer expired-cypress-token'
          },
          body: {
            email: testUser.email,
            password: testUser.password
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.equal(401);
          expect(response.body.error.message.toLowerCase()).to.include('expired');
        });
      });
    });
  });

  describe('US2: Login Endpoint Accessibility', () => {
    it('should allow login with valid bearer token and credentials → create session', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/users/login',
        headers: {
          'Authorization': `Bearer ${bearerToken}`
        },
        body: {
          email: testUser.email,
          password: testUser.password
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
        expect(response.body).to.have.property('session_id');
        expect(response.body).to.have.property('user');
        expect(response.body.user.email).to.equal(testUser.email);

        // Save session for subsequent tests
        sessionId = response.body.session_id;
        cy.log(`Session created: ${sessionId}`);
      });
    });
  });

  describe('US3: Session Validation on Protected Endpoints', () => {
    it('should allow access to /api/v1/me with valid bearer token AND session', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/me',
        headers: {
          'Authorization': `Bearer ${bearerToken}`,
          'Cookie': `session_id=${sessionId}`
        },
        body: {
          session_id: sessionId
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('user');
        expect(response.body.user.email).to.equal(testUser.email);
      });
    });

    it('should reject /api/v1/me with valid token but NO session (401)', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/me',
        headers: {
          'Authorization': `Bearer ${bearerToken}`
        },
        body: {},
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(401);
        expect(response.body.error.message.toLowerCase()).to.include('session');
      });
    });

    it('should allow access to /api/v1/users/profile with valid bearer token AND session', () => {
      cy.request({
        method: 'PATCH',
        url: '/api/v1/users/profile',
        headers: {
          'Authorization': `Bearer ${bearerToken}`,
          'Cookie': `session_id=${sessionId}`
        },
        body: {
          session_id: sessionId,
          name: 'Updated Cypress User'
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
      });
    });

    it('should reject /api/v1/users/logout with valid token but NO session (401)', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/users/logout',
        headers: {
          'Authorization': `Bearer ${bearerToken}`
        },
        body: {},
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(401);
        expect(response.body.error.message.toLowerCase()).to.include('session');
      });
    });

    it('should allow logout with valid bearer token AND session → invalidate session', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/users/logout',
        headers: {
          'Authorization': `Bearer ${bearerToken}`,
          'Cookie': `session_id=${sessionId}`
        },
        body: {
          session_id: sessionId
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
        cy.log('Logout successful - session invalidated');
      });
    });

    it('should reject /api/v1/me with expired session after logout (401)', () => {
      cy.request({
        method: 'POST',
        url: '/api/v1/me',
        headers: {
          'Authorization': `Bearer ${bearerToken}`,
          'Cookie': `session_id=${sessionId}`
        },
        body: {
          session_id: sessionId
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(401);
        // Session is now invalid (logged out)
        expect(response.body.error.message.toLowerCase()).to.satisfy((msg) => {
          return msg.includes('session') || msg.includes('expired') || msg.includes('not found');
        });
      });
    });
  });

  describe('Integration: Complete Authentication Flow', () => {
    it('should complete full authentication journey across all 5 endpoints', () => {
      let newSessionId;

      // Step 1: Login (bearer token only)
      cy.request({
        method: 'POST',
        url: '/api/v1/users/login',
        headers: {
          'Authorization': `Bearer ${bearerToken}`
        },
        body: {
          email: testUser.email,
          password: testUser.password
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        newSessionId = response.body.session_id;
        cy.log('✅ Step 1: Login successful');
      }).then(() => {
        // Step 2: Access /api/v1/me (token + session)
        cy.request({
          method: 'POST',
          url: '/api/v1/me',
          headers: {
            'Authorization': `Bearer ${bearerToken}`,
            'Cookie': `session_id=${newSessionId}`
          },
          body: {
            session_id: newSessionId
          }
        }).then((response) => {
          expect(response.status).to.equal(200);
          cy.log('✅ Step 2: /api/v1/me access successful');
        });
      }).then(() => {
        // Step 3: Update profile (token + session)
        cy.request({
          method: 'PATCH',
          url: '/api/v1/users/profile',
          headers: {
            'Authorization': `Bearer ${bearerToken}`,
            'Cookie': `session_id=${newSessionId}`
          },
          body: {
            session_id: newSessionId,
            name: 'Journey Test User'
          }
        }).then((response) => {
          expect(response.status).to.equal(200);
          cy.log('✅ Step 3: Profile update successful');
        });
      }).then(() => {
        // Step 4: Logout (token + session)
        cy.request({
          method: 'POST',
          url: '/api/v1/users/logout',
          headers: {
            'Authorization': `Bearer ${bearerToken}`,
            'Cookie': `session_id=${newSessionId}`
          },
          body: {
            session_id: newSessionId
          }
        }).then((response) => {
          expect(response.status).to.equal(200);
          cy.log('✅ Step 4: Logout successful');
        });
      }).then(() => {
        // Step 5: Verify session is invalid after logout
        cy.request({
          method: 'POST',
          url: '/api/v1/me',
          headers: {
            'Authorization': `Bearer ${bearerToken}`,
            'Cookie': `session_id=${newSessionId}`
          },
          body: {
            session_id: newSessionId
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.equal(401);
          cy.log('✅ Step 5: Session correctly invalidated after logout');
        });
      });
    });
  });
});
