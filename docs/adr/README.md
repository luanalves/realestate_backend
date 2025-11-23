# Architecture Decision Records (ADR)

Este diretório contém as decisões arquiteturais do projeto Real Estate Management System.

## Índice de ADRs

| ADR | Título | Status | Data |
|-----|--------|--------|------|
| [ADR-001](./ADR-001-development-guidelines-for-odoo-screens.md) | Development Guidelines for Odoo Screens and Features | Accepted | 2025-10-14 |
| [ADR-002](./ADR-002-cypress-end-to-end-testing.md) | Uso do Cypress para Testes End-to-End | Accepted | 2025-11-15 |
| [ADR-003](./ADR-003-mandatory-test-coverage.md) | Cobertura de Testes Obrigatória para Todos os Módulos | Accepted | 2025-11-16 |

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