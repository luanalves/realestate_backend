# Feature Specification: Gestão Completa de Agentes/Funcionários da Imobiliária

**Feature Branch**: `004-agent-management`  
**Created**: 2026-01-09  
**Status**: Draft  
**Input**: User description: "Implementar gestão completa de agentes e funcionários vinculados à imobiliária com CRUD, atribuições, permissões e comissionamento"

## Clarifications

### Session 2026-01-09

- Q: CRECI obrigatório ou opcional? → A: CRECI opcional - Campo opcional, mas se fornecido deve ser válido (permite estagiários e auxiliares sem CRECI)
- Q: Agente pode trabalhar em múltiplas imobiliárias? → A: Um agente pertence a uma única imobiliária (organização/empresa). A imobiliária pode ter múltiplas filiais, e o agente trabalha para a imobiliária podendo atender em qualquer filial
- Q: Desativar agente com contratos ativos - permite ou bloqueia? → A: Permite desativar com contratos ativos - Soft-delete permitido, contratos mantêm referência histórica ao agente desativado
- Q: Comissão retroativa - aplica em contratos antigos ou só novos? → A: Apenas contratos novos - Alteração de regra de comissão aplica apenas a contratos/transações criados após a data da mudança
- Q: Formato exato de validação do CRECI → A: Formato flexível - Aceita variações comuns (CRECI/SP 12345, CRECI-SP-12345, CRECI SP 12345, 12345-SP) e normaliza internamente para formato padrão "CRECI/UF NNNNN"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Cadastrar e Visualizar Agentes (Priority: P1)

Um gestor da imobiliária precisa cadastrar novos agentes/corretores e visualizar a lista de todos os agentes ativos vinculados à sua empresa. Cada agente deve ter informações básicas como nome, CPF, CRECI, contato e vinculação à imobiliária.

**Why this priority**: É a funcionalidade base essencial - sem poder cadastrar e visualizar agentes, nenhuma outra funcionalidade pode funcionar. Representa o MVP mínimo viável.

**Independent Test**: Pode ser completamente testado criando um agente via API POST /api/v1/agents e listando via GET /api/v1/agents. O teste valida que agentes são vinculados automaticamente à empresa do usuário logado.

**Acceptance Scenarios**:

1. **Given** um gestor autenticado da Imobiliária A, **When** ele cria um agente com dados válidos (nome, CPF, CRECI, telefone, email), **Then** o sistema cria o agente vinculado à Imobiliária A e retorna HTTP 201 com o ID do agente
2. **Given** um gestor autenticado da Imobiliária A com 5 agentes cadastrados, **When** ele lista todos os agentes, **Then** o sistema retorna apenas os 5 agentes da Imobiliária A (isolamento multi-tenant)
3. **Given** um gestor da Imobiliária B, **When** ele tenta listar agentes, **Then** o sistema retorna apenas agentes da Imobiliária B, não vendo agentes da Imobiliária A
4. **Given** um gestor autenticado, **When** ele tenta criar um agente com CPF inválido, **Then** o sistema retorna HTTP 400 com mensagem de erro de validação
5. **Given** um gestor autenticado, **When** ele tenta criar um agente com CRECI duplicado na mesma imobiliária, **Then** o sistema retorna HTTP 400 com mensagem "CRECI já cadastrado"

---

### User Story 2 - Atualizar e Desativar Agentes (Priority: P2)

Um gestor precisa poder atualizar informações de agentes existentes (telefone, email, dados bancários) e desativar agentes que não trabalham mais na imobiliária, sem deletar o histórico de transações.

**Why this priority**: Mantém os dados atualizados e permite gestão do ciclo de vida dos agentes, preservando histórico para auditoria e relatórios.

**Independent Test**: Pode ser testado independentemente via PUT /api/v1/agents/{id} para atualização e PATCH /api/v1/agents/{id}/deactivate para desativação. Valida que agentes inativos não aparecem em listagens ativas mas mantêm histórico.

**Acceptance Scenarios**:

1. **Given** um agente ativo da Imobiliária A, **When** um gestor da mesma imobiliária atualiza o telefone do agente, **Then** o sistema atualiza o telefone e retorna HTTP 200
2. **Given** um agente da Imobiliária A, **When** um gestor da Imobiliária B tenta atualizar dados do agente, **Then** o sistema retorna HTTP 404 (isolamento multi-tenant)
3. **Given** um agente ativo com 10 propriedades atribuídas, **When** o gestor desativa o agente, **Then** o agente fica inativo mas mantém histórico de propriedades
4. **Given** um agente inativo, **When** o gestor lista agentes ativos, **Then** o agente inativo não aparece na lista
5. **Given** um agente inativo, **When** o gestor visualiza histórico de vendas, **Then** as vendas realizadas pelo agente inativo ainda aparecem no histórico

---

### User Story 3 - Atribuir Agentes a Imóveis (Priority: P3)

Um gestor precisa atribuir agentes responsáveis a imóveis específicos, permitindo que cada imóvel tenha um ou mais agentes responsáveis pela venda/locação.

**Why this priority**: Permite rastreabilidade e responsabilização, fundamental para cálculo de comissões e gestão de performance.

**Independent Test**: Pode ser testado via PATCH /api/v1/properties/{id}/assign-agent passando agent_id. Valida que apenas agentes da mesma imobiliária podem ser atribuídos.

**Acceptance Scenarios**:

1. **Given** um imóvel da Imobiliária A e um agente ativo da mesma imobiliária, **When** o gestor atribui o agente ao imóvel, **Then** o sistema vincula o agente e retorna HTTP 200
2. **Given** um imóvel da Imobiliária A, **When** o gestor tenta atribuir um agente da Imobiliária B, **Then** o sistema retorna HTTP 403 "Agente não pertence à mesma imobiliária"
3. **Given** um imóvel com agente A atribuído, **When** o gestor atribui agente B ao mesmo imóvel, **Then** ambos agentes ficam vinculados (co-responsáveis)
4. **Given** um imóvel com 2 agentes atribuídos, **When** o gestor lista os agentes do imóvel, **Then** o sistema retorna os 2 agentes
5. **Given** um agente com 15 imóveis atribuídos, **When** o gestor consulta a carteira do agente, **Then** o sistema retorna os 15 imóveis

---

### User Story 4 - Configurar Comissões de Agentes (Priority: P4)

Um gestor precisa configurar regras de comissionamento por agente, definindo percentuais de comissão sobre vendas e locações, podendo ter regras diferentes por agente ou tipo de transação.

**Why this priority**: Automatiza cálculo de comissões, evita erros manuais e facilita gestão financeira.

**Independent Test**: Pode ser testado via POST /api/v1/agents/{id}/commission-rules definindo percentuais. Valida que regras são aplicadas corretamente em simulações de comissão.

**Acceptance Scenarios**:

1. **Given** um agente ativo, **When** o gestor define comissão de 6% sobre vendas, **Then** o sistema salva a regra e retorna HTTP 201
2. **Given** um agente com comissão de 6% em vendas, **When** o agente fecha uma venda de R$ 300.000, **Then** o sistema calcula comissão de R$ 18.000
3. **Given** um agente com comissão de 10% em locações, **When** o agente fecha uma locação de R$ 2.000/mês, **Then** o sistema calcula comissão de R$ 200/mês
4. **Given** um agente com 2 regras (vendas e locações), **When** o gestor consulta regras do agente, **Then** o sistema retorna ambas regras
5. **Given** um agente, **When** o gestor tenta definir comissão acima de 100%, **Then** o sistema retorna HTTP 400 "Percentual inválido"

---

### User Story 5 - Visualizar Performance de Agentes (Priority: P5)

Um gestor precisa visualizar indicadores de performance de cada agente (quantidade de vendas, locações, comissões geradas, imóveis ativos) para análise de desempenho.

**Why this priority**: Fornece insights para gestão de equipe, bonificações e identificação de top performers.

**Independent Test**: Pode ser testado via GET /api/v1/agents/{id}/performance retornando métricas agregadas. Valida isolamento (métricas apenas da imobiliária do gestor).

**Acceptance Scenarios**:

1. **Given** um agente com 5 vendas realizadas no mês, **When** o gestor consulta performance do agente, **Then** o sistema retorna métricas: 5 vendas, valor total, comissões geradas
2. **Given** um agente com 10 imóveis ativos e 3 locações ativas, **When** o gestor consulta performance, **Then** o sistema retorna: 10 imóveis em carteira, 3 locações ativas
3. **Given** dois agentes A e B da mesma imobiliária, **When** o gestor consulta ranking de performance, **Then** o sistema retorna lista ordenada por número de vendas ou comissões
4. **Given** um agente que realizou vendas em 2025 e 2026, **When** o gestor filtra performance por período (2026), **Then** o sistema retorna apenas dados de 2026
5. **Given** um gestor da Imobiliária A, **When** ele consulta performance de agentes, **Then** o sistema retorna apenas performance de agentes da Imobiliária A

---

### Edge Cases

- **Agente sem CRECI**: Sistema permite cadastro de agentes sem CRECI (estagiários, auxiliares). CRECI é validado apenas quando fornecido. Agentes sem CRECI podem ter restrições em operações críticas (ex: fechar contratos) conforme regras de negócio.
- **Agente com múltiplas imobiliárias**: Agente pertence a uma única imobiliária. Se a imobiliária tem filiais, o agente pode atender em qualquer filial (hierarquia de companies do Odoo). Se um corretor trabalha para duas organizações diferentes, precisa de dois cadastros separados.
- **Desativação com contratos ativos**: Sistema permite desativar agente mesmo com contratos de locação/venda ativos. Contratos mantêm referência ao agente desativado para histórico e auditoria. Agente desativado não pode mais realizar novas operações, mas contratos existentes continuam válidos até o término natural.
- **Comissão retroativa**: Alteração de regra de comissão aplica apenas a contratos/transações fechados após a data da mudança. Contratos anteriores mantêm comissão calculada com regra vigente na época. Isso evita recálculos retroativos e mantém previsibilidade contábil.
- **Agente deletado vs desativado**: Sistema permite deletar agente ou apenas desativar? O que acontece com histórico?
- **Limites de agentes**: Existe limite de agentes por imobiliária?
- **Agente sem vinculação**: Sistema permite agente existir sem estar vinculado a nenhuma imobiliária?
- **Transferência de carteira**: O que acontece quando um agente sai e precisa transferir seus imóveis para outro agente?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide REST API endpoint POST /api/v1/agents for creating new agents
- **FR-002**: System MUST validate CPF format (11 digits) and uniqueness within the same company
- **FR-003**: System MUST validate CRECI (Conselho Regional de Corretores de Imóveis) format and uniqueness within the same company when provided (CRECI is optional to allow trainees/assistants without CRECI). System MUST accept flexible input formats and normalize to standard "CRECI/UF NNNNN"
- **FR-004**: System MUST automatically link agents to the authenticated user's company (multi-tenant isolation)
- **FR-005**: System MUST provide GET /api/v1/agents endpoint returning only agents from user's company
- **FR-006**: System MUST provide GET /api/v1/agents/{id} endpoint with 404 if agent doesn't belong to user's company
- **FR-007**: System MUST provide PUT /api/v1/agents/{id} for updating agent information
- **FR-008**: System MUST prevent updating company_ids field via API (security constraint)
- **FR-009**: System MUST provide soft-delete functionality (deactivation) preserving agent history
- **FR-010**: System MUST filter out inactive agents from default listing (unless explicitly requested)
- **FR-011**: System MUST allow multiple agents to be assigned to a single property
- **FR-012**: System MUST prevent assigning agents from different companies to same property
- **FR-013**: System MUST provide commission rule configuration per agent
- **FR-014**: System MUST support different commission percentages for sales vs rentals
- **FR-015**: System MUST calculate commission amounts based on transaction value and agent rules
- **FR-016**: System MUST provide performance metrics endpoint GET /api/v1/agents/{id}/performance
- **FR-017**: System MUST track agent metrics: number of properties, active leases, completed sales, total commissions
- **FR-018**: System MUST support filtering performance by date range
- **FR-019**: System MUST log all agent creation/update/deactivation operations for audit trail
- **FR-020**: System MUST enforce @require_company decorator on all agent endpoints
- **FR-021**: System MUST support pagination on agent listing (limit, offset parameters)
- **FR-022**: System MUST support search/filtering agents by name, CPF, CRECI, status
- **FR-023**: System MUST validate email format when provided
- **FR-024**: System MUST validate Brazilian phone number format
- **FR-025**: System MUST prevent hard deletion of agents with active contracts, but MUST allow soft-delete (deactivation) preserving referential integrity
- **FR-026**: System MUST maintain referential integrity between agents and properties/contracts
- **FR-027**: System MUST return detailed error messages for validation failures (HTTP 400)
- **FR-028**: System MUST return HTTP 404 for non-existent or unauthorized agent access
- **FR-029**: System MUST return HTTP 403 for cross-company unauthorized operations
- **FR-030**: System MUST support Odoo's record rules for Web UI access control
- **FR-031**: System MUST apply commission rule changes only to new transactions created after the rule change date (no retroactive recalculation)

### Key Entities

- **Agent/Corretor**: Represents a real estate agent or broker linked to a company
  - Attributes: name, CPF, CRECI (optional), phone, email, active status, hire date, bank account, commission rates
  - Relationships: belongs to company (many-to-one), assigned to properties (many-to-many), linked to user account (one-to-one optional)
  
- **Commission Rule**: Defines commission calculation rules per agent
  - Attributes: agent_id, transaction_type (sale/rental), percentage, min_value, max_value
  - Relationships: belongs to agent (many-to-one)
  
- **Agent Performance Metrics**: Aggregated performance data (computed/cached)
  - Attributes: agent_id, period, total_sales, total_rentals, total_commissions, active_properties
  - Relationships: belongs to agent (one-to-one per period)

- **Property-Agent Assignment**: Links agents to properties they manage
  - Attributes: property_id, agent_id, assignment_date, responsibility_type (primary/secondary)
  - Relationships: links property to agent (many-to-many junction table)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Managers can create a new agent in under 1 minute via API with complete data validation
- **SC-002**: System enforces 100% isolation - users from Company A never see agents from Company B
- **SC-003**: Agent listing endpoint returns results in under 500ms for up to 1000 agents
- **SC-004**: Commission calculations are automatically computed with 100% accuracy based on configured rules
- **SC-005**: Performance metrics are generated and cached, accessible in under 200ms
- **SC-006**: 95% of agent operations complete successfully on first attempt without validation errors
- **SC-007**: System maintains complete audit trail - all agent changes are logged with user, timestamp, and changes
- **SC-008**: Zero data leakage between companies in security tests (all isolation tests pass)
- **SC-009**: API returns appropriate HTTP status codes (201, 200, 400, 404, 403) 100% of the time
- **SC-010**: Inactive agents are completely hidden from active listings while preserving historical data integrity

## Assumptions *(include if applicable)*

- **A-001**: Agents must be linked to exactly one company (imobiliária/organização) at any given time. The company may have multiple branches/filials, and the agent works for the company (can serve any branch). If a person works for two different companies, they need separate agent records.
- **A-002**: CRECI number format follows Brazilian standard. System accepts flexible input formats ("CRECI/SP 12345", "CRECI-SP-12345", "CRECI SP 12345", "12345-SP") and normalizes internally to standard format "CRECI/UF NNNNN" for storage
- **A-003**: CPF validation uses Brazilian CPF algorithm (11 digits with checksum validation)
- **A-004**: Commission percentages are stored as decimals (e.g., 6% = 0.06) with max 2 decimal places
- **A-005**: Soft-delete is preferred over hard-delete to maintain referential integrity
- **A-006**: Phone numbers follow Brazilian format: +55 (DDD) 9XXXX-XXXX
- **A-007**: Email is optional for agents but required for agents with user accounts
- **A-008**: Performance metrics are calculated daily via scheduled job (not real-time)
- **A-009**: Existing `real.estate.agent` model in Odoo already has base structure with company_ids field
- **A-010**: Record rules for multi-tenancy are already configured in `security/record_rules.xml`
- **A-011**: API authentication via JWT token is already implemented (@require_jwt decorator)
- **A-012**: Session validation is already implemented (@require_session decorator)

## Scope Boundaries *(optional but recommended)*

### In Scope

- CRUD operations for agents via REST API
- Multi-tenant isolation (company-based filtering)
- Commission rule configuration and calculation
- Agent-property assignment
- Performance metrics and reporting
- Data validation (CPF, CRECI, email, phone)
- Soft-delete/deactivation
- Audit logging
- Pagination and search/filtering
- Integration with existing Odoo models

### Out of Scope

- User interface (Web UI) - only API endpoints
- Agent scheduling/calendar integration
- Lead assignment automation
- Real-time notifications
- Mobile app
- Document management for agents
- Training/certification tracking
- Integration with external CRM systems
- Advanced analytics/dashboards (beyond basic metrics)
- Multi-language support (Portuguese only)
- Agent hierarchy/teams management

## Technical Constraints *(optional)*

- **TC-001**: Must follow Odoo 18.0 ORM patterns and conventions
- **TC-002**: Must use existing middleware decorators: @require_jwt, @require_session, @require_company
- **TC-003**: Must follow ADR-001 (development guidelines) and ADR-004 (nomenclatura)
- **TC-004**: Must use thedevkitchen_ prefix for all custom modules/models
- **TC-005**: Must implement endpoints in `controllers/agent_api.py`
- **TC-006**: Must use CompanyValidator service for company_ids validation
- **TC-007**: Must return JSON responses following existing API patterns
- **TC-008**: Must write integration tests in `tests/api/test_agent_api.py`
- **TC-009**: Must maintain compatibility with existing record rules
- **TC-010**: Must not break existing property API or master data endpoints
