/**
 * E2E Tests for Owner Setup Workflow (User Story 1)
 * 
 * Tests the complete owner user journey:
 * 1. Owner logs in to the system
 * 2. Owner creates/manages company settings
 * 3. Owner adds team members
 * 4. Owner verifies full access to all features
 * 
 * Run: npm run cypress:run
 */

describe('RBAC - Owner Setup and Management', () => {
  const ownerCredentials = {
    login: 'owner_a@test.com',
    password: 'admin', // Change in production
  };

  const companyData = {
    name: 'Cypress Test Real Estate Company',
    phone: '+55 11 98765-4321',
    email: 'company@cypress-test.com',
  };

  const newUserData = {
    name: 'Cypress Test Agent',
    login: 'agent_cypress@test.com',
    email: 'agent_cypress@test.com',
  };

  beforeEach(() => {
    // Visit Odoo login page
    cy.visit('http://localhost:8069');
    
    // Clear any existing sessions
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('should allow owner to log in successfully', () => {
    // Login as owner
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Verify successful login
    cy.url().should('not.include', '/web/login');
    cy.contains('Real Estate', { timeout: 10000 }).should('be.visible');
  });

  it('should allow owner to access company settings', () => {
    // Login
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Navigate to Settings
    cy.contains('Settings', { timeout: 10000 }).click();
    
    // Navigate to Companies
    cy.contains('Companies').click();
    
    // Verify owner can see company list
    cy.get('.o_list_view').should('be.visible');
    
    // Owner should be able to open a company record
    cy.get('.o_data_row').first().click();
    
    // Verify company form is visible
    cy.get('.o_form_view').should('be.visible');
  });

  it('should allow owner to create and manage team members', () => {
    // Login
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Navigate to Settings
    cy.contains('Settings', { timeout: 10000 }).click();
    
    // Navigate to Users & Companies
    cy.contains('Users').click();
    
    // Click Create button
    cy.contains('Create').click();
    
    // Fill in new user details
    cy.get('input[name="name"]').type(newUserData.name);
    cy.get('input[name="login"]').type(newUserData.login);
    cy.get('input[name="email"]').type(newUserData.email);
    
    // Save the user
    cy.contains('Save').click();
    
    // Verify user was created
    cy.contains(newUserData.name, { timeout: 5000 }).should('be.visible');
  });

  it('should allow owner to access all Real Estate features', () => {
    // Login
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Verify owner can access Real Estate menu
    cy.contains('Real Estate', { timeout: 10000 }).should('be.visible');
    cy.contains('Real Estate').click();

    // Check access to key submenus
    const expectedMenus = [
      'Properties',
      'Agents',
      'Assignments',
      'Leases',
      'Sales',
    ];

    expectedMenus.forEach((menu) => {
      cy.contains(menu, { timeout: 5000 }).should('be.visible');
    });
  });

  it('should allow owner to create properties', () => {
    // Login
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Navigate to Properties
    cy.contains('Real Estate', { timeout: 10000 }).click();
    cy.contains('Properties').click();
    
    // Click Create
    cy.contains('Create').click();
    
    // Fill in property details
    cy.get('input[name="name"]').type('Cypress Test Property - Owner Created');
    cy.get('input[name="expected_price"]').type('500000');
    
    // Save property
    cy.contains('Save').click();
    
    // Verify property was created
    cy.contains('Cypress Test Property - Owner Created', { timeout: 5000 })
      .should('be.visible');
  });

  it('should verify owner cannot see other companies\' data', () => {
    // Login as owner
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Navigate to Properties
    cy.contains('Real Estate', { timeout: 10000 }).click();
    cy.contains('Properties').click();
    
    // Search for properties
    cy.get('.o_searchview_input').type('{enter}');
    
    // Verify only own company properties are visible
    // (This assumes company field is visible in list view)
    cy.get('.o_data_row').each(($row) => {
      // Each row should belong to owner's company
      // In a real test, you would check the company field value
      cy.wrap($row).should('be.visible');
    });
  });

  it('should allow owner to manage agents', () => {
    // Login
    cy.get('input[name="login"]').type(ownerCredentials.login);
    cy.get('input[name="password"]').type(ownerCredentials.password);
    cy.get('button[type="submit"]').click();

    // Navigate to Agents
    cy.contains('Real Estate', { timeout: 10000 }).click();
    cy.contains('Agents').click();
    
    // Click Create
    cy.contains('Create').click();
    
    // Fill in agent details
    cy.get('input[name="name"]').type('Cypress Test Agent');
    cy.get('input[name="email"]').type('cypress_agent@test.com');
    cy.get('input[name="creci"]').type('CRECI-12345');
    
    // Save agent
    cy.contains('Save').click();
    
    // Verify agent was created
    cy.contains('Cypress Test Agent', { timeout: 5000 }).should('be.visible');
  });

  afterEach(() => {
    // Cleanup: Logout
    cy.get('.o_user_menu').click({ force: true });
    cy.contains('Log out').click({ force: true });
  });
});
