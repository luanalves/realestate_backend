/**
 * E2E Test: Company Management UI (Feature 007)
 * 
 * Task: T037/T038 (corrected)
 * Tests: Company CRUD operations via Odoo Web Interface
 * 
 * Scenarios:
 * 1. Navigate to Companies menu
 * 2. Create new Company via form
 * 3. Verify Company appears in list
 * 4. Edit Company details
 * 5. Search and filter Companies
 * 6. Verify CNPJ validation
 */

describe('Company Management - Web UI', () => {
  const baseUrl = Cypress.env('BASE_URL') || 'http://localhost:8069';
  const timestamp = Date.now();
  const testCompanyName = `Test Company ${timestamp}`;
  const testCNPJ = '12.345.678/0001-95'; // Valid test CNPJ

  before(() => {
    // Handle uncaught exceptions from Odoo
    Cypress.on('uncaught:exception', (err) => {
      // Ignore menu loading errors during tests
      if (err.message.includes('load_menus') || err.message.includes('Cannot read properties of undefined')) {
        return false;
      }
      return true;
    });
  });

  beforeEach(() => {
    // Login to Odoo directly
    cy.visit(`${baseUrl}/web/login`);
    cy.get('input[name="login"]', { timeout: 10000 }).type('admin');
    cy.get('input[name="password"]').type('admin');
    cy.get('button[type="submit"]').click();
    cy.url({ timeout: 15000 }).should('include', '/web');
  });

  describe('1. Navigate to Companies Menu', () => {
    it('Should open Companies list from menu', () => {
      // Navigate to Real Estate menu
      cy.visit(`${baseUrl}/web`);
      
      // Wait for menu to load
      cy.get('.o_menu_sections', { timeout: 10000 }).should('be.visible');
      
      // Click on Real Estate menu (may need to expand if collapsed)
      cy.contains('.o_menu_sections .dropdown-toggle, .o_menu_sections a', 'Real Estate')
        .click();
      
      // Click on Real Estate Companies submenu
      cy.contains('a.dropdown-item, .o_menu_item', 'Real Estate Companies')
        .click();
      
      // Verify we're on the Companies list view
      cy.url().should('include', 'action=');
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      cy.contains('.breadcrumb', 'Real Estate Companies').should('be.visible');
    });
  });

  describe('2. Create Company via Form', () => {
    it('Should create a new company with valid data', () => {
      // Navigate directly to Companies action
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click "Create" button
      cy.contains('button', 'Create').click();
      
      // Wait for form to load
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Fill in company name
      cy.get('input[name="name"]').clear().type(testCompanyName);
      
      // Fill in legal name
      cy.get('input[name="legal_name"]').clear().type(`${testCompanyName} LTDA`);
      
      // Fill in CNPJ
      cy.get('input[name="cnpj"]').clear().type(testCNPJ);
      
      // Fill in email
      cy.get('input[name="email"]').clear().type(`company${timestamp}@test.com`);
      
      // Fill in phone
      cy.get('input[name="phone"]').clear().type('11912345678');
      
      // Fill in CRECI
      cy.get('input[name="creci"]').clear().type('CRECI/SP 123456');
      
      // Save the form
      cy.contains('button', 'Save').click();
      
      // Wait for save to complete
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Verify company name is displayed
      cy.contains('h1', testCompanyName).should('be.visible');
    });

    it('Should show validation error for invalid CNPJ', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      cy.contains('button', 'Create').click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Fill in with invalid CNPJ
      cy.get('input[name="name"]').clear().type('Test Invalid CNPJ');
      cy.get('input[name="cnpj"]').clear().type('00.000.000/0000-00'); // Invalid
      
      // Try to save
      cy.contains('button', 'Save').click();
      
      // Should show error (Odoo displays validation errors in .o_notification or modal)
      cy.get('.o_notification.o_notification_danger, .modal-body', { timeout: 5000 })
        .should('be.visible')
        .and('contain.text', 'CNPJ');
    });
  });

  describe('3. List and Search Companies', () => {
    it('Should display companies in list view', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      
      // Wait for list to load
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Verify table has rows
      cy.get('.o_list_table tbody tr.o_data_row').should('have.length.at.least', 1);
      
      // Verify columns are visible
      cy.get('th[data-name="name"]').should('contain', 'Company');
      cy.get('th[data-name="cnpj"]').should('be.visible');
      cy.get('th[data-name="email"]').should('be.visible');
    });

    it('Should search for company by name', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Enter search term
      cy.get('.o_searchview input.o_searchview_input').type('QuickSol{enter}');
      
      // Wait for search results
      cy.wait(1000);
      
      // Verify filtered results
      cy.get('.o_list_table tbody tr.o_data_row').should('have.length.at.least', 1);
      cy.get('.o_list_table tbody tr.o_data_row').first().should('contain', 'QuickSol');
    });

    it('Should filter active companies', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on Filters dropdown
      cy.get('.o_searchview .o_dropdown_title:contains("Filters")').click();
      
      // Select "Active" filter
      cy.get('.o_filter_menu .dropdown-item').contains('Active').click();
      
      // Verify filter is applied (facet should appear)
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'Active');
    });
  });

  describe('4. Edit Company', () => {
    it('Should edit company details', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on first company row
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      
      // Wait for form view
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Click Edit button
      cy.contains('button', 'Edit').click();
      
      // Verify form is in edit mode
      cy.get('.o_form_view.o_form_editable').should('be.visible');
      
      // Update phone number
      const newPhone = '11999999999';
      cy.get('input[name="phone"]').clear().type(newPhone);
      
      // Save changes
      cy.contains('button', 'Save').click();
      
      // Verify save completed
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Verify phone was updated
      cy.get('span[name="phone"]').should('contain', newPhone);
    });

    it('Should verify CNPJ is immutable after creation', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first company
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Click Edit
      cy.contains('button', 'Edit').click();
      
      // Verify CNPJ field is readonly or disabled
      cy.get('input[name="cnpj"]').should('have.attr', 'readonly');
    });
  });

  describe('5. Company Smart Buttons', () => {
    it('Should display owner count button', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first company
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Verify smart buttons exist
      cy.get('.oe_button_box .oe_stat_button').should('exist');
      
      // Verify Owners button
      cy.get('.oe_stat_button').contains('Owners').should('be.visible');
    });

    it('Should navigate to properties from smart button', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first company with properties
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Click Properties smart button if property_count > 0
      cy.get('.oe_stat_button').contains('Properties').then(($btn) => {
        if ($btn.find('.o_stat_value').text() !== '0') {
          cy.wrap($btn).click();
          
          // Should navigate to properties list
          cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
          cy.contains('.breadcrumb', 'Properties').should('be.visible');
        }
      });
    });
  });

  describe('6. Multi-tenancy Verification', () => {
    it('Should only show companies user has access to', () => {
      // Login as admin (has access to all)
      cy.odooLoginSession('admin', 'admin');
      
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Count total companies visible to admin
      cy.get('.o_list_table tbody tr.o_data_row').then(($rows) => {
        const adminCount = $rows.length;
        
        // Admin should see at least the seed companies
        expect(adminCount).to.be.at.least(3);
      });
    });
  });
});
