# Multitenancy Checklist: User Onboarding & Password Management

**Purpose**: Validar a qualidade dos requisitos da Feature 009 (US1–US6), com foco em isolamento entre empresas e readiness de release.
**Created**: 2026-02-17
**Feature**: /opt/homebrew/var/www/realestate/realestate_backend/specs/009-user-onboarding-password-management/spec.md

## Requirement Completeness

- [x] CHK001 Os requisitos definem explicitamente o comportamento de isolamento por empresa para todos os endpoints autenticados (`/users/invite`, `/users/{id}/resend-invite`), e não apenas exemplos pontuais? [Completeness, Spec §FR1, Spec §User Story 4] — Decisão: isolamento obrigatório por `X-Company-ID` ativo.
- [x] CHK002 O spec cobre de forma completa como o isolamento se aplica aos fluxos públicos (`set-password`, `forgot-password`, `reset-password`) sem depender de sessão de empresa? [Completeness, Spec §FR2, Spec §FR3, Spec §User Story 3] — Decisão: forgot/reset públicos com anti-enumeration e sem dependência de sessão.
- [x] CHK003 Está documentado, para cada perfil RBAC, se o escopo é “mesma empresa” ou “todas as empresas vinculadas” quando há múltiplas vinculações? [Gap, Spec §FR1, Spec §User Story 1] — Decisão: escopo apenas da empresa selecionada no header.
- [ ] CHK004 O comportamento esperado para conflito de `document` em tenant existente sem vínculo de `res.users` está completamente definido (mensagem, código, fluxo de resolução)? [Completeness, Spec §Clarifications Q5]

## Requirement Clarity

- [ ] CHK005 O termo “isolamento multi-tenancy” está operacionalizado com critérios verificáveis (filtros, escopo de busca, respostas esperadas) e não apenas textual? [Clarity, Spec §User Story 1, Spec §User Story 4]
- [x] CHK006 A distinção entre “não encontrado por isolamento” e “não encontrado de fato” está clara para evitar ambiguidade entre 404 e 403? [Ambiguity, Spec §User Story 4] — Decisão: cross-company deve responder sempre 404.
- [x] CHK007 O spec define com precisão quando retornar 409 por conflito de documento/email em contexto multiempresa (mesma empresa vs outra empresa)? [Clarity, Spec §FR1.7, Spec §FR1.8] — Decisão: conflito de `document` permitido por empresa (não global).
- [ ] CHK008 O requisito para `profile=portal` explicita com clareza quais campos condicionais são obrigatórios e em quais cenários exatos de validação? [Clarity, Spec §FR1.11, Spec §Clarifications Q2]

## Requirement Consistency

- [ ] CHK009 As regras de isolamento descritas nas User Stories são consistentes com os FRs (especialmente FR1/FR3/US4/US5)? [Consistency, Spec §FR1, Spec §FR3, Spec §User Story 4, Spec §User Story 5]
- [ ] CHK010 A matriz de autorização por perfil (Owner/Manager/Agent etc.) não conflita com as restrições de isolamento por empresa em nenhum cenário de convite/reenvio? [Consistency, Spec §User Story 1, Spec §User Story 4]
- [x] CHK011 As definições de endpoints públicos (anti-enumeration) não entram em conflito com os requisitos de isolamento/segurança dos endpoints privados? [Consistency, Spec §FR2.9, Spec §FR3.1] — Decisão: manter paridade de status/shape/tempo aproximado no forgot-password.
- [ ] CHK012 O comportamento de dual record (`res.users` + `real.estate.tenant`) está consistente entre critérios de criação, validação e conflitos de documento? [Consistency, Spec §FR1.11, Spec §Clarifications Q2, Q5]

## Acceptance Criteria Quality

- [ ] CHK013 Cada critério de aceitação relevante para isolamento inclui resultado mensurável (status code, escopo de dados, condição de sucesso/falha)? [Acceptance Criteria, Spec §User Story 1, Spec §User Story 4]
- [x] CHK014 Os critérios para erros (400/403/404/409/410/429) são objetivos e não deixam margem para interpretações divergentes entre times? [Measurability, Spec §User Stories 1–4] — Decisão de precedência: AuthZ > Isolamento > Validação.
- [x] CHK015 Os critérios de “sempre 200” no forgot-password têm medição explícita de paridade de resposta (estrutura e semântica) para evitar enumeração? [Acceptance Criteria, Spec §FR3.1, Spec §User Story 3] — Decisão: exigir mesmo status, mesmo shape e tempo aproximado.

## Scenario Coverage

- [ ] CHK016 Os requisitos cobrem cenário primário e alternativo para convite em multiempresa (empresa correta, empresa incorreta, usuário sem acesso)? [Coverage, Spec §User Story 1, Spec §User Story 4]
- [ ] CHK017 Cenários de exceção para token em contexto multiempresa (token válido, expirado, usado, inexistente, inválido) estão completos e sem lacunas? [Coverage, Spec §FR2, Spec §FR3]
- [ ] CHK018 O spec cobre cenários de recuperação (reenvio de convite, geração de novo reset token, invalidação de anteriores) com condições claras de rollback lógico? [Recovery Flow, Spec §User Story 3, Spec §User Story 4]
- [x] CHK019 O cenário de usuário com múltiplas empresas vinculadas está coberto ou explicitamente excluído? [Gap, Assumption, Spec §FR1, Spec §User Story 5] — Decisão: atuar somente no `X-Company-ID` ativo.

## Edge Case Coverage

- [ ] CHK020 Estão definidos requisitos para comportamento quando `company_id` informado é inválido, ausente ou incompatível com contexto do usuário? [Edge Case, Spec §FR1, Spec §User Story 1]
- [x] CHK021 O spec aborda casos limite de race condition (dois convites/reenvios simultâneos para o mesmo usuário) com resultado esperado? [Gap, Edge Case] — Decisão: último token vence, anteriores devem ser invalidados.
- [ ] CHK022 Há definição para conflitos de dados entre tenant pré-existente e novo convite portal em empresas diferentes? [Edge Case, Spec §Clarifications Q5]
- [ ] CHK023 O comportamento com usuário inativo em fluxos públicos (forgot/reset) está completo e consistente com anti-enumeration? [Edge Case, Spec §User Story 3]

## Non-Functional Requirements

- [ ] CHK024 Requisitos de segurança para isolamento de dados estão descritos com critérios auditáveis (não apenas intenção arquitetural)? [NFR-Security, Spec §FR1, Spec §FR3]
- [ ] CHK025 Requisitos de desempenho para operações de token e validação multiempresa estão quantificados e testáveis? [Gap, NFR-Performance, Plan §Technical Context] — Decisão atual: sem número fixo (ainda pendente de quantificação).
- [x] CHK026 Requisitos de observabilidade (logs/auditoria) distinguem eventos de autorização negada vs falhas operacionais sem expor dados sensíveis? [NFR-Observability, Gap] — Decisão: exigir logs apenas de erro.
- [x] CHK027 Há cobertura de conformidade/LGPD para exposição mínima de dados em respostas de erro cross-company? [NFR-Compliance, Plan §Technical Context] — Decisão: não identificar recurso/empresa em erros cross-company.

## Dependencies & Assumptions

- [x] CHK028 As dependências críticas (record rules, decorators, company scoping, Redis/session) estão explicitadas como pré-condições de comportamento dos requisitos? [Dependency, Plan §Constitution Check] — Decisão: pré-condições obrigatórias.
- [x] CHK029 As suposições sobre suporte a CPF/CNPJ e validação de documento por perfil estão documentadas de modo inequívoco? [Assumption, Spec §FR1.13] — Decisão confirmada: CPF/CNPJ por perfil conforme FR1.13.
- [x] CHK030 O spec define como validar que configurações dinâmicas de TTL não causam deriva entre empresas/ambientes? [Dependency, Gap, Spec §User Story 5] — Decisão: validação manual (sem automação obrigatória neste ciclo).

## Ambiguities & Conflicts

- [x] CHK031 Existe definição inequívoca para precedência de erro quando múltiplas violações ocorrem (ex.: perfil proibido + empresa incorreta + payload inválido)? [Ambiguity, Conflict] — Decisão: AuthZ > Isolamento > Validação.
- [ ] CHK032 O documento resolve potenciais conflitos entre “mesma resposta por segurança” e necessidades de troubleshooting operacional? [Conflict, Spec §FR3.1]
- [x] CHK033 O spec estabelece estratégia de rastreabilidade (IDs/links) entre FRs, User Stories e testes para evitar lacunas de interpretação em release gate? [Traceability, Gap] — Decisão: esquema FR/AC/TEST obrigatório.

## Notes

- Este checklist avalia qualidade de requisitos (não valida implementação).
- Marque itens com `[x]` após revisão e anexe observações ao lado de cada CHK.
- Em caso de dúvida, registrar o ponto como `[Ambiguity]` e abrir clarificação formal no spec.
