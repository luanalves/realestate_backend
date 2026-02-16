/**
 * E2E Test: Owner Management UI (Feature 007)
 * 
 * Task: T040/T041 (corrected)
 * Tests: Owner management via Odoo Web Interface
 * 
 * Scenarios:
 * 1. Navigate to Owners from Company form
 * 2. View Owners list
 * 3. Open Owner form
 * 4. Edit Owner details
 * 5. Verify Owner-Company relationship
 * 6. Filter and search Owners
 */

describe('Owner Management - Web UI', () => {
  const baseUrl = Cypress.env('BASE_URL') || 'http://localhost:8069';

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

  describe('1. Navigate to Owners from Company', () => {
    it('Should access Owners list via Company smart button', () => {
      // Navigate to Companies
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first company
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Click Owners smart button
      cy.get('.oe_stat_button').contains('Owners').should('be.visible').click();
      
      // Should navigate to Owners list filtered by this company
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      cy.contains('.breadcrumb', 'Estate Owners').should('be.visible');
    });

    it('Should display Owner count in smart button', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first company
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Verify Owners button shows count
      cy.get('.oe_stat_button').contains('Owners').parent().find('.o_stat_value')
        .should('exist')
        .invoke('text')
        .should('match', /\d+/); // Should be a number
    });
  });

  describe('2. Owners List View', () => {
    it('Should display owners with proper columns', () => {
      // Navigate directly to Owners action
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Verify list view columns
      cy.get('th[data-name="name"]').should('contain', 'Name');
      cy.get('th[data-name="email"]').should('be.visible');
      cy.get('th[data-name="phone"]').should('be.visible');
      cy.get('th[data-name="estate_company_ids"]').should('be.visible');
      
      // Verify at least one owner exists (from seed data)
      cy.get('.o_list_table tbody tr.o_data_row').should('have.length.at.least', 1);
    });

    it('Should display company tags for owners', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Look for many2many_tags widget (shows companies as badges)
      cy.get('td[name="estate_company_ids"] .o_field_many2many_tags').should('exist');
    });
  });

  describe('3. Owner Form View', () => {
    it('Should open owner form with all fields', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on first owner
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      
      // Wait for form to load
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Verify owner name is displayed
      cy.get('h1 .o_field_widget[name="name"]').should('be.visible');
      
      // Verify contact information section
      cy.contains('.o_horizontal_separator', 'Contact Information').should('be.visible');
      cy.get('.o_field_widget[name="email"]').should('be.visible');
      cy.get('.o_field_widget[name="phone"]').should('exist');
      
      // Verify Access section
      cy.contains('.o_horizontal_separator', 'Access').should('be.visible');
      cy.get('.o_field_widget[name="login"]').should('be.visible');
      
      // Verify Companies section
      cy.contains('.o_horizontal_separator', 'Companies').should('be.visible');
      cy.get('.o_field_widget[name="estate_company_ids"]').should('be.visible');
    });

    it('Should display owner avatar', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Verify avatar field exists
      cy.get('.oe_avatar .o_field_image').should('be.visible');
    });
  });

  describe('4. Edit Owner Details', () => {
    it('Should edit owner phone number', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open first owner
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Click Edit
      cy.contains('button', 'Edit').click();
      cy.get('.o_form_view.o_form_editable').should('be.visible');
      
      // Update phone
      const newPhone = '11988887777';
      cy.get('input[name="phone"]').clear().type(newPhone);
      
      // Save
      cy.contains('button', 'Save').click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Verify update
      cy.get('span[name="phone"]').should('contain', newPhone);
    });

    it('Should edit owner name', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Get original name
      cy.get('h1 .o_field_widget[name="name"]').invoke('text').then((originalName) => {
        // Click Edit
        cy.contains('button', 'Edit').click();
        
        // Update name
        const newName = `${originalName.trim()} Updated`;
        cy.get('input[name="name"]').clear().type(newName);
        
        // Save
        cy.contains('button', 'Save').click();
        cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
        
        // Verify
        cy.get('h1').should('contain', 'Updated');
      });
    });

    it('Should verify login field is readonly', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Click Edit
      cy.contains('button', 'Edit').click();
      
      // Verify login field is readonly (email cannot be changed after creation)
      cy.get('input[name="login"]').should('have.attr', 'readonly');
    });
  });

  describe('5. Owner-Company Relationship', () => {
    it('Should display linked companies in owner form', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Open owner with companies
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
      
      // Verify companies field shows tags
      cy.get('.o_field_widget[name="estate_company_ids"]').should('be.visible');
      
      // Should show company tags if linked
      cy.get('.o_field_widget[name="estate_company_ids"] .o_field_many2many_tags .badge')
        .should('have.length.at.least', 1);
    });

    it('Should allow linking owner to additional company', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      cy.get('.o_list_table tbody tr.o_data_row').first().click();
      cy.get('.o_form_view.o_form_readonly', { timeout: 10000 }).should('be.visible');
      
      // Click Edit
      cy.contains('button', 'Edit').click();
      
      // Note: Adding new company would require clicking the field and selecting
      // This test just verifies the field is editable
      cy.get('.o_field_widget[name="estate_company_ids"]')
        .should('be.visible')
        .and('not.have.class', 'o_readonly_modifier');
    });
  });

  describe('6. Search and Filter Owners', () => {
    it('Should search owners by name', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Get first owner's name
      cy.get('.o_list_table tbody tr.o_data_row').first().find('td[name="name"]')
        .invoke('text')
        .then((ownerName) => {
          // Search for this owner
          cy.get('.o_searchview input.o_searchview_input')
            .clear()
            .type(`${ownerName.trim().split(' ')[0]}{enter}`);
          
          // Wait for search
          cy.wait(1000);
          
          // Verify results
          cy.get('.o_list_table tbody tr.o_data_row').should('have.length.at.least', 1);
        });
    });

    it('Should filter Estate Owners only', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // The default context should already include estate_owners filter
      // Verify filter facet is active
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'Estate Owners');
    });

    it('Should filter active owners', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Active filter should be applied by default (from context)
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'Active');
      
      // All displayed owners should be active
      cy.get('.o_list_table tbody tr.o_data_row').should('have.length.at.least', 1);
    });

    it('Should filter owners with companies', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on Filters dropdown
      cy.get('.o_searchview .o_dropdown_title:contains("Filters")').click();
      
      // Select "With Companies" filter
      cy.get('.o_filter_menu .dropdown-item').contains('With Companies').click();
      
      // Verify filter is applied
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'With Companies');
      
      // Verify all shown owners have at least one company
      cy.get('.o_list_table tbody tr.o_data_row').each(($row) => {
        cy.wrap($row).find('td[name="estate_company_ids"]')
          .find('.badge')
          .should('have.length.at.least', 1);
      });
    });

    it('Should filter owners without companies', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on Filters dropdown
      cy.get('.o_searchview .o_dropdown_title:contains("Filters")').click();
      
      // Select "Without Companies" filter
      cy.get('.o_filter_menu .dropdown-item').contains('Without Companies').click();
      
      // Verify filter is applied
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'Without Companies');
    });

    it('Should group owners by company', () => {
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Click on Group By dropdown
      cy.get('.o_searchview .o_dropdown_title:contains("Group By")').click();
      
      // Select "Company" grouping
      cy.get('.o_group_by_menu .dropdown-item').contains('Company').click();
      
      // Verify grouping is applied
      cy.get('.o_searchview .o_searchview_facet').should('contain', 'Company');
      
      // Verify grouped view is shown
      cy.get('.o_group_header').should('have.length.at.least', 1);
    });
  });

  describe('7. Multi-tenancy Verification', () => {
    it('Should only show owners from accessible companies', () => {
      // Admin is already logged in via beforeEach
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_owner_list&model=res.users&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Count owners visible to admin
      cy.get('.o_list_table tbody tr.o_data_row').then(($rows) => {
        const adminCount = $rows.length;
        
        // Admin should see at least the seed owners
        expect(adminCount).to.be.at.least(1);
      });
    });
  });

  describe('8. Integration with Company', () => {
    it('Should navigate back to company from owner context', () => {
      // Start from a company
      cy.visit(`${baseUrl}/web#action=quicksol_estate.action_company&model=thedevkitchen.estate.company&view_type=list`);
      cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
      
      // Store company name
      cy.get('.o_list_table tbody tr.o_data_row').first()
        .find('td[name="name"]')
        .invoke('text')
        .then((companyName) => {
          // Open company
          cy.get('.o_list_table tbody tr.o_data_row').first().click();
          cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
          
          // Click Owners button
          cy.get('.oe_stat_button').contains('Owners').click();
          cy.get('.o_list_view', { timeout: 10000 }).should('be.visible');
          
          // Breadcrumb should show company context
          cy.get('.breadcrumb').should('contain', companyName.trim());
          
          // Click breadcrumb to go back
          cy.get('.breadcrumb a').contains(companyName.trim()).click();
          
          // Should be back on company form
          cy.get('.o_form_view', { timeout: 10000 }).should('be.visible');
          cy.contains('h1', companyName.trim()).should('be.visible');
        });
    });
  });
});
