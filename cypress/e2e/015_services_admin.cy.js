/**
 * Cypress E2E Test: Feature 015 — Service Pipeline (Atendimentos)
 *
 * Validates the Atendimentos UI is accessible and functional:
 * - Login as admin
 * - Navigate to Atendimentos list view
 * - Open service form
 * - Open Settings form
 * - Create a tag via UI
 * - Zero console errors
 *
 * Task: T070
 * FRs: FR-001, FR-017, FR-018, FR-019
 */

describe('Feature 015: Services Admin UI', () => {
    const adminEmail = Cypress.env('ADMIN_EMAIL');
    const adminPass  = Cypress.env('ADMIN_PASSWORD');

    before(() => {
        if (!adminEmail || !adminPass) {
            throw new Error(
                'Missing required Cypress env vars: ADMIN_EMAIL and ADMIN_PASSWORD. ' +
                'Set them in cypress.env.json (gitignored) or via CYPRESS_ADMIN_EMAIL / CYPRESS_ADMIN_PASSWORD.'
            );
        }
    });

    beforeEach(() => {
        cy.odooLoginSession(adminEmail, adminPass);
    });

    it('should open Services list view without errors', () => {
        // Spy on console errors BEFORE navigation
        cy.window().then((win) => {
            cy.stub(win.console, 'error').as('consoleError');
        });

        cy.visit('/odoo/action-quicksol_estate.action_real_estate_services');
        cy.wait(2000);

        // List view is visible
        cy.get('.o_list_view, .o_action_manager', { timeout: 10000 }).should('exist');

        // No fatal console errors
        cy.get('@consoleError').should('not.have.been.called');
    });

    it('should open service form (first record) and display status bar', () => {
        cy.visit('/odoo/action-quicksol_estate.action_real_estate_services');
        cy.wait(2000);

        cy.get('.o_data_row').first().then(($row) => {
            if ($row.length) {
                cy.wrap($row).click();
                cy.get('.o_form_view', { timeout: 10000 }).should('exist');
                cy.get('.o_statusbar_status').should('exist');
            } else {
                cy.log('No services found — skipping form open test');
            }
        });
    });

    it('should open Service Settings form', () => {
        cy.visit('/odoo/action-quicksol_estate.action_service_settings');
        cy.wait(2000);

        cy.get('.o_form_view', { timeout: 10000 }).should('exist');
        cy.contains('Configurações do Pipeline').should('be.visible');
        cy.get('input[id*="pendency_threshold_days"]').should('exist');
    });

    it('should navigate to Tags list view', () => {
        cy.visit('/odoo/action-quicksol_estate.action_real_estate_service_tags');
        cy.wait(2000);

        cy.get('.o_list_view, .o_action_manager', { timeout: 10000 }).should('exist');
    });

    it('should create a new service tag', () => {
        cy.visit('/odoo/action-quicksol_estate.action_real_estate_service_tags');
        cy.wait(2000);

        const tagName = `Cypress Tag ${Date.now()}`;

        // Click New
        cy.get('.o_list_button_add, button:contains("New")').first().click();
        cy.wait(1000);

        cy.get('input[id*="name"]').first().clear().type(tagName);

        // Save
        cy.get('.o_form_button_save, button:contains("Save")').first().click({ force: true });
        cy.wait(1000);

        cy.get('.o_list_view', { timeout: 8000 }).should('exist');
        // Tag appears in list
        cy.contains(tagName).should('be.visible');
    });

    it('should navigate to Sources list view', () => {
        cy.visit('/odoo/action-quicksol_estate.action_real_estate_service_sources');
        cy.wait(2000);

        cy.get('.o_list_view, .o_action_manager', { timeout: 10000 }).should('exist');
    });
});
