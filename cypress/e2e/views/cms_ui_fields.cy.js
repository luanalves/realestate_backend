/**
 * cypress/e2e/views/cms_ui_fields.cy.js
 * Feature 021 — CMS Admin UI Fields
 *
 * Validates the Odoo admin UI fields that differ from the REST API:
 *   - CmsPage.html_content   → rich HTML editor (Content tab) vs Puck JSON tab (API)
 *   - CmsTemplate.html_content → same split
 *   - CmsMedia.image_1920   → binary image preview widget (visible for images only)
 *
 * Pre-conditions:
 *   - Odoo running, thedevkitchen_cms installed and upgraded (html_content column exists)
 *   - admin user (base.group_system)
 */

const BASE_URL = 'http://localhost:8069';
const USER     = Cypress.env('ODOO_USERNAME') || 'admin';
const PASS     = Cypress.env('ODOO_PASSWORD') || 'admin';

const CMS_PAGES     = '/web#action=thedevkitchen_cms.action_cms_pages&model=thedevkitchen.cms.page&view_type=list';
const CMS_TEMPLATES = '/web#action=thedevkitchen_cms.action_cms_templates&model=thedevkitchen.cms.template&view_type=list';
const CMS_MEDIA     = '/web#action=thedevkitchen_cms.action_cms_media&model=thedevkitchen.cms.media&view_type=list';

describe('CMS UI Fields — html_content e image_1920', () => {

  beforeEach(() => {
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
    cy.on('uncaught:exception', () => false);
  });

  // ─── CMS PAGE: html_content ──────────────────────────────────────────────

  describe('CMS Page — HTML content tab', () => {

    beforeEach(() => {
      cy.visit(CMS_PAGES);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');

      // Open first row, or create a new page
      cy.get('body').then(($body) => {
        if ($body.find('.o_data_row').length > 0) {
          cy.get('.o_data_row').first().click();
        } else {
          cy.get('.o_list_button_add, button:contains("New")').first().click();
        }
      });
      cy.get('.o_form_view', { timeout: 10000 }).should('exist');
    });

    it('S1: Content tab exists and is active by default', () => {
      cy.get('.o_notebook .nav-link').contains('Content').should('exist');
      cy.get('.o_notebook .nav-link.active').contains('Content').should('exist');
    });

    it('S2: html_content field renders as HTML editor (not plain text area)', () => {
      cy.get('.o_notebook .nav-link').contains('Content').click();
      // Odoo renders fields.Html as .o_field_html
      cy.get('[name="html_content"]', { timeout: 8000 }).should('exist');
      cy.get('[name="html_content"] .odoo-editor-editable, [name="html_content"] .o_editable, [name="html_content"] div[contenteditable]')
        .should('exist');
    });

    it('S3: Puck JSON (API) tab exists and contains content_ids grid', () => {
      cy.get('.o_notebook .nav-link').contains('Puck JSON (API)').should('exist');
      cy.get('.o_notebook .nav-link').contains('Puck JSON (API)').click();
      // content_ids is a One2many list
      cy.get('.o_notebook .tab-pane.active .o_field_one2many, .o_notebook .tab-pane.active .o_list_renderer')
        .should('exist');
    });

    it('S4: html_content tab and Puck JSON tab are distinct (API and UI separation)', () => {
      // Content tab must NOT show a raw text widget (that is for Puck JSON)
      cy.get('.o_notebook .nav-link').contains('Content').click();
      cy.get('.o_notebook .tab-pane.active [name="html_content"]').should('exist');
      // html_content should not be a plain <textarea> — it must be an HTML editor
      cy.get('.o_notebook .tab-pane.active [name="html_content"] textarea').should('not.exist');
    });

  });

  // ─── CMS TEMPLATE: html_content ──────────────────────────────────────────

  describe('CMS Template — HTML content tab', () => {

    beforeEach(() => {
      cy.visit(CMS_TEMPLATES);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');

      cy.get('body').then(($body) => {
        if ($body.find('.o_data_row').length > 0) {
          cy.get('.o_data_row').first().click();
        } else {
          cy.get('.o_list_button_add, button:contains("New")').first().click();
        }
      });
      cy.get('.o_form_view', { timeout: 10000 }).should('exist');
    });

    it('S5: Template form has Content tab with HTML editor', () => {
      cy.get('.o_notebook .nav-link').contains('Content').should('exist');
      cy.get('.o_notebook .nav-link').contains('Content').click();
      cy.get('[name="html_content"]', { timeout: 8000 }).should('exist');
      cy.get('[name="html_content"] .odoo-editor-editable, [name="html_content"] .o_editable, [name="html_content"] div[contenteditable]')
        .should('exist');
    });

    it('S6: Template form has Puck JSON (API) tab', () => {
      cy.get('.o_notebook .nav-link').contains('Puck JSON (API)').should('exist');
    });

    it('S7: html_content and Puck JSON tabs are distinct in template form', () => {
      cy.get('.o_notebook .nav-link').contains('Content').click();
      // html_content must not be a plain textarea
      cy.get('.o_notebook .tab-pane.active [name="html_content"] textarea').should('not.exist');
    });

  });

  // ─── CMS MEDIA: image_1920 preview ───────────────────────────────────────

  describe('CMS Media — image preview field', () => {

    it('S8: Media list view loads without error', () => {
      cy.visit(CMS_MEDIA);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');
      cy.get('body').should('not.contain.text', 'Missing Action');
    });

    it('S9: Media form shows image preview field (image_1920) when media_type is image', () => {
      cy.visit(CMS_MEDIA);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');

      // Look for an existing media record with media_type = image
      cy.get('body').then(($body) => {
        if ($body.find('.o_data_row').length > 0) {
          cy.get('.o_data_row').first().click();
          cy.get('.o_form_view', { timeout: 10000 }).should('exist');

          cy.get('[name="media_type"]').invoke('text').then((mediaTypeText) => {
            if (mediaTypeText.trim().toLowerCase().includes('image')) {
              // image_1920 must be visible for image media type
              cy.get('[name="image_1920"]').should('exist');
              cy.get('[name="image_1920"]').should('be.visible');
            } else {
              // For non-image types the field is present but invisible (CSS hidden)
              cy.get('[name="image_1920"]').should('not.be.visible');
            }
          });
        } else {
          // No records yet — just verify the media list view loaded correctly
          cy.get('.o_list_view').should('exist');
          cy.log('No media records to open — skipping form check');
        }
      });
    });

    it('S10: Media form shows "File URL (API)" label for url field', () => {
      cy.visit(CMS_MEDIA);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');

      cy.get('body').then(($body) => {
        if ($body.find('.o_data_row').length > 0) {
          cy.get('.o_data_row').first().click();
          cy.get('.o_form_view', { timeout: 10000 }).should('exist');
          // The url field label was renamed to "File URL (API)" to make the API/UI split explicit
          cy.get('.o_form_view').contains('File URL (API)').should('exist');
        } else {
          cy.log('No media records — skipping label check');
        }
      });
    });

    it('S11: image_1920 field is NOT a plain text or char input (it is a binary widget)', () => {
      cy.visit(CMS_MEDIA);
      cy.get('.o_list_view', { timeout: 15000 }).should('exist');

      cy.get('body').then(($body) => {
        if ($body.find('.o_data_row').length > 0) {
          cy.get('.o_data_row').first().click();
          cy.get('.o_form_view', { timeout: 10000 }).should('exist');

          cy.get('[name="media_type"]').invoke('text').then((mediaTypeText) => {
            if (mediaTypeText.trim().toLowerCase().includes('image')) {
              // Must render as image widget, not as text input
              cy.get('[name="image_1920"] input[type="text"]').should('not.exist');
              cy.get('[name="image_1920"] img, [name="image_1920"] .o_field_image').should('exist');
            }
          });
        } else {
          cy.log('No media records — skipping widget type check');
        }
      });
    });

  });

});
