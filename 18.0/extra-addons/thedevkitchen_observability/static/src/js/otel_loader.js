/** @odoo-module **/

/**
 * OpenTelemetry Browser Loader for Odoo
 * 
 * Loads and initializes the OpenTelemetry bundle when Odoo web client starts.
 * The bundle (opentelemetry-bundle.js) is loaded first via assets.
 */

// Initialize OpenTelemetry when this module loads
// whenReady was removed in Odoo 18.0; the bundle auto-initializes on DOMContentLoaded
if (window.OdooOTel && typeof window.OdooOTel.initialize === 'function') {
    window.OdooOTel.initialize();
} else {
    console.warn('[OTel Browser] Bundle not loaded or incompatible version');
}
