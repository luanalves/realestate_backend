/**
 * E2E Test: Prospector Profile - Commission Split
 * 
 * Tests FR-054 to FR-060 (Prospector profile requirements)
 * 
 * Scenarios:
 * 1. Prospector registers new property (prospector_id auto-assigned)
 * 2. Manager assigns selling agent to prospected property
 * 3. Sale completes → commission split calculation (30% prospector, 70% agent)
 * 4. Verify commission transactions created for both agents
 */

describe('RBAC: Prospector Profile - Commission Split', () => {
  let prospectorAuthToken;
  let managerAuthToken;
  let companyId;
  let prospectorAgentId;
  let sellingAgentId;
  let prospectedPropertyId;
  let saleId;

  before(() => {
    // Setup: Create company, prospector user, selling agent, manager
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      body: {
        name: 'Company Prospector Test',
        cnpj: '11.111.111/0001-11',
        creci: 'CRECI-SP 11111'
      }
    }).then((response) => {
      companyId = response.body.id;

      // Create Prospector user
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Prospector User',
          login: 'prospector@e2e.test',
          email: 'prospector@e2e.test',
          password: 'prospector123',
          groups_id: [{ id: 'quicksol_estate.group_real_estate_prospector' }],
          estate_company_ids: [companyId]
        }
      }).then((userResponse) => {
        // Get OAuth token for Prospector
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/oauth/token',
          form: true,
          body: {
            grant_type: 'password',
            username: 'prospector@e2e.test',
            password: 'prospector123'
          }
        }).then((tokenResponse) => {
          prospectorAuthToken = tokenResponse.body.access_token;
        });

        // Create prospector agent record
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/agents',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            name: 'Prospector Agent',
            creci: 'CRECI-SP 99999',
            user_id: userResponse.body.id,
            company_ids: [companyId]
          }
        }).then((response) => {
          prospectorAgentId = response.body.id;
        });
      });

      // Create Selling Agent
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/agents',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Selling Agent',
          creci: 'CRECI-SP 88888',
          company_ids: [companyId]
        }
      }).then((response) => {
        sellingAgentId = response.body.id;

        // Create commission rule for selling agent (6%)
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/commission_rules',
          headers: {
            'Authorization': 'Basic ' + btoa('admin:admin')
          },
          body: {
            agent_id: sellingAgentId,
            company_id: companyId,
            transaction_type: 'sale',
            structure_type: 'percentage',
            percentage: 6.0,
            valid_from: '2024-01-01'
          }
        });
      });

      // Create Manager user
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Manager User',
          login: 'manager_prospector@e2e.test',
          email: 'manager_prospector@e2e.test',
          password: 'manager123',
          groups_id: [{ id: 'quicksol_estate.group_real_estate_manager' }],
          estate_company_ids: [companyId]
        }
      }).then((userResponse) => {
        // Get OAuth token for Manager
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/oauth/token',
          form: true,
          body: {
            grant_type: 'password',
            username: 'manager_prospector@e2e.test',
            password: 'manager123'
          }
        }).then((tokenResponse) => {
          managerAuthToken = tokenResponse.body.access_token;
        });
      });
    });
  });

  context('T100: Prospector Registers Property', () => {
    it('should allow prospector to create property', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${prospectorAuthToken}`
        },
        body: {
          name: 'Prospected Property',
          price: 500000,
          company_ids: [companyId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        prospectedPropertyId = response.body.id;

        // Verify prospector_id is auto-assigned
        expect(response.body.prospector_id).to.eq(prospectorAgentId);
      });
    });

    it('should allow prospector to read their own property', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${prospectedPropertyId}`,
        headers: {
          'Authorization': `Bearer ${prospectorAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.prospector_id).to.eq(prospectorAgentId);
      });
    });
  });

  context('T101: Manager Assigns Selling Agent', () => {
    it('should allow manager to assign selling agent to prospected property', () => {
      cy.request({
        method: 'PATCH',
        url: `http://localhost:8069/api/v1/properties/${prospectedPropertyId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          agent_id: sellingAgentId
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.agent_id).to.eq(sellingAgentId);
        expect(response.body.prospector_id).to.eq(prospectorAgentId);
      });
    });

    it('should verify property now has both prospector and agent', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/properties/${prospectedPropertyId}`,
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        }
      }).then((response) => {
        expect(response.body.prospector_id).to.eq(prospectorAgentId);
        expect(response.body.agent_id).to.eq(sellingAgentId);
      });
    });
  });

  context('T102: Commission Split Calculation', () => {
    it('should create sale for prospected property', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/sales',
        headers: {
          'Authorization': `Bearer ${managerAuthToken}`
        },
        body: {
          property_id: prospectedPropertyId,
          buyer_name: 'Test Buyer',
          sale_date: '2024-06-15',
          sale_price: 500000,
          company_ids: [companyId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        saleId = response.body.id;
      });
    });

    it('should verify commission transactions created for both agents', () => {
      cy.wait(2000); // Wait for observer to process

      // Get prospector commission transaction
      cy.request({
        method: 'GET',
        url: 'http://localhost:8069/api/v1/commission_transactions',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        qs: {
          agent_id: prospectorAgentId,
          property_id: prospectedPropertyId
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.length).to.be.greaterThan(0);

        const prospectorTransaction = response.body[0];
        // 6% of R$ 500,000 = R$ 30,000, 30% split = R$ 9,000
        expect(prospectorTransaction.amount).to.be.closeTo(9000, 10);
        expect(prospectorTransaction.transaction_type).to.eq('sale');
      });

      // Get selling agent commission transaction
      cy.request({
        method: 'GET',
        url: 'http://localhost:8069/api/v1/commission_transactions',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        qs: {
          agent_id: sellingAgentId,
          property_id: prospectedPropertyId
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.length).to.be.greaterThan(0);

        const agentTransaction = response.body[0];
        // 6% of R$ 500,000 = R$ 30,000, 70% split = R$ 21,000
        expect(agentTransaction.amount).to.be.closeTo(21000, 10);
        expect(agentTransaction.transaction_type).to.eq('sale');
      });
    });

    it('should verify total commission adds up correctly', () => {
      cy.request({
        method: 'GET',
        url: 'http://localhost:8069/api/v1/commission_transactions',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        qs: {
          property_id: prospectedPropertyId
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.length).to.eq(2);

        const totalCommission = response.body.reduce((sum, t) => sum + t.amount, 0);
        // 6% of R$ 500,000 = R$ 30,000
        expect(totalCommission).to.be.closeTo(30000, 10);
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
