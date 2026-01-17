# API Contracts - Agent Management

Este diretório contém os schemas OpenAPI 3.0 para as APIs do módulo de gerenciamento de agentes.

## Arquivos

| Arquivo | Descrição | Modelo Odoo |
|---------|-----------|-------------|
| `agent.schema.yaml` | API de gerenciamento de agentes | `real.estate.agent` |
| `commission-rule.schema.yaml` | API de regras de comissão | `real.estate.commission.rule` |
| `assignment.schema.yaml` | API de atribuição agente-propriedade | `real.estate.agent.property.assignment` |
| `commission-transaction.schema.yaml` | API de transações de comissão | `real.estate.commission.transaction` |

## Conformidade com ADRs

Todos os schemas seguem as decisões arquiteturais:

- **ADR-005**: OpenAPI 3.0 com request/response schemas obrigatórios
- **ADR-007**: HATEOAS (hypermedia links) em todas as respostas
- **ADR-008**: Segurança multi-tenancy (company_id filtering)
- **ADR-011**: Dual authentication (JWT + Session)
- **ADR-012**: Validação CRECI (formato, verificação)
- **ADR-013**: Cálculo de comissões (versioning, snapshots)
- **ADR-014**: Many2many Agent-Property (junction table patterns)
- **ADR-015**: Soft-delete (active field, preservação de referências)

## Como usar

### 1. Validar schemas

```bash
# Instalar validator
npm install -g @stoplight/spectral-cli

# Validar
spectral lint agent.schema.yaml
spectral lint commission-rule.schema.yaml
```

### 2. Gerar documentação interativa

```bash
# Usando Swagger UI
docker run -p 8080:8080 \
  -v $(pwd):/schemas \
  swaggerapi/swagger-ui

# Acessar: http://localhost:8080
```

### 3. Gerar client SDKs

```bash
# Gerar client Python
openapi-generator-cli generate \
  -i agent.schema.yaml \
  -g python \
  -o clients/python

# Gerar client JavaScript
openapi-generator-cli generate \
  -i agent.schema.yaml \
  -g javascript \
  -o clients/js
```

## Endpoints principais

### Agents API

- `GET /api/v1/agents` - Listar agentes
- `POST /api/v1/agents` - Criar agente
- `GET /api/v1/agents/{id}` - Obter agente
- `PUT /api/v1/agents/{id}` - Atualizar agente
- `DELETE /api/v1/agents/{id}` - Desativar agente (soft-delete)
- `POST /api/v1/agents/{id}/deactivate` - Desativar com motivo
- `POST /api/v1/agents/{id}/reactivate` - Reativar agente

### Commission Rules API

- `GET /api/v1/agents/{id}/commission-rules` - Listar regras
- `POST /api/v1/agents/{id}/commission-rules` - Criar regra
- `PUT /api/v1/agents/{id}/commission-rules/{rule_id}` - Atualizar (cria versão)
- `POST /api/v1/agents/{id}/calculate-commission` - Simular cálculo

### Assignments API

- `GET /api/v1/assignments` - Listar atribuições
- `POST /api/v1/assignments` - Criar atribuição
- `DELETE /api/v1/assignments/{id}` - Remover atribuição

### Commission Transactions API

- `GET /api/v1/commission-transactions` - Listar transações
- `PUT /api/v1/commission-transactions/{id}/mark-paid` - Marcar como pago


## Exemplos de uso

### Criar um agente

```bash
curl -X POST http://localhost:8069/api/v1/agents \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "email": "joao.silva@example.com",
    "phone": "+55 11 98765-4321",
    "creci_number": "123456",
    "creci_state": "SP",
    "company_ids": [1]
  }'
```

### Listar agentes ativos

```bash
curl -X GET "http://localhost:8069/api/v1/agents?active=true&limit=20" \
  -H "Authorization: Bearer <token>"
```

### Criar regra de comissão

```bash
curl -X POST http://localhost:8069/api/v1/agents/1/commission-rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Comissão Vendas 6%",
    "transaction_type": "sale",
    "structure_type": "percentage",
    "percentage": 6.0,
    "valid_from": "2026-01-01T00:00:00Z"
  }'
```

## Testes com Cypress

Os schemas podem ser testados end-to-end com Cypress (ADR-002):

```javascript
// cypress/e2e/agent-api.cy.js
describe('Agent API', () => {
  it('should create agent with valid CRECI', () => {
    cy.request({
      method: 'POST',
      url: '/api/v1/agents',
      body: {
        name: 'João Silva',
        email: 'joao@example.com',
        creci_number: '123456',
        creci_state: 'SP',
        company_ids: [1]
      }
    }).then((response) => {
      expect(response.status).to.eq(201)
      expect(response.body.success).to.be.true
      expect(response.body.data).to.have.property('id')
    })
  })
})
```

## Roadmap

- [ ] Phase 1: Agent CRUD (basic endpoints)
- [ ] Phase 2: Commission Rules CRUD
- [ ] Phase 3: Assignments (many2many)
- [ ] Phase 4: Commission Transactions
- [ ] Phase 5: CRECI verification integration
- [ ] Phase 6: Batch operations
- [ ] Phase 7: Webhooks (agent.created, commission.paid)

## Referências

- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
- [ADR-005: OpenAPI Documentation](../../docs/adr/ADR-005-openapi-30-swagger-documentation.md)
- [ADR-007: HATEOAS](../../docs/adr/ADR-007-hateoas-hypermedia-rest-api.md)
- [Spec: Agent Management](../spec.md)
