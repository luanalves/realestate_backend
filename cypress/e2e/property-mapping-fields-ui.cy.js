describe('Feature 016 - Property Mapping Fields UI', () => {
  const db = Cypress.env('ODOO_DB') || 'realestate'
  const username = Cypress.env('ODOO_USERNAME') || 'admin'
  const password = Cypress.env('ODOO_PASSWORD') || 'admin'

  const login = () => {
    cy.request({
      method: 'POST',
      url: '/web/session/authenticate',
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: {
          db,
          login: username,
          password,
        },
        id: Date.now(),
      },
    }).then((response) => {
      expect(response.status).to.eq(200)
      expect(response.body.result.uid).to.be.a('number')
    })
  }

  const openNewPropertyForm = () => {
    cy.visit('/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list')
    cy.get('.o_list_view', { timeout: 20000 }).should('be.visible')
    cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 20000 }).first().click()
    cy.get('.o_form_view', { timeout: 20000 }).should('be.visible')
  }

  const clickTab = (label) => {
    cy.contains('.o_notebook .nav-link, .o_notebook_headers a', label, { timeout: 10000 })
      .scrollIntoView()
      .click({ force: true })
  }

  const assertFieldsExist = (fields) => {
    fields.forEach((field) => {
      cy.get(`.o_field_widget[name="${field}"], div[name="${field}"]`, { timeout: 10000 })
        .should('exist')
    })
  }

  beforeEach(() => {
    login()
  })

  it('shows Feature 016 mapping fields in the Odoo property form tabs', () => {
    openNewPropertyForm()

    clickTab('Dados do Proprietário')
    assertFieldsExist([
      'send_activities_to_owner',
      'owner_email',
      'owner_home_phone',
      'owner_business_phone',
      'owner_mobile_phone',
    ])

    clickTab('Structure')
    assertFieldsExist(['registered_by', 'alternative_reference'])

    clickTab('Primary Data')
    assertFieldsExist([
      'iptu_payment_condition',
      'iptu_value',
      'rental_guarantee_insurance',
      'fire_insurance',
      'property_situation',
      'intention',
      'exclusivity',
    ])

    clickTab('Key Control')
    assertFieldsExist(['key_location'])

    clickTab('Signs')
    assertFieldsExist(['publish_super_featured'])

    clickTab('Commissions')
    assertFieldsExist([
      'commission_type',
      'captured_intention',
      'included_in_commission_date',
      'commercial_condition',
    ])

    clickTab('Documents')
    assertFieldsExist([
      'electricity_network_code',
      'water_network_code',
      'titles_rights',
      'approved_environmental_agency',
      'approved_project',
      'documentation_observations',
    ])
  })
})
