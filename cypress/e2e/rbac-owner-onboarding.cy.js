/**
 * E2E Test: Owner Profile - Company Onboarding
 * 
 * Tests FR-001 to FR-010 (Owner profile requirements)
 * 
 * Scenarios:
 * 1. Owner creates a new company
 * 2. Owner assigns users to their company
 * 3. Owner cannot assign users to other companies (negative test)
 * 4. Owner has full CRUD access to company data
 * 5. Multi-tenant isolation (cannot see other companies)
 */

describe('RBAC: Owner Profile - Company Onboarding', () => {
  let ownerAuthToken;
  let ownerSessionCookie;
  let companyId;
  let otherCompanyId;

  before(() => {
    // Create test data: Owner user and 2 companies
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/oauth/applications/new',
      body: {
        name: 'E2E Test App - Owner',
        redirect_uris: 'http://localhost:3000/callback',
        scopes: 'all'
      },
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      }
    }).then((response) => {
      const clientId = response.body.client_id;
      const clientSecret = response.body.client_secret;
      
      // Get OAuth token for owner user
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/oauth/token',
        form: true,
        body: {
          grant_type: 'password',
          username: 'owner_a@test.com',
          password: 'owner123',
          client_id: clientId,
          client_secret: clientSecret
        }
      }).then((tokenResponse) => {
        ownerAuthToken = tokenResponse.body.access_token;
      });
    });

    // Create Company A (owned by owner_a)
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': `Bearer ${ownerAuthToken}`
      },
      body: {
        name: 'Real Estate Company A',
        cnpj: '12.345.678/0001-90',
        creci: 'CRECI-SP 12345'
      }
    }).then((response) => {
      companyId = response.body.id;
    });

    // Create Company B (owned by another owner)
    cy.request({
      method: 'POST',
      url: 'http://localhost:8069/api/v1/companies',
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      body: {
        name: 'Real Estate Company B',
        cnpj: '98.765.432/0001-10',
        creci: 'CRECI-RJ 54321'
      }
    }).then((response) => {
      otherCompanyId = response.body.id;
    });
  });

  context('T036: Owner Company Creation', () => {
    it('should allow owner to create a new company', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/companies',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'New Company C',
          cnpj: '11.111.111/0001-11',
          creci: 'CRECI-MG 11111'
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body).to.have.property('id');
        expect(response.body.name).to.eq('New Company C');
      });
    });

    it('should allow owner to read their company data', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.name).to.eq('Real Estate Company A');
      });
    });

    it('should allow owner to update their company data', () => {
      cy.request({
        method: 'PATCH',
        url: `http://localhost:8069/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Real Estate Company A (Updated)'
        }
      }).then((response) => {
        expect(response.status).to.eq(200);
        expect(response.body.name).to.include('Updated');
      });
    });

    it('should NOT allow owner to read other companies (multi-tenant isolation)', () => {
      cy.request({
        method: 'GET',
        url: `http://localhost:8069/api/v1/companies/${otherCompanyId}`,
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(403);
      });
    });
  });

  context('T037: Owner Assigns Users to Company', () => {
    it('should allow owner to create a user in their company', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Agent User A1',
          login: 'agent_a1@test.com',
          email: 'agent_a1@test.com',
          password: 'agent123',
          estate_company_ids: [companyId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body).to.have.property('id');
        expect(response.body.estate_company_ids).to.include(companyId);
      });
    });

    it('should allow owner to assign multiple users to their company', () => {
      const users = [
        { name: 'User A2', login: 'user_a2@test.com', email: 'user_a2@test.com' },
        { name: 'User A3', login: 'user_a3@test.com', email: 'user_a3@test.com' }
      ];

      users.forEach((userData) => {
        cy.request({
          method: 'POST',
          url: 'http://localhost:8069/api/v1/users',
          headers: {
            'Authorization': `Bearer ${ownerAuthToken}`
          },
          body: {
            ...userData,
            password: 'user123',
            estate_company_ids: [companyId]
          }
        }).then((response) => {
          expect(response.status).to.eq(201);
        });
      });
    });
  });

  context('T038: Negative Tests - Owner Cannot Cross Companies', () => {
    it('should NOT allow owner to assign users to other companies', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Invalid User',
          login: 'invalid@test.com',
          email: 'invalid@test.com',
          password: 'invalid123',
          estate_company_ids: [otherCompanyId]
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.eq(400);
        expect(response.body.error).to.include('cannot assign users to companies');
      });
    });

    it('should NOT allow owner to read properties from other companies', () => {
      // Create property in Company B (as admin)
      let propertyB;
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'Property B1',
          company_ids: [otherCompanyId]
        }
      }).then((response) => {
        propertyB = response.body.id;

        // Try to read as owner_a (should fail)
        cy.request({
          method: 'GET',
          url: `http://localhost:8069/api/v1/properties/${propertyB}`,
          headers: {
            'Authorization': `Bearer ${ownerAuthToken}`
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(403);
        });
      });
    });

    it('should NOT allow owner to update users from other companies', () => {
      // Create user in Company B (as admin)
      let userB;
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/users',
        headers: {
          'Authorization': 'Basic ' + btoa('admin:admin')
        },
        body: {
          name: 'User B1',
          login: 'user_b1@test.com',
          email: 'user_b1@test.com',
          password: 'user123',
          estate_company_ids: [otherCompanyId]
        }
      }).then((response) => {
        userB = response.body.id;

        // Try to update as owner_a (should fail)
        cy.request({
          method: 'PATCH',
          url: `http://localhost:8069/api/v1/users/${userB}`,
          headers: {
            'Authorization': `Bearer ${ownerAuthToken}`
          },
          body: {
            name: 'User B1 (Hacked)'
          },
          failOnStatusCode: false
        }).then((response) => {
          expect(response.status).to.eq(403);
        });
      });
    });
  });

  context('Owner Full CRUD Access to Company Resources', () => {
    it('should allow owner to create properties in their company', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Property A1',
          price: 500000,
          company_ids: [companyId]
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.name).to.eq('Property A1');
      });
    });

    it('should allow owner to create commission rules', () => {
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/commission-rules',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Standard Commission',
          commission_rate: 6.0,
          company_id: companyId
        }
      }).then((response) => {
        expect(response.status).to.eq(201);
        expect(response.body.commission_rate).to.eq(6.0);
      });
    });

    it('should allow owner to delete resources in their company', () => {
      // Create temporary property
      cy.request({
        method: 'POST',
        url: 'http://localhost:8069/api/v1/properties',
        headers: {
          'Authorization': `Bearer ${ownerAuthToken}`
        },
        body: {
          name: 'Temp Property',
          company_ids: [companyId]
        }
      }).then((response) => {
        const propertyId = response.body.id;

        // Delete it
        cy.request({
          method: 'DELETE',
          url: `http://localhost:8069/api/v1/properties/${propertyId}`,
          headers: {
            'Authorization': `Bearer ${ownerAuthToken}`
          }
        }).then((deleteResponse) => {
          expect(deleteResponse.status).to.eq(204);
        });
      });
    });
  });

  after(() => {
    // Cleanup: Delete test companies and users
    cy.request({
      method: 'DELETE',
      url: `http://localhost:8069/api/v1/companies/${companyId}`,
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      failOnStatusCode: false
    });

    cy.request({
      method: 'DELETE',
      url: `http://localhost:8069/api/v1/companies/${otherCompanyId}`,
      headers: {
        'Authorization': 'Basic ' + btoa('admin:admin')
      },
      failOnStatusCode: false
    });
  });
});
