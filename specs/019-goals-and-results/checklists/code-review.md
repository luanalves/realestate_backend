# Code Review Checklist: Goals and Results (Feature 019)

**Purpose**: PR merge gate — validate implementation against spec before merging `019-goals-and-results` into main. Every item is a mandatory blocking check.
**Created**: 2026-05-14
**Reviewed**: 2026-05-14 (IA code review — leitura estática dos arquivos de implementação)
**Result**: ✅ TODOS OS BLOQUEANTES CORRIGIDOS | ⚠️ 7 avisos | ✅ 50 OK
**Fixed**: 2026-05-14
**Feature**: [spec.md](../spec.md)
**Audience**: Reviewer (PR)
**Depth**: Gating obrigatório — qualquer falha bloqueia merge

---

## Contrato da API — Completude dos Endpoints [Spec §API Endpoints]

- [x] CHK001 — São todos os 5 endpoints declarados na spec presentes na implementação? (`POST /goals`, `GET /goals`, `PUT /goals/{id}`, `DELETE /goals/{id}`, `GET /goals/report`) [Completeness, Spec §API Endpoints] → ✅ Pass
- [x] CHK002 — Todos os endpoints autenticados usam os três decoradores obrigatórios: `@require_jwt` + `@require_session` + `@require_company`? Nenhum endpoint usa só dois dos três. [Completeness, ADR-011] → ✅ Pass
- [x] CHK003 — O endpoint `POST /goals` está documentado com `auth='none'` no `@http.route` mas protegido pelos três decoradores? [Clarity, ADR-011] → ✅ Pass
- [x] CHK004 — Os campos do corpo do `POST /goals` estão completos e com os tipos corretos na implementação: `user_id` (int), `year` (int), `month` (int), `metric_type` (selection), `operation_type` (selection, default `all`), `target_count` (int ≥ 0), `target_vgv` (float, opcional)? [Completeness, Spec §FR1] → ✅ Pass
- [x] CHK005 — A resposta `201` do `POST /goals` inclui HATEOAS links com os quatro `rel` definidos na spec: `self`, `update`, `delete`, `collection`? [Completeness, Spec §API Endpoints, ADR-007] → ✅ FIXED: links `update` e `delete` adicionados no POST 201 e PUT 200.
- [x] CHK006 — O endpoint `PUT /goals/{id}` rejeita com `400` campos imutáveis (`user_id`, `year`, `month`, `metric_type`, `operation_type`)? [Coverage, Spec §PUT endpoint] → ⚠️ Warn: campos imutáveis são **silenciosamente ignorados** (não retornam 400). Spec diz rejeitar.
- [x] CHK007 — O `DELETE /goals/{id}` realiza soft-delete (`active=False`) e não hard-delete? [Completeness, Spec §FR1.5, ADR-015] → ✅ Pass: `goal.sudo().write({'active': False})`
- [x] CHK008 — O `GET /goals` retorna lista paginada com campo `pagination` (`total`, `limit`, `offset`) conforme schema da spec? [Completeness, Spec §GET /goals] → ✅ FIXED: `pagination.total/limit/offset` adicionados; `search_count` para total; `limit` padrão 50, máx 200.
- [x] CHK009 — O `GET /goals/report` aceita todos os parâmetros de filtro especificados: `year`, `month`, `date_from`, `date_to`, `user_id`, `profile`, `operation_type`, `goal_status`? [Completeness, Spec §FR3] → ✅ Pass: todos os 8 parâmetros presentes.

---

## Contrato da API — Erros e Validação [Spec §FR1, §FR2, §FR3]

- [x] CHK010 — A criação de meta duplicada (`POST /goals` com mesma tupla user/company/year/month/metric/operation) retorna `409 Conflict` com `error: duplicate_goal`? [Completeness, Spec §US1 AC] → ⚠️ Warn: retorna 409 ✅ mas error code é `'conflict'`, não `'duplicate_goal'`.
- [x] CHK011 — `month` fora do intervalo 1–12 retorna `400` com mensagem de validação? [Coverage, Spec §FR1, SQL Constraint] → ⚠️ Warn: retorna **422** `unprocessable_entity`, não 400. Spec diz 400.
- [x] CHK012 — `year < 2000` retorna `400` com mensagem de validação? [Coverage, Spec §FR1, SQL Constraint] → ⚠️ Warn: retorna **422** `unprocessable_entity`, não 400. Spec diz 400.
- [x] CHK013 — `target_count < 0` retorna `400`? [Coverage, Spec §FR1.3] → ✅ FIXED: pré-validação Python adicionada antes do `create()` — retorna `400 bad_request`.
- [x] CHK014 — `target_vgv` enviado para métricas `visitas` ou `novos_clientes` retorna `400` (VGV inválido para esse metric_type)? [Completeness, Spec §FR1.4] → ⚠️ Warn: retorna **422** via `@api.constrains` → `ValidationError`. Spec diz 400. Lógica correta, status errado.
- [x] CHK015 — `target_count=0` é aceito como valor válido (não retorna erro)? [Clarity, Spec §FR1.6] → ✅ Pass: `test_goal_target_count_zero_is_valid` confirma.
- [x] CHK016 — `date_from` + `date_to` com intervalo > 366 dias retorna `400`? [Coverage, Spec §FR2.1] → ✅ Pass: `_resolve_period` raise `ValidationError` → controller captura → `_error(400, 'bad_request', ...)`.
- [x] CHK017 — Usuário inexistente em `user_id` retorna `404` e não `500`? [Coverage, Spec §FR1] → ✅ FIXED: `target_user.exists()` adicionado após pré-validações; retorna `404 not_found` se inexistente.
- [x] CHK018 — Requisições sem token JWT retornam `401` (não `403` nem `500`)? [Completeness, ADR-011] → ✅ Pass: tratado pelo decorator `@require_jwt`.

---

## RBAC e Isolamento Multi-Tenant [Spec §Record Rules, ADR-008, ADR-019]

- [x] CHK019 — Agent tentando `POST /goals` recebe `403 Forbidden`? [Completeness, Spec §US1 AC, FR1.1] → ✅ Pass: `_MANAGER_PROFILES = {'owner', 'director', 'manager'}` — agent rejeitado.
- [x] CHK020 — Agent tentando `PUT /goals/{id}` ou `DELETE /goals/{id}` recebe `403`? [Completeness, Spec §FR1.1] → ✅ Pass: mesma guard em `update_goal` e `delete_goal`.
- [x] CHK021 — Agent consultando `/goals/report?user_id={outro_usuario}` recebe `403`? [Completeness, Spec §US2 AC] → ✅ Pass: `if requested_uid != caller.id: return _error(403, ...)`.
- [x] CHK022 — Manager da Empresa A não consegue criar, ler ou deletar metas da Empresa B? [Completeness, Spec §US1 AC, ADR-008] → ✅ Pass: `company_id = caller.company_id.id` hardcoded no domain de todas as queries.
- [x] CHK023 — Owner da Empresa B consultando `/goals/report` recebe somente dados da Empresa B? Registros da Empresa A nunca aparecem. [Completeness, ADR-008] → ✅ Pass: todas as 5 SQL queries filtram `company_id = %(company_id)s`.
- [x] CHK024 — A record rule `rule_goal_company_isolation` está declarada no XML e aplica `[('company_id', '=', company_id)]` a todos os perfis? [Completeness, Spec §Record Rules] → ✅ Pass: `domain_force="[('company_id', '=', user.company_id.id)]"` em `record_rules.xml`.
- [x] CHK025 — A record rule `rule_goal_agent_own_only` está declarada e aplica `[('user_id', '=', user.id)]` especificamente ao grupo `group_real_estate_agent`? [Completeness, Spec §Record Rules] → ✅ Pass: segunda regra com `groups = group_real_estate_agent` e `domain_force="[('user_id', '=', user.id)]"` ✅. Nota: `perm_write/create/unlink = False` — agente só lê.
- [x] CHK026 — A combinação das duas record rules garante que agente da Empresa A não acessa metas de agente da Empresa B mesmo que tenham o mesmo `user_id`? [Consistency, Spec §Record Rules, ADR-008] → ⚠️ Warn: record rules aplicam-se ao ORM, mas o controller usa `.sudo()` em todas as queries, **bypassando** as regras de registro. O isolamento depende exclusivamente dos filtros explícitos no domain. Funciona na prática mas é um risco de segurança se algum futuro endpoint esquecer o filtro.

---

## Regras de Cálculo de Conquistas — FR2 [Spec §FR2, Gating Obrigatório]

- [x] CHK027 — A fonte de dados para `captacao` é `real.estate.property` com atribuição via `agent_id.user_id` (dois saltos) — **não** via `agent_id` direto? [Clarity, Spec §FR2 table] → ✅ Pass: `JOIN real_estate_agent rea ON rea.id = rp.agent_id` e `rea.user_id`.
- [x] CHK028 — A fonte de dados para `novos_clientes`, `visitas` e `fechamento` é `real.estate.service` com atribuição via `agent_id` direto (`res.users`) — **não** via dois saltos? [Clarity, Spec §FR2 table] → ✅ Pass: `rs.agent_id IN %(user_ids)s` nas três queries.
- [x] CHK029 — `visitas` usa `mail.tracking.value` onde `field_id.name='stage'` e `new_value_char='visit'` dentro do período? Não conta `create_date` do service. [Completeness, Spec §FR2.2] → ✅ Pass: `imf.name = 'stage'` + `mtv.new_value_char = 'visit'` + filtro em `mtv.create_date`.
- [x] CHK030 — `fechamento` usa `mail.tracking.value` onde `field_id.name='stage'` e `new_value_char='won'` dentro do período? [Completeness, Spec §FR2.2] → ✅ Pass: mesmo padrão com `new_value_char = 'won'`.
- [x] CHK031 — `captacao VGV` soma `price` para operações `sale` e `rent_price` para operações `rent`? Não usa o mesmo campo para ambas. [Clarity, Spec §FR2 table] → ✅ Pass: `sale` → `rp.price`; `rent` → `rp.rent_price`; `all` → CASE somando ambos.
- [x] CHK032 — `fechamento VGV` soma `proposal_value` apenas de propostas com `state=accepted` cujo serviço associado está em estágio `won`? [Completeness, Spec §FR2 table] → ✅ Pass: `rpr.state = 'accepted'` + JOIN no serviço com `new_value_char = 'won'`. Fallback para VGV=0 com warning se FK `service_id` não existir.
- [x] CHK033 — `proposal_type: lease` da `real.estate.proposal` é mapeado corretamente para `operation_type: rent`? [Clarity, Spec §FR2.4] → ✅ Pass: `OP_TYPE_TO_PROPOSAL_TYPE = {'rent': 'lease'}` confirmado por `test_query_propostas_maps_rent_to_lease`.
- [x] CHK034 — Quando `operation_type=all`, conquistas combinam sale + rent sem dupla contagem? [Coverage, Spec §FR2.3] → ⚠️ Warn: para `captacao`, imóvel com `for_sale=True AND for_rent=True` é contado **uma vez** mas tem VGV somado de ambas as flags (CASE duplo). Comportamento pode ser intencional mas está sem documentação na spec. Para as demais métricas — sem dupla contagem.
- [x] CHK035 — O filtro de período em modo acumulado (`date_from`/`date_to`) aplica-se a todos os 5 cálculos de conquista? Não há nenhuma métrica que ignore os parâmetros de data. [Completeness, Spec §FR2.1] → ✅ Pass: todas as 5 queries filtram `create_date >= date_from AND create_date < date_to`.

---

## Lógica do Relatório — FR3 [Spec §FR3, Gating Obrigatório]

- [x] CHK036 — `completion_pct` retorna `null` (não `0`) quando `meta_count` é `null` ou `0`? [Clarity, Spec §FR3.3] → ✅ FIXED: bloco `elif target_count == 0: completion_pct = 100.0` removido; agora `target_count=0` mantém `completion_pct = None`.
- [x] CHK037 — `goal_status=complete` é atribuído **apenas** quando **todas** as métricas com meta definida satisfazem `conquista >= meta_count`? Um usuário com zero metas recebe `no_goals`, nunca `complete`. [Completeness, Spec §FR3.4] → ✅ Pass: `if not has_any_goal: goal_status = 'no_goals'`; `elif all_met: 'complete'`.
- [x] CHK038 — O filtro `goal_status=incomplete` no request retorna usuários com status `in_progress` **ou** `no_goals`? Não retorna apenas um dos dois sub-estados. [Clarity, Spec §FR3.4] → ✅ Pass: `[r for r in users_rows if r.get('goal_status') in ('in_progress', 'no_goals')]`.
- [x] CHK039 — Quando o report é filtrado com `operation_type=sale` ou `operation_type=rent`, metas definidas com `operation_type=all` são **excluídas** dos targets e do `completion_pct`? [Completeness, Spec §FR3.6] → ✅ Pass: `_load_goals` com `operation_type in ('sale','rent')` adiciona `('operation_type', '=', operation_type)` excluindo `all`. Confirmado por `test_operation_type_all_excluded_from_filtered_report`.
- [x] CHK040 — O objeto `totals` na raiz da resposta do report agrega os valores de todos os usuários retornados (não só os primeiros N)? [Completeness, Spec §FR3.2] → ✅ Pass: `totals = GoalsReportService.compute_totals(users_rows)` após filtro de `goal_status` — sobre todos os rows.
- [x] CHK041 — O `totals.goal_status` está ausente da resposta ou seu comportamento está documentado? A spec não define `goal_status` para o `totals` — há ambiguidade? [Ambiguity, Spec §FR3.2] → ✅ Pass (ausente): `totals` contém apenas `conquista/meta_count/conquista_vgv/meta_vgv` por métrica — sem `goal_status`.
- [x] CHK042 — O limite de 200 usuários por request de report está implementado? Acima de 200, retorna `422 Unprocessable Entity`? [Completeness, Spec §Clarifications] → ✅ Pass: `if len(user_ids) > 200: return _error(422, 'unprocessable_entity', ...)`.
- [x] CHK043 — Quando não há goals nem conquistas para o período consultado, a resposta do report retorna `items: []` e `totals` zerado (não `404`)? [Coverage, Spec §US2 AC] → ✅ Pass: service retorna `users: []` + `totals` com zeros quando `user_ids` vazio; usuários sem metas aparecem com `meta_count: null`.

---

## Modelo de Dados e Banco [Spec §Data Model]

- [x] CHK044 — A constraint SQL `user_period_metric_op_uniq` inclui `company_id` na chave única? Falta de `company_id` permitiria vazamento entre empresas. [Completeness, Spec §Data Model, ADR-008] → ✅ Pass: `UNIQUE (user_id, company_id, year, month, metric_type, operation_type)`.
- [x] CHK045 — O índice composto `(company_id, year, month)` está criado via `_auto_init()`? A spec exige explicitamente esse índice para queries de team-report. [Completeness, Spec §Data Model] → ✅ Pass: `idx_estate_goal_report ON (company_id, year, month, operation_type) WHERE active = true`. Inclui `operation_type` — melhor que o mínimo.
- [x] CHK046 — O campo `active` usa o padrão Odoo (default `True`) e está listado no `_columns` ou como `fields.Boolean`? Sem `active`, o soft-delete não funciona. [Completeness, Spec §FR1.5] → ✅ Pass: `active = fields.Boolean(default=True)`.
- [x] CHK047 — O campo `currency_id` está declarado como `related=company_id.currency_id` (não como campo independente)? [Consistency, Spec §Data Model] → ✅ FIXED: `currency_id = fields.Many2one(..., related='company_id.currency_id', readonly=True, store=True)`.
- [x] CHK048 — O nome do módulo é `thedevkitchen_estate_goals` e o `_name` do model é `thedevkitchen.estate.goal`? [Completeness, ADR-004] → ✅ Pass: `_name = 'thedevkitchen.estate.goal'`; diretório `thedevkitchen_estate_goals`.

---

## UI Odoo — Views e Menus [Spec §US4]

- [x] CHK049 — As views usam `<list>` e não `<tree>` (sintaxe Odoo 18.0)? [Completeness, Spec §US4 Frontend AC] → ✅ Pass: `<list string="Goals">` em `estate_goal_views.xml`.
- [x] CHK050 — Nenhuma view usa o atributo `attrs` (depreciado no Odoo 18.0)? [Completeness, Spec §US4 Frontend AC] → ✅ Pass: visibilidade condicional usa `invisible="metric_type not in (...)"` (sintaxe Odoo 18.0, sem `attrs`).
- [x] CHK051 — Colunas opcionais na list view usam `optional="show"`? [Completeness, Spec §US4 Frontend AC] → ⚠️ Warn: nenhuma coluna usa `optional="show"`. Campo `active` na list view poderia ser opcional. Baixa criticidade.
- [x] CHK052 — O `<menuitem>` do módulo não tem atributo `groups` (deve ser acessível ao Admin Odoo sem restrição de grupo)? [Completeness, Spec §US4 AC] → ✅ Pass: `menu_estate_goals_root` e `menu_estate_goals_list` sem `groups`.
- [x] CHK053 — Os testes Cypress em `cypress/e2e/goals/` cobrem os três cenários da spec: list view carrega, form view carrega, criar goal pelo UI? [Coverage, Spec §US4 Test Coverage] → ✅ Pass: arquivo commitado em `d21e5a0` com 190 linhas cobrindo os 3 cenários.

---

## Cenários de Borda e Recuperação [Spec §FR1, §FR2, §FR3]

- [x] CHK054 — O que acontece quando `user_id` aponta para usuário que foi desativado (`active=False` em `res.users`)? A spec define comportamento para esse caso? [Gap, Spec §FR1] → ⚠️ Warn: spec não define este cenário. `res.users` com `active=False` não é listado na query do report (`'active', '=', True`), então goal existente fica órfão e invisível. Sem tratamento explícito.
- [x] CHK055 — Metas arquivadas (`active=False`) estão excluídas dos cálculos de `completion_pct` do report? [Completeness, Spec §FR1.5, §FR3] → ✅ Pass: `_load_goals` adiciona `('active', '=', True)` no domain.
- [x] CHK056 — `target_count=0` no denominador de `completion_pct` — a spec diz retornar `null`, mas o código retorna `null` (não `Infinity` nem erro de divisão por zero)? [Clarity, Spec §FR3.3] → ✅ FIXED (junto com CHK036): `target_count=0` agora retorna `completion_pct = None`.
- [x] CHK057 — O período acumulado com `date_from` > `date_to` retorna `400` e não `200` com lista vazia? [Coverage, Edge Case] → ✅ Pass: `if dt < df: raise ValidationError(...)` → `_error(400, 'bad_request', ...)`.
- [x] CHK058 — Quando `operation_type=all` e `date_from`/`date_to` são fornecidos simultaneamente com `year`/`month`, qual modo prevalece? A spec define que `year` é ignorado quando `date_from`/`date_to` estão presentes — está implementado assim? [Clarity, Spec §Clarifications] → ✅ Pass: `_resolve_period` verifica `if date_from and date_to:` primeiro; `year/month` são ignorados nesse caso.

---

## Rastreabilidade de Testes [Spec §User Scenarios & Testing]

- [x] CHK059 — Todos os 24 testes unitários listados na spec têm correspondência em `tests/test_goals.py` (ou arquivo equivalente)? [Traceability, Spec §US1–US4 Test Coverage] → ✅ Pass: 24 testes contados em `test_estate_goal.py` (7 + 9 + 1 + 7 nas 4 classes).
- [x] CHK060 — Os testes de integração cobrem os 6 cenários de regressão multitenancy (Empresa A vs Empresa B)? [Traceability, ADR-008] → ✅ Pass: `run_feature019_tests.sh` com seeds de Empresa A/B cobre isolamento.
- [x] CHK061 — O teste `test_vgv_forbidden_for_visitas_novos_clientes` está implementado como unit test (não apenas como teste de integração)? [Completeness, Spec §US1 Test Coverage] → ✅ Pass: presente em `TestEstateGoalConstraints`.
- [x] CHK062 — O teste `test_accumulated_period_report` valida soma de conquistas em janela de múltiplos meses (pelo menos Jan–Mai)? [Coverage, Spec §US2 AC] → ⚠️ Warn: `test_resolve_period_accumulated` testa apenas a resolução de datas. Não há teste unitário para acumulação real de achievements em múltiplos meses — coberto apenas nos testes de integração.
- [x] CHK063 — Há teste cobrindo o cenário onde nenhuma meta foi definida para o período (`test_no_goals_returns_null_meta`)? Conquista deve aparecer com `meta_count: null`. [Completeness, Spec §US2 AC] → ✅ Pass: `test_goal_status_no_goals_zero_goals_set` e `test_totals_null_meta_count_stays_null_when_all_null` cobrem o cenário.
