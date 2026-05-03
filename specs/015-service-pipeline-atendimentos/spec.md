# Feature Specification: Service Pipeline Management (Atendimentos)

**Feature Branch**: `015-service-pipeline-atendimentos`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "utilizar o arquivo `spec-idea.md` como base"
**Source Document**: [spec-idea.md](./spec-idea.md) (technical/architectural detail — for plan phase)

## Clarifications

### Session 2026-05-03

- Q: Política de transições do pipeline (saltos vs adjacência)? → A: **Flexível com gates** — qualquer salto à frente permitido desde que os validators de etapa passem (Proposta exige imóvel; Formalização exige proposta aprovada); rollback permitido em qualquer ponto e sempre auditado; `lost` permitido a partir de qualquer etapa não-terminal.
- Q: O que conta como "interação" para o cálculo de pendência (FR-015)? → A: **Mudanças no atendimento + mensagens no timeline** — `last_activity_date` = max(write_date manual, mais recente `mail.message` postada por usuário). Writes automaticos de campos computados NÃO contam.
- Q: Comportamento de atendimentos quando o corretor responsável é desativado? → A: **Visível para Owner/Manager com sinalização "Sem corretor responsável"** — `agent_id` original é preservado para auditoria, mas o atendimento entra em fila especial "Sem corretor responsável" visível a Owners/Managers da imobiliária; permanece nessa fila até reatribuição manual; nenhuma ação automática além da sinalização.
- Q: Política de vínculo do mesmo imóvel a múltiplos atendimentos ativos? → A: **Sem restrição no atendimento** — vários atendimentos ativos podem referenciar o mesmo imóvel simultaneamente (cenário comum: múltiplos corretores/clientes interessados). A exclusividade é garantida apenas no nível de **Proposta** (spec 013, partial unique index `real_estate_proposal_one_active_per_property`).
- Q: Efeito do ciclo de vida do Atendimento sobre o Lead de origem? → A: **Independência total** — Atendimento mantém referência opcional `lead_id` apenas para rastreabilidade histórica, mas Lead (006) e Atendimento (015) têm ciclos de vida totalmente independentes. Nenhuma mudança de etapa do Atendimento (incluindo Ganho/Perdido) altera automaticamente o estado do Lead. Atualizações no Lead são sempre manuais pelo corretor.

## Overview

Imobiliárias brasileiras precisam acompanhar, de forma estruturada, cada oportunidade de relacionamento entre um corretor e um cliente potencial sobre uma operação específica (Venda ou Locação). Hoje o sistema cobre **leads** (clientes potenciais) e **propostas** (etapa final), mas não modela a jornada completa entre os dois — o **atendimento**. Sem isso, gestores não conseguem visualizar o pipeline em formato kanban, balancear a carga entre corretores, nem identificar oportunidades estagnadas.

Esta feature introduz o conceito de **Atendimento** como entidade própria, distinta de Lead, permitindo que um mesmo cliente origine múltiplos atendimentos (ex.: um de venda + um de locação, ou atendimentos com corretores diferentes). O atendimento move-se por um pipeline estilo Kanban inspirado em CRMs imobiliários consolidados no mercado brasileiro (Kenlo IMOB, Vista, Imobzi).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Corretor cria atendimento e move pelo pipeline (Priority: P1) 🎯 MVP

Um corretor recebe um contato de cliente potencial interessado em alugar um apartamento. Ele precisa registrar esse atendimento, vincular o cliente, indicar a operação (locação), origem (Site/WhatsApp/Indicação) e mover o atendimento pelas etapas do funil — de "Sem atendimento" até "Formalização" — conforme evolui o relacionamento.

**Why this priority**: É a funcionalidade mínima viável que entrega valor imediato ao corretor. Sem ela, não há captura nem evolução de oportunidades.

**Independent Test**: Corretor autenticado cria um atendimento completo, move-o por todas as etapas válidas, marca como ganho ou perdido, e o sistema preserva histórico de cada transição. O corretor não enxerga atendimentos de outros corretores.

**Acceptance Scenarios**:

1. **Given** o corretor está autenticado, **When** registra um novo atendimento informando dados do cliente (nome, telefone, e-mail), tipo de operação (Locação), origem e observações, **Then** o sistema cria o atendimento na etapa "Sem atendimento" associado ao corretor logado.
2. **Given** atendimento na etapa "Em atendimento" sem imóvel vinculado, **When** o corretor tenta movê-lo para "Proposta", **Then** o sistema bloqueia a transição e exige que ao menos um imóvel seja vinculado primeiro.
3. **Given** atendimento em qualquer etapa, **When** o corretor o marca como "Perdido", **Then** o sistema exige um motivo obrigatório antes de concluir.
4. **Given** atendimento com etiqueta "Encerrado", **When** o corretor tenta movê-lo no pipeline, **Then** o sistema bloqueia a alteração e informa que o atendimento está encerrado.
5. **Given** Corretor A criou um atendimento, **When** Corretor B (mesma imobiliária) tenta acessá-lo, **Then** o sistema não exibe o atendimento (isolamento por corretor).
6. **Given** já existe atendimento ativo para o mesmo cliente + tipo de operação + corretor, **When** o corretor tenta criar outro idêntico, **Then** o sistema impede a duplicação.

---

### User Story 2 — Gestor visualiza, filtra e reatribui atendimentos da imobiliária (Priority: P2)

Um gerente precisa de visão consolidada de todos os atendimentos da sua imobiliária para acompanhar performance da equipe, identificar gargalos e redistribuir atendimentos quando um corretor está sobrecarregado ou ausente.

**Why this priority**: Essencial para operação coordenada de equipes, mas não bloqueia produtividade individual do corretor.

**Independent Test**: Gerente autenticado visualiza painel com todos os atendimentos da sua imobiliária, aplica filtros (tipo, etapa, corretor, etiquetas, pendências), reatribui um atendimento de um corretor para outro, e confirma que não enxerga atendimentos de outras imobiliárias.

**Acceptance Scenarios**:

1. **Given** gerente da Imobiliária A, **When** acessa o painel de atendimentos, **Then** vê todos os atendimentos da Imobiliária A com nome do cliente, corretor responsável, etapa e data da última interação.
2. **Given** painel kanban exibido, **When** o gerente solicita os contadores por etapa, **Then** o sistema retorna a quantidade de atendimentos em cada etapa (Sem atendimento, Em atendimento, Visita, Proposta, Formalização).
3. **Given** corretor de férias com atendimentos ativos, **When** o gerente reatribui esses atendimentos para outro corretor, **Then** o sistema atualiza a responsabilidade, registra a mudança no histórico e mantém auditoria.
4. **Given** corretor (não-gerente), **When** tenta reatribuir um atendimento, **Then** o sistema bloqueia a operação por falta de permissão.
5. **Given** gerente da Imobiliária A, **When** consulta atendimentos, **Then** o sistema nunca retorna atendimentos da Imobiliária B.

---

### User Story 3 — Filtros, ordenações e busca no pipeline (Priority: P2)

Corretores e gerentes precisam encontrar rapidamente atendimentos relevantes no meio de dezenas/centenas, filtrando por tipo, corretor, etiquetas, identificando pendências (atendimentos sem interação recente) e buscando por dados do cliente ou do imóvel.

**Why this priority**: Multiplica a usabilidade do pipeline em volume operacional real; sem isso, o painel se torna inutilizável quando há muitos atendimentos.

**Independent Test**: Usuário aplica combinações de filtros (Locação + corretor X + etiqueta "Follow Up") e ordena por "Pendências" — o sistema retorna a lista correta, ordenada do atendimento mais antigo sem interação para o mais recente.

**Acceptance Scenarios**:

1. **Given** painel de atendimentos, **When** filtra por tipo "Locação" + etapa "Em atendimento" + corretor específico, **Then** o sistema retorna apenas atendimentos que satisfazem todos os critérios.
2. **Given** ordenação selecionada como "Pendências", **When** carrega a lista, **Then** atendimentos sem interação há mais tempo aparecem primeiro.
3. **Given** usuário digita parte do nome ou telefone do cliente na busca, **When** confirma, **Then** o sistema retorna atendimentos onde o cliente corresponde à busca.
4. **Given** atendimento sem interação há mais dias do que o configurado pela imobiliária, **When** consulta o pipeline, **Then** esse atendimento é sinalizado como "pendente".

---

### User Story 4 — Etiquetas e Origens configuráveis pela imobiliária (Priority: P2)

Cada imobiliária quer padronizar a categorização de atendimentos com etiquetas próprias (Follow Up, Qualificado, Lançamento, Parceria, VIP, etc.) e configurar suas origens de captação (Site, Indicação, Portal, WhatsApp, etc.).

**Why this priority**: Aumenta consistência entre corretores e habilita relatórios significativos, mas não é bloqueante para uso individual.

**Independent Test**: Owner/Manager cria, edita, desativa etiquetas e origens; corretores podem associá-las a atendimentos; etiquetas/origens da Imobiliária A não aparecem para Imobiliária B.

**Acceptance Scenarios**:

1. **Given** Owner ou Manager da imobiliária, **When** cria uma nova etiqueta com nome e cor, **Then** ela fica disponível para todos os corretores da mesma imobiliária.
2. **Given** corretor (sem permissão de gestão), **When** tenta criar etiqueta, **Then** o sistema bloqueia.
3. **Given** etiqueta usada em atendimentos antigos, **When** Owner desativa a etiqueta, **Then** o histórico dos atendimentos é preservado e a etiqueta deixa de aparecer em novas seleções.
4. **Given** lista de origens, **When** corretor cria atendimento, **Then** consegue escolher entre as origens cadastradas pela sua imobiliária.

---

### User Story 5 — Múltiplos telefones e deduplicação de cliente (Priority: P3)

Clientes potenciais frequentemente fornecem múltiplos contatos (celular + WhatsApp + comercial). Corretores e recepcionistas precisam registrar todos. Quando o mesmo cliente já existe (cadastrado em outro atendimento), o sistema deve reaproveitar o cadastro em vez de duplicá-lo.

**Why this priority**: Qualidade de dados e produtividade na recepção; não bloqueia o fluxo principal.

**Independent Test**: Recepcionista registra atendimento informando dois telefones (celular + WhatsApp); ao criar outro atendimento informando o mesmo telefone ou e-mail, o sistema reaproveita o cadastro do cliente.

**Acceptance Scenarios**:

1. **Given** novo atendimento, **When** o usuário informa dois ou mais telefones do cliente classificados por tipo (celular, residencial, comercial, WhatsApp), **Then** todos são gravados e associados ao cliente.
2. **Given** cliente já existe (telefone ou e-mail correspondem), **When** novo atendimento é criado para ele, **Then** o sistema reutiliza o cadastro existente em vez de criar duplicata.
3. **Given** tipo de telefone fora dos valores aceitos, **When** o usuário tenta salvar, **Then** o sistema rejeita com mensagem clara.

---

### Edge Cases

- O que acontece quando um atendimento é avançado para "Formalização" sem proposta aprovada vinculada? → O sistema deve bloquear a transição e indicar a regra ao usuário.
- O que acontece quando o gerente tenta reatribuir um atendimento já marcado como ganho ou perdido? → O sistema deve impedir a reatribuição em atendimentos finalizados.
- O que acontece quando uma etiqueta marcada como "sistema" (ex.: "Encerrado") é editada/excluída por um Owner? → O sistema deve impedir alterações em etiquetas de sistema.
- O que acontece quando o corretor responsável pelo atendimento é desativado/removido? → O sistema deve manter o atendimento, sinalizar a ausência de corretor e exigir reatribuição pelo gerente.
- O que acontece quando dois usuários movem o mesmo atendimento de etapa simultaneamente? → A última transição vence; ambas ficam registradas no histórico para auditoria.
- O que acontece quando o cliente potencial original é desativado? → Atendimentos existentes permanecem visíveis para histórico; novos atendimentos não podem ser criados para esse cliente.
- O que acontece quando o cliente fornece um telefone idêntico a outro cliente já existente? → Comportamento padrão do sistema é reaproveitar cadastro do cliente existente; o operador deve confirmar se trata-se da mesma pessoa antes de prosseguir.

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline e ciclo de vida**

- **FR-001**: O sistema MUST registrar atendimento como entidade distinta de Lead, vinculando cliente, corretor, tipo de operação (Venda ou Locação) e origem.
- **FR-001a**: O sistema MUST manter Lead (spec 006) e Atendimento (015) como entidades com **ciclos de vida totalmente independentes**: o Atendimento pode opcionalmente referenciar um Lead de origem (`lead_id`) apenas para rastreabilidade histórica, mas nenhuma transição de etapa do Atendimento (incluindo Ganho/Perdido) altera automaticamente o estado do Lead. Atualizações do Lead permanecem manuais pelo corretor.
- **FR-002**: O sistema MUST suportar pipeline com etapas: Sem atendimento, Em atendimento, Visita, Proposta, Formalização, Ganho, Perdido.
- **FR-003**: O sistema MUST permitir transições de etapa **flexíveis com gates**: saltos arbitrários para frente são permitidos desde que os validators da etapa-alvo sejam satisfeitos (FR-004 e FR-005); rollback (retroceder) é permitido a partir de qualquer etapa não-terminal; toda transição (avanço ou rollback) registra data, hora, usuário responsável e etapa de origem/destino no histórico (auditoria).
- **FR-003a**: O sistema MUST tratar `Ganho` e `Perdido` como etapas terminais — não permite transições de saída sem ação explícita de reabertura (fora do escopo desta feature).
- **FR-004**: O sistema MUST exigir ao menos um imóvel vinculado para mover atendimento à etapa "Proposta".
- **FR-005**: O sistema MUST exigir proposta aprovada vinculada para mover atendimento à etapa "Formalização".
- **FR-006**: O sistema MUST exigir motivo obrigatório quando atendimento é marcado como "Perdido".
- **FR-007**: O sistema MUST bloquear movimentação no pipeline quando o atendimento possuir etiqueta de sistema "Encerrado".
- **FR-008**: O sistema MUST impedir criação de mais de um atendimento ativo para a mesma combinação de cliente + tipo de operação + corretor.
- **FR-008a**: O sistema MUST permitir que o **mesmo imóvel** esteja vinculado a múltiplos atendimentos ativos simultaneamente (clientes e/ou corretores distintos podem estar interessados no mesmo imóvel). A exclusividade de imóvel é garantida apenas no nível de **Proposta** (spec 013), não no atendimento.

**Multi-tenancy e autorização**

- **FR-009**: O sistema MUST garantir que cada atendimento pertença a uma única imobiliária e que usuários só visualizem atendimentos da própria imobiliária.
- **FR-010**: O sistema MUST aplicar a seguinte matriz de autorização:
  | Operação | Owner | Manager | Agent | Reception | Prospector |
  |----------|:---:|:---:|:---:|:---:|:---:|
  | Criar atendimento | ✓ | ✓ | ✓ | ✓ | ✓ |
  | Ler atendimentos da imobiliária | ✓ | ✓ | apenas próprios | ✓ | apenas próprios |
  | Atualizar atendimento | ✓ | ✓ | apenas próprios | — | — |
  | Excluir (desativar) | ✓ | ✓ | — | — | — |
  | Mover etapa | ✓ | ✓ | apenas próprios | — | — |
  | Reatribuir corretor | ✓ | ✓ | — | — | — |
  | Gerenciar etiquetas e origens | ✓ | ✓ | — | — | — |

**Filtros e visualização**

- **FR-011**: O sistema MUST permitir filtrar atendimentos por: tipo (Venda/Locação), etapa, corretor responsável, etiquetas, origem, status de pendência, e busca textual em cliente/telefone/imóvel.
- **FR-012**: O sistema MUST oferecer ordenações: pendências (mais antigos sem interação primeiro), mais recentes, mais antigos.
- **FR-013**: O sistema MUST oferecer paginação com tamanho de página configurável (default razoável para dispositivos web).
- **FR-014**: O sistema MUST disponibilizar contagem de atendimentos por etapa para apresentação em painel kanban.
- **FR-015**: O sistema MUST sinalizar atendimentos como "pendentes" quando a última interação for mais antiga que um limite configurável pela imobiliária. Considera-se **interação** qualquer uma das seguintes ações atribuíveis a um usuário: (a) alteração manual de campos do atendimento (write explícito), (b) mensagem postada no timeline do atendimento, ou (c) transição de etapa. Atualizações automáticas (recomputação de campos calculados, jobs em background) NÃO contam como interação.

**Etiquetas, origens e configuração**

- **FR-016**: O sistema MUST permitir CRUD de etiquetas (nome + cor) escopadas por imobiliária, restrito a Owner/Manager.
- **FR-017**: O sistema MUST permitir CRUD de origens de atendimento escopadas por imobiliária, restrito a Owner/Manager.
- **FR-018**: O sistema MUST manter ao menos uma etiqueta de sistema ("Encerrado") imutável pelo usuário.
- **FR-019**: O sistema MUST aplicar soft delete em etiquetas/origens em uso por atendimentos históricos, preservando histórico.
- **FR-020**: O sistema MUST permitir que cada imobiliária configure o limite de dias para considerar um atendimento como "pendente".

**Cliente e contatos**

- **FR-021**: O sistema MUST suportar múltiplos telefones por cliente, classificados por tipo (celular, residencial, comercial, WhatsApp, fax).
- **FR-022**: O sistema MUST reaproveitar cadastro de cliente existente quando telefone OR e-mail informados correspondem a um cliente já cadastrado.
- **FR-023**: O sistema MUST validar formato de telefone e tipo dentro dos valores aceitos.

**Reatribuição e auditoria**

- **FR-024**: O sistema MUST permitir reatribuição de corretor por Owner/Manager, registrando a mudança no histórico do atendimento.
- **FR-024b**: O sistema MUST notificar, via `mail.activity` (mensageria interna), tanto o corretor anterior quanto o novo corretor sempre que ocorrer uma reatribuição (FR-024). A notificação conterá referencia ao atendimento, motivo (se informado) e usuário que executou a ação.
- **FR-024a**: O sistema MUST sinalizar como "Sem corretor responsável" todo atendimento ativo cujo `agent_id` aponte para um usuário desativado (`active=False`); esses atendimentos:
  - permanecem com o `agent_id` original preservado para auditoria;
  - tornam-se visíveis a Owners e Managers da imobiliária por meio de uma fila/filtro dedicado ("Sem corretor responsável");
  - permanecem nessa fila até que um Owner ou Manager realize a reatribuição manual (FR-024);
  - bloqueiam transições de etapa enquanto não tiverem corretor ativo responsável.
- **FR-025**: O sistema MUST manter histórico completo de mudanças do atendimento (etapas, atribuições, etiquetas, observações), preservado indefinidamente.
- **FR-026**: O sistema MUST oferecer soft delete de atendimentos (sem remoção física), com possibilidade de visualização de arquivados via filtro.

### Key Entities

- **Atendimento (Service)**: jornada de um corretor com um cliente sobre uma operação específica. Atributos principais: cliente, corretor responsável, tipo (Venda/Locação), origem, etapa atual, etiquetas, imóveis vinculados, propostas vinculadas, observações, motivo de perda (se aplicável), data da última interação, indicador de pendência, imobiliária, situação (ativo/arquivado).
- **Etiqueta de Atendimento (Service Tag)**: marcador classificatório (nome + cor) escopado por imobiliária; pode ser de sistema (imutável) ou customizada.
- **Origem do Atendimento (Service Source)**: canal/fonte de captação configurável por imobiliária (Site, Indicação, Portal, WhatsApp, etc.).
- **Telefone do Cliente (Partner Phone)**: contato telefônico do cliente classificado por tipo, com indicação opcional de telefone primário.
- **Configurações de Atendimento (Service Settings)**: parâmetros por imobiliária — limite de dias para considerar atendimento pendente; opcionalmente, dias para encerramento automático.
- **Cliente (Client)**: pessoa potencialmente interessada em uma operação; pode ter múltiplos atendimentos simultâneos (de tipos ou corretores diferentes).
- **Corretor (Agent)**: usuário responsável pelo atendimento.
- **Imobiliária (Company)**: organização à qual atendimento, etiquetas, origens e configurações estão escopados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um corretor consegue criar um atendimento completo (cliente novo + dados básicos) em menos de 2 minutos.
- **SC-002**: Movimentação de etapa do pipeline (incluindo validações e registro de auditoria) é confirmada ao usuário em menos de 1 segundo no caso típico.
- **SC-003**: Painel kanban com contadores por etapa carrega em menos de 3 segundos para imobiliárias com até 10.000 atendimentos.
- **SC-004**: Listagem filtrada do pipeline retorna em menos de 1 segundo para 95% das consultas (até 10.000 atendimentos por imobiliária).
- **SC-005**: Zero vazamento de dados entre imobiliárias diferentes (verificado via testes automatizados de isolamento multi-tenant).
- **SC-006**: 100% das transições de etapa ficam auditadas com data, hora e usuário responsável.
- **SC-007**: 100% das tentativas de duplicar atendimento ativo (mesmo cliente + tipo + corretor) são bloqueadas.
- **SC-008**: 100% das tentativas de avançar para "Proposta" sem imóvel ou para "Formalização" sem proposta aprovada são bloqueadas com mensagem clara.
- **SC-009**: Gerente consegue identificar atendimentos pendentes (sem interação acima do limite configurado) em uma única ação de filtro/ordenação.
- **SC-010**: Reatribuição de atendimento é concluída em menos de 1 minuto para o gerente, incluindo notificação aos corretores envolvidos.

## Assumptions

- O sistema de **Leads** (spec 006) já existe; atendimentos podem opcionalmente referenciar leads, mas não dependem deles (atendimento pode ser criado direto a partir de um cliente novo).
- O sistema de **Propostas** (spec 013) já existe; a etapa "Formalização" depende de proposta aprovada.
- O sistema de **RBAC com 9 perfis** (spec 005) e o módulo de **onboarding/usuários** (spec 009) já existem; a feature reutiliza os perfis Owner, Manager, Agent, Reception, Prospector.
- O sistema de **gestão de imóveis e corretores** (spec 004) já existe; atendimentos referenciam imóveis e corretores existentes.
- A interface administrativa Odoo é restrita ao usuário admin; demais perfis acessam o sistema via aplicação frontend headless usando os endpoints REST.
- Notificações internas a corretores em reatribuição utilizam o mecanismo de mensageria interna do Odoo (`mail.thread`).
- O limite default de "pendência" é 3 dias, configurável entre 1 e 30 dias por imobiliária.

## Dependencies

- Spec 004 — Agent Management
- Spec 005 — RBAC User Profiles
- Spec 006 — Lead Management
- Spec 009 — User Onboarding
- Spec 013 — Property Proposals
- Mensageria interna e auditoria (Odoo `mail.thread`/`mail.activity.mixin`)

## Out of Scope (Non-Goals)

- Importação em massa de atendimentos a partir de planilhas ou de outros CRMs (poderá ser tratado em feature futura).
- Integrações com plataformas externas de captação (portais imobiliários, redes sociais, chatbots) — fora do escopo desta feature.
- Conversão automática de Lead para Atendimento (mantém-se manual; corretor seleciona o lead ou cria cliente novo).
- Relatórios analíticos avançados de funil/conversão (poderá ser tratado em feature dedicada).
- Agendamento de visitas como entidade própria (poderá ser tratado em feature dedicada; atendimento apenas marca a etapa).
- Aplicativo mobile nativo — atendimento via interface web responsiva.
- Comunicação direta com cliente (e-mail/WhatsApp do atendimento) — fora desta feature.

---

> **Technical detail / architecture / API contracts**: ver [spec-idea.md](./spec-idea.md). Esses elementos serão refinados em `plan.md`.
