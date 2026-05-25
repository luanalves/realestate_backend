/**
 * cypress/e2e/views/cms.cy.js
 * US7 — CMS Admin UI Tests
 * Covers: T034
 *
 * Pre-conditions:
 *   - Odoo running, thedevkitchen_cms installed
 *   - CYPRESS_ODOO_URL, CYPRESS_ADMIN_USER, CYPRESS_ADMIN_PASSWORD set in cypress.env.json
 */

describe('CMS Admin UI — Odoo Views', () => {
  const baseUrl = Cypress.env('ODOO_URL') || 'http://localhost:8069';
  const adminUser = Cypress.env('ADMIN_USER') || 'admin';
  const adminPass = Cypress.env('ADMIN_PASSWORD') || 'admin';

  beforeEach(() => {
    // Login via session cookie
    cy.session([adminUser, adminPass], () => {
      cy.request({
        method: 'POST',
        url: `${baseUrl}/web/session/authenticate`,
        body: {
          jsonrpc: '2.0',
          method: 'call',
          params: {
            db: 'realestate',
            login: adminUser,
            password: adminPass,
          },
        },
        headers: { 'Content-Type': 'application/json' },
      }).then((resp) => {
        expect(resp.body.result).to.have.property('uid');
      });
    });
  });

  it('S1: CMS menu is visible and loads without JavaScript error', () => {
    const errors = [];
    cy.on('uncaught:exception', (err) => {
      errors.push(err.message);
      return false; // prevent Cypress from failing on handled errors
    });

    cy.visit(`${baseUrl}/odoo/cms`);
    cy.get('body').should('not.contain.text', 'Oops!');
    cy.wrap(errors).should('have.length', 0);
  });

  it('S2: Pages list view shows status badge and date columns', () => {
    cy.visit(`${baseUrl}/odoo/cms`);
    // Status column
    cy.get('.o_list_view').should('exist');
    cy.get('th').contains('Status').should('exist');
    // Optional date columns present
    cy.get('th').contains('Created At').should('exist');
  });

  it('S3: Page form shows statusbar with all 4 statuses', () => {
    cy.visit(`${baseUrl}/odoo/cms`);
    cy.get('.o_list_view .o_data_row').first().click();
    cy.get('.o_statusbar_status button, .o_statusbar_status .o_arrow_button').then(($buttons) => {
      const texts = [...$buttons].map((b) => b.textContent.trim().toLowerCase());
      ['draft', 'pending review', 'published', 'archived'].forEach((s) => {
        expect(texts.some((t) => t.includes(s.replace(' ', '_').replace(' ', ' ')))).to.be.true;
      });
    });
    // SEO tab
    cy.get('.o_notebook .nav-link').contains(/seo/i).click();
    cy.get('[name="title"]').should('exist');
    cy.get('[name="meta_description"]').should('exist');
  });

  it('S4: Templates form view loads without error', () => {
    const errors = [];
    cy.on('uncaught:exception', (err) => { errors.push(err.message); return false; });

    cy.visit(`${baseUrl}/odoo/cms/templates`);
    cy.get('body').should('not.contain.text', 'Oops!');
    cy.get('.o_list_view').should('exist');
    cy.wrap(errors).should('have.length', 0);
  });

  it('S5: Settings form shows company_slug and custom code section', () => {
    cy.visit(`${baseUrl}/odoo/cms/settings`);
    cy.get('[name="company_slug"]').should('exist');
    cy.get('[name="custom_css"]').should('exist');
    cy.get('[name="custom_js"]').should('exist');
  });

  it('S6: Zero JavaScript console errors during full CMS navigation', () => {
    const errors = [];
    cy.on('uncaught:exception', (err) => { errors.push(err.message); return false; });

    cy.visit(`${baseUrl}/odoo/cms`);
    cy.get('.o_list_view').should('exist');

    cy.visit(`${baseUrl}/odoo/cms/templates`);
    cy.get('.o_list_view').should('exist');

    cy.visit(`${baseUrl}/odoo/cms/media`);
    cy.get('.o_list_view').should('exist');

    cy.visit(`${baseUrl}/odoo/cms/settings`);
    cy.get('[name="company_slug"]').should('exist');

    cy.wrap(errors, { log: false }).then((errs) => {
      if (errs.length > 0) {
        cy.log('JS errors found:', errs.join('\n'));
      }
      expect(errs).to.have.length(0);
    });
  });
});
