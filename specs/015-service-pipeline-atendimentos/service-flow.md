# Fluxo Completo de Atendimentos — Spec 015

Este documento descreve o ciclo de vida completo de um **Atendimento** no sistema imobiliário, cobrindo desde o registro inicial pelo corretor até a resolução final (ganho ou perdido). A spec 015 — Service Pipeline (Atendimentos) introduz o atendimento como entidade própria, posicionada entre o **Lead** (006) e a **Proposta** (013), formando o pipeline kanban completo da imobiliária.

Um atendimento nasce na etapa "Sem atendimento", evolui pelo funil conforme o relacionamento com o cliente avança, e pode ser ganho (negócio fechado) ou perdido (desistência) a qualquer momento. Gestores podem visualizar, filtrar e reatribuir atendimentos. Etiquetas e origens são configuradas por imobiliária.

---

## Estados do Atendimento

```
         [no_service]
              │
    PATCH /services/{id}/stage
              │
         [in_service]
              │
    PATCH /services/{id}/stage
              │
           [visit]
              │
    PATCH /services/{id}/stage
    (gate: property_ids obrigatório)
              │
          [proposal]
              │
    PATCH /services/{id}/stage
    (gate: proposta aceita obrigatória)
              │
       [formalization]
              │
    PATCH /services/{id}/stage
              │
           [won]  ← terminal (negócio fechado)
```

```
[qualquer etapa não-terminal]
    │
    PATCH /services/{id}/stage  { stage: "lost", lost_reason: "..." }
    │
  [lost]  ← terminal (motivo obrigatório)
```

```
[qualquer etapa não-terminal]
    │
    PATCH /services/{id}/stage  { stage: <etapa anterior> }  ← rollback permitido
```

> **Obs.:** Etiqueta de sistema `closed` trava qualquer transição de etapa (FR-007).  
> Atendimento com corretor desativado (`is_orphan_agent=True`) também bloqueia transições até reatribuição (FR-024a).

---

## Jornadas

### J1 — Corretor registra e evolui atendimento pelo pipeline

Um corretor recebe um cliente interessado em locação. Ele cria o atendimento vinculando os dados do cliente, o tipo de operação e a origem, e vai movendo pelo funil conforme o relacionamento evolui.

**Por que esta prioridade (P1 — MVP):** É a funcionalidade mínima que entrega valor imediato. Sem ela, não há captura nem evolução de oportunidades.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/services` | Cria atendimento em `no_service`; corretor logado é atribuído automaticamente |
| 2 | `GET /api/v1/services/{id}` | Confirma dados e etapa inicial |
| 3 | `PATCH /api/v1/services/{id}/stage` `{ stage: "in_service" }` | Avança para "Em atendimento" |
| 4 | `PATCH /api/v1/services/{id}/stage` `{ stage: "visit" }` | Agendou visita |
| 5 | `PUT /api/v1/services/{id}` `{ property_ids: [X] }` | Vincula imóvel de interesse |
| 6 | `PATCH /api/v1/services/{id}/stage` `{ stage: "proposal" }` | Avança para "Proposta" (gate: imóvel obrigatório) |
| 7 | `PATCH /api/v1/services/{id}/stage` `{ stage: "won" }` | Negócio fechado — estado terminal |

---

### J2 — Atendimento marcado como perdido com motivo

O cliente desistiu. O corretor registra o encerramento com motivo obrigatório. O estado `lost` é terminal — o atendimento não pode ser reativado sem flag especial.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/services/{id}` | Confirma etapa atual |
| 2 | `PATCH /api/v1/services/{id}/stage` `{ stage: "lost", lost_reason: "Cliente desistiu" }` | Marca como perdido (motivo obrigatório — sem ele retorna 422) |

---

### J3 — Rollback de etapa

O atendimento avançou cedo demais para "Proposta", mas o cliente quer voltar a visitar. O sistema permite rollback explícito.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/services/{id}` | Confirma etapa atual (`proposal`) |
| 2 | `PATCH /api/v1/services/{id}/stage` `{ stage: "visit", comment: "Cliente quer rever o imóvel" }` | Reverte para `visit`; transição auditada no timeline |

---

### J4 — Gestor visualiza, filtra e reatribui atendimentos

O gerente precisa de visão consolidada da equipe, identificar gargalos e redistribuir atendimentos de um corretor sobrecarregado.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/services?ordering=pendency` | Lista todos os atendimentos ordenados por pendência (sem interação há mais tempo) |
| 2 | `GET /api/v1/services/summary` | Contadores por etapa para o kanban |
| 3 | `GET /api/v1/services?agent_id={id}&stage=in_service` | Filtra atendimentos de um corretor específico em etapa "Em atendimento" |
| 4 | `PATCH /api/v1/services/{id}/reassign` `{ new_agent_id: Y, reason: "Balanceamento" }` | Reatribui para outro corretor (somente Owner/Manager) |

> **Isolamento multi-tenancy:** Gestor da Imobiliária A nunca enxerga atendimentos da Imobiliária B.

---

### J5 — Filtros e busca no pipeline

Corretor ou gestor precisa encontrar rapidamente um atendimento por nome de cliente ou telefone.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/services?q=João` | Busca livre por nome, telefone ou e-mail do cliente |
| 2 | `GET /api/v1/services?operation_type=rent&stage=visit&is_pending=true` | Filtro combinado: locações em visita com pendência |
| 3 | `GET /api/v1/services?ordering=pendency` | Ordena do mais antigo sem interação para o mais recente |
| 4 | `GET /api/v1/services?orphan_agent=true` | Lista atendimentos sem corretor ativo (FR-024a) |

---

### J6 — Etiquetas e origens configuráveis

O Owner cria etiquetas personalizadas (Follow Up, VIP, Qualificado) e origens de captação (WhatsApp, Site, Indicação) para a sua imobiliária.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/service-sources` | Lista origens disponíveis |
| 2 | `POST /api/v1/service-sources` `{ name: "WhatsApp", code: "whatsapp" }` | Cria nova origem (Owner/Manager) |
| 3 | `GET /api/v1/service-tags` | Lista etiquetas disponíveis |
| 4 | `POST /api/v1/service-tags` `{ name: "Follow Up", color: "#FF6B35" }` | Cria nova etiqueta (Owner/Manager) |
| 5 | `PUT /api/v1/services/{id}` `{ tag_ids: [tag_id] }` | Associa etiqueta ao atendimento |
| 6 | `DELETE /api/v1/service-tags/{id}` | Arquiva etiqueta (soft delete) — histórico preservado |

> **Isolamento:** Etiquetas e origens da Imobiliária A não aparecem para a Imobiliária B.

---

### J7 — Múltiplos telefones e deduplicação de cliente

A recepcionista registra um atendimento informando celular e WhatsApp. Ao criar um segundo atendimento com o mesmo número, o sistema reaproveita o cadastro do cliente.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/services` com `client.phones: [{type:"mobile", number:"..."}, {type:"whatsapp", number:"..."}]` | Cria atendimento com dois telefones; todos gravados em `partner.phone_ids` |
| 2 | `POST /api/v1/services` com mesmo número de telefone | Sistema identifica parceiro existente e reutiliza (`client.id` = mesmo) |
| 3 | `GET /api/v1/services/{id}` | Confirma `client.phones` com todos os contatos |

> **Deduplicação (FR-022a):** Telefone único → reusa parceiro. Telefone ambíguo (dois parceiros distintos com mesmo número) → 409 com `candidate_ids` para resolução manual (FR-022b). Conflito telefone vs. e-mail → prefere telefone (FR-022c).

---

### J8 — Atendimento com corretor desativado (Orphan Agent)

O corretor responsável foi desativado. O atendimento fica sinalizado como "Sem corretor responsável" e toda transição de etapa é bloqueada até reatribuição.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/services?orphan_agent=true` | Gestor/Owner localiza atendimentos órfãos |
| 2 | `GET /api/v1/services/{id}` | Confirma `is_orphan_agent=true` |
| 3 | `PATCH /api/v1/services/{id}/reassign` `{ new_agent_id: Z }` | Reatribui para corretor ativo |
| 4 | `PATCH /api/v1/services/{id}/stage` | Agora desbloqueado para transições |

---

## Restrições e Gates

| Regra | Detalhe |
|---|---|
| Gate `proposal` | `property_ids` deve ter pelo menos 1 imóvel vinculado — sem imóvel → 422 |
| Gate `formalization` | Pelo menos uma proposta vinculada com `state=accepted` — sem proposta aceita → 422 |
| `lost_reason` obrigatório | Transição para `lost` sem motivo → 422 |
| Etapas terminais imutáveis | Qualquer ação em `won` ou `lost` → 405/422 (exceto `allow_reopen` explícito) |
| Etiqueta `closed` trava transições | Atendimento com tag de sistema `closed` → 423 Locked |
| Corretor desativado bloqueia etapas | `is_orphan_agent=True` → 422 até reatribuição (FR-024a) |
| EXCLUDE constraint | Mesmo cliente + tipo de operação + corretor com atendimento ativo → 409 |
| Reatribuição em terminal bloqueada | `reassign` em `won`/`lost` → 409 |
| Corretor não pode reatribuir | Somente Owner/Manager → 403 |
| Escopo do corretor | Corretor acessa apenas os próprios atendimentos — fora do escopo → 404 (anti-enumeração) |
| Isolamento multi-tenancy | Atendimentos, etiquetas e origens são isolados por `company_id` |
