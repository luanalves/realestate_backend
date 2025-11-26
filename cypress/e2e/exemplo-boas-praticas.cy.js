/// <reference types="cypress" />

/**
 * EXEMPLO DE TESTE MODERNO USANDO COMANDOS CUSTOMIZADOS
 * 
 * Este arquivo demonstra as melhores práticas para escrever testes Cypress para Odoo
 * usando os comandos customizados disponíveis.
 * 
 * LEIA TAMBÉM: cypress/COMANDOS_CUSTOMIZADOS.md
 */

describe('Exemplo: Boas Práticas com Comandos Customizados', () => {
  
  // ✅ BOA PRÁTICA: Use cy.odooLoginSession() em beforeEach()
  // Isso mantém a sessão entre testes e é 3x mais rápido!
  beforeEach(() => {
    cy.odooLoginSession()
  })

  it('✅ Exemplo 1: Navegação direta com cy.odooNavigateTo()', () => {
    // Navega diretamente para a lista de aplicações OAuth
    // Muito mais rápido do que clicar em menus!
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // Verifica que a lista está visível
    cy.get('.o_list_view').should('be.visible')
  })

  it('✅ Exemplo 2: Criar registro usando comandos customizados', () => {
    // Navega para lista
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // Cria novo registro
    cy.get('button.o_list_button_add').first().click()
    cy.wait(1500) // Aguarda navegação
    
    // Aguarda formulário
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Preenche campos com seletor flexível
    const appName = `Test App ${Date.now()}`
    cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input').first().type(appName, { force: true })
    
    // Verifica se campo description existe antes de preencher
    cy.get('body').then($body => {
      if ($body.find('textarea[name="description"]').length > 0) {
        cy.get('textarea[name="description"]').first().type('Aplicação de exemplo', { force: true })
      }
    })
    
    // Salva
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Valida em qualquer formato (input, span, ou div)
    cy.get('.o_field_widget[name="name"], input[name="name"]').should('exist')
  })

  it('✅ Exemplo 3: Usar URLs relativas ao invés de absolutas', () => {
    // ❌ NÃO FAÇA: cy.visit('http://localhost:8069/web#...')
    // ✅ FAÇA: Use URLs relativas
    cy.visit('/web')
    cy.get('.o_main_navbar', { timeout: 10000 }).should('be.visible')
    
    // Verifica que a página Odoo carregou corretamente
    cy.get('body').should('be.visible')
  })

  it('✅ Exemplo 4: Aguardar elementos com timeout apropriado', () => {
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // ✅ BOA PRÁTICA: Especificar timeout para elementos que podem demorar
    cy.get('.o_list_view', { timeout: 10000 }).should('be.visible')
  })

  it('✅ Exemplo 5: Verificações condicionais', () => {
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // Verificar se há registros antes de tentar clicar
    cy.get('body').then($body => {
      if ($body.find('tr.o_data_row').length > 0) {
        cy.get('tr.o_data_row').first().click()
        cy.get('.o_form_view').should('be.visible')
      } else {
        cy.log('Nenhum registro encontrado')
      }
    })
  })

  it('✅ Exemplo 6: Capturar valores para usar em outros testes', () => {
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    cy.get('button.o_list_button_add').first().click()
    cy.wait(1500) // Aguarda navegação
    
    // Aguarda formulário
    cy.get('.o_form_view', { timeout: 15000 }).should('be.visible')
    
    // Preenche com seletor flexível
    cy.get('.o_field_widget[name="name"] input, input[name="name"], div[name="name"] input').first().type('App para Captura', { force: true })
    cy.get('button.o_form_button_save').click()
    cy.wait(2000)
    
    // Captura Client ID (pode estar em input ou span após salvar)
    cy.get('.o_field_widget[name="client_id"] input, input[name="client_id"], .o_field_widget[name="client_id"] span, span[name="client_id"]')
      .first()
      .invoke('val')
      .then((clientId) => {
        // Se não tem valor em input, tenta pegar o texto
        if (!clientId) {
          cy.get('.o_field_widget[name="client_id"]').invoke('text').then((text) => {
            const trimmedText = text.trim()
            cy.log('Client ID:', trimmedText)
            expect(trimmedText).to.not.be.empty
          })
        } else {
          cy.log('Client ID:', clientId)
          expect(clientId).to.not.be.empty
          expect(clientId).to.include('client_')
        }
      })
  })
})

describe('❌ ANTI-PADRÕES: O que NÃO fazer', () => {
  
  it('❌ NÃO FAÇA: Login manual em cada teste', () => {
    // ❌ LENTO: Fazer login toda vez
    cy.visit('/web/login')
    cy.get('input[name="login"]').type('admin')
    cy.get('input[name="password"]').type('admin')
    cy.get('button[type="submit"]').click()
    cy.wait(2000)
    
    // ✅ CORRETO: Usar cy.odooLoginSession() no beforeEach()
  })

  it('❌ NÃO FAÇA: Navegar clicando em menus', () => {
    cy.odooLoginSession()
    
    // ❌ LENTO E FRÁGIL: Clicar em múltiplos menus
    // cy.contains('Configurações').click()
    // cy.contains('Técnico').click()
    // cy.contains('API Gateway').click()
    
    // ✅ CORRETO: Navegação direta
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
  })

  it('❌ NÃO FAÇA: Usar cy.wait() com tempos fixos', () => {
    cy.odooLoginSession()
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // ❌ RUIM: Tempo fixo desnecessário
    // cy.wait(5000)
    
    // ✅ CORRETO: Aguardar elemento específico
    cy.get('.o_list_view').should('be.visible')
  })

  it('❌ NÃO FAÇA: Usar URLs absolutas', () => {
    // ❌ RUIM: Só funciona em localhost
    // cy.visit('http://localhost:8069/web')
    
    // ✅ CORRETO: URL relativa funciona em qualquer ambiente
    cy.visit('/web')
  })
})

describe('🚀 COMPARAÇÃO DE PERFORMANCE', () => {
  
  // Este exemplo mostra a diferença de performance entre abordagens
  
  it('❌ LENTO: Sem comandos customizados (~10s)', () => {
    const startTime = Date.now()
    
    cy.visit('/web/login')
    cy.get('input[name="login"]').type('admin')
    cy.get('input[name="password"]').type('admin')
    cy.get('button[type="submit"]').click()
    cy.wait(2000)
    cy.visit('/web#action=thedevkitchen_apigateway.action_oauth_application')
    cy.wait(2000)
    
    const endTime = Date.now()
    cy.log(`Tempo: ${endTime - startTime}ms`)
  })

  it('✅ RÁPIDO: Com comandos customizados (~3s)', () => {
    const startTime = Date.now()
    
    cy.odooLoginSession()
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    const endTime = Date.now()
    cy.log(`Tempo: ${endTime - startTime}ms`)
  })
})

describe('📖 RECURSOS ÚTEIS', () => {
  
  it('Exemplo: Logs para debugging', () => {
    cy.odooLoginSession()
    
    cy.log('Navegando para aplicações OAuth')
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    cy.log('Verificando lista')
    cy.get('.o_list_view').should('be.visible')
    
    cy.log('Teste concluído!')
  })

  it('Exemplo: Capturar screenshots', () => {
    cy.odooLoginSession()
    cy.odooNavigateTo('thedevkitchen_apigateway.action_oauth_application', 'thedevkitchen.oauth.application')
    
    // Captura screenshot para documentação
    cy.screenshot('oauth-applications-list')
  })

  it('Exemplo: Testar API diretamente', () => {
    // Você pode testar endpoints sem navegar na UI
    cy.request({
      method: 'GET',
      url: '/web/database/list',
      failOnStatusCode: false,
    }).then((response) => {
      cy.log('Databases:', response.body)
    })
  })
})

/**
 * CHECKLIST PARA NOVOS TESTES:
 * 
 * ✅ Usa cy.odooLoginSession() no beforeEach()?
 * ✅ Usa cy.odooNavigateTo() ao invés de clicar em menus?
 * ✅ Usa URLs relativas ao invés de absolutas?
 * ✅ Aguarda elementos com should() ao invés de cy.wait()?
 * ✅ Tem nomes descritivos (it('Deve fazer X'))?
 * ✅ Não depende de outros testes?
 * ✅ Limpa dados criados (se necessário)?
 * 
 * Se SIM para todos, seu teste está ótimo! 🎉
 */
