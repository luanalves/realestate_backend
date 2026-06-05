const path = require('path');
const fs   = require('fs');

/**
 * Load credentials from 18.0/.env into Cypress env.
 * This avoids storing sensitive values in cypress.env.json or test files.
 */
function loadEnvFile() {
  const envPath = path.resolve(__dirname, '18.0', '.env');
  if (!fs.existsSync(envPath)) return {};
  const result = {};
  const lines = fs.readFileSync(envPath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, '');
    result[key] = val;
  }
  return result;
}

const envVars = loadEnvFile();

module.exports = {
  e2e: {
    baseUrl: envVars.ODOO_BASE_URL || 'http://localhost:8069',
    viewportWidth: 1280,
    viewportHeight: 720,
    defaultCommandTimeout: 10000,
    supportFile: false,
    env: {
      ODOO_BASE_URL:        envVars.ODOO_BASE_URL        || 'http://localhost:8069',
      ODOO_USERNAME:        envVars.TEST_USER_ADMIN,
      ODOO_PASSWORD:        envVars.TEST_PASSWORD_ADMIN,
      ODOO_USERNAME_OWNER:  envVars.TEST_USER_OWNER,
      ODOO_PASSWORD_OWNER:  envVars.TEST_PASSWORD_OWNER,
      OAUTH_CLIENT_ID:      envVars.OAUTH_CLIENT_ID,
      OAUTH_CLIENT_SECRET:  envVars.OAUTH_CLIENT_SECRET,
    },
    video: true,
    videoCompression: 32,
    screenshotOnRunFailure: true,
    trashAssetsBeforeRuns: false,
    setupNodeEvents(on, config) {
      // env is already injected above from 18.0/.env
      return config;
    },
  },
};

