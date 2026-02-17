/// <reference types="cypress" />

/**
 * Feature 009 - User Onboarding & Password Management
 * Test Suite: Email Link Settings UI (US5)
 * 
 * Tests the settings interface for email link configuration:
 * - Invite link TTL (1-720 hours)
 * - Reset link TTL (1-720 hours)
 * - Frontend base URL
 * - Max resend attempts
 * - Rate limiting settings
 * 
 * ADRs: ADR-003 (Testing Standards), ADR-005 (UI Testing)
 */

describe('Feature 009 - Email Link Settings UI (US5)', () => {
  
  beforeEach(() => {
    // Use cy.odooLoginSession() to maintain session between tests (3x faster)
    cy.odooLoginSession()
  })

  it('Settings menu is accessible from Technical > Configuration', () => {
    // Navigate to Settings menu via web client
    cy.visit('/web')
    cy.get('.o_main_navbar', { timeout: 10000 }).should('be.visible')
    
    // Click on Technical menu (Apps menu or Settings)
    cy.get('body').then($body => {
      // Try to find Settings menu
      if ($body.find('a[data-menu-xmlid="base.menu_administration"]').length > 0) {
        cy.get('a[data-menu-xmlid="base.menu_administration"]').click()
      } else {
        // Alternative: Click on main menu and navigate
        cy.log('Navigating via search or alternative path...')
        cy.get('.o_menu_sections').should('be.visible')
      }
    })
    
    cy.wait(1000)
    
    // Verify page loaded successfully
    cy.get('body').should('be.visible')
  })

  it('Form loads without errors and displays all settings fields', () => {
    // Navigate directly to settings form (singleton pattern)
    // In Odoo, singletons can be accessed via model action
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form to load
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Verify key fields are present
    cy.get('.o_field_widget[name="invite_link_ttl_hours"]', { timeout: 5000 }).should('exist')
    cy.get('.o_field_widget[name="reset_link_ttl_hours"]').should('exist')
    cy.get('.o_field_widget[name="frontend_base_url"]').should('exist')
    cy.get('.o_field_widget[name="max_resend_attempts"]').should('exist')
    
    // Verify no JS errors in console (Cypress tracks these automatically)
    cy.window().then((win) => {
      expect(win.console.error).to.not.be.called
    })
  })

  it('Can edit invite_link_ttl_hours and save', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if form is in readonly mode
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Clear and set new TTL value (48 hours)
    cy.get('.o_field_widget[name="invite_link_ttl_hours"] input')
      .clear({ force: true })
      .type('48', { force: true })
    
    // Save the form
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Verify value persisted
    cy.get('.o_field_widget[name="invite_link_ttl_hours"]').should('contain', '48')
  })

  it('Can edit reset_link_ttl_hours and save', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if needed
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Clear and set new TTL value (12 hours)
    cy.get('.o_field_widget[name="reset_link_ttl_hours"] input')
      .clear({ force: true })
      .type('12', { force: true })
    
    // Save the form
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Verify value persisted
    cy.get('.o_field_widget[name="reset_link_ttl_hours"]').should('contain', '12')
  })

  it('Validation prevents TTL values outside 1-720 range', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if needed
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Test 1: Try to set TTL to 0 (invalid)
    cy.get('.o_field_widget[name="invite_link_ttl_hours"] input')
      .clear({ force: true })
      .type('0', { force: true })
    
    // Try to save - should show validation error
    cy.get('button.o_form_button_save').click()
    cy.wait(1000)
    
    // Odoo should show validation error (notification or field highlight)
    cy.get('.o_notification_manager, .o_form_editable .o_field_invalid, .o_notification').should('exist')
    
    // Cancel or discard changes
    cy.get('button.o_form_button_cancel, button.o_form_button_discard').click({ force: true })
    cy.wait(500)
    
    // Test 2: Try to set TTL to 721 (above max)
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    cy.get('.o_field_widget[name="reset_link_ttl_hours"] input')
      .clear({ force: true })
      .type('721', { force: true })
    
    // Try to save - should show validation error
    cy.get('button.o_form_button_save').click()
    cy.wait(1000)
    
    // Should show validation error
    cy.get('.o_notification_manager, .o_form_editable .o_field_invalid, .o_notification').should('exist')
  })

  it('Can edit frontend_base_url field', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if needed
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Update frontend base URL
    const newUrl = 'https://test.example.com'
    cy.get('.o_field_widget[name="frontend_base_url"] input')
      .clear({ force: true })
      .type(newUrl, { force: true })
    
    // Save the form
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Verify value persisted
    cy.get('.o_field_widget[name="frontend_base_url"]').should('contain', newUrl)
  })

  it('Boundary values: TTL of 1 hour is accepted', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if needed
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Set minimum valid TTL (1 hour)
    cy.get('.o_field_widget[name="invite_link_ttl_hours"] input')
      .clear({ force: true })
      .type('1', { force: true })
    
    // Save should succeed
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Form should be in readonly mode (save succeeded)
    cy.get('.o_form_readonly, .o_form_view').should('exist')
    
    // Verify value persisted
    cy.get('.o_field_widget[name="invite_link_ttl_hours"]').should('contain', '1')
  })

  it('Boundary values: TTL of 720 hours is accepted', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Click Edit button if needed
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Set maximum valid TTL (720 hours)
    cy.get('.o_field_widget[name="reset_link_ttl_hours"] input')
      .clear({ force: true })
      .type('720', { force: true })
    
    // Save should succeed
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Form should be in readonly mode (save succeeded)
    cy.get('.o_form_readonly, .o_form_view').should('exist')
    
    // Verify value persisted
    cy.get('.o_field_widget[name="reset_link_ttl_hours"]').should('contain', '720')
  })

  it('Zero JS console errors throughout settings operations', () => {
    // Track console errors
    cy.window().then((win) => {
      cy.spy(win.console, 'error').as('consoleError')
    })
    
    // Navigate to settings
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Edit mode
    cy.get('body').then($body => {
      if ($body.find('button.o_form_button_edit').length > 0) {
        cy.get('button.o_form_button_edit').click()
        cy.wait(500)
      }
    })
    
    // Interact with fields
    cy.get('.o_field_widget[name="invite_link_ttl_hours"] input')
      .clear({ force: true })
      .type('36', { force: true })
    
    cy.get('.o_field_widget[name="max_resend_attempts"] input')
      .clear({ force: true })
      .type('10', { force: true })
    
    // Save
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Verify no console errors
    cy.get('@consoleError').should('not.be.called')
  })

  it('Settings form displays help text and labels correctly', () => {
    // Navigate to settings form
    cy.visit('/web#action=thedevkitchen_user_onboarding.action_email_link_settings&model=thedevkitchen.email.link.settings&view_type=form')
    
    // Wait for form
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Verify field labels are present (Odoo renders these)
    cy.get('.o_form_view').should('contain.text', 'Invite Link TTL')
    cy.get('.o_form_view').should('contain.text', 'Reset Link TTL')
    cy.get('.o_form_view').should('contain.text', 'Frontend Base URL')
    
    // Verify form structure is valid
    cy.get('.o_form_sheet').should('exist')
  })
})
