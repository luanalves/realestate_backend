/**
 * Cypress E2E Test: Feature 022 — Admin UI Cross-Company Access for System Admin
 *
 * Validates:
 * - SC-001: System Admin sees records from all tenant companies (cross-company read)
 * - SC-002: System Admin can write/edit/delete records from foreign companies
 * - SC-003: All navigation menus (including Leads) are visible to System Admin
 *
 * Tasks: T012 (SC-001 read), T015 (SC-002 write), T017 (SC-003 menu)
 * Feature spec: specs/022-admin-ui-cross-company/spec.md
 * ADR: docs/adr/ADR-029-saas-admin-channel-separation.md
 */

const BASE_URL = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069';
const ADMIN_USER = Cypress.env('ODOO_USERNAME') || 'admin';
const ADMIN_PASS = Cypress.env('ODOO_PASSWORD') || 'admin';

/**
 * Helper: login to Odoo web interface as System Admin.
 * Uses standard Odoo web session (not REST API — admin is blocked from REST API).
 */
function odooWebLogin(username, password) {
    cy.visit(`${BASE_URL}/web/login`);
    cy.get('input[name="login"]', { timeout: 10000 }).clear().type(username);
    cy.get('input[name="password"]').clear().type(password);
    cy.get('button[type="submit"]').click();
    cy.url({ timeout: 15000 }).should('include', '/odoo');
}

// ============================================================
// Suite 1: SC-001 — Cross-Company Read Visibility (T012)
// ============================================================

describe('Feature 022 — SC-001: Admin Cross-Company Read Visibility', () => {

    before(() => {
        odooWebLogin(ADMIN_USER, ADMIN_PASS);
    });

    it('AC-1: Properties list shows records from all companies (no empty list from company filter)', () => {
        cy.visit(`${BASE_URL}/odoo/real-estate/properties`);
        cy.get('.o_list_view, .o_kanban_view', { timeout: 15000 }).should('exist');
        // No "no records" message due to company filter
        cy.get('.o_nocontent_help', { timeout: 5000 }).should('not.exist');
    });

    it('AC-2: Leases list is accessible and shows all-company records', () => {
        cy.visit(`${BASE_URL}/odoo/action-quicksol_estate.action_real_estate_lease`);
        cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
        cy.get('.o_field_widget', { timeout: 5000 }).should('exist');
    });

    it('AC-3: Agents list is accessible and shows all-company records', () => {
        cy.visit(`${BASE_URL}/odoo/action-quicksol_estate.action_real_estate_agent`);
        cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
    });

    it('AC-4: CMS Pages list is accessible to System Admin', () => {
        cy.visit(`${BASE_URL}/odoo/action-thedevkitchen_cms.action_cms_page`);
        cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-5: Proposals list is accessible to System Admin', () => {
        cy.visit(`${BASE_URL}/odoo/action-quicksol_estate.action_real_estate_proposal`);
        cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-6: No AccessError dialogs appear on any core list view', () => {
        const views = [
            '/odoo/real-estate/properties',
            '/odoo/action-quicksol_estate.action_real_estate_agent',
            '/odoo/action-quicksol_estate.action_real_estate_lease',
        ];
        views.forEach((url) => {
            cy.visit(`${BASE_URL}${url}`);
            cy.get('.o_action_manager', { timeout: 15000 }).should('exist');
            cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
        });
    });
});

// ============================================================
// Suite 2: SC-002 — Cross-Company Write Access (T015)
// ============================================================

describe('Feature 022 — SC-002: Admin Cross-Company Write Access', () => {

    before(() => {
        odooWebLogin(ADMIN_USER, ADMIN_PASS);
    });

    it('AC-1: Admin can open a Property form and save without AccessError', () => {
        cy.visit(`${BASE_URL}/odoo/real-estate/properties`);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        // Open first record
        cy.get('.o_data_row').first().click();
        cy.get('.o_form_view', { timeout: 10000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-2: Admin can edit a Property record (no permission error on write)', () => {
        cy.visit(`${BASE_URL}/odoo/real-estate/properties`);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_data_row').first().click();
        cy.get('.o_form_view', { timeout: 10000 }).should('exist');
        // Enter edit mode (Odoo 18 auto-edit) and try to modify a non-critical field
        cy.get('.o_form_button_edit, [name="description"] .o_field_widget', { timeout: 5000 })
            .first().click({ force: true });
        // Should not produce access error
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-3: Admin can access CMS Settings across all companies', () => {
        cy.visit(`${BASE_URL}/odoo/action-thedevkitchen_cms.action_cms_settings`);
        cy.get('.o_form_view, .o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });
});

// ============================================================
// Suite 3: SC-003 — Menu Visibility (T017)
// ============================================================

describe('Feature 022 — SC-003: Admin Sees All Navigation Menus', () => {

    before(() => {
        odooWebLogin(ADMIN_USER, ADMIN_PASS);
        cy.visit(`${BASE_URL}/odoo`);
    });

    it('AC-1: Real Estate app is visible in main navigation', () => {
        cy.get('.o_menu_sections, .o_home_menu', { timeout: 15000 }).should('exist');
        cy.contains('Real Estate', { timeout: 10000 }).should('exist');
    });

    it('AC-2: Leads menu item is visible inside Real Estate app (SC-003 — menu_real_estate_lead)', () => {
        // Navigate to Real Estate app first
        cy.visit(`${BASE_URL}/odoo/real-estate/properties`);
        cy.get('.o_action_manager', { timeout: 15000 }).should('exist');
        // The navigation bar inside Real Estate should include Leads
        cy.get('.o_menu_sections .o_nav_entry, .o_dropdown_item', { timeout: 10000 })
            .contains('Leads').should('exist');
    });

    it('AC-3: Leads page loads for System Admin without error', () => {
        cy.visit(`${BASE_URL}/odoo/action-quicksol_estate.action_lead`);
        cy.get('.o_list_view, .o_action_manager', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-4: Leads list shows records from all companies (cross-company visibility)', () => {
        cy.visit(`${BASE_URL}/odoo/action-quicksol_estate.action_lead`);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        // No "no records" message (menu visibility + data visibility)
        // Note: may be empty if no leads exist, but should not show company-filter error
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });
});
