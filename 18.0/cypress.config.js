const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:8069',
    viewportWidth: 1280,
    viewportHeight: 720,
    defaultCommandTimeout: 10000,
    // Aponta para os arquivos de teste na pasta raiz do projeto
    specPattern: '../cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: '../cypress/support/e2e.js',
    fixturesFolder: '../cypress/fixtures',
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
