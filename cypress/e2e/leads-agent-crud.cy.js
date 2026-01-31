// ==============================================================================
// Cypress E2E Test: Agent Lead CRUD Operations
// ==============================================================================
// User Story 6: As an agent, I want to create, view, update and archive leads
// Tests: Agent creates lead, views list, updates state, archives lead
// ADR-003: E2E UI test WITH database (Cypress + real Odoo instance)
// Task: T033
// ==============================================================================

describe('US6: Agent Lead CRUD Operations', () => {
  beforeEach(() => {
    // Use cy.session to keep login persistent (faster than logging in every time)
    cy.odooLoginSession()
  })

  it('Should navigate to leads list view', () => {
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')
    cy.contains('Leads', { timeout: 10000 }).should('be.visible')
  })

  it('Should create a new lead with minimal data', () => {
    // Navigate to leads list
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Click "Create" button
    cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 })
      .should('be.visible')
      .first()
      .click()
    
    // Wait for form to load in edit mode
    cy.wait(1500)
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 }).should('exist')
    
    // Fill in required field: name
    cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input', { timeout: 10000 })
      .should('be.visible')
      .first()
      .clear()
      .type('Cypress Test Lead - CRUD')
    
    // Fill in phone (optional but recommended)
    cy.get('.o_field_widget[name="phone"] input, input[name="phone"], div[name="phone"] input', { timeout: 10000 })
      .should('be.visible')
      .first()
      .clear()
      .type('+5511999888777')
    
    // Fill in email (optional but recommended)
    cy.get('.o_field_widget[name="email"] input, input[name="email"], div[name="email"] input', { timeout: 10000 })
      .should('be.visible')
      .first()
      .clear()
      .type('cypress.crud@example.com')
    
    // Save the lead
    cy.get('button.o_form_button_save', { timeout: 10000 })
      .should('be.visible')
      .first()
      .click()
    
    // Wait for save to complete
    cy.wait(2000)
    
    // Verify lead was created (form becomes readonly)
    cy.get('.o_form_view:not(.o_form_editable), .o_form_view.o_form_readonly', { timeout: 10000 }).should('exist')
    
    // Verify name is displayed
    cy.contains('Cypress Test Lead - CRUD', { timeout: 5000 }).should('be.visible')
  })

  it('Should create a lead with complete data', () => {
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Create new lead
    cy.get('button.o_list_button_add, button.o-list-button-add', { timeout: 10000 })
      .first()
      .click()
    
    cy.wait(1500)
    cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 }).should('exist')
    
    // Fill all fields
    cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input', { timeout: 10000 })
      .first()
      .type('Complete Test Lead')
    
    cy.get('.o_field_widget[name="phone"] input, input[name="phone"], div[name="phone"] input', { timeout: 10000 })
      .first()
      .type('+5511988777666')
    
    cy.get('.o_field_widget[name="email"] input, input[name="email"], div[name="email"] input', { timeout: 10000 })
      .first()
      .type('complete.cypress@example.com')
    
    // Click on Preferences tab
    cy.contains('a.nav-link, button', 'Preferences', { timeout: 10000 }).click()
    cy.wait(500)
    
    // Fill budget
    cy.get('.o_field_widget[name="budget_min"] input, input[name="budget_min"], div[name="budget_min"] input', { timeout: 10000 })
      .first()
      .clear()
      .type('300000')
    
    cy.get('.o_field_widget[name="budget_max"] input, input[name="budget_max"], div[name="budget_max"] input', { timeout: 10000 })
      .first()
      .clear()
      .type('500000')
    
    // Save
    cy.get('button.o_form_button_save', { timeout: 10000 })
      .first()
      .click()
    
    cy.wait(2000)
    
    // Verify saved
    cy.contains('Complete Test Lead', { timeout: 5000 }).should('be.visible')
  })

  it('Should update lead state from new to contacted', () => {
    // Navigate to leads
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Click on first lead to open form
    cy.get('.o_data_row', { timeout: 10000 })
      .first()
      .click()
    
    cy.wait(1500)
    cy.get('.o_form_view', { timeout: 10000 }).should('be.visible')
    
    // Click edit button
    cy.get('button.o_form_button_edit', { timeout: 10000 })
      .should('be.visible')
      .first()
      .click()
    
    cy.wait(500)
    
    // Change state to contacted (statusbar)
    cy.get('.o_statusbar_status button[data-value="contacted"]', { timeout: 10000 })
      .should('be.visible')
      .click()
    
    // Save
    cy.get('button.o_form_button_save', { timeout: 10000 })
      .first()
      .click()
    
    cy.wait(2000)
    
    // Verify state changed
    cy.get('.o_statusbar_status button.btn-primary', { timeout: 5000 })
      .should('contain', 'Contacted')
  })

  it('Should archive (soft delete) a lead', () => {
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Get initial lead count
    cy.get('.o_data_row', { timeout: 10000 }).its('length').then((initialCount) => {
      // Click on last lead
      cy.get('.o_data_row', { timeout: 10000 })
        .last()
        .click()
      
      cy.wait(1500)
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible')
      
      // Click Action menu
      cy.get('button.o_dropdown_toggler_btn', { timeout: 10000 })
        .contains('Action')
        .click()
      
      cy.wait(500)
      
      // Click Archive
      cy.get('.dropdown-item')
        .contains('Archive')
        .click()
      
      // Confirm archive (if confirmation dialog appears)
      cy.get('body').then(($body) => {
        if ($body.find('.modal .btn-primary').length > 0) {
          cy.get('.modal .btn-primary').contains('Ok').click()
        }
      })
      
      cy.wait(2000)
      
      // Should redirect to list
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
      
      // Verify lead count decreased
      cy.get('.o_data_row', { timeout: 10000 }).its('length').should('be.lessThan', initialCount)
    })
  })

  it('Should filter leads by state', () => {
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Click on search dropdown
    cy.get('.o_searchview_dropdown_toggler, .o_searchview_input', { timeout: 10000 })
      .first()
      .click()
    
    cy.wait(500)
    
    // Select filter "New"
    cy.get('.o_menu_item, .dropdown-item')
      .contains('New')
      .click({ force: true })
    
    cy.wait(2000)
    
    // Verify filter is applied (facet visible)
    cy.get('.o_searchview_facet, .o_facet_values', { timeout: 5000 })
      .should('be.visible')
  })

  it('Should search leads by name', () => {
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list')
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
    
    // Type in search box
    cy.get('.o_searchview_input input, input.o_searchview_input', { timeout: 10000 })
      .first()
      .clear()
      .type('Cypress{enter}')
    
    cy.wait(2000)
    
    // Verify search results contain "Cypress"
    cy.get('.o_data_row', { timeout: 10000 }).should('exist')
  })
})
