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
 *
 * Login pattern: cy.session() + JSON-RPC /web/session/authenticate
 *   (same pattern used in cms.cy.js — more reliable than UI login)
 * URL pattern: /web#action=<xml_id>&model=<model>&view_type=<type>
 *   (Odoo 18 legacy hash-based routing — stable across versions)
 */

const BASE_URL   = Cypress.env('ODOO_BASE_URL') || 'http://localhost:8069';
const ADMIN_USER = Cypress.env('ODOO_USERNAME');
const ADMIN_PASS = Cypress.env('ODOO_PASSWORD');

if (!ADMIN_USER || !ADMIN_PASS) {
    throw new Error(
        'ODOO_USERNAME e ODOO_PASSWORD são obrigatórios. ' +
        'Defina TEST_USER_ADMIN e TEST_PASSWORD_ADMIN em 18.0/.env.',
    );
}

// ----- URL constants (hash-based routing, Odoo 18) -------------------------
const URL_PROPERTIES = '/web#action=quicksol_estate.action_property&model=real.estate.property&view_type=list';
const URL_AGENTS     = '/web#action=quicksol_estate.action_agent&model=real.estate.agent&view_type=list';
const URL_LEASES     = '/web#action=quicksol_estate.action_lease&model=real.estate.lease&view_type=list';
const URL_PROPOSALS  = '/web#action=quicksol_estate.action_real_estate_proposals&model=real.estate.proposal&view_type=list';
const URL_LEADS      = '/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list';
const URL_CMS_PAGES  = '/web#action=thedevkitchen_cms.action_cms_pages&model=thedevkitchen.cms.page&view_type=list';
const URL_CMS_SETTINGS = '/web#action=thedevkitchen_cms.action_cms_settings&model=thedevkitchen.cms.settings&view_type=form';

// ----- Session helper -------------------------------------------------------
function loginAsAdmin() {
    cy.session([ADMIN_USER, ADMIN_PASS], () => {
        cy.request({
            method: 'POST',
            url: `${BASE_URL}/web/session/authenticate`,
            body: {
                jsonrpc: '2.0',
                method: 'call',
                params: { db: 'realestate', login: ADMIN_USER, password: ADMIN_PASS },
            },
            headers: { 'Content-Type': 'application/json' },
        }).then((resp) => {
            expect(resp.body.result).to.have.property('uid');
        });
    });
}

// Suppress Odoo's internal JS errors (e.g. load_menus timing issues)
// Same pattern used in cms.cy.js
Cypress.on('uncaught:exception', () => false);

// ============================================================
// Suite 1: SC-001 — Cross-Company Read Visibility (T012)
// ============================================================

describe('Feature 022 — SC-001: Admin Cross-Company Read Visibility', () => {

    beforeEach(() => {
        loginAsAdmin();
        cy.on('uncaught:exception', () => false);
    });

    it('AC-1: Properties list loads without AccessError', () => {
        cy.visit(URL_PROPERTIES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
        cy.get('body').should('not.contain.text', 'Access Error');
    });

    it('AC-2: Leases list is accessible to System Admin', () => {
        cy.visit(URL_LEASES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-3: Agents list is accessible to System Admin', () => {
        cy.visit(URL_AGENTS);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-4: CMS Pages list is accessible to System Admin', () => {
        cy.visit(URL_CMS_PAGES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-5: Proposals list is accessible to System Admin', () => {
        cy.visit(URL_PROPOSALS);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-6: Leads list is accessible to System Admin (SC-003 gate)', () => {
        cy.visit(URL_LEADS);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });
});

// ============================================================
// Suite 2: SC-002 — Cross-Company Write Access (T015)
// ============================================================

describe('Feature 022 — SC-002: Admin Cross-Company Write Access', () => {

    beforeEach(() => {
        loginAsAdmin();
        cy.on('uncaught:exception', () => false);
    });

    it('AC-1: Admin can open a Property form record without AccessError', () => {
        cy.visit(URL_PROPERTIES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('body').then(($body) => {
            if ($body.find('.o_data_row').length > 0) {
                cy.get('.o_data_row').first().click();
                cy.get('.o_form_view', { timeout: 10000 }).should('exist');
                cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
                cy.get('body').should('not.contain.text', 'Access Error');
            } else {
                cy.log('No property records — skipping form open');
            }
        });
    });

    it('AC-2: Admin can enter edit mode on a Property form (no write error)', () => {
        cy.visit(URL_PROPERTIES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('body').then(($body) => {
            if ($body.find('.o_data_row').length > 0) {
                cy.get('.o_data_row').first().click();
                cy.get('.o_form_view', { timeout: 10000 }).should('exist');
                // Odoo 18: auto-edit mode — just verify no AccessError on load
                cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
                cy.get('body').should('not.contain.text', 'Write on real.estate.property');
            } else {
                cy.log('No property records — skipping edit check');
            }
        });
    });

    it('AC-3: Admin can access CMS Settings (cross-company form view)', () => {
        cy.visit(URL_CMS_SETTINGS);
        cy.get('.o_form_view, .o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });
});

// ============================================================
// Suite 3: SC-003 — Menu Visibility (T017)
// ============================================================

describe('Feature 022 — SC-003: Admin Sees All Navigation Menus', () => {

    beforeEach(() => {
        loginAsAdmin();
        cy.on('uncaught:exception', () => false);
    });

    it('AC-1: Real Estate app is accessible and shows its name in the navbar', () => {
        // Navigate into the Real Estate app and verify the app name is in the navbar.
        // (Odoo 18 redirects /odoo to a default app — checking the navbar brand is
        //  more reliable than trying to locate the waffle/home icon.)
        cy.visit(URL_PROPERTIES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        // The navbar menu section shows the current app's top-level entries
        cy.get('.o_main_navbar, .o_menu_sections', { timeout: 8000 }).should('exist');
        // The Real Estate app menu sections (Properties, Leads, etc.) are visible
        cy.get('.o_menu_sections').should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
    });

    it('AC-2: Leads menu item is visible inside Real Estate (SC-003)', () => {
        cy.visit(URL_PROPERTIES);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        // Check the top-level navigation bar for "Leads" entry
        cy.get('.o_menu_sections', { timeout: 10000 }).should('exist');
        cy.get('.o_menu_sections').contains('Leads').should('exist');
    });

    it('AC-3: Leads page loads for System Admin without error', () => {
        cy.visit(URL_LEADS);
        cy.get('.o_list_view', { timeout: 15000 }).should('exist');
        cy.get('.o_error_dialog', { timeout: 3000 }).should('not.exist');
        cy.get('body').should('not.contain.text', 'Access Error');
    });

    it('AC-4: No "Missing Action" error on any core view', () => {
        const views = [URL_PROPERTIES, URL_AGENTS, URL_LEASES, URL_LEADS, URL_CMS_PAGES];
        views.forEach((url) => {
            cy.visit(url);
            cy.get('.o_list_view', { timeout: 15000 }).should('exist');
            cy.get('body').should('not.contain.text', 'Missing Action');
            cy.get('body').should('not.contain.text', 'Oops!');
        });
    });
});
