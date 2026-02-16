// ==============================================================================
// Cypress E2E Test: Lease Management Lifecycle
// ==============================================================================
// User Story 2: Lease lifecycle — create, list, update, renew, terminate
// Feature: 008-tenant-lease-sale-api
// ADR-003: E2E UI test WITH database (Cypress + real Odoo instance)
// Task: T028
// ==============================================================================

describe('US8: Lease Management Lifecycle', () => {
  const baseUrl = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069'
  let accessToken
  let sessionId
  let tenantId
  let propertyId
  let leaseId

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

    // Step 2: Get session
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

    // Step 3: Create a test tenant for lease tests
    cy.request({
      method: 'POST',
      url: `${baseUrl}/api/v1/tenants`,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'CypressE2E/1.0',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
      },
      body: {
        name: 'Cypress Lease Test Tenant',
        phone: '11999002233',
        email: 'cypress.lease.tenant@example.com',
        session_id: sessionId
      },
      failOnStatusCode: false
    }).then((res) => {
      if (res.status === 201 && res.body.data) {
        tenantId = res.body.data.id
      }
    })

    // Step 4: Find an available property
    cy.request({
      method: 'GET',
      url: `${baseUrl}/api/v1/properties?page=1&page_size=5`,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'CypressE2E/1.0',
        ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {}),
        ...(sessionId ? { 'X-Openerp-Session-Id': sessionId } : {})
      },
      failOnStatusCode: false
    }).then((res) => {
      if (res.status === 200 && res.body.data && res.body.data.length > 0) {
        propertyId = res.body.data[0].id
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

  context('T028-01: Create Lease', () => {
    it('should create a new lease with valid data', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          property_id: propertyId,
          tenant_id: tenantId,
          start_date: '2026-06-01',
          end_date: '2027-05-31',
          rent_amount: 3500.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(201)
        expect(res.body.data).to.have.property('id')
        expect(res.body.data.rent_amount).to.eq(3500.00)
        expect(res.body.data).to.have.property('_links')
        leaseId = res.body.data.id
      })
    })

    it('should reject lease with invalid dates (end before start)', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          property_id: propertyId,
          tenant_id: tenantId,
          start_date: '2027-01-01',
          end_date: '2026-01-01',
          rent_amount: 2000.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })

    it('should reject lease with zero rent amount', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          property_id: propertyId,
          tenant_id: tenantId,
          start_date: '2028-01-01',
          end_date: '2028-12-31',
          rent_amount: 0
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })
  })

  context('T028-02: List & Get Leases', () => {
    it('should list leases with pagination', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/leases?page=1&page_size=20`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body).to.have.property('data')
        expect(res.body.data).to.be.an('array')
        expect(res.body).to.have.property('pagination')
      })
    })

    it('should retrieve the created lease by ID', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/leases/${leaseId}`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.id).to.eq(leaseId)
        expect(res.body.data).to.have.property('_links')
      })
    })
  })

  context('T028-03: Update Lease', () => {
    it('should update lease rent amount', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/leases/${leaseId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({
          rent_amount: 3800.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.rent_amount).to.eq(3800.00)
      })
    })
  })

  context('T028-04: Renew Lease', () => {
    it('should renew lease with new end date and rent', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases/${leaseId}/renew`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          new_end_date: '2028-05-31',
          new_rent_amount: 4200.00,
          reason: 'Annual renewal via Cypress E2E'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.rent_amount).to.eq(4200.00)
        expect(res.body.data.end_date).to.eq('2028-05-31')
      })
    })
  })

  context('T028-05: Terminate Lease', () => {
    it('should terminate the lease with reason and penalty', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases/${leaseId}/terminate`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          termination_date: '2027-03-15',
          reason: 'Cypress E2E termination test',
          penalty_amount: 7000.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.status).to.eq('terminated')
        expect(res.body.data.termination_reason).to.eq('Cypress E2E termination test')
      })
    })

    it('should reject renewal on terminated lease', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/leases/${leaseId}/renew`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          new_end_date: '2029-05-31',
          reason: 'Should fail'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })

    it('should reject updates on terminated lease', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/leases/${leaseId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({
          rent_amount: 5000.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })
  })
})
