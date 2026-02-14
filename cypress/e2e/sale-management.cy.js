// ==============================================================================
// Cypress E2E Test: Sale Management
// ==============================================================================
// User Story 3: Sale registration — create, list, view, update, cancel
// Feature: 008-tenant-lease-sale-api
// ADR-003: E2E UI test WITH database (Cypress + real Odoo instance)
// Task: T029
// ==============================================================================

describe('US8: Sale Management', () => {
  const baseUrl = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069'
  let accessToken
  let sessionId
  let propertyId
  let companyId
  let saleId

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

    // Step 3: Find a property and company for sale
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
        const prop = res.body.data[0]
        propertyId = prop.id
        companyId = prop.company_id || prop.company_ids?.[0] || 1
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

  context('T029-01: Create Sale', () => {
    it('should reject sale with zero price', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/sales`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          property_id: propertyId,
          company_id: companyId,
          buyer_name: 'Zero Price Buyer',
          sale_date: '2026-04-01',
          sale_price: 0
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })

    it('should create a sale with valid data', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/sales`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          property_id: propertyId,
          company_id: companyId,
          buyer_name: 'Cypress Test Buyer',
          buyer_phone: '11999003344',
          buyer_email: 'cypress.buyer@example.com',
          sale_date: '2026-04-15',
          sale_price: 550000.00
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(201)
        expect(res.body.data).to.have.property('id')
        expect(res.body.data.buyer_name).to.eq('Cypress Test Buyer')
        expect(res.body.data.sale_price).to.eq(550000.00)
        expect(res.body.data).to.have.property('_links')
        saleId = res.body.data.id
      })
    })
  })

  context('T029-02: List & Get Sales', () => {
    it('should list sales with pagination', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/sales?page=1&page_size=20`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body).to.have.property('data')
        expect(res.body.data).to.be.an('array')
        expect(res.body).to.have.property('pagination')
      })
    })

    it('should retrieve the created sale by ID', () => {
      cy.request({
        method: 'GET',
        url: `${baseUrl}/api/v1/sales/${saleId}`,
        headers: apiHeaders('GET'),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.id).to.eq(saleId)
        expect(res.body.data.buyer_name).to.eq('Cypress Test Buyer')
        expect(res.body.data).to.have.property('_links')
      })
    })
  })

  context('T029-03: Update Sale', () => {
    it('should update buyer information', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/sales/${saleId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({
          buyer_name: 'Cypress Updated Buyer',
          buyer_phone: '11988776655'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.buyer_name).to.eq('Cypress Updated Buyer')
        expect(res.body.data.buyer_phone).to.eq('11988776655')
      })
    })
  })

  context('T029-04: Cancel Sale', () => {
    it('should cancel the sale with reason', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/sales/${saleId}/cancel`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          reason: 'Cypress E2E cancellation test'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(200)
        expect(res.body.data.status).to.eq('cancelled')
      })
    })

    it('should reject update on cancelled sale', () => {
      cy.request({
        method: 'PUT',
        url: `${baseUrl}/api/v1/sales/${saleId}`,
        headers: apiHeaders('PUT'),
        body: bodyWithSession({
          buyer_name: 'Should Not Update'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })

    it('should reject double cancellation', () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/api/v1/sales/${saleId}/cancel`,
        headers: apiHeaders('POST'),
        body: bodyWithSession({
          reason: 'Double cancel attempt'
        }),
        failOnStatusCode: false
      }).then((res) => {
        expect(res.status).to.eq(400)
      })
    })
  })
})
