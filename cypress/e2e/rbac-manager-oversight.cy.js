/**
 * E2E Test: Manager Profile - Company Oversight
 * 
 * Tests FR-041 to FR-050 (Manager profile requirements)
 * 
 * Scenarios:
 * 1. Manager views all company properties (regardless of agent)
 * 2. Manager reassigns properties between agents
 * 3. Manager creates assignments (lead distribution)
 * 4. Manager cannot create users
 * 5. Multi-tenant isolation (Manager Company A cannot see Company B)
 */

describe('RBAC: Manager Profile - Company Oversight', () => {
  let managerAuthToken;
  let companyAId;
  let companyBId;
  let agentAId;
  let agentBId;
  let propertyAId;
  let propertyBId;

  before(() => {
    // Setup: Create 2 companies, manager for Company A, 2 agents in Company A
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      body: {
        name: 'Company A (Manager Test)',
        cnpj: '11.111.111/0001-11',
        creci: 'CRECI-SP 11111'
      }
    }).then((response) => {
      companyAId = response.body.id;

      // Create Manager user
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Manager User',
          login: 'manager@e2e.test',
          email: 'manager@e2e.test',
          password: 'manager123',
          groups_id: [{ id: 'quicksol_estate.group_real_estate_manager' }],
          estate_company_ids: [companyAId]
        }
      }).then((userResponse) => {
        // Get OAuth token for Manager
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/oauth/token',
          form: true,
          body: {
            grant_type: 'password',
            username: 'manager@e2e.test',
            password: 'manager123'
          }
        }).then((tokenResponse) => {
          managerAuthToken = tokenResponse.body.access_token;
        });
      });

      // Create 2 agents in Company A
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/agents',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Agent A (Manager Test)',
          creci: 'CRECI-SP 99999',
          company_ids: [companyAId]
        }
      }).then((response) => {
        agentAId = response.body.id;

        // Create property for Agent A
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/properties',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            name: 'Property Agent A',
            agent_id: agentAId,
            company_ids: [companyAId]
          }
        }).then((response) => {
          propertyAId = response.body.id;
        });
      });

      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/agents',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Agent B (Manager Test)',
          creci: 'CRECI-SP 88888',
          company_ids: [companyAId]
        }
      }).then((response) => {
        agentBId = response.body.id;

        // Create property for Agent B
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/properties',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            name: 'Property Agent B',
            agent_id: agentBId,
            company_ids: [companyAId]
          }
        }).then((response) => {
          propertyBId = response.body.id;
        });
      });
    });

    // Create Company B (for multi-tenant isolation test)
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      body: {
        name: 'Company B (Manager Test)',
        cnpj: '22.222.222/0001-22',
        creci: 'CRECI-RJ 22222'
      }
    }).then((response) => {
      companyBId = response.body.id;
    });
  });

  context('T077: Manager Views All Company Data', () => {
    it('should allow manager to see all properties in their company', () => {
      cy.request({
        method: 'GET',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        
        const propertyIds = response.body.map(p => p.id);
        expect(propertyIds).to.include(propertyAId);
        expect(propertyIds).to.include(propertyBId);
      });
    });

    it('should allow manager to read properties from both agents', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${propertyAId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.agent_id).to.eq(agentAId);
      });

      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${propertyBId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.agent_id).to.eq(agentBId);
      });
    });

    it('should allow manager to create properties', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          name: 'Property Created by Manager',
          agent_id: agentAId,
          price: 400000,
          company_ids: [companyAId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.name).to.eq('Property Created by Manager');
      });
    });
  });

  context('T078: Manager Reassigns Leads', () => {
    it('should allow manager to reassign property to different agent', () => {
      cy.request({
        method: 'PATCH',
        url: `http://localhost:8069/api/v1/properties/${propertyAId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          agent_id: agentBId
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.agent_id).to.eq(agentBId);
      });
    });

    it('should allow manager to create property assignments', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/assignments',
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          property_id: propertyBId,
          agent_id: agentAId,
          assignment_type: 'sale'
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.agent_id).to.eq(agentAId);
      });
    });
  });

  context('Manager Cannot Create Users (Negative Test)', () => {
    it('should NOT allow manager to create users', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          name: 'Unauthorized User',
          login: 'unauthorized@test.com',
          email: 'unauthorized@test.com',
          password: 'user123',
          estate_company_ids: [companyAId]
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(403);
      });
    });
  });

  context('Multi-Tenant Isolation', () => {
    let propertyCompanyBId;

    before(() => {
      // Create property in Company B
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Property Company B',
          company_ids: [companyBId]
        }
      }).then((response) => {
        propertyCompanyBId = response.body.id;
      });
    });

    it('should NOT allow Manager Company A to see Company B properties', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${propertyCompanyBId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(403);
      });
    });
  });

  after(() => {
    // Cleanup
    cy.request({
      method: 'DELETE',
      url: `http://localhost:8069/api/v1/companies/${companyAId}`,
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      failOnStatusCode: false
    });

    cy.request({
      method: 'DELETE',
      url: `http://localhost:8069/api/v1/companies/${companyBId}`,
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      failOnStatusCode: false
    });
  });
});
