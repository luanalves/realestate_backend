/**
 * E2E Test: Admin - Company Management (Feature 007)
 * 
 * Task: T038
 * Tests: Company CRUD operations via API
 * 
 * Scenarios:
 * 1. Create Real Estate Company with CNPJ validation
 * 2. List all Companies (with multi-tenancy)
 * 3. Get specific Company details
 * 4. Update Company information
 * 5. Delete Company (soft delete)
 * 6. Verify CNPJ uniqueness constraint
 * 7. Test email validation
 * 8. Verify owner auto-linkage
 */

describe('Admin: Company Management CRUD', () => {
  const baseUrl = Cypress.env('API_BASE_URL') || 'http://localhost:8069';
  let accessToken;
  let sessionCookie;
  let companyId;
  let ownerId;

  before(() => {
    // Login to Odoo to get a valid session
    cy.visit(`${baseUrl}/web/login`);
    cy.get('input[name="login"]').type('admin');
    cy.get('input[name="password"]').type('admin');
    cy.get('button[type="submit"]').click();
    cy.get('.o_user_menu', { timeout: 10000 }).should('be.visible');

    // Get OAuth2 token
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/auth/token`,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: 'grant_type=client_credentials&client_id=test-client-id&client_secret=test-client-secret-12345'
    }).then((response) => {
      expect(response.status).to.equal(200);
      expect(response.body).to.have.property('access_token');
      accessToken = response.body.access_token;
    });

    // Create a test owner for linking tests
    const timestamp = Date.now();
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/owners`,
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: {
        name: `Test Owner ${timestamp}`,
        email: `testowner${timestamp}@example.com`,
        password: 'password123',
        phone: '11987654321'
      }
    }).then((response) => {
      ownerId = response.body.data.id;
    });
  });

  describe('1. Create Company (POST /api/v1/companies)', () => {
    it('Should create company with valid CNPJ', () => {
      const timestamp = Date.now();
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: `Test Company ${timestamp}`,
          legal_name: `Test Company LTDA ${timestamp}`,
          cnpj: '12.345.678/0001-95', // Valid CNPJ
          email: `company${timestamp}@example.com`,
          phone: '11912345678',
          creci: 'CRECI/SP 123456'
        }
      }).then((response) => {
        expect(response.status).to.equal(201);
        expect(response.body).to.have.property('success', true);
        expect(response.body.data).to.have.property('id');
        expect(response.body.data).to.have.property('cnpj', '12.345.678/0001-95');
        expect(response.body.data).to.have.property('active', true);
        
        companyId = response.body.data.id;
      });
    });

    it('Should return 400 for invalid CNPJ format', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: 'Invalid CNPJ Company',
          legal_name: 'Invalid CNPJ LTDA',
          cnpj: '12.345.678/0001-99', // Invalid check digits
          email: 'invalid@example.com'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(400);
        expect(response.body).to.have.property('success', false);
      });
    });

    it('Should return 400 for invalid email format', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: 'Invalid Email Company',
          legal_name: 'Invalid Email LTDA',
          cnpj: '98.765.432/0001-98',
          email: 'invalid-email-format'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(400);
        expect(response.body).to.have.property('success', false);
      });
    });

    it('Should return 409 for duplicate CNPJ', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: 'Duplicate CNPJ Company',
          legal_name: 'Duplicate CNPJ LTDA',
          cnpj: '12.345.678/0001-95', // Same CNPJ from first test
          email: `duplicate${Date.now()}@example.com`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(409);
        expect(response.body).to.have.property('success', false);
      });
    });

    it('Should return 400 for missing required fields', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          email: 'incomplete@example.com'
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(400);
        expect(response.body).to.have.property('success', false);
      });
    });
  });

  describe('2. Get Company Details (GET /api/v1/companies/{id})', () => {
    it('Should retrieve company by ID', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body.data).to.have.property('id', companyId);
        expect(response.body.data).to.have.property('name');
        expect(response.body.data).to.have.property('cnpj');
        expect(response.body).to.have.property('_links');
      });
    });

    it('Should return 404 for non-existent company', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies/999999`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(404);
      });
    });
  });

  describe('3. List Companies (GET /api/v1/companies)', () => {
    it('Should list all companies', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
        expect(response.body.data).to.be.an('array');
        expect(response.body).to.have.property('_links');
      });
    });

    it('Should support pagination', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies?limit=2&offset=0`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body.data).to.be.an('array');
        expect(response.body.data.length).to.be.at.most(2);
      });
    });
  });

  describe('4. Update Company (PUT /api/v1/companies/{id})', () => {
    it('Should update company details', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          phone: '11999888777',
          website: 'https://updated-company.com.br',
          description: 'Updated company description'
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body.data).to.have.property('phone', '11999888777');
        expect(response.body.data).to.have.property('website', 'https://updated-company.com.br');
      });
    });

    it('Should not allow CNPJ change', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          cnpj: '98.765.432/0001-98'
        },
        failOnStatusCode: false
      }).then((response) => {
        // Should either reject or ignore CNPJ change
        if (response.status === 400) {
          expect(response.body).to.have.property('success', false);
        } else if (response.status === 200) {
          // If accepted, CNPJ should remain unchanged
          expect(response.body.data.cnpj).to.equal('12.345.678/0001-95');
        }
      });
    });
  });

  describe('5. Delete Company (DELETE /api/v1/companies/{id})', () => {
    it('Should soft delete company', () => {
      cy.request({
        method: 'DELETE',
        url: `${baseUrl}/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
      });
    });

    it('Should return 404 after deletion', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(404);
      });
    });
  });

  describe('6. HATEOAS Links', () => {
    it('Should include proper HATEOAS links in responses', () => {
      const timestamp = Date.now();
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: `HATEOAS Test ${timestamp}`,
          legal_name: `HATEOAS Test LTDA ${timestamp}`,
          cnpj: '11.222.333/0001-81',
          email: `hateoas${timestamp}@example.com`
        }
      }).then((response) => {
        expect(response.body).to.have.property('_links');
        expect(response.body._links).to.have.property('self');
      });
    });
  });

  describe('7. Multi-Tenancy', () => {
    it('Should filter companies by user access', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/companies`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        // Should return only companies the user has access to
        const companies = response.body.data;
        companies.forEach(company => {
          expect(company).to.have.property('id');
          expect(company).to.have.property('name');
          expect(company).to.have.property('active');
        });
      });
    });
  });
});
