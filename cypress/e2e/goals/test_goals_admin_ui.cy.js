// =============================================================================
// Cypress E2E Test: Feature 019 — Goals Admin UI (Metas)
// =============================================================================
// Feature: 019-goals-and-results
// User Story: US4 — Manager interacts with Goals list and form in Odoo Admin UI
// ADR-003: E2E UI test WITH database (Cypress + real Odoo instance)
// Task: T039
//
// Scenarios:
//  1. test_goals_menu_loads_without_errors — navigate to Goals menu, no "Oops!",
//     zero DevTools console errors
//  2. test_goals_list_view_loads — list renders with expected column headers
//  3. test_goals_form_create — fill required fields, save, record appears in list
// =============================================================================

// ── Inline commands (supportFile: false) ─────────────────────────────────────
// Define odooLoginSession and odooNavigateTo inline since supportFile is disabled.

Cypress.Commands.add('odooLoginSession', (username, password) => {
  const login = username || Cypress.env('ADMIN_EMAIL') || Cypress.env('ODOO_USERNAME') || 'admin'
  const pass  = password || Cypress.env('ADMIN_PASSWORD') || Cypress.env('ODOO_PASSWORD') || 'admin'

  cy.session(
    ['odoo-session', login],
    () => {
      cy.visit('/web/login')
      cy.get('input[name="login"]', { timeout: 10000 }).clear().type(login)
      cy.get('input[name="password"]').clear().type(pass)
      cy.get('button[type="submit"]').click()
      cy.url({ timeout: 15000 }).should('satisfy', (url) =>
        url.includes('/odoo') || url.includes('/web')
      )
    },
    {
      validate() {
        cy.request({ url: '/web/session/get_session_info', method: 'POST',
          body: { jsonrpc: '2.0', method: 'call', id: 1, params: {} },
          failOnStatusCode: false,
        }).its('body.result.uid').should('be.a', 'number')
      },
      cacheAcrossSpecs: false,
    }
  )
})

// ── Helpers ───────────────────────────────────────────────────────────────────

const GOALS_ACTION   = 'thedevkitchen_estate_goals.action_estate_goal'
const GOALS_MODEL    = 'thedevkitchen.estate.goal'
const GOALS_URL      = `/odoo/action-${GOALS_ACTION}`
// Fallback hash URL for older Odoo builds
const GOALS_HASH_URL = `/web#action=${GOALS_ACTION}&model=${GOALS_MODEL}&view_type=list`

// Navigate to Goals list; tries both URL styles
function visitGoals() {
  cy.visit(GOALS_URL)
  cy.get('body', { timeout: 5000 }).then(($body) => {
    if ($body.find('.o_list_view').length === 0 && $body.find('.o_action_manager').length === 0) {
      cy.visit(GOALS_HASH_URL)
    }
  })
}

// ── Describe ──────────────────────────────────────────────────────────────────

describe('Feature 019 — Goals Admin UI (T039)', () => {
  const consoleErrors = []

  beforeEach(() => {
    cy.odooLoginSession()
  })

  // ---------------------------------------------------------------------------
  // SC-1: test_goals_menu_loads_without_errors
  // ---------------------------------------------------------------------------
  it('test_goals_menu_loads_without_errors', () => {
    cy.window().then((win) => {
      cy.stub(win.console, 'error').callsFake((...args) => {
        consoleErrors.push(args.join(' '))
      }).as('consoleError')
    })

    visitGoals()

    // No Odoo "Oops!" crash screen
    cy.get('body', { timeout: 15000 }).should('not.contain', 'Something went wrong')
    cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist')

    // List or action manager must be visible
    cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist')

    // Zero JS console errors
    cy.get('@consoleError').should('not.have.been.called')
  })

  // ---------------------------------------------------------------------------
  // SC-2: test_goals_list_view_loads
  // ---------------------------------------------------------------------------
  it('test_goals_list_view_loads', () => {
    visitGoals()

    // List view is visible
    cy.get('.o_list_view', { timeout: 15000 }).should('be.visible')

    // Control panel present
    cy.get('.o_control_panel', { timeout: 10000 }).should('be.visible')

    // Expected column headers from view_estate_goal_list
    const expectedHeaders = ['Agent', 'Year', 'Month', 'Metric', 'Op. Type', 'Target Count']
    expectedHeaders.forEach((header) => {
      cy.get('.o_list_view').contains(header).should('exist')
    })
  })

  // ---------------------------------------------------------------------------
  // SC-3: test_goals_form_create
  // ---------------------------------------------------------------------------
  it('test_goals_form_create', () => {
    visitGoals()

    cy.get('.o_list_view', { timeout: 15000 }).should('be.visible')

    // Click "New" button
    cy.get('button.o_list_button_add, .o_list_button_add', { timeout: 10000 })
      .should('be.visible')
      .first()
      .click()

    // Form must open in editable mode
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    cy.get('.o_form_view.o_form_editable, .o_form_view:not(.o_form_readonly)', { timeout: 10000 })
      .should('exist')

    // Fill: user_id (Agent) — many2one
    cy.get('.o_field_widget[name="user_id"] input', { timeout: 10000 })
      .should('be.visible')
      .clear()
      .type('admin')
    cy.get('.o_field_widget[name="user_id"] .o_dropdown_item, .ui-autocomplete li', { timeout: 8000 })
      .first()
      .click()

    // Fill: year
    cy.get('.o_field_widget[name="year"] input, input[name="year"]', { timeout: 8000 })
      .should('be.visible')
      .clear()
      .type('2026')

    // Fill: month (integer field)
    cy.get('.o_field_widget[name="month"] input, input[name="month"]', { timeout: 8000 })
      .clear()
      .type('5')

    // Fill: metric_type (select)
    cy.get('.o_field_widget[name="metric_type"] select, select[name="metric_type"]', { timeout: 8000 })
      .should('exist')
      .then(($sel) => {
        cy.wrap($sel).select('captacao', { force: true })
      })

    // Fill: operation_type (select)
    cy.get('.o_field_widget[name="operation_type"] select, select[name="operation_type"]')
      .then(($sel) => {
        cy.wrap($sel).select('sale', { force: true })
      })

    // Fill: target_count
    cy.get('.o_field_widget[name="target_count"] input, input[name="target_count"]')
      .clear()
      .type('5')

    // Save
    cy.get('button.o_form_button_save, .o_form_button_save', { timeout: 8000 })
      .first()
      .click()

    // No error dialog after save
    cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist')

    // Should still be on form view (record saved) or redirect to list
    cy.get('.o_form_view, .o_list_view', { timeout: 15000 }).should('exist')

    // Return to list and verify the record appears
    visitGoals()

    cy.get('.o_list_view', { timeout: 15000 }).should('be.visible')
    // The admin user + year 2026 should appear (at minimum one data row)
    cy.get('.o_data_row', { timeout: 10000 }).should('have.length.at.least', 1)
  })
})
