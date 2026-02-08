/**
 * E2E Test: Admin - Owner Management (Feature 007)
 * 
 * Task: T037
 * Tests: Owner CRUD operations via API
 * 
 * Scenarios:
 * 1. Create Owner without company (self-registration)
 * 2. List all Owners (Admin perspective)
 * 3. Get specific Owner details
 * 4. Update Owner profile
 * 5. Delete Owner (soft delete)
 * 6. Link Owner to Company
 * 7. Unlink Owner from Company
 * 8. Verify multi-tenancy isolation
 */

describe('Admin: Owner Management CRUD', () => {
  const baseUrl = Cypress.env('API_BASE_URL') || 'http://localhost:8069';
  let accessToken;
  let ownerId;
  let companyId;

  before(() => {
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

    // Get a company ID for linking tests
    cy.request({
      method: 'GET',
      url: `${baseUrl}/api/v1/companies`,
      headers: {
        'Authorization': `Bearer ${accessToken}`
      },
      failOnStatusCode: false
    }).then((response) => {
      if (response.status === 200 && response.body.data && response.body.data.length > 0) {
        companyId = response.body.data[0].id;
      }
    });
  });

  describe('1. Create Owner (POST /api/v1/owners)', () => {
    it('Should create owner without company', () => {
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
          email: `owner${timestamp}@example.com`,
          password: 'secure_password_123',
          phone: '11987654321'
        }
      }).then((response) => {
        expect(response.status).to.equal(201);
        expect(response.body).to.have.property('success', true);
        expect(response.body.data).to.have.property('id');
        expect(response.body.data).to.have.property('email', `owner${timestamp}@example.com`);
        expect(response.body.data).to.have.property('company_count', 0);
        expect(response.body.data.companies).to.be.an('array').that.is.empty;
        
        ownerId = response.body.data.id;
      });
    });

    it('Should return 400 for missing required fields', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/owners`,
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

    it('Should return 409 for duplicate email', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/owners`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: 'Duplicate Owner',
          email: `owner${Date.now() - 1000}@example.com`,
          password: 'password123'
        },
        failOnStatusCode: false
      }).then((response) => {
        // First request should succeed
        const email = response.body.data.email;
        
        // Try to create duplicate
        cy.request({
          method: 'POST',
          url: `${baseUrl}/api/v1/owners`,
          headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          },
          body: {
            name: 'Duplicate Owner 2',
            email: email,
            password: 'password456'
          },
          failOnStatusCode: false
        }).then((dupResponse) => {
          expect(dupResponse.status).to.equal(409);
        });
      });
    });
  });

  describe('2. Get Owner Details (GET /api/v1/owners/{id})', () => {
    it('Should retrieve owner by ID', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/owners/${ownerId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body.data).to.have.property('id', ownerId);
        expect(response.body.data).to.have.property('name');
        expect(response.body.data).to.have.property('email');
        expect(response.body).to.have.property('_links');
      });
    });

    it('Should return 404 for non-existent owner', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/owners/999999`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(404);
      });
    });
  });

  describe('3. Update Owner (PUT /api/v1/owners/{id})', () => {
    it('Should update owner details', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/owners/${ownerId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: 'Updated Owner Name',
          phone: '11999888777'
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body.data).to.have.property('name', 'Updated Owner Name');
        expect(response.body.data).to.have.property('phone', '11999888777');
      });
    });
  });

  describe('4. Link Owner to Company (POST /api/v1/owners/{id}/companies/{cid})', () => {
    it('Should link owner to company', function() {
      if (!companyId) {
        this.skip();
      }

      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/owners/${ownerId}/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
      });
    });

    it('Should verify owner is linked to company', function() {
      if (!companyId) {
        this.skip();
      }

      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/owners/${ownerId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.body.data.company_count).to.be.at.least(1);
        expect(response.body.data.companies).to.be.an('array').that.is.not.empty;
      });
    });
  });

  describe('5. Unlink Owner from Company (DELETE /api/v1/owners/{id}/companies/{cid})', () => {
    it('Should unlink owner from company', function() {
      if (!companyId) {
        this.skip();
      }

      cy.request({
        method: 'DELETE',
        url: `${baseUrl}/api/v1/owners/${ownerId}/companies/${companyId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        }
      }).then((response) => {
        expect(response.status).to.equal(200);
        expect(response.body).to.have.property('success', true);
      });
    });
  });

  describe('6. Delete Owner (DELETE /api/v1/owners/{id})', () => {
    it('Should soft delete owner', () => {
      cy.request({
        method: 'DELETE',
        url: `${baseUrl}/api/v1/owners/${ownerId}`,
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
        url: `${baseUrl}/api/v1/owners/${ownerId}`,
        headers: {
          'Authorization': `Bearer ${accessToken}`
        },
        failOnStatusCode: false
      }).then((response) => {
        expect(response.status).to.equal(404);
      });
    });
  });

  describe('7. HATEOAS Links', () => {
    it('Should include proper HATEOAS links in responses', () => {
      const timestamp = Date.now();
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/owners`,
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: {
          name: `HATEOAS Test ${timestamp}`,
          email: `hateoas${timestamp}@example.com`,
          password: 'password123'
        }
      }).then((response) => {
        expect(response.body).to.have.property('_links');
        expect(response.body._links).to.have.property('self');
        expect(response.body._links).to.have.property('companies');
      });
    });
  });
});
