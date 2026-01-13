# Architecture Decision Records (ADR)

Este diretório contém as decisões arquiteturais do projeto Real Estate Management System.

## Índice de ADRs

| ADR | Título | Status | Data |
|-----|--------|--------|------|
| [ADR-001](./ADR-001-development-guidelines-for-odoo-screens.md) | Development Guidelines for Odoo Screens and Features | Accepted | 2025-10-14 |
| [ADR-002](./ADR-002-cypress-end-to-end-testing.md) | Uso do Cypress para Testes End-to-End | Accepted | 2025-11-15 |
| [ADR-003](./ADR-003-mandatory-test-coverage.md) | Cobertura de Testes Obrigatória para Todos os Módulos | Accepted | 2025-11-16 |
| [ADR-004](./ADR-004-nomenclatura-modulos-tabelas.md) | Nomenclatura de Módulos e Tabelas | Accepted | 2025-11-17 |
| [ADR-005](./ADR-005-openapi-30-swagger-documentation.md) | OpenAPI 3.0 com Request Body e Response Schemas Obrigatórios | Accepted | 2025-11-18 |
| [ADR-006](./ADR-006-git-flow-workflow.md) | Git Flow Workflow | Accepted | 2025-11-19 |
| [ADR-007](./ADR-007-hateoas-hypermedia-rest-api.md) | HATEOAS (Hypermedia as the Engine of Application State) para APIs REST | Accepted | 2025-11-30 |
| [ADR-008](./ADR-008-api-security-multi-tenancy.md) | **Segurança de APIs em Ambiente Multi-Tenancy** | **Accepted** | **2025-11-30** |
| [ADR-009](./ADR-009-headless-authentication-user-context.md) | **Autenticação Headless com Contexto de Usuário** | **Proposed** | **2025-11-30** |
| [ADR-010](./ADR-010-python-virtual-environment.md) | Python Virtual Environment | Accepted | 2025-12-01 |
| [ADR-011](./ADR-011-controller-security-authentication-storage.md) | **Segurança de Controllers - Autenticação Dual e Armazenamento** | **Accepted** | **2025-12-13** |
| [ADR-012](./ADR-012-creci-validation-brazilian-real-estate.md) | **CRECI Validation for Brazilian Real Estate System** | **Proposed** | **2026-01-12** |
| [ADR-013](./ADR-013-commission-calculation-rule-management.md) | **Real Estate Commission Calculation and Rule Management** | **Proposed** | **2026-01-12** |
| [ADR-014](./ADR-014-odoo-many2many-agent-property-relationship.md) | **Odoo ORM Many2many Relationship Patterns for Agent-Property Assignment** | **Accepted** | **2026-01-12** |
| [ADR-015](./ADR-015-soft-delete-logical-deletion-odoo-models.md) | **Soft-Delete (Logical Deletion) Strategies for Odoo Models with Referential Integrity** | **Accepted** | **2026-01-12** |

## Como usar as ADRs

1. **Para desenvolvedores**: Consulte as ADRs antes de implementar novas funcionalidades
2. **Para code reviews**: Use as ADRs como referência para validar implementações
3. **Para novos membros**: Leia todas as ADRs aceitas para entender as decisões arquiteturais

## Formato das ADRs

Seguimos o formato proposto por Michael Nygard:
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: Situação que motivou a decisão
- **Decision**: Descrição da decisão tomada
- **Consequences**: Consequências positivas e negativas da decisão

## Como criar uma nova ADR

1. Crie um novo arquivo: `ADR-XXX-titulo-da-decisao.md`
2. Use o próximo número sequencial
3. Siga o template padrão
4. Atualize este índice
5. Submeta para review da equipe

## Referências

- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) - Michael Nygard
- [ADR GitHub](https://adr.github.io/) - Ferramentas e exemplos