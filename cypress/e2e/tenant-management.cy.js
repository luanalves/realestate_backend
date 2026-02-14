// ==============================================================================
// Cypress E2E Test: Tenant Management
// ==============================================================================
// User Story 1: Tenant CRUD — create, list, view, update, archive
// Feature: 008-tenant-lease-sale-api
// ADR-003: E2E UI test WITH database (Cypress + real Odoo instance)
// Task: T027
// ==============================================================================

describe('US8: Tenant Management CRUD', () => {
  const baseUrl = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069'
  let accessToken
  let sessionId
  let tenantId

  before(() => {
    // Step 1: Get OAuth token
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/auth/token`,
      body: {
        client_id: Cypress.env('OAUTH_CLIENT_ID') || 'test_client',
        client_secret: Cypress.env('OAUTH_CLIENT_SECRET') || 'test_secret',
        grant_type: 'client_credentials'
      },
      failOnStatusCode: false
    }).then((tokenRes) => {
      if (tokenRes.status === 200 && tokenRes.body.access_token) {
        accessToken = tokenRes.body.access_token
      }
    })

    // Step 2: Get session via user login
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/users/login`,
      headers: {
        'Content-Type': 'application/json',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
      },
      body: {
        email: Cypress.env('TEST_USER_MANAGER') || Cypress.env('ODOO_USERNAME') || 'admin',
        password: Cypress.env('TEST_PASSWORD_MANAGER') || Cypress.env('ODOO_PASSWORD') || 'admin'
      },
      failOnStatusCode: false
    }).then((loginRes) => {
      if (loginRes.status === 200) {
        sessionId = loginRes.body.session_id || (loginRes.body.result && loginRes.body.result.session_id)
      }
    })
  })

  function apiHeaders(method = 'GET') {
    const headers = {
      'Content-Type': 'application/json',
      'User-Agent': 'CypressE2E/1.0'
    }
    if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`
    if (method === 'GET' || method === 'DELETE') {
      if (sessionId) headers['X-Openerp-Session-Id'] = sessionId
    }
    return headers
  }

  function bodyWithSession(data) {
    return { ...data, session_id: sessionId }
  }

  context('T027-01: Create Tenant', () => {
    it('should create a new tenant with valid data', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/tenants`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          name: 'Cypress Test Tenant',
          phone: '11999001122',
          email: 'cypress.tenant@example.com',
          occupation: 'QA Engineer'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(201)
        expect(res.body.data).to.have.property('id')
        expect(res.body.data.name).to.eq('Cypress Test Tenant')
        expect(res.body.data.email).to.eq('cypress.tenant@example.com')
        expect(res.body.data).to.have.property('_links')
        tenantId = res.body.data.id
      })
    })

    it('should reject tenant without required name', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/tenants`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          phone: '11999001122',
          email: 'no-name@example.com'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })

    it('should reject tenant with invalid email format', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/tenants`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          name: 'Invalid Email Tenant',
          email: 'not-an-email'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })
  })

  context('T027-02: List Tenants', () => {
    it('should list tenants with pagination', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/tenants?page=1&page_size=20`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body).to.have.property('data')
        expect(res.body.data).to.be.an('array')
        expect(res.body).to.have.property('pagination')
        expect(res.body.pagination).to.have.property('total')
        expect(res.body.pagination).to.have.property('page')
      })
    })
  })

  context('T027-03: Get Tenant by ID', () => {
    it('should retrieve the created tenant', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/tenants/${tenantId}`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.id).to.eq(tenantId)
        expect(res.body.data.name).to.eq('Cypress Test Tenant')
        expect(res.body.data).to.have.property('_links')
      })
    })

    it('should return 404 for nonexistent tenant', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/tenants/999999`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(404)
      })
    })
  })

  context('T027-04: Update Tenant', () => {
    it('should update tenant fields', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/tenants/${tenantId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({
          phone: '11988776655',
          occupation: 'Senior QA Engineer'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.phone).to.eq('11988776655')
        expect(res.body.data.occupation).to.eq('Senior QA Engineer')
      })
    })
  })

  context('T027-05: Archive Tenant (Soft Delete)', () => {
    it('should archive (soft delete) the tenant', () => {
      cy.request({
        method: 'DELETE',
        url: `${baseUrl}/api/v1/tenants/${tenantId}`,
        headers: apiHeaders('DELETE'),
        body: { reason: 'Cypress E2E test cleanup' },
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
      })
    })

    it('should not find archived tenant in active list', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/tenants?page=1&page_size=100`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        const found = res.body.data.find((t) => t.id === tenantId)
        expect(found).to.be.undefined
      })
    })

    it('should find archived tenant with is_active=false filter', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/tenants?is_active=false&page=1&page_size=100`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        const found = res.body.data.find((t) => t.id === tenantId)
        expect(found).to.not.be.undefined
      })
    })

    it('should reactivate archived tenant', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/tenants/${tenantId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({ active: true }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.active).to.be.true
      })
    })
  })
})
