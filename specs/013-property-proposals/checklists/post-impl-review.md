# Post-Implementation Review Checklist: Property Proposals (Feature 013)

**Purpose**: Validate quality, completeness, clarity, and consistency of the written requirements in spec.md against the implemented feature — "unit tests for the spec".
**Created**: 2026-04-28
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)
**Audience**: Reviewer (post-implementation spec audit, pre-deploy gate)
**Depth**: Deep (55 items)
**Scope**: Gaps from áudio sessions (optional presentation flow, ficha analysis) explicitly excluded — deferred to future feature.

---

## Requirement Completeness

- [ ] CHK001 - São todos os 5 perfis de RBAC (Owner, Manager, Agent, Receptionist, Prospector) cobertos com requisitos de criação, leitura, mutação e deleção na matriz FR-044? O Prospector tem linha explícita de "nenhum acesso" documentada ou apenas ausência de linha? [Completeness, Spec §FR-044]

- [ ] CHK002 - FR-001 lista os campos obrigatórios da proposta, mas o campo `currency` (moeda) está ausente da lista de campos obrigatórios mesmo sendo citado nas Assumptions como "defaults to BRL". É um campo implícito ou precisa ser explicitado em FR-001? [Completeness, Spec §FR-001, Assumptions]

- [ ] CHK003 - FR-039 restringe tipos de arquivo (PDF, JPEG, PNG, DOC/DOCX, XLS/XLSX) mas US7 menciona "ID copies, financing letters" — há requisito definindo o que acontece com arquivos válidos de tipo TIFF, SVG ou outros formatos de imagem/documento que agentes podem precisar? [Completeness, Spec §FR-039, §US7]

- [ ] CHK004 - FR-026 define a rotina diária de expiração, mas não especifica o horário de execução do cron (ex: 00:00 UTC? horário do servidor?). Isso é relevante para contratos com `valid_until` no dia atual. Está documentado em algum lugar da spec? [Completeness, Spec §FR-026, Gap]

- [ ] CHK005 - FR-041 lista 7 templates de email, mas não especifica quem são os destinatários de "proposal.sent" (comprador? agente? ambos?). A spec tem um mapeamento evento → destinatário completo para todos os 7 eventos? [Completeness, Spec §FR-041]

- [ ] CHK006 - FR-042 exige registro de toda transição de estado no timeline, mas não especifica o formato/conteúdo mínimo de uma entrada de timeline (ex: timestamp, autor, estado anterior, estado novo, motivo). Esse contrato está definido? [Completeness, Spec §FR-042, Gap]

- [ ] CHK007 - A spec cobre o caso de cancelamento da proposta (FR-021, FR-046, T049), mas não define explicitamente quem pode cancelar manualmente (vs. auto-cancelamento). FR-044 menciona "Cancel (soft-delete): Yes/Yes/No/No/No" — essa restrição de agente não poder cancelar está descrita em prosa, ou apenas na tabela? [Completeness, Spec §FR-044, §FR-046]

- [ ] CHK008 - FR-040 exige que o detalhe da proposta exponha `documents_count` e metadados de anexos. A spec define o comportamento quando a proposta tem 0 anexos — retorna array vazio `[]` ou campo ausente? [Completeness, Spec §FR-040, Gap]

- [ ] CHK009 - US8 (Expiração) cenário 4 menciona uma ação de "renew" (criar novo rascunho a partir de expirado). Existe um FR correspondente a esse flow de renovação? Não foi encontrado FR explícito para isso. [Completeness, Spec §US8, Gap]

- [ ] CHK010 - A spec define que `valid_until` default é 7 dias após o envio (FR-025), mas não especifica o que acontece se o agente altera `valid_until` após o envio (estado `sent`). Propostas em `sent` são editáveis? [Completeness, Spec §FR-025, §FR-007]

---

## Requirement Clarity

- [ ] CHK011 - FR-003 rejeita "non-positive monetary value". O termo "non-positive" inclui zero? A spec deve ser inequívoca: é `value > 0` ou `value >= 0`? [Clarity, Spec §FR-003]

- [ ] CHK012 - FR-008 define "active proposal" como estado em `(Draft, Sent, Negotiation, Accepted)`. No entanto, FR-007 classifica `Accepted` como terminal. Essa aparente contradição entre "active" e "terminal" está explicada claramente na spec? [Clarity, Ambiguity, Spec §FR-007, §FR-008]

- [ ] CHK013 - FR-009 ordena a fila por "creation timestamp (FIFO)" — é o `create_date` (quando o registro foi criado) ou `sent_date` (quando foi enviado)? Para propostas que entram direto como `queued`, o timestamp relevante está claro? [Clarity, Spec §FR-009]

- [ ] CHK014 - FR-010 diz que `queue_position` é "undefined if terminal". Qual é o valor serializado na API para undefined — `null`, ausência do campo, ou `-1`? O contrato OpenAPI especifica isso? [Clarity, Spec §FR-010]

- [ ] CHK015 - FR-018 diz que a contraproposta "ocupa o active slot da propriedade (NÃO entra na fila)". Como o sistema determina quem ocupa o slot quando a contraproposta é criada — a contraproposta é criada em estado `draft` ou `sent` diretamente? [Clarity, Spec §FR-018]

- [ ] CHK016 - FR-020 exige "rejection reason" sem especificar tamanho mínimo/máximo. Uma string de 1 caractere atende ao requisito? Há uma validação de conteúdo mínimo? [Clarity, Spec §FR-020]

- [ ] CHK017 - FR-025a define `valid_until > today` e `valid_until <= create_date + 90 days`. O "today" refere-se à data UTC do servidor ou à timezone do usuário? [Clarity, Spec §FR-025a]

- [ ] CHK018 - FR-030 define estados "ativos" de lead como `new, contacted, qualified, won`. O estado `won` indica lead já ganho/fechado. Por que `won` é considerado "ativo" para efeito de de-duplicação, e esse raciocínio está documentado na spec? [Clarity, Spec §FR-030]

- [ ] CHK019 - FR-048 exige que o sistema retorne "not found" para acessos não autorizados (sem revelar existência). A spec define quando retornar 404 vs 403? Um usuário autenticado porém sem permissão deve receber 403 ou 404? [Clarity, Spec §FR-048]

- [ ] CHK020 - FR-046a descreve o cancelamento em cascata quando a propriedade é arquivada. A spec define se esse cancelamento é síncrono (na mesma transação) ou assíncrono (via evento)? [Clarity, Spec §FR-046a]

---

## Requirement Consistency

- [ ] CHK021 - FR-044 tabela diz "Accept/Reject/Counter: Yes (own)" para Agent, mas o modelo implementado restringe `action_accept()` apenas a Manager/Owner. Há conflito entre FR-044 e a implementação esperada de `action_accept()`? A spec precisa ser corrigida ou a tabela está errada? [Conflict, Spec §FR-044, §FR-043]

- [ ] CHK022 - FR-008 inclui `Accepted` no conjunto de estados "ativos" para o slot. FR-014 cancela todos os competidores quando uma proposta é aceita. Se `Accepted` é ativo, como a invariante "um ativo por propriedade" é mantida logo após a aceitação (antes dos competidores serem cancelados)? A transação atômica é descrita? [Consistency, Spec §FR-008, §FR-014]

- [ ] CHK023 - FR-011 diz que a promoção ocorre quando a ativa termina como "Rejected, Expired, ou Cancelled". FR-024 diz "Queued → Draft (auto-promotion only)". São consistentes — mas FR-024 não menciona `Expired`. Os dois FRs cobrem os mesmos estados de trigger? [Consistency, Spec §FR-011, §FR-024]

- [ ] CHK024 - US4 cenário 1 diz que aceitação "indicates a 'create contract' follow-up action is now available". FR-027 diz "MUST present a 'create contract' follow-up action". O verbo "present" implica que o link HATEOAS é retornado na resposta da API de aceitação — isso é consistente com o contrato OpenAPI? [Consistency, Spec §US4, §FR-027]

- [ ] CHK025 - FR-033 exige validação CPF/CNPJ, e as Assumptions dizem "Document validity is restricted to Brazilian CPF/CNPJ in this feature". A spec de US1 (cenário 5) menciona "RBAC denies portal" mas não menciona documento inválido como caso de rejeição no user story. Os acceptance scenarios de US1 e os FRs são consistentes? [Consistency, Spec §US1, §FR-033]

- [ ] CHK026 - FR-044 diz que o Agente pode "Update (non-terminal): Yes (own)" mas FR-007 já cobre o bloqueio de terminais. Os dois requisitos se complementam sem sobreposição conflitante? E qual é a definição exata de "update" — inclui alterar o valor da proposta após enviada? [Consistency, Spec §FR-044, §FR-007]

- [ ] CHK027 - FR-015 notifica agentes de cancelamento automático (quando proposta é superseded). FR-041 lista o template `email_template_proposal_superseded`. Esses dois FRs são a mesma funcionalidade ou há diferença entre "cancelamento automático por aceitação" (FR-014/FR-015) e "superseded" (FR-041)? A terminologia está unificada? [Consistency, Spec §FR-015, §FR-041]

---

## Acceptance Criteria Quality

- [ ] CHK028 - SC-003 exige "verified across 100 trial runs without any duplicate active proposal". Esse critério é executável em CI? Existe um test que faz 100 trials? O test `test_us_proposal_concurrent_creation.sh` implementado faz apenas 10 trials. Há gap entre SC-003 e o que está testado? [Acceptance Criteria, Spec §SC-003]

- [ ] CHK029 - SC-004 diz "100% of N competitors cancelled in a single atomic operation". A "atomicidade" é verificável via teste de integração? Existe um teste que verifica que uma falha no meio do cancelamento em lote faz rollback? [Acceptance Criteria, Spec §SC-004]

- [ ] CHK030 - SC-002 diz promoção dentro de 5 segundos. Como é medido esse SLA nos testes automatizados? Existe um teste de performance para esse critério? [Acceptance Criteria, Spec §SC-002]

- [ ] CHK031 - SC-007 diz "0% de taxa de duplicação de leads verificado por testes automatizados". O test T051 (`test_us5_proposal_lead_capture.sh`) cobre apenas 2 propostas com o mesmo documento. Isso é suficiente para verificar 0% de duplicação? [Acceptance Criteria, Spec §SC-007]

- [ ] CHK032 - SC-012 diz "100% dos cenários de aceitação da spec passam em testes E2E". A spec tem 12 acceptance scenarios apenas para US4 — todos os 12 têm testes E2E cobrindo-os? Existe rastreabilidade cenário-por-cenário? [Acceptance Criteria, Spec §SC-012]

- [ ] CHK033 - SC-008 diz "100% das transições de estado registradas no activity timeline". O test T020 (`test_proposal_send.py`) verifica a entrada no timeline? Ou apenas a transição de estado? [Acceptance Criteria, Spec §SC-008]

---

## Scenario Coverage

- [ ] CHK034 - US2 cobre promoção após rejeição, expiração e cancelamento do ativo. Há cenário explícito para o caso em que a propriedade tem fila mas o ativo é cancelado manualmente (não por rejeição nem expiração)? [Coverage, Spec §US2, §FR-011]

- [ ] CHK035 - US3 (contador-proposta) — há cenário para o caso em que o agente tenta criar uma contraproposta em estado `draft` (antes de enviar)? O FSM permite `draft → counter`? [Coverage, Spec §US3, §FR-018]

- [ ] CHK036 - US4 cenário 5 cobre "terminal state blocks update". Mas há cenário para tentar mudar o estado de `accepted` para qualquer outro estado (ex: tentativa de "undo accept")? [Coverage, Spec §US4, §FR-007]

- [ ] CHK037 - Edge case "Agent reassignment of property" diz que propostas existentes permanecem válidas. Há acceptance scenario ou FR explícito para o que acontece quando um agente *desassignado* tenta modificar sua proposta em andamento? [Coverage, Spec §Edge Cases]

- [ ] CHK038 - US5 (lead capture) — há cenário para quando o sistema falha ao criar o lead (ex: dado inválido, erro de banco)? A spec define se a proposta deve ser criada mesmo assim ou ser bloqueada? [Coverage, Spec §US5, Gap]

- [ ] CHK039 - US7 (attachments) — há cenário para download de anexo? FR-040 menciona "download link" mas nenhum acceptance scenario de US7 cobre o fluxo de download efetivo. [Coverage, Spec §US7, §FR-040]

- [ ] CHK040 - US6 menciona "date range" filter. Há especificação de quais campos a faixa de data usa — `create_date`, `sent_date`, ou ambos? [Coverage, Spec §US6, §FR-034]

- [ ] CHK041 - A spec cobre "Acceptance with no queue" como edge case mas não tem acceptance scenario em US4. Está testado no T044? [Coverage, Spec §Edge Cases, §US4]

- [ ] CHK042 - A spec menciona "receptionist sees full org list as read-only" mas não define o que "read-only" significa na API — os endpoints de mutação retornam 403, ou os HATEOAS `_links` simplesmente são omitidos da resposta? [Coverage, Spec §FR-036, Gap]

---

## Edge Case Coverage

- [ ] CHK043 - O edge case "Soft-deleted (cancelled) proposal does NOT count for the active slot" está coberto por um FR explícito ou apenas pela lógica implícita do estado `Cancelled`? Há cenário de teste que cria proposta após cancelamento e verifica que a nova fica como `draft` (não `queued`)? [Edge Cases, Spec §FR-008, §Edge Cases]

- [ ] CHK044 - O edge case "lead with same document but inactive" define criação de novo lead. Mas se a proposta é criada, depois o lead pré-existente é reativado, há duplicação? A spec define o comportamento pós-criação? [Edge Cases, Spec §FR-030, §Edge Cases]

- [ ] CHK045 - A spec cobre a archivação da propriedade (FR-046a). O que acontece se a propriedade é arquivada e depois *restaurada* (active=True)? As propostas canceladas devem ser reativadas? [Edge Cases, Spec §FR-046a, Gap]

- [ ] CHK046 - FR-025a valida `valid_until <= create_date + 90 days`. O que acontece se a proposta é criada no dia 1 com `valid_until` no dia 90, mas a regra de negócio muda para 60 dias? Propostas existentes são afetadas? [Edge Cases, Spec §FR-025a, Assumption]

- [ ] CHK047 - O edge case de corrida concorrente (FR-016) é descrito para "duas criações simultâneas". Mas o que acontece com 10+ criações simultâneas — apenas 1 ativa e N-1 queued? O comportamento com N>2 está especificado? [Edge Cases, Spec §FR-016, §SC-003]

- [ ] CHK048 - FR-039 define tamanho máximo de 10 MB por arquivo. Mas não especifica o número máximo de anexos por proposta. Existe um limite máximo de arquivos ou de storage total por proposta? [Edge Cases, Spec §FR-039, Gap]

---

## Non-Functional Requirements

- [ ] CHK049 - SC-005 exige p95 < 1s para 50k propostas na listagem. Há requisito de índice de banco de dados definido para as colunas de filtro mais comuns (`state`, `property_id`, `agent_id`, `company_id`)? O `data-model.md` especifica esses índices? [Non-Functional, Spec §SC-005]

- [ ] CHK050 - SC-006 exige métricas em < 200ms p95. O endpoint `/stats` usa uma query agregada ou lê da tabela principal em tempo real? Esse detalhe de performance está especificado para garantir o SLA? [Non-Functional, Spec §SC-006]

- [ ] CHK051 - SC-010 exige que o cron de expiração rode em < 5 minutos para 10k propostas ativas. Há requisito de batch size ou estratégia de processamento em chunks? Ou o cron pode processar todas em memória? [Non-Functional, Spec §SC-010]

- [ ] CHK052 - FR-041a desacopla envio de email via Outbox/Celery. Há SLA definido para retry (quantas tentativas, qual backoff)? FR-041b menciona "bounded backoff" mas não quantifica. [Non-Functional, Spec §FR-041b, Ambiguity]

- [ ] CHK053 - A spec define multi-tenancy por `company_id` e record rules. Há requisito explícito de teste de isolamento (ex: SC-009 com "0 ocorrências de vazamento")? O método de verificação — comparar resposta de org A para IDs de org B com "not found" — está automatizado? [Non-Functional, Spec §SC-009, §FR-043]

---

## Dependencies & Assumptions

- [ ] CHK054 - A spec assume que o módulo de lead "aceita extensão da lista de fontes via migration controlada". Essa migration está implementada e testada no T009? O rollback da migration está definido? [Dependencies, Spec §Assumptions, §T009]

- [ ] CHK055 - A spec assume que "agent-property assignment" é verificado como pré-condição de criação (FR-045). Esse check é feito no módulo de propostas ou delega para o módulo de propriedades? O contrato de interface está documentado? [Dependencies, Spec §FR-045, §Dependencies]

- [ ] CHK056 - A spec menciona "Acceptance is final; 'undo accept' is out of scope (future feature)". Há documentação de por que esse requisito foi excluído e quais são as consequências de negócio de não tê-lo? Isso está explícito para o revisor? [Dependencies, Spec §Assumptions]

---

## Ambiguities & Conflicts

- [ ] CHK057 - FR-044 tabela coluna "Counter": "Yes (own)" para Agent. Na prática, criar uma contraproposta em um `sent` ou `negotiation` implica que o agente pode contrapropor sobre propostas **de outros agentes**? Ou "own" significa apenas sobre propostas onde o agente é o responsável? Essa nuance está clara? [Ambiguity, Conflict, Spec §FR-044, §FR-018]

- [ ] CHK058 - A spec usa "cancellation reason" (FR-021) e "rejection reason" (FR-020) como campos distintos, mas a tabela FR-044 usa apenas "Cancel (soft-delete)". Há risco de confusão entre cancelamento manual (com `cancellation_reason`) e rejeição (com `rejection_reason`)? Está clara a diferença para o desenvolvedor? [Ambiguity, Spec §FR-020, §FR-021]

- [ ] CHK059 - FR-019 diz "sistema DEVE expor a cadeia completa de propostas relacionadas (pai + descendentes)". No entanto, o endpoint implementado (`GET /proposals/{id}`) retorna `proposal_chain` com apenas 1 item quando a proposta é o pai (observado nos testes). Há conflito entre o que FR-019 especifica e o que está implementado? [Conflict, Spec §FR-019]

---

## Notes

- Itens marcados `[Conflict]` requerem resolução antes de release em produção.
- Itens marcados `[Gap]` podem ser aceitos como "fora de escopo v1" desde que documentados.
- Itens marcados `[Ambiguity]` devem ser clarificados na spec antes de qualquer feature de extensão.
- CHK021 e CHK057 são os conflitos de maior risco — envolvem autorização de agente em aceitação/contraproposta.
- CHK059 é um desvio de implementação confirmado nos testes de integração desta sessão.
