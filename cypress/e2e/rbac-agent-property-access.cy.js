/**
 * E2E Test: Agent Profile - Property Access Control
 * 
 * Tests FR-031 to FR-040 (Agent profile requirements)
 * 
 * Scenarios:
 * 1. Agent creates a property (auto-assigned)
 * 2. Agent sees only own properties
 * 3. Agent cannot see other agents' properties (isolation)
 * 4. Agent can update own properties
 * 5. Agent sees properties in assignments
 */

describe('RBAC: Agent Profile - Property Access Control', () => {
  let agentAAuthToken;
  let agentBAuthToken;
  let companyId;
  let agentAId;
  let agentBId;

  before(() => {
    // Setup: Create company and 2 agent users
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      body: {
        name: 'Test Company for Agents',
        cnpj: '11.111.111/0001-11',
        creci: 'CRECI-SP 11111'
      }
    }).then((response) => {
      companyId = response.body.id;

      // Create Agent A user
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Agent A User',
          login: 'agent_a@e2e.test',
          email: 'agent_a@e2e.test',
          password: 'agent123',
          groups_id: [{ id: 'quicksol_estate.group_real_estate_agent' }],
          estate_company_ids: [companyId]
        }
      }).then((userResponse) => {
        // Create agent record for Agent A
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/agents',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            name: 'Agent A',
            creci: 'CRECI-SP 99999',
            user_id: userResponse.body.id,
            company_ids: [companyId]
          }
        }).then((agentResponse) => {
          agentAId = agentResponse.body.id;

          // Get OAuth token for Agent A
          cy.request({
            method: 'POST',
            url: 'http://localhost:8069/api/v1/oauth/token',
            form: true,
            body: {
              grant_type: 'password',
              username: 'agent_a@e2e.test',
              password: 'agent123'
            }
          }).then((tokenResponse) => {
            agentAAuthToken = tokenResponse.body.access_token;
          });
        });
      });

      // Create Agent B user (same company, different agent)
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Agent B User',
          login: 'agent_b@e2e.test',
          email: 'agent_b@e2e.test',
          password: 'agent123',
          groups_id: [{ id: 'quicksol_estate.group_real_estate_agent' }],
          estate_company_ids: [companyId]
        }
      }).then((userResponse) => {
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/agents',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            name: 'Agent B',
            creci: 'CRECI-SP 88888',
            user_id: userResponse.body.id,
            company_ids: [companyId]
          }
        }).then((agentResponse) => {
          agentBId = agentResponse.body.id;

          cy.request({
            method: 'POST',
            url: 'http://localhost:8069/api/v1/oauth/token',
            form: true,
            body: {
              grant_type: 'password',
              username: 'agent_b@e2e.test',
              password: 'agent123'
            }
          }).then((tokenResponse) => {
            agentBAuthToken = tokenResponse.body.access_token;
          });
        });
      });
    });
  });

  context('T065: Agent Creates and Manages Properties', () => {
    it('should allow agent to create a property', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        body: {
          name: 'Property by Agent A',
          agent_id: agentAId,
          price: 500000,
          company_ids: [companyId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.agent_id).to.eq(agentAId);
      });
    });

    it('should allow agent to update own property', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        body: {
          name: 'Property A1',
          agent_id: agentAId,
          price: 300000,
          company_ids: [companyId]
        }
      }).then((createResponse) => {
        const propertyId = createResponse.body.id;

        cy.request({
          method: 'PATCH',
          url: `http://localhost:8069/api/v1/properties/${propertyId}`,
          headers: {
            'Authorization': `Bearer ${agentAAuthToken}`
          },
          body: {
            price: 350000
          }
        }).then((updateResponse) => {
          expect(updateResponse.status).to.eq(200);
          expect(updateResponse.body.price).to.eq(350000);
        });
      });
    });
  });

  context('T066: Agent Sees Only Own Properties', () => {
    let propertyAId;
    let propertyBId;

    before(() => {
      // Create property for Agent A
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        body: {
          name: 'Property A Visible',
          agent_id: agentAId,
          company_ids: [companyId]
        }
      }).then((response) => {
        propertyAId = response.body.id;
      });

      // Create property for Agent B
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentBAuthToken}`
        },
        body: {
          name: 'Property B Confidential',
          agent_id: agentBId,
          company_ids: [companyId]
        }
      }).then((response) => {
        propertyBId = response.body.id;
      });
    });

    it('should allow agent to see own properties', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${propertyAId}`,
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.name).to.eq('Property A Visible');
      });
    });

    it('should list only own properties', () => {
      cy.request({
        method: 'GET',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        
        const propertyIds = response.body.map(p => p.id);
        expect(propertyIds).to.include(propertyAId);
        expect(propertyIds).to.not.include(propertyBId);
      });
    });
  });

  context('T067: Agent Isolation (Cannot Access Other Agents)', () => {
    let propertyBId;

    before(() => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${agentBAuthToken}`
        },
        body: {
          name: 'Property B Secret',
          agent_id: agentBId,
          company_ids: [companyId]
        }
      }).then((response) => {
        propertyBId = response.body.id;
      });
    });

    it('should NOT allow Agent A to read Agent B property', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${propertyBId}`,
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(403);
      });
    });

    it('should NOT allow Agent A to update Agent B property', () => {
      cy.request({
        method: 'PATCH',
        url: `http://localhost:8069/api/v1/properties/${propertyBId}`,
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        body: {
          name: 'Property B (Hacked by Agent A)'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(403);
      });
    });

    it('should NOT allow Agent A to delete Agent B property', () => {
      cy.request({
        method: 'DELETE',
        url: `http://localhost:8069/api/v1/properties/${propertyBId}`,
        headers: {
          'Authorization': `Bearer ${agentAAuthToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.be.oneOf([403, 405]); // 403 Forbidden or 405 Method Not Allowed
      });
    });
  });

  after(() => {
    // Cleanup
    cy.request({
      method: 'DELETE',
      url: `http://localhost:8069/api/v1/companies/${companyId}`,
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      failOnStatusCode: false
    });
  });
});
