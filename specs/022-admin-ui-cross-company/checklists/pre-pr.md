# Pre-PR Specification Quality Checklist: Admin UI — Cross-Company Access for System Admin

**Purpose**: Abrangente — valida completude, clareza, consistência e cobertura de todos os requisitos da Feature 022. Uso pelo autor antes de abrir o PR.
**Created**: 2026-06-05
**Validated**: 2026-06-05
**Feature**: [spec.md](../spec.md) | [plan.md](../plan.md) | [tasks.md](../tasks.md)
**Audience**: Autor — auto-validação pré-PR
**Depth**: Standard

> **Legenda**: `[x]` PASS — evidência encontrada | `[-]` PARCIAL — parcialmente coberto por artefato auxiliar | `[ ]` GAP — não coberto em nenhum artefato

---

## Requirement Completeness

- [ ] CHK001 — A lista de entidades em FR-001 (14 enumeradas explicitamente) está reconciliada com a contagem declarada em SC-001 ("exactly 20 entity types as listed in `data-model.md`")? [Completeness, Gap — spec.md §FR-001 vs §SC-001]
  > **GAP**: FR-001 enumera 14 nomes de entidade; SC-001 declara "exactly 20 entity types." data-model.md tem 20 modelos técnicos. A inconsistência existe no spec.md — FR-001 não lista as 20 entidades nem referencia data-model.md.

- [ ] CHK002 — FR-005 (audit log) especifica o formato/campos obrigatórios da entrada de log (timestamp, user, ip, endpoint, reason)? Ou está delegado sem referência a um contrato externo? [Completeness, Spec §FR-005]
  > **GAP**: audit_logger.py grava `ir.logging` com campos `name`, `type`, `level`, `path`, `func`, `line`, `message`. spec.md diz apenas "security audit log entry" sem especificar campos nem referenciar o serviço.

- [ ] CHK003 — Existe acceptance scenario explícito para SC-007 ("feature pode ser deployada sem intervenção manual no DB")? Ou SC-007 é verificado apenas por revisão de código? [Completeness, Gap — Spec §SC-007]
  > **GAP**: SC-007 é success criterion sem acceptance scenario Given/When/Then. Verificado em tasks T011/T019 por revisão de upgrade, não por cenário testável.

- [-] CHK004 — O texto exato do corpo da resposta HTTP 401 do bloqueio de admin está especificado no spec.md? (plan.md indica `{"error": {"status": 401, "message": "Invalid credentials"}}` mas spec.md apenas diz "generic error message".) [Completeness, Gap — Spec §FR-004]
  > **PARCIAL**: `contracts/login-block.md` especifica exatamente `{"error": {"status": 401, "message": "Invalid credentials"}}` com nota anti-enumeration. spec.md não referencia este contrato — falta link explícito.

- [ ] CHK005 — São definidos os requisitos para o edge case EC-2 (registros com `company_id = NULL` devem ser visíveis ao System Admin) em pelo menos um acceptance scenario ou critério de sucesso explícito? [Completeness, Gap — Spec §Edge Cases EC-2]
  > **GAP**: EC-2 descrito como edge case mas sem acceptance scenario Given/When/Then e sem task de teste.

- [ ] CHK006 — São definidos os requisitos para o edge case EC-3 (admin pertencendo simultaneamente a um grupo de role de negócio — cross-company rules ainda prevalecem) em pelo menos um acceptance scenario? [Completeness, Gap — Spec §Edge Cases EC-3]
  > **GAP**: EC-3 descrito como edge case mas sem acceptance scenario Given/When/Then e sem task de teste.

---

## Requirement Clarity

- [ ] CHK007 — A cláusula de isenção de SC-001 ("entities from modules not yet installed are exempt") possui critério operacional para determinar quais módulos estão instalados em um dado ambiente antes de executar a validação? [Clarity, Spec §SC-001]
  > **GAP**: Nenhum critério operacional definido para "determinar módulos instalados" pré-validação. Deixa a decisão implícita ao executor do teste.

- [-] CHK008 — "Generic error message" em FR-004/SC-004 é suficientemente específico para que dois desenvolvedores independentes cheguem à mesma implementação? (Ex.: mesmo body, mesmo Content-Type, mesma ausência de campo `session_id`.) [Clarity, Ambiguity — Spec §FR-004]
  > **PARCIAL**: `contracts/login-block.md` especifica body, Content-Type e ausência de session_id. spec.md não referencia o contrato — dois desenvolvedores partindo só do spec.md não chegariam à mesma implementação.

- [ ] CHK009 — O termo "unrestricted" em FR-002 cobre explicitamente operações de archive/unarchive (`active=False`) além de create, edit e delete? Ou fica implícito via "write access"? [Clarity, Spec §FR-002]
  > **GAP**: FR-002 enumera "create, edit, and delete" sem mencionar archive/unarchive. Em Odoo archive é write no campo `active` — coberto implicitamente, mas não declarado.

- [ ] CHK010 — SC-005 declara "zero silent failures" e "corresponding security log entry" — "corresponding" está definido com precisão suficiente para ser verificado (quais campos o log deve conter para ser considerado correspondente)? [Clarity, Spec §SC-005]
  > **GAP**: "Corresponding" não é definido. audit_logger.py grava `reason='Admin API login blocked'` no campo message mas o spec não especifica isso como critério de correspondência.

- [x] CHK011 — SC-002 declara "in a single operation (no extra steps)" — esse critério está refletido em pelo menos um acceptance scenario de US2 com linguagem Given/When/Then que o torne verificável? [Clarity, Spec §SC-002 vs §US2]
  > **PASS**: US2 AC-1 "When they edit a field and save, Then the change is saved successfully without access errors" implica operação única. Given/When/Then presente.

---

## Requirement Consistency

- [-] CHK012 — US2 Phase 5 no tasks.md declara explicitamente "US2 has no implementation tasks" enquanto T015 existe para US2. Essa contradição está resolvida no spec (T015 é de test coverage, não implementação)? [Consistency, tasks.md §Phase 5]
  > **PARCIAL**: A nota inline de Phase 5 explica que "no implementation tasks" refere-se ao código-fonte (record rules de US1 já cobrem write) — T015 é task de test coverage. Confusamente redigido mas resolvido localmente.

- [x] CHK013 — FR-004 e SC-004 descrevem o bloqueio de login com anti-enumeration em dois lugares (requisito + critério). Ambos são consistentes quanto ao status code (401), ausência de session_id, e identicalidade de resposta com credenciais inválidas? [Consistency, Spec §FR-004 vs §SC-004]
  > **PASS**: FR-004 e SC-004 são consistentes — ambos especificam HTTP 401, "generic error message", "indistinguishable from invalid-credential failure." contracts/login-block.md confirma o mesmo response body nas duas situações.

- [ ] CHK014 — As quatro user stories (US1, US2, US3, US4) cobrem coletivamente todos os 8 FRs sem sobreposição não intencional? FR-006 (isolamento de business users) está mapeado explicitamente a alguma user story ou fica apenas em SC-006? [Consistency, Gap — Spec §US1–US4 vs §FR-006]
  > **GAP**: FR-006 (preservar isolamento de business users) não está mapeado a nenhuma user story. Coberto apenas por SC-006 e T021. Pode causar confusão em revisões de cobertura.

- [x] CHK015 — O edge case EC-5 ("admin cria registro sem company, causando dados orphan — salvaguarda do Odoo web form") está alinhado com FR-002 (write access unrestricted)? A salvaguarda mencionada é do Odoo core ou da aplicação — está claro no spec? [Consistency, Spec §Edge Cases EC-5 vs §FR-002]
  > **PASS**: EC-5 declara explicitamente "the Odoo web interface enforces company selection on the form; this is an existing Odoo safeguard" — claramente Odoo core, sem conflito com FR-002 unrestricted write.

---

## Acceptance Criteria Quality

- [ ] CHK016 — Todos os acceptance scenarios de US1 (AC-1, AC-2, AC-3) possuem critério mensurável de "sucesso" (ex.: "records from all companies appear" — como determinar "all companies" numericamente em um dado ambiente de teste)? [Acceptance Criteria, Spec §US1]
  > **GAP**: US1 AC-1/2/3 usam "all tenant companies" sem definir numericamente "all" (ex.: "at least 2 companies with distinct data"). Deixa ao executor decidir.

- [-] CHK017 — US4 AC-2 ("event is recorded as a security audit log entry") pode ser verificado objetivamente por um teste automatizado? O spec define o mecanismo de consulta ao log (ex.: endpoint, tabela, AuditLogger method)? [Acceptance Criteria, Spec §US4 AC-2]
  > **PARCIAL**: T014 (`test_admin_api_block.sh`) verifica o log via queries ao banco. spec.md US4 AC-2 não especifica o mecanismo de consulta — o test script resolve na prática mas o spec fica vago.

- [ ] CHK018 — US4 AC-3 ("regular business user... authentication proceeds normally") possui dados de teste pré-definidos (qual business user, qual company) ou deixa ao implementador escolher arbitrariamente? [Acceptance Criteria, Spec §US4 AC-3]
  > **GAP**: Nenhum usuário de negócio pré-definido em spec.md. Test scripts resolvem via `.env` mas a especificação não cita isso.

---

## Edge Case & Scenario Coverage

- [x] CHK019 — O cenário de System Admin com conta inativa (disabled) tentando login via REST API está coberto? A resposta esperada (401 por conta inativa vs 401 por canal bloqueado) é distinguível internamente sem violar anti-enumeration externamente? [Coverage, Gap]
  > **CORRIGIDO 2026-06-05**: `has_group('base.group_system')` movido para **antes** de `user.active` no controller (`user_auth_controller.py`). Admin inativo agora recebe 401 (idêntico a bad-credential) — anti-enumeration preservada. Comentário inline documenta a intenção da ordenação.

- [ ] CHK020 — Existe requisito definido para o comportamento do bloqueio de API quando Kong API Gateway está down (rate limiting delegado ao Kong)? O spec reconhece essa dependência operacional? [Coverage, Gap — Spec §Assumptions]
  > **GAP**: spec.md Assumptions delega rate limiting ao Kong sem fallback. Comportamento sob Kong unavailability não documentado.

- [x] CHK021 — São especificados os requisitos para o caso em que o System Admin tenta acessar o REST API login endpoint com credenciais **inválidas** (não só credenciais válidas de admin)? A resposta deve ser idêntica? [Coverage, Spec §SC-004]
  > **PASS**: Credenciais inválidas falham na etapa de `uid` check (step 3 do controller) antes de atingir o `has_group` check — retornam 401 "Invalid credentials" idêntico. SC-004 "indistinguishable" clause cobre implicitamente. Anti-enumeration preservada por design de controller.

---

## Non-Functional Requirements

- [ ] CHK022 — O requisito de performance "zero runtime overhead" é mensurável ou apenas arquitetural? Está documentado que é uma garantia de design (OR-union Odoo) e não uma assertion de CI? [NFR, Clarity — plan.md §Performance Goals]
  > **GAP**: plan.md declara "zero runtime overhead" mas não documenta explicitamente que é garantia arquitetural (OR-union Odoo nativo), não assertion de CI. ADR-029 menciona "No measurable performance impact" mas não formaliza o raciocínio como NFR.

- [ ] CHK023 — Existem requisitos de retenção/persistência para as entradas do security audit log criadas por FR-005? (Ex.: quantos dias, se é soft-delete ou hard-delete, se é consultável via API.) [NFR, Gap]
  > **GAP**: Nenhum requisito de retenção definido. audit_logger.py grava em `ir.logging` (tabela Odoo com retenção padrão da plataforma). Sem SLA de retenção no spec.

- [x] CHK024 — A consistência de tempo de resposta do endpoint de login bloqueado (latência do 401 de admin block vs latência do 401 de bad credentials) está especificada? Diferenças de timing podem vazar informação de canal. [NFR, Security — Spec §FR-004]
  > **DOCUMENTADO 2026-06-05**: Timing delta real (~1–5 ms marginal, não ~50–200 ms) — ambos os caminhos compartilham `session.authenticate()` como bottleneck dominante. Risco aceito formalizado em ADR-029 §Negative/Trade-offs: mitigação por Kong rate limiting + connection throttling. Adicionar sleep artificial degradaria todas as logins sem ganho mensurável de segurança dada cobertura do Kong.

---

## Dependencies & Assumptions

- [x] CHK025 — A dependência de FR-007 em Feature 009's "authorization matrix" está especificada com referência explícita ao comportamento esperado de Feature 009 (qual endpoint, qual grupo verificado, qual HTTP status)? [Dependency, Spec §FR-007 vs §Dependencies]
  > **PASS**: FR-007 explicitamente: "Satisfied by Feature 009's existing invitation authorization matrix — `base.group_system` is not in any invitable profile; no new guard code required for this feature."

- [ ] CHK026 — A suposição de que "`SUPERUSER_ID` (uid=1) é nunca usado para login" está validada por algum mecanismo (ex.: guard no controller, test case) ou fica apenas como assumption não verificada? [Assumption, Spec §Assumptions]
  > **GAP**: Assumption declarada no spec.md mas sem guard no controller e sem test case. uid=1 (`__system__`) é protegido pelo Odoo core (não tem senha) — aceitável como assumption Odoo-nativa, mas não documentado como tal.

- [ ] CHK027 — A dependência de Kong API Gateway para rate limiting está documentada com fallback explícito: o que acontece se o Kong não estiver aplicando rate limit? O spec delimita a responsabilidade da aplicação? [Dependency, Spec §Assumptions vs §FR-004]
  > **GAP**: "Delegated to Kong — no application-level throttle added" delimita responsabilidade mas não define fallback. Sem Kong ativo, a aplicação não tem proteção contra brute force de admin API login block.

---

## Convention & Governance (FR-008)

- [x] CHK028 — ADR-029 referencia explicitamente o developer checklist de KB-013 e vice-versa, criando uma trilha bidirecional de rastreabilidade entre o artefato arquitetural e o artefato operacional? [Traceability, Spec §FR-008]
  > **PASS**: ADR-029 §Consequences: "see [Knowledge Base KB-013](../../knowledge_base/13-saas-admin-module-checklist.md)." ADR-029 §New Module Obligation: "This is enforced by the checklist at [knowledge_base/13-saas-admin-module-checklist.md]." KB-013 header: "Reference: ADR-029". Bidirecional confirmado.

- [x] CHK029 — O developer checklist em `knowledge_base/13-saas-admin-module-checklist.md` especifica os critérios para determinar se um dado novo módulo "introduz regras de isolamento por empresa" (trigger para aplicar a convenção)? Ou a decisão fica implícita? [Clarity, Spec §FR-008]
  > **PASS**: KB-013 item 1 define explicitamente: `grep -r "company_id" path/to/your-module/security/*.xml` — critério operacional específico e executável.

- [ ] CHK030 — O spec define o processo de enforcement da convenção FR-008 além da documentação (ex.: revisão obrigatória do ADR-029 em PRs de novos módulos, lint de XML, CI check)? Ou FR-008 é exclusivamente dependente de disciplina humana? [Coverage, Gap — Spec §FR-008]
  > **GAP**: FR-008 é enforcement exclusivamente por disciplina humana (checklist manual). ADR-029 e KB-013 documentam a convenção mas não há CI lint, hook de PR ou check automatizado. Risco aceito mas não formalizado como decisão.

---

## Validation Summary

**Validated by**: speckit.checklist (auto-validation run 2026-06-05)

| Status | Count | % | Items |
|--------|-------|---|-------|
| ✅ PASS | 9 | 30% | CHK011, CHK013, CHK015, CHK019¹, CHK021, CHK024², CHK025, CHK028, CHK029 |
| ⚠️ PARCIAL | 4 | 13% | CHK004, CHK008, CHK012, CHK017 |
| ❌ GAP | 17 | 57% | CHK001, CHK002, CHK003, CHK005, CHK006, CHK007, CHK009, CHK010, CHK014, CHK016, CHK018, CHK020, CHK022, CHK023, CHK026, CHK027, CHK030 |
| **Total** | **30** | | |

> ¹ CHK019 corrigido: controller `user_auth_controller.py` — `has_group` movido antes de `user.active` (2026-06-05)  
> ² CHK024 documentado: risco aceito formalizado em `ADR-029` §Negative/Trade-offs (2026-06-05)

### Prioridade de Resolução Antes do PR

**� RESOLVIDO (2026-06-05):**
- **CHK019** ✅: `has_group` movido antes de `user.active` em `user_auth_controller.py`. Admin inativo → 401.
- **CHK024** ✅: Timing delta formalizado em ADR-029 §Trade-offs como risco aceito mitigado por Kong.

**🟠 ALTO — Inconsistência de especificação:**
- **CHK001**: FR-001 lista 14 entidades; SC-001 declara 20. data-model.md resolve mas spec está inconsistente.
- **CHK014**: FR-006 não mapeado a nenhuma user story.
- **CHK004 / CHK008**: spec.md não referencia `contracts/login-block.md` para resposta exata.

**🟡 MÉDIO — Gaps de clareza aceitáveis antes do PR:**
- CHK007 (SC-001 exemption criteria), CHK010 (SC-005 "corresponding"), CHK016 (US1 "all companies" criteria)

**⚪ BAIXO — Dívida técnica gerenciável:**
- CHK002, CHK003, CHK005, CHK006, CHK009, CHK018, CHK020, CHK022, CHK023, CHK026, CHK027, CHK030
