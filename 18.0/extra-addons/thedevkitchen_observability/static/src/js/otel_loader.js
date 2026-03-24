/** @odoo-module **/

/**
 * OpenTelemetry Browser Loader for Odoo
 * 
 * Loads and initializes the OpenTelemetry bundle when Odoo web client starts.
 * The bundle (opentelemetry-bundle.js) is loaded first via assets.
 */

import { whenReady } from "@web/core/utils/concurrency";
import { browser } from "@web/core/browser/browser";

// Initialize OpenTelemetry when Odoo web client is ready
whenReady(() => {
    if (window.OdooOTel && typeof window.OdooOTel.initialize === 'function') {
        window.OdooOTel.initialize();
    } else {
        console.warn('[OTel Browser] Bundle not loaded or incompatible version');
    }
});
