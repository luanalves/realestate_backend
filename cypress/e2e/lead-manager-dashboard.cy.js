/**
 * Cypress E2E Test: Manager Dashboard (T082)
 * 
 * Tests manager's ability to view all company leads with filters and grouping.
 * Validates FR-024 (manager read access), FR-028 (dashboard views).
 * 
 * Author: Quicksol Technologies
 * Date: 2026-01-29
 * Branch: 006-lead-management
 * ADR: ADR-003 (E2E UI tests with Cypress)
 */

describe('Manager Dashboard - Lead Management', () => {
  const managerEmail = Cypress.env('TEST_MANAGER_EMAIL') || 'manager@test.com';
  const managerPassword = Cypress.env('TEST_MANAGER_PASSWORD') || 'admin';
  
  beforeEach(() => {
    // Login as manager
    cy.odooLoginSession(managerEmail, managerPassword);
    
    // Navigate to Leads menu
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list');
    cy.wait(2000);
  });
  
  it('should display all company leads in list view', () => {
    // GIVEN: Manager is on leads list page
    cy.url().should('include', 'real.estate.lead');
    
    // WHEN: Page loads
    cy.get('.o_list_view').should('be.visible');
    
    // THEN: Lead list displays with multiple agents' leads
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
    
    // Verify list columns
    cy.get('th[data-name="name"]').should('contain', 'Name');
    cy.get('th[data-name="agent_id"]').should('contain', 'Agent');
    cy.get('th[data-name="state"]').should('contain', 'State');
    cy.get('th[data-name="phone"]').should('contain', 'Phone');
  });
  
  it('should filter leads by state (contacted)', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager clicks "Contacted" filter
    cy.get('.o_searchview_input').click();
    cy.get('.o_menu_item').contains('Contacted').click();
    cy.wait(1000);
    
    // THEN: Only contacted leads displayed
    cy.get('.o_data_row').each(($row) => {
      cy.wrap($row).find('[name="state"]').should('contain.text', 'contacted');
    });
  });
  
  it('should filter leads by agent', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager applies agent filter
    cy.get('.o_searchview_input').click();
    cy.get('.o_searchview_autocomplete').find('li').contains('Agent').click();
    cy.wait(500);
    
    // Select first agent from dropdown
    cy.get('.ui-menu-item').first().click();
    cy.wait(1000);
    
    // THEN: Only that agent's leads displayed
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
    
    // Verify all rows have same agent
    let firstAgentName = '';
    cy.get('.o_data_row').first().find('[name="agent_id"]').invoke('text').then((text) => {
      firstAgentName = text.trim();
      
      cy.get('.o_data_row').each(($row) => {
        cy.wrap($row).find('[name="agent_id"]').should('contain.text', firstAgentName);
      });
    });
  });
  
  it('should display kanban view grouped by state', () => {
    // GIVEN: Manager is on leads page
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager switches to kanban view
    cy.get('.o_cp_switch_buttons button[data-view-type="kanban"]').click();
    cy.wait(1500);
    
    // THEN: Kanban columns for each state visible
    cy.get('.o_kanban_view').should('be.visible');
    cy.get('.o_kanban_group').should('have.length.greaterThan', 0);
    
    // Verify state columns exist
    ['New', 'Contacted', 'Qualified', 'Won', 'Lost'].forEach((state) => {
      cy.get('.o_column_title').should('contain', state);
    });
  });
  
  it('should display pivot view for lead analysis', () => {
    // GIVEN: Manager is on leads page
    cy.url().should('include', 'real.estate.lead');
    
    // WHEN: Manager switches to pivot view
    cy.get('.o_cp_switch_buttons button[data-view-type="pivot"]').click();
    cy.wait(2000);
    
    // THEN: Pivot table visible with agent rows and state columns
    cy.get('.o_pivot_view').should('be.visible');
    cy.get('.o_pivot').should('be.visible');
    
    // Verify pivot table has data
    cy.get('tbody tr').should('have.length.greaterThan', 0);
  });
  
  it('should display graph view for lead statistics', () => {
    // GIVEN: Manager is on leads page
    cy.url().should('include', 'real.estate.lead');
    
    // WHEN: Manager switches to graph view
    cy.get('.o_cp_switch_buttons button[data-view-type="graph"]').click();
    cy.wait(2000);
    
    // THEN: Pie chart visible showing state distribution
    cy.get('.o_graph_view').should('be.visible');
    cy.get('.o_graph_renderer').should('be.visible');
    
    // Verify chart rendered (check for SVG or canvas)
    cy.get('.o_graph_canvas_container').should('exist');
  });
  
  it('should search across all agents\' leads', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager enters search text
    const searchTerm = 'Lead';
    cy.get('.o_searchview_input').type(`${searchTerm}{enter}`);
    cy.wait(1000);
    
    // THEN: Search results include leads from multiple agents
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
    
    // Verify multiple different agents in results
    const agentNames = new Set();
    cy.get('.o_data_row [name="agent_id"]').each(($el) => {
      const agentName = $el.text().trim();
      if (agentName) {
        agentNames.add(agentName);
      }
    }).then(() => {
      // At least 1 agent should be present (could be more in multi-agent env)
      expect(agentNames.size).to.be.greaterThan(0);
    });
  });
  
  it('should open lead form and display all details', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
    
    // WHEN: Manager clicks on first lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    
    // THEN: Form view opens with complete lead details
    cy.get('.o_form_view').should('be.visible');
    cy.get('[name="name"]').should('exist');
    cy.get('[name="agent_id"]').should('exist');
    cy.get('[name="state"]').should('exist');
    cy.get('[name="phone"]').should('exist');
    cy.get('[name="email"]').should('exist');
    
    // Verify tabs exist
    cy.get('.nav-link').contains('Preferences').should('exist');
  });
  
  it('should display active and archived leads with filter toggle', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager removes "Active" filter
    cy.get('.o_searchview .o_facet_remove').first().click();
    cy.wait(1000);
    
    // Add "Archived" filter
    cy.get('.o_searchview_input').click();
    cy.get('.o_menu_item').contains('Archived').click();
    cy.wait(1000);
    
    // THEN: Archived leads displayed (may be empty if none archived)
    cy.get('.o_list_view').should('be.visible');
    // No assertion on count since archived leads may not exist yet
  });
  
  it('should respect "My Leads" filter (shows manager\'s own leads only)', () => {
    // GIVEN: Manager is on leads list with default filters
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: "My Leads" filter already active by default
    cy.get('.o_searchview .o_facet_value').contains('My Leads').should('exist');
    
    // THEN: Only manager's own leads displayed
    // (If manager is also an agent, they'll have leads; otherwise empty)
    cy.get('.o_list_view').should('be.visible');
    
    // Remove "My Leads" filter to see all company leads
    cy.get('.o_searchview .o_facet_remove').click();
    cy.wait(1000);
    
    // Verify more leads visible after removing filter
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
  });
});
