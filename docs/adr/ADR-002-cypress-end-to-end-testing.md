# ADR-002: Uso do Cypress para Testes End-to-End

## Status
**Accepted** - 2025-11-15

## Context

Durante o desenvolvimento do sistema Odoo (Real Estate Management e API Gateway), identificamos a necessidade de testes automatizados End-to-End (E2E) para garantir:

1. **Qualidade de UI/UX**: Validar que a interface funciona corretamente para usuários finais
2. **Integração Frontend-Backend**: Testar fluxos completos desde a UI até a API
3. **Regressão**: Detectar quebras em funcionalidades existentes ao adicionar novas features
4. **Confiabilidade**: Garantir que APIs REST (especialmente OAuth 2.0) funcionam como esperado
5. **Documentação Viva**: Testes servem como documentação de como o sistema deve funcionar
6. **CI/CD**: Possibilitar automação de testes em pipelines de integração contínua

### Alternativas Consideradas

1. **Selenium WebDriver**
   - Pros: Maduro, suporta múltiplos navegadores
   - Cons: Configuração complexa, testes flaky, lento
   
2. **Playwright**
   - Pros: Moderno, rápido, multi-browser nativo
   - Cons: Comunidade menor, menos exemplos para Odoo
   
3. **Cypress** ✅
   - Pros: Sintaxe simples, debugging excelente, time travel, screenshots/vídeos automáticos
   - Cons: Limitado a Chromium-based browsers (suficiente para nosso caso)

## Decision

**Adotamos Cypress como framework oficial para testes E2E** por:

- ✅ Sintaxe JavaScript moderna e intuitiva
- ✅ Excelente experiência de debugging (time travel, screenshots, vídeos)
- ✅ Comandos customizados permitem reutilização de código
- ✅ Sistema de sessões acelera testes (3x mais rápido)
- ✅ Suporta testes de API além de UI
- ✅ Documentação extensa e comunidade ativa
- ✅ Fácil integração com CI/CD (GitHub Actions, GitLab CI)

## Estrutura de Arquivos

### Diretório Principal
```
/opt/homebrew/var/www/realestate/odoo-docker/cypress/
```

### Organização
```
cypress/
├── README.md                          # Guia de uso e comandos de execução
├── COMANDOS_CUSTOMIZADOS.md         # Documentação completa de comandos
├── e2e/                              # Testes End-to-End
│   ├── api-gateway.cy.js            # Testes de UI do API Gateway (20 testes)
│   ├── api-gateway-integration.cy.js # Testes de integração UI+API (12 testes)
│   ├── exemplo-boas-praticas.cy.js  # Guia de boas práticas
│   ├── imoveis-*.cy.js              # Testes do módulo de imóveis
│   └── login-custom-command.cy.js   # Exemplo de comando customizado
├── fixtures/                         # Dados de teste (JSON)
│   └── example.json
├── support/                          # Comandos customizados e configurações
│   ├── commands.js                  # Comandos reutilizáveis
│   └── e2e.js                       # Configuração global
├── screenshots/                      # Screenshots automáticos em falhas
└── downloads/                        # Downloads durante testes
```

## Comandos Customizados

Para maximizar reutilização e performance, criamos comandos customizados:

### 1. `cy.odooLoginSession(username, password)`
Login com cache de sessão (3x mais rápido que login tradicional).

**Uso:**
```javascript
beforeEach(() => {
  cy.odooLoginSession() // Recomendado!
})
```

### 2. `cy.odooLogin(username, password)`
Login simples sem cache.

**Uso:**
```javascript
cy.odooLogin('admin', 'admin')
```

### 3. `cy.odooLogout()`
Logout do sistema.

**Uso:**
```javascript
cy.odooLogout()
```

### 4. `cy.odooNavigateTo(action, model, viewType)`
Navegação direta para menus (evita clicks em cascata).

**Uso:**
```javascript
cy.odooNavigateTo('api_gateway.action_oauth_application', 'oauth.application')
```

## Padrões de Teste

### Estrutura Padrão
```javascript
describe('Módulo: Funcionalidade', () => {
  beforeEach(() => {
    cy.odooLoginSession() // Login com sessão persistente
  })

  it('Deve fazer X quando Y', () => {
    // Arrange: Preparar dados
    cy.odooNavigateTo('module.action', 'model.name')
    
    // Act: Executar ação
    cy.get('button.o_list_button_add').click()
    cy.get('input[name="field"]').type('valor')
    
    // Assert: Verificar resultado
    cy.get('.o_field_widget').should('contain', 'valor')
  })
})
```

### Boas Práticas

✅ **FAÇA:**
- Use `cy.odooLoginSession()` no `beforeEach()`
- Use `cy.odooNavigateTo()` para navegação
- Use URLs relativas (`/web`) ao invés de absolutas
- Aguarde elementos com `.should()` ao invés de `cy.wait()`
- Nomeie testes descritivamente: `'Deve criar aplicação quando...'`

❌ **NÃO FAÇA:**
- Login manual em cada teste (lento!)
- Navegação clicando em menus (frágil!)
- URLs absolutas `http://localhost:8069` (ambiente-específico!)
- `cy.wait(5000)` fixos (instável!)
- Testes dependentes uns dos outros

## Módulos Testados

### API Gateway
- **Arquivo**: `cypress/e2e/api-gateway.cy.js`
- **Cobertura**: 20 testes de UI
  - Criação/edição de OAuth Applications
  - Gerenciamento de tokens
  - Validações de campos
  - Regeneração de secrets
  
- **Arquivo**: `cypress/e2e/api-gateway-integration.cy.js`
- **Cobertura**: 12 testes de integração
  - OAuth 2.0 Client Credentials flow
  - Geração e validação de tokens
  - Revogação de tokens
  - Validações de segurança

### Imóveis (quicksol_estate)
- **Arquivos**: `cypress/e2e/imoveis-*.cy.js`
- **Cobertura**: Testes de listagem, criação e jornada completa

## Como Executar

### Modo Interativo (Desenvolvimento)
```bash
cd /opt/homebrew/var/www/realestate/odoo-docker
npx cypress open
```

### Modo Headless (CI/CD)
```bash
# Todos os testes
npx cypress run

# Apenas API Gateway
npx cypress run --spec "cypress/e2e/api-gateway*.cy.js"

# Com vídeo
npx cypress run --video
```

### Pré-requisitos
1. Odoo rodando: `docker compose up -d`
2. Módulos instalados: `api_gateway`, `quicksol_estate`
3. Database: `realestate`
4. Usuário padrão: `admin` / `admin`

## Performance

### Otimização com Sessões
```javascript
// ❌ LENTO: ~30s para 10 testes
beforeEach(() => {
  cy.visit('/web/login')
  cy.get('input[name="login"]').type('admin')
  // ... login manual
})

// ✅ RÁPIDO: ~10s para 10 testes (3x mais rápido!)
beforeEach(() => {
  cy.odooLoginSession()
})
```

## Integração CI/CD

### GitHub Actions (exemplo)
```yaml
name: Cypress Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start Odoo
        run: |
          cd 18.0
          docker compose up -d
      - name: Run Tests
        uses: cypress-io/github-action@v5
        with:
          working-directory: .
          spec: cypress/e2e/**/*.cy.js
```

## Documentação

- **README Principal**: `/cypress/README.md`
- **Comandos Customizados**: `/cypress/COMANDOS_CUSTOMIZADOS.md`
- **Exemplo de Boas Práticas**: `/cypress/e2e/exemplo-boas-praticas.cy.js`

## Consequences

### Positivas
✅ Testes automatizados garantem qualidade contínua  
✅ Debugging facilitado com time travel e screenshots  
✅ Documentação viva do comportamento esperado  
✅ CI/CD permite validação automática em PRs  
✅ Comandos customizados aumentam produtividade  
✅ Performance otimizada (3x mais rápido com sessões)  

### Negativas
⚠️ Requer manutenção quando UI muda  
⚠️ Testes podem ser flaky se mal escritos  
⚠️ Curva de aprendizado inicial para novos desenvolvedores  

### Mitigações
- Documentação completa de boas práticas
- Comandos customizados simplificam uso
- Exemplo prático (`exemplo-boas-praticas.cy.js`)
- Code review obrigatório para novos testes

## Próximos Passos

1. ✅ Criar testes para API Gateway (concluído)
2. ⏳ Expandir cobertura para módulo `quicksol_estate`
3. ⏳ Integrar com GitHub Actions para CI/CD
4. ⏳ Adicionar testes de performance/carga
5. ⏳ Criar relatórios HTML com Mochawesome

## Referências

- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
- [Cypress Session API](https://docs.cypress.io/api/commands/session)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)

## Histórico de Revisões

| Data       | Versão | Autor | Mudanças                                    |
|------------|--------|-------|---------------------------------------------|
| 2025-11-15 | 1.0    | Equipe| Criação inicial - Adoção do Cypress        |

---

**Responsável**: Equipe de Desenvolvimento  
**Revisores**: Tech Lead, QA Lead  
**Data de Aprovação**: 2025-11-15
