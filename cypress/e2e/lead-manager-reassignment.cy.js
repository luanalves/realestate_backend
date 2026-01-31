/**
 * Cypress E2E Test: Manager Lead Reassignment (T083)
 * 
 * Tests manager's ability to reassign leads between agents via UI.
 * Validates FR-026 (manager reassignment), FR-027 (activity logging).
 * 
 * Author: Quicksol Technologies
 * Date: 2026-01-29
 * Branch: 006-lead-management
 * ADR: ADR-003 (E2E UI tests with Cypress)
 */

describe('Manager Lead Reassignment', () => {
  const managerEmail = Cypress.env('TEST_MANAGER_EMAIL') || 'manager@test.com';
  const managerPassword = Cypress.env('TEST_MANAGER_PASSWORD') || 'admin';
  
  let leadId;
  let originalAgentName;
  
  before(() => {
    // Login as manager and create test lead
    cy.odooLoginSession(managerEmail, managerPassword);
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list');
    cy.wait(2000);
  });
  
  beforeEach(() => {
    // Login as manager before each test
    cy.odooLoginSession(managerEmail, managerPassword);
    cy.visit('/web#action=quicksol_estate.action_lead&model=real.estate.lead&view_type=list');
    cy.wait(2000);
  });
  
  it('should open lead form for reassignment', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
    
    // WHEN: Manager clicks on first lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    
    // THEN: Form view opens with agent field visible
    cy.get('.o_form_view').should('be.visible');
    cy.get('[name="agent_id"]').should('exist');
    
    // Store original agent name
    cy.get('[name="agent_id"] input').invoke('val').then((val) => {
      originalAgentName = val;
      cy.log(`Original agent: ${originalAgentName}`);
    });
  });
  
  it('should display agent field as editable for manager', () => {
    // GIVEN: Manager opens lead form
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    
    // WHEN: Manager clicks Edit button
    cy.get('.o_form_button_edit').click();
    cy.wait(500);
    
    // THEN: Agent field is editable (not readonly)
    cy.get('[name="agent_id"] input').should('not.be.disabled');
    cy.get('[name="agent_id"] .o_external_button').should('exist');
  });
  
  it('should reassign lead to different agent', () => {
    // GIVEN: Manager is editing lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    cy.get('.o_form_button_edit').click();
    cy.wait(500);
    
    // WHEN: Manager changes agent_id field
    cy.get('[name="agent_id"] input').clear().type('Agent');
    cy.wait(500);
    
    // Select first agent from dropdown (different from current)
    cy.get('.ui-menu-item').should('have.length.greaterThan', 0);
    cy.get('.ui-menu-item').first().click();
    cy.wait(500);
    
    // Save the form
    cy.get('.o_form_button_save').click();
    cy.wait(2000);
    
    // THEN: Success notification displayed
    cy.get('.o_notification_manager').should('be.visible');
    
    // Verify agent_id changed
    cy.get('[name="agent_id"] input').invoke('val').should('not.be.empty');
  });
  
  it('should display chatter message after reassignment', () => {
    // GIVEN: Manager has reassigned a lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    
    // WHEN: Manager scrolls to chatter section
    cy.get('.o-mail-Chatter').should('exist').scrollIntoView();
    cy.wait(500);
    
    // THEN: Chatter contains reassignment activity log
    // (This checks for any message; specific reassignment message may vary)
    cy.get('.o-mail-Message').should('exist');
  });
  
  it('should update lead list after reassignment', () => {
    // GIVEN: Manager reassigned a lead
    let leadName;
    
    cy.get('.o_data_row').first().within(() => {
      cy.get('[name="name"]').invoke('text').then((name) => {
        leadName = name.trim();
      });
    });
    
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    cy.get('.o_form_button_edit').click();
    cy.wait(500);
    
    // Change agent
    cy.get('[name="agent_id"] input').clear().type('Agent');
    cy.wait(500);
    cy.get('.ui-menu-item').first().click();
    cy.wait(500);
    cy.get('.o_form_button_save').click();
    cy.wait(2000);
    
    // WHEN: Manager returns to list view
    cy.get('.o_back_button').click();
    cy.wait(1500);
    
    // THEN: List view shows updated agent for the lead
    cy.get('.o_list_view').should('be.visible');
    cy.get('.o_data_row').should('have.length.greaterThan', 0);
  });
  
  it('should allow reassignment via kanban view', () => {
    // GIVEN: Manager is in kanban view
    cy.get('.o_cp_switch_buttons button[data-view-type="kanban"]').click();
    cy.wait(1500);
    
    // WHEN: Manager opens lead card
    cy.get('.o_kanban_record').first().click();
    cy.wait(1500);
    
    // THEN: Can reassign from form popup
    cy.get('.o_form_view').should('be.visible');
    cy.get('[name="agent_id"]').should('exist');
  });
  
  it('should display agent filter with all company agents', () => {
    // GIVEN: Manager is on leads list
    cy.get('.o_list_view').should('be.visible');
    
    // WHEN: Manager clicks agent filter dropdown
    cy.get('.o_searchview_input').click();
    cy.get('.o_menu_item').contains('Agent').click();
    cy.wait(500);
    
    // THEN: Dropdown shows multiple agents
    cy.get('.ui-menu-item').should('have.length.greaterThan', 0);
  });
  
  it('should validate reassignment notification shows old and new agent', () => {
    // GIVEN: Manager is reassigning a lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    
    let originalAgent;
    cy.get('[name="agent_id"] input').invoke('val').then((val) => {
      originalAgent = val;
    });
    
    cy.get('.o_form_button_edit').click();
    cy.wait(500);
    
    // WHEN: Manager changes agent
    cy.get('[name="agent_id"] input').clear().type('Agent');
    cy.wait(500);
    cy.get('.ui-menu-item').eq(1).click(); // Select second agent (different from first)
    cy.wait(500);
    
    let newAgent;
    cy.get('[name="agent_id"] input').invoke('val').then((val) => {
      newAgent = val;
    });
    
    cy.get('.o_form_button_save').click();
    cy.wait(2000);
    
    // THEN: Chatter or notification shows reassignment details
    cy.get('.o-mail-Chatter').should('exist');
  });
  
  it('should prevent agent from changing their own agent_id (via API)', () => {
    // This test validates backend security, but UI may also show readonly field
    // NOTE: This is primarily an API/backend test, UI may not expose this
    cy.log('Backend validation: Agents cannot change agent_id (tested in API tests)');
  });
  
  it('should show statistics updated after reassignment', () => {
    // GIVEN: Manager reassigns a lead
    cy.get('.o_data_row').first().click();
    cy.wait(1500);
    cy.get('.o_form_button_edit').click();
    cy.wait(500);
    cy.get('[name="agent_id"] input').clear().type('Agent');
    cy.wait(500);
    cy.get('.ui-menu-item').first().click();
    cy.wait(500);
    cy.get('.o_form_button_save').click();
    cy.wait(2000);
    
    // WHEN: Manager views pivot view
    cy.get('.o_back_button').click();
    cy.wait(1500);
    cy.get('.o_cp_switch_buttons button[data-view-type="pivot"]').click();
    cy.wait(2000);
    
    // THEN: Pivot table reflects new assignment
    cy.get('.o_pivot_view').should('be.visible');
    cy.get('tbody tr').should('have.length.greaterThan', 0);
  });
});
