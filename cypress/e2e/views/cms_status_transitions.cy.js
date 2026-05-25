/**
 * cypress/e2e/views/cms_status_transitions.cy.js
 * Feature 021 — CMS Status Transitions & Seed Content
 *
 * Validates:
 *   1. Status transition buttons (Submit for Review, Publish, Archive, Reset to Draft)
 *      appear/hide correctly based on current page status
 *   2. Seed demo pages have html_content visible in the Odoo form
 *   3. The full transition workflow: draft → pending_review → published → archived → draft
 *
 * Pre-conditions:
 *   - Odoo running, thedevkitchen_cms installed with demo data (cms_demo_pages.xml loaded)
 *   - cypress.env.json must define ODOO_USERNAME, ODOO_PASSWORD, ODOO_BASE_URL
 */

const BASE_URL = Cypress.env('ODOO_BASE_URL');
const USER     = Cypress.env('ODOO_USERNAME');
const PASS     = Cypress.env('ODOO_PASSWORD');

before(() => {
  if (!BASE_URL || !USER || !PASS) {
    throw new Error(
      'Missing required Cypress env vars. ' +
      'Define ODOO_BASE_URL, ODOO_USERNAME and ODOO_PASSWORD in cypress.env.json.',
    );
  }
});

const CMS_PAGES = '/web#action=thedevkitchen_cms.action_cms_pages&model=thedevkitchen.cms.page&view_type=list';

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Authenticate via JSON-RPC and persist session. */
function login() {
  cy.session([USER, PASS], () => {
    cy.request({
      method: 'POST',
      url: `${BASE_URL}/web/session/authenticate`,
      body: {
        jsonrpc: '2.0',
        method: 'call',
        params: { db: 'realestate', login: USER, password: PASS },
      },
      headers: { 'Content-Type': 'application/json' },
    }).then((resp) => {
      expect(resp.body.result).to.have.property('uid');
    });
  });
}

/** Open CMS Pages list and click the row whose name contains the given text. */
function openPageByName(nameFragment) {
  cy.visit(CMS_PAGES);
  cy.get('.o_list_view', { timeout: 15000 }).should('exist');
  cy.get('.o_data_row').contains(nameFragment).click();
  cy.get('.o_form_view', { timeout: 10000 }).should('exist');
}

// ─── Suite 1: Button visibility per status ────────────────────────────────────

describe('CMS Status Transitions — button visibility', () => {

  beforeEach(() => {
    login();
    cy.on('uncaught:exception', () => false);
  });

  it('S1: Draft page shows "Submit for Review" and "Publish" buttons', () => {
    openPageByName('Entre em Contato'); // seed draft page
    cy.get('button').contains('Submit for Review').should('exist').and('be.visible');
    cy.get('button').contains('Publish').should('exist').and('be.visible');
    cy.get('button').contains('Archive').should('exist').and('be.visible');
    cy.get('button').contains('Reset to Draft').should('not.exist');
  });

  it('S2: Pending Review page shows "Publish", "Archive" and "Reset to Draft"', () => {
    openPageByName('Dicas para Comprar'); // seed pending_review page
    cy.get('button').contains('Submit for Review').should('not.exist');
    cy.get('button').contains('Publish').should('exist').and('be.visible');
    cy.get('button').contains('Archive').should('exist').and('be.visible');
    cy.get('button').contains('Reset to Draft').should('exist').and('be.visible');
  });

  it('S3: Published page shows only "Archive" button', () => {
    openPageByName('Sobre Nós'); // seed published page
    cy.get('button').contains('Submit for Review').should('not.exist');
    // Use exact regex to avoid case-insensitive match on "published" in Odoo notifications
    cy.contains('button', /^Publish$/).should('not.exist');
    cy.get('button').contains('Archive').should('exist').and('be.visible');
    cy.get('button').contains('Reset to Draft').should('not.exist');
  });

  it('S4: Archived page shows only "Reset to Draft" button', () => {
    openPageByName('Promoção de Verão'); // seed archived page
    cy.get('button').contains('Submit for Review').should('not.exist');
    // Use exact regex to avoid case-insensitive match on Odoo status notifications
    cy.contains('button', /^Publish$/).should('not.exist');
    cy.contains('button', /^Archive$/).should('not.exist');
    cy.get('button').contains('Reset to Draft').should('exist').and('be.visible');
  });

});

// ─── Suite 2: Transition workflow ─────────────────────────────────────────────

describe('CMS Status Transitions — workflow execution', () => {

  beforeEach(() => {
    login();
    cy.on('uncaught:exception', () => false);
  });

  it('S5: "Submit for Review" changes status from Draft to Pending Review', () => {
    openPageByName('Entre em Contato');
    // Confirm starting state
    cy.get('.o_statusbar_status .o_arrow_button_current, .o_statusbar_status button.active')
      .invoke('text').then((txt) => {
        expect(txt.trim().toLowerCase()).to.match(/draft/i);
      });

    cy.get('button').contains('Submit for Review').click();

    // After transition: statusbar should show Pending Review as current
    cy.get('.o_statusbar_status', { timeout: 8000 })
      .contains(/pending.review/i)
      .closest('button, .o_arrow_button')
      .should('have.class', 'o_arrow_button_current').then(() => {
        // Restore state: reset to draft so the test is idempotent
        cy.get('button').contains('Reset to Draft').click();
      });
  });

  it('S6: "Publish" on a Pending Review page sets status to Published', () => {
    openPageByName('Dicas para Comprar');

    // Ensure we are in pending_review (reset if needed)
    cy.get('.o_form_view').then(($form) => {
      if ($form.find('button:contains("Submit for Review")').length) {
        cy.get('button').contains('Submit for Review').click();
        cy.get('.o_form_view', { timeout: 8000 }).should('exist');
      }
    });

    cy.contains('button', /^Publish$/).should('be.visible').click();

    cy.get('.o_statusbar_status', { timeout: 8000 })
      .contains(/published/i)
      .closest('button, .o_arrow_button')
      .should('have.class', 'o_arrow_button_current');

    // Restore: archive then reset to pending_review is not possible —
    // restore to draft via Archive then Reset to Draft
    cy.get('button').contains('Archive').click();
    cy.get('button', { timeout: 5000 }).contains('Reset to Draft').click();
    cy.get('button').contains('Submit for Review').click(); // back to pending_review
  });

  it('S7: "Archive" on a Published page sets status to Archived', () => {
    openPageByName('Serviços Imobiliários'); // seed published page

    cy.get('button').contains('Archive').should('be.visible').click();

    cy.get('.o_statusbar_status', { timeout: 8000 })
      .contains(/archived/i)
      .closest('button, .o_arrow_button')
      .should('have.class', 'o_arrow_button_current');

    // Restore to published
    cy.get('button').contains('Reset to Draft').click();
    cy.get('button').contains('Publish').click();
  });

  it('S8: "Reset to Draft" on an Archived page sets status to Draft', () => {
    openPageByName('Promoção de Verão'); // seed archived page

    cy.get('button').contains('Reset to Draft').should('be.visible').click();

    cy.get('.o_statusbar_status', { timeout: 8000 })
      .contains(/draft/i)
      .closest('button, .o_arrow_button')
      .should('have.class', 'o_arrow_button_current');

    // Restore to archived
    cy.get('button').contains('Archive').click();
  });

});

// ─── Suite 3: Seed pages have html_content ────────────────────────────────────

describe('CMS Seed Pages — html_content is present', () => {

  beforeEach(() => {
    login();
    cy.on('uncaught:exception', () => false);
  });

  const seedPages = [
    { name: 'Sobre Nós',              expectedText: 'Imobiliária Seed' },
    { name: 'Serviços Imobiliários',  expectedText: 'Compra e Venda'   },
    { name: 'Dicas para Comprar',     expectedText: 'Primeiro Imóvel'  },
    { name: 'Entre em Contato',       expectedText: 'Contato'          },
    { name: 'Promoção de Verão',      expectedText: 'Promoção'         },
  ];

  seedPages.forEach(({ name, expectedText }, index) => {
    it(`S${index + 9}: "${name}" has html_content visible in Content tab`, () => {
      openPageByName(name);

      // Activate Content tab
      cy.get('.o_notebook .nav-link').contains('Content').click();

      // The html_content field must exist and render an editable area
      cy.get('[name="html_content"]', { timeout: 8000 }).should('exist');

      // The editable area must not be empty
      cy.get('[name="html_content"] .odoo-editor-editable, [name="html_content"] .o_editable, [name="html_content"] div[contenteditable]')
        .should('exist')
        .invoke('text')
        .should('not.be.empty');
    });
  });

});
