# Fluxo Completo de Propostas — Specs 013 + 014

Este documento descreve o ciclo de vida completo de uma proposta imobiliária no sistema, cobrindo desde a criação até a resolução final (aceite, rejeição ou análise de crédito). Consolida as duas specs complementares: **013 — Property Proposals** (gestão do ciclo de vida e fila de prioridade) e **014 — Rental Credit Check** (análise de ficha cadastral para contratos de locação).

Uma proposta nasce como rascunho, é enviada ao proprietário e segue por diferentes caminhos conforme o tipo de negócio (venda ou locação) e a decisão das partes. Propostas de locação passam obrigatoriamente por análise de crédito antes do aceite. Imóveis com múltiplos interessados operam em fila FIFO — apenas a primeira proposta fica ativa; as demais aguardam sua vez.

## Estados da Proposta

```
         [draft]
            │
      POST /proposals/{id}/send
            │
         [sent] ◄─────────────────────────────────┐
            │                                      │
   (Locação)│        (Venda)                       │ PATCH credit-checks/{id}
            │            │                         │   result=cancelled
    POST /proposals/{id}/credit-checks             │
            │                                      │
   [credit_check_pending]─────────────────────────►┘
            │
    PATCH /proposals/{id}/credit-checks/{id}
     result=approved|rejected
            │
     ┌──────┴──────┐
     │             │
 [approved]   [rejected] ──► queue promove próxima proposta
     │
   (concorrentes → cancelled)
```

```
[sent] ──► POST /proposals/{id}/counter ──► [negotiation]
           (contraproposta de valor)               │
                                           POST /proposals/{id}/send (reenvio)
                                                   │
                                                [sent]
```

```
[sent] ──► POST /proposals/{id}/reject ──► [rejected]  (terminal)
[sent] ──► POST /proposals/{id}/accept ──► [accepted]  (terminal, cancela concorrentes)
```

---

## Jornadas

### J1 — Criação e envio de proposta

Um agente cria uma proposta para um imóvel específico (vinculando cliente e valor) e a envia ao proprietário. Enquanto não enviada, a proposta fica em rascunho e pode ser editada livremente. O envio é irreversível — a partir daí o estado só avança via ações explícitas.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals` | Cria rascunho (`draft`) |
| 2 | `GET /api/v1/proposals/{id}` | Confirma dados antes de enviar |
| 3 | `POST /api/v1/proposals/{id}/send` | Envia → `sent` |

---

### J2 — Aceite direto (venda ou locação sem análise)

O proprietário aceita a proposta sem passar por análise de crédito (típico em propostas de venda ou locações com garantias já comprovadas externamente). O aceite é terminal: todas as propostas concorrentes ativas para o mesmo imóvel são canceladas automaticamente.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/proposals/{id}` | Consulta proposta em `sent` |
| 2 | `POST /api/v1/proposals/{id}/accept` | Aceita → `accepted`; concorrentes → `cancelled` |

---

### J3 — Rejeição com motivo

O proprietário recusa a proposta. O campo `reason` é obrigatório — sem justificativa o endpoint retorna 400. A rejeição é um estado terminal; a proposta não pode ser reativada. Se houver fila, a próxima proposta é promovida automaticamente para `sent`.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals/{id}/reject` | Rejeita → `rejected` (obriga `reason`) |
| 2 | `GET /api/v1/proposals/stats` | Atualiza contadores do painel |

---

### J4 — Contraproposta (negociação de valor)

O proprietário não aceita nem rejeita — propõe um valor diferente. A proposta entra em `negotiation`. O agente negocia com o cliente fora do sistema e, quando há acordo, reenvia a proposta (possivelmente com novo valor). O ciclo pode se repetir mais de uma vez antes de uma decisão final.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals/{id}/counter` | Contra-oferta → `negotiation` |
| 2 | *(cliente aceita/rejeita fora do sistema)* | — |
| 3 | `POST /api/v1/proposals/{id}/send` | Reenvio → `sent` |
| 4 | `POST /api/v1/proposals/{id}/accept` | Aceite final |

---

### J5 — Fila de prioridade (múltiplas propostas no imóvel)

Um imóvel popular recebe interesse de vários clientes simultaneamente. O sistema aplica ordem FIFO: a primeira proposta enviada fica ativa (`sent`) e as demais entram em `queued`. Quando a proposta ativa é rejeitada ou cancelada, a fila avança automaticamente — a próxima entra em `sent` sem intervenção manual.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals` (×N) | N propostas criadas para o mesmo imóvel |
| 2 | `POST /api/v1/proposals/{id}/send` (×N) | 1ª → `sent`, 2ª+ → `queued` (FIFO) |
| 3 | `GET /api/v1/proposals/{id}/queue` | Consulta posição na fila |
| 4 | `POST /api/v1/proposals/{id}/reject` | 1ª rejeitada, fila promove a 2ª → `sent` |

---

### J6 — Análise de crédito (locação)

Exclusiva para propostas de locação (`proposal_type=lease`). Antes de aceitar, o proprietário ou gestor solicita uma análise de ficha cadastral junto a uma seguradora. A proposta fica bloqueada em `credit_check_pending` enquanto aguarda o resultado. Apenas um check pode estar pendente por vez (409 se tentar abrir um segundo). O resultado final define o destino da proposta: aprovado fecha o negócio, rejeitado libera a fila, cancelado devolve a proposta ao estado anterior.

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/proposals/{id}` | Confirma `proposal_type=lease` e `state=sent/negotiation` |
| 2 | `POST /api/v1/proposals/{id}/credit-checks` | Inicia análise → `credit_check_pending` |
| 3 | *(análise externa pela seguradora)* | — |
| 4 | `PATCH /api/v1/proposals/{id}/credit-checks/{check_id}` | Registra resultado (`approved/rejected/cancelled`) |
| 5a | resultado `approved` | Proposta → `accepted`; concorrentes → `cancelled` |
| 5b | resultado `rejected` | Proposta → `rejected`; fila promove próxima |
| 5c | resultado `cancelled` | Check cancelado; proposta reverte para `sent` |

---

### J7 — Histórico de crédito do cliente

Permite ao gestor ou proprietário consultar o histórico completo de análises de crédito de um cliente em todas as propostas da empresa. Útil para avaliar o risco antes de aceitar uma nova proposta. O sumário traz totais por resultado (aprovados, rejeitados, pendentes, cancelados). Agentes só visualizam clientes das suas próprias propostas — fora do escopo retorna 404 (anti-enumeração).

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/clients/{partner_id}/credit-history` | Lista todos os checks do cliente, sumário + itens |
| 2 | `GET /api/v1/proposals/{id}/credit-checks` | Lista checks de uma proposta específica |

---

## Restrições principais

| Regra | Detalhe |
|---|---|
| Análise de crédito só para locação | Proposta de venda → 422 |
| Apenas 1 check pendente por proposta | 2º pedido → 409 |
| `rejection_reason` obrigatório | Sem motivo → 400 |
| Proposta em estado terminal é imutável | Qualquer ação → 405/422 |
| Proposta em fila (`queued`) não pode ser enviada | `send` → 422 |
| Agente só acessa suas próprias propostas | Fora do escopo → 404 |
