# Feature Specification: Redis Cache para Sessão e JWT

**Feature Branch**: `023-redis-session-cache`
**Created**: 2026-06-08
**Status**: Ready for Planning
**Solution Type**: Backend — melhoria de performance sem quebra de contrato
**Input**: Dívida técnica — Redis configurado mas não utilizado para lookup de sessão e token de acesso em produção

## Contexto do Problema

Toda requisição autenticada na API realiza atualmente **2 consultas de leitura + 1 escrita** no banco de dados antes de qualquer lógica de negócio:

1. `require_jwt` → busca o token de acesso OAuth na tabela de tokens
2. `require_session` → busca a sessão ativa na tabela de sessões
3. `require_session` → atualiza o campo `last_activity` da sessão

O serviço de cache já está configurado na infraestrutura do projeto (host, porta, banco de índice e persistência definidos), porém não é utilizado em nenhum desses caminhos críticos. O módulo de observabilidade já instrumenta o cache para rastreamento, confirmando que a infraestrutura está operacional.

Adicionalmente, os métodos de cache de métricas de agentes (`_get_cached_performance`, `_cache_performance`, `invalidate_cache`) estão implementados como stubs que retornam `None` e `pass` sem nenhuma integração real com o cache.

## Clarifications

### Session 2026-06-08

- Q: O contrato de resposta dos decoradores de autenticação pode mudar? → A: Não. Os objetos `request.jwt_token`, `request.jwt_application` e `request.api_session` devem continuar sendo os mesmos tipos de objetos. Controllers, `log_api_access` e `require_company` dependem de seus campos (id, scope, expires_at, name, client_id, company_id, write).
- Q: O cache pode falhar sem derrubar a requisição? → A: Sim, obrigatoriamente. Qualquer falha no cache deve degradar silenciosamente para o banco de dados — nenhuma exceção pode propagar para a requisição. Apenas log de aviso.
- Q: O fluxo de login deve usar o cache? → A: Não. O login cria uma nova sessão a cada chamada. O cache é populado apenas pela primeira requisição subsequente autenticada.
- Q: A precisão de `last_activity` é crítica para segurança? → A: Não. É campo de métricas de uso. Pode ficar desatualizado em até 5 minutos (TTL do cache de sessão). Trade-off aceito.
- Q: As informações de validação de identidade da sessão devem estar presentes no cache? → A: Sim. Sem elas no cache, uma consulta ao banco seria necessária para obtê-las, eliminando o ganho. O cache de sessão deve incluir todos os campos necessários para completar a validação sem banco de dados.
- Q: O que dispara a invalidação do cache de métricas de corretores (FR-010)? → A: Automático — toda vez que uma nova transação ou venda é registrada para o corretor, o cache de métricas dele é invalidado automaticamente. Não há invalidação somente manual.
- Q: Um critério de latencia percentual (ex: segunda requisição ≤ 60% do tempo da primeira) deve constar nos critérios de sucesso? → A: Não. O ganho de performance será percebido empiricamente durante o desenvolvimento. Não é necessário um critério mensurável de latencia na spec.
- Q: Mudança de perfil do usuário (ex: de gerente para agente) deve invalidar o cache de sessão? → A: Sim. Quando o perfil de um usuário é alterado, o cache de todas as suas sessões ativas deve ser invalidado imediatamente para que as novas permissões entrem em vigor na próxima requisição.
- Q: Quando um perfil é desativado via API (`DELETE /api/v1/profiles/:id`), a invalidação das sessões ativas deve ser imediata (proativa) ou reativa (detectada na próxima request)? → A: Proativa. O endpoint deve buscar e invalidar explicitamente todas as sessões ativas do `res.users` vinculado ao perfil desativado, sem aguardar a próxima requisição. O mesmo padrão já implementado em `password_service._invalidate_user_sessions()`.
- Q: Qual nível de telemetria deve ser capturado para as operações do cache (hits, misses, invalidações, erros de conexão)? → A: Logging estruturado por operação: INFO para cache hits e invalidações, WARNING para misses e erros de conexão. Coletado pelo Loki/Grafana já operacional no projeto. Não são necessárias métricas OpenTelemetry nesta feature.
- Q: Qual é o TTL correto para o cache de JWT? O token já tem `expires_at` — isso é suficiente? → A: Sim. O JWT já carrega seu próprio prazo de expiração no campo `expires_at`. O TTL do cache é calculado como `expires_at - now()` no momento da escrita. Não há campo configurável de TTL para JWT. Revogação antes do `expires_at` é coberta pela invalidação imediata (FR-007). Para sessões, que não têm `expires_at` próprio, o TTL é configurável via backoffice. Os seguintes campos serão adicionados ao modelo existente `thedevkitchen.security.settings` (menu Technical → API Gateway → Security Settings): `session_cache_ttl_seconds` (padrão: 300s) e `session_inactivity_days` (padrão: 7 dias).
- Q: O TTL do cache de métricas de corretores deve ser hardcoded, compartilhado com sessões ou ter campo próprio? → A: Campo separado `performance_cache_ttl_seconds` (padrão: 300s) em `thedevkitchen.security.settings`. Métricas têm ciclo de vida diferente de sessões — podem ser consultadas em dashboards com frequência e o recalculo é custoso — por isso merecem controle operacional independente sem criar novo modelo.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Cache elimina consultas ao banco em requisições autenticadas subsequentes (Priority: P1)

Toda requisição com autenticação completa (token de acesso + sessão de usuário), após o primeiro acesso com aquele token/sessão, deve ser processada sem nenhuma consulta ao banco de dados para validar identidade.

**Why this priority**: É o núcleo da dívida técnica. Cada endpoint autenticado da plataforma paga esse custo por requisição. Eliminar o banco de dados do caminho de autenticação reduz a carga proporcional ao volume de requisições e melhora o tempo de resposta de todos os endpoints.

**Independent Test**: Pode ser testado de forma isolada: fazer login, executar uma segunda requisição autenticada e verificar nos logs de banco de dados que nenhuma consulta a tabelas de token ou sessão foi executada nessa segunda requisição.

**Acceptance Scenarios**:

1. **Given** um token de acesso OAuth válido já utilizado em uma requisição anterior, **When** uma nova requisição autenticada chega com o mesmo token, **Then** nenhuma busca na tabela de tokens é realizada; a requisição é processada com sucesso.

2. **Given** o serviço de cache indisponível (timeout ou fora do ar), **When** qualquer requisição autenticada chega, **Then** o sistema consulta o banco de dados normalmente e a requisição é processada com sucesso — nunca retorna erro 500 por falha de cache.

3. **Given** um token de acesso marcado como revogado armazenado no cache, **When** uma requisição chega com esse token, **Then** a requisição é rejeitada com 401 sem consultar o banco de dados.

4. **Given** um token de acesso com prazo de validade expirado armazenado no cache, **When** uma requisição chega com esse token, **Then** a requisição é rejeitada com 401 sem consultar o banco de dados.

5. **Given** uma sessão de usuário válida já utilizada em uma requisição anterior, **When** uma nova requisição autenticada chega com a mesma sessão, **Then** nenhuma busca na tabela de sessões é realizada e o campo `last_activity` não é atualizado no banco.

6. **Given** uma sessão com estado inativo armazenada no cache (estado pós-logout), **When** uma requisição chega com essa sessão, **Then** a requisição é rejeitada com 401 imediatamente, sem consultar o banco de dados.

7. **Given** uma sessão de um usuário que foi desativado, cujo cache ainda está ativo, **When** uma requisição chega com essa sessão, **Then** a requisição é rejeitada com 401 `User inactive` sem banco de dados.

---

### User Story 2 — Invalidação imediata ao mutar estado de segurança (Priority: P1)

Operações que alteram o estado de autenticação (logout, revogação de token, troca de empresa) devem remover imediatamente o cache correspondente, impedindo que dados desatualizados sejam servidos.

**Why this priority**: Sem invalidação correta, o cache se torna um vetor de segurança: um usuário que fez logout poderia continuar autenticado por até 5 minutos. A invalidação é o contrato de segurança do cache.

**Independent Test**: Fazer login, executar uma requisição para popular o cache, fazer logout e verificar com inspeção direta do cache que a chave da sessão foi removida. Uma nova requisição com a mesma sessão deve retornar 401 imediatamente.

**Acceptance Scenarios**:

1. **Given** uma sessão ativa com cache populado, **When** o usuário realiza logout, **Then** a entrada de cache da sessão é removida imediatamente; a próxima requisição com a mesma sessão vai ao banco de dados e recebe 401.

2. **Given** um token de acesso OAuth com cache populado, **When** o token é revogado via endpoint de revogação, **Then** a entrada de cache do token é removida; a próxima requisição com esse token recebe 401.

3. **Given** uma sessão com empresa A em cache, **When** o usuário troca para empresa B, **Then** a entrada de cache da sessão é removida; a próxima requisição repopula o cache com a empresa B correta.

4. **Given** um usuário que faz login enquanto tinha sessões anteriores ativas com cache, **When** o novo login é realizado, **Then** os caches de todas as sessões anteriores são removidos automaticamente (já que essas sessões são desativadas no banco).

5. **Given** um usuário com sessão ativa cujo perfil é alterado (ex: de gerente para agente), **When** a alteração de perfil é salva, **Then** o cache de todas as sessões ativas daquele usuário é removido imediatamente; a próxima requisição recarrega a sessão do banco com as novas permissões.

---

### User Story 3 — Cache de métricas de desempenho de corretores (Priority: P2)

O módulo de métricas de corretores já possui infraestrutura de cache com métodos definidos, mas que não executam nenhuma operação real. Esses métodos devem ser conectados ao cache para evitar recalcular métricas em cada consulta.

**Why this priority**: O cálculo de métricas agrega múltiplas transações e pode ser custoso. O cache é necessário para performance em cenários de uso real, mas não bloqueia o MVP da feature de autenticação.

**Independent Test**: Pode ser testado de forma isolada: chamar o endpoint de performance de um corretor duas vezes com os mesmos parâmetros e verificar que a segunda chamada retorna do cache (sem consultas de métricas ao banco).

**Acceptance Scenarios**:

1. **Given** a primeira chamada ao endpoint de performance de um corretor com determinado período, **When** a resposta é retornada com sucesso, **Then** o resultado é armazenado no cache com validade definida pelo campo `performance_cache_ttl_seconds` configurado no backoffice (padrão: 300 segundos).

2. **Given** uma segunda chamada ao endpoint de performance com os mesmos parâmetros dentro do período de validade, **When** a requisição chega, **Then** o resultado é retornado do cache sem nenhuma consulta de métricas ao banco.

3. **Given** métricas de um corretor em cache, **When** uma nova transação ou venda é registrada para aquele corretor, **Then** o cache de métricas dele é invalidado automaticamente; a próxima consulta ao dashboard recalcula os dados do banco e os armazena no cache novamente.

---

### Edge Cases

- O que acontece quando o cache retorna dados parcialmente corrompidos (JSON inválido)? → Trata como cache miss e consulta o banco; log de warning com a chave afetada.
- O que acontece quando o token está no cache como não-revogado mas foi revogado no banco (janela entre revogação e propagação)? → A revogação dispara remoção imediata do cache; não há janela de inconsistência em operação normal.
- O que acontece quando `last_activity` não é atualizado durante a janela do cache TTL de sessão? → Campo de métrica aceitável com imprecisão de até 1 TTL configurado (padrão 300s); não impacta segurança.
- O que acontece quando o perfil de um usuário é alterado enquanto ele tem sessões ativas em cache? → O cache de todas as suas sessões ativas é invalidado imediatamente após a alteração de perfil; a próxima requisição recarrega a sessão do banco com as permissões atualizadas.
- O que acontece quando o banco de dados do cache está cheio (sem memória)? → Degradação graceful: a operação de escrita no cache falha silenciosamente, a próxima requisição consulta o banco normalmente.
- O que acontece se o deploy das hooks de invalidação ocorrer antes do cache ser ativado? → Comportamento correto: invalidações sem-ops (nada para deletar). O inverso (cache ativo sem hooks) não deve ocorrer — ver ordem de deploy no plano.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE consultar o cache antes de qualquer busca ao banco de dados na validação de tokens de acesso OAuth.
- **FR-002**: O sistema DEVE consultar o cache antes de qualquer busca ao banco de dados na validação de sessões de usuário.
- **FR-003**: O sistema DEVE armazenar no cache os dados de validação do token de acesso OAuth imediatamente após validação bem-sucedida no banco. O TTL da entrada de cache é calculado como `expires_at - now()` no momento da escrita — o cache expira naturalmente quando o token expira, sem nenhuma configuração adicional.
- **FR-004**: O sistema DEVE armazenar no cache os dados de validação da sessão de usuário (incluindo token de validação de identidade) imediatamente após validação bem-sucedida no banco, com validade definida pelo campo `session_cache_ttl_seconds` configurado no backoffice (padrão: 300 segundos).
- **FR-005**: O sistema DEVE remover a entrada de cache de uma sessão imediatamente quando seu estado é alterado para inativo (logout, desativação de usuário via API de perfil, expiração) ou quando o perfil do usuário vinculado à sessão é modificado. A desativação de usuário via API (`DELETE /api/v1/profiles/:id`) é **proativa**: o endpoint deve buscar e invalidar explicitamente as sessões ativas do usuário antes de retornar 200.
- **FR-006**: O sistema DEVE remover a entrada de cache de uma sessão imediatamente quando sua empresa ativa é alterada (troca de empresa).
- **FR-007**: O sistema DEVE remover a entrada de cache de um token de acesso imediatamente quando ele é revogado.
- **FR-008**: O sistema DEVE continuar operando normalmente se o serviço de cache estiver indisponível, utilizando o banco de dados como fonte de dados sem retornar erros para o cliente.
- **FR-009**: O sistema DEVE armazenar resultados de métricas de desempenho de corretores no cache com validade definida pelo campo `performance_cache_ttl_seconds` configurado no backoffice (padrão: 300 segundos).
- **FR-010**: O sistema DEVE invalidar o cache de métricas de um corretor automaticamente sempre que uma nova transação ou venda for registrada para aquele corretor.
- **FR-011**: O sistema DEVE emitir logs estruturados por operação de cache: nível INFO para cache hits e invalidações bem-sucedidas; nível WARNING para cache misses (quando o banco é consultado como fallback) e para erros de conexão com o serviço de cache. Cada log deve incluir o tipo de cache (jwt, session, performance) e a chave afetada (anonimizada se sensível).
- **FR-012**: O sistema DEVE permitir que o administrador configure os parâmetros de cache e inatividade via backoffice Odoo, sem reinicialização do servidor. Os campos `session_cache_ttl_seconds` (padrão: 300), `performance_cache_ttl_seconds` (padrão: 300) e `session_inactivity_days` (padrão: 7) devem ser adicionados ao modelo existente `thedevkitchen.security.settings` (menu: Technical → API Gateway → Security Settings). O TTL de cache JWT não é configurável — é derivado automaticamente de `expires_at - now()`.

### Key Entities

- **Token de Acesso OAuth** (`thedevkitchen.oauth.token`): Credencial de aplicação que autoriza chamadas à API. Tem prazo de validade e pode ser revogado. Dados relevantes para cache: id, id-da-aplicação, tipo, prazo de expiração, escopo de permissões, estado de revogação.
- **Sessão de Usuário** (`thedevkitchen.api.session`): Registro da sessão ativa de um usuário na plataforma. Vinculada a um usuário e uma empresa. Dados relevantes para cache: id, id-do-usuário, estado ativo, token de validação de identidade, empresa ativa.
- **Métricas de Desempenho de Corretor**: Resultados agregados de vendas, comissões e ranking de um corretor para um período. Calculados sob demanda e cacheáveis por período+parâmetros.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero requisições retornam erro 500 causado por falha do serviço de cache — a indisponibilidade do cache é transparente para o cliente.
- **SC-002**: Após logout, uma nova requisição com a sessão encerrada recebe 401 imediatamente, sem consultar o banco de dados.
- **SC-003**: A segunda consulta de métricas de um corretor com os mesmos parâmetros retorna sem consultas de agregação ao banco de dados (cache hit verificável em logs).
- **SC-004**: Todos os testes automatizados existentes do módulo de autenticação continuam passando sem modificação após a implementação.

---

## Assumptions

- O serviço de cache já está configurado e acessível no ambiente de desenvolvimento (host, porta e banco de índice definidos na configuração do servidor).
- O TTL de cache de JWT é derivado automaticamente de `expires_at - now()` — sem configuração manual necessária.
- O TTL de cache de sessão (padrão 300s) é configurável via backoffice e representa um trade-off entre performance e frequência de atualização do campo `last_activity`. Não se aplica a eventos de segurança: logout, revogação de token, desativação de usuário via API e troca de empresa geram invalidação imediata do cache.
- A imprecisão do campo `last_activity` durante a janela do cache TTL de sessão é aceita, pois é métrica de uso e não controle de segurança.
- O timeout de inatividade de sessão (padrão 7 dias) é configurável via backoffice e controla quando o cron marca sessões inativas no banco — é diferente do cache TTL e sim pode deslogar o usuário.
- As hooks de invalidação devem ser ativadas antes das hooks de população do cache no momento do deploy (ordem documentada no plano de implementação).

## Dependencies

- Serviço de cache configurado e operacional na infraestrutura (já disponível conforme configuração existente).
- Módulo `thedevkitchen_apigateway` como local dos decoradores de autenticação e modelos de token/sessão.
- Módulo `quicksol_estate` como local do serviço de métricas de agentes.
