# Fluxo Completo de Propostas — Specs 013 + 014

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

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals` | Cria rascunho (`draft`) |
| 2 | `GET /api/v1/proposals/{id}` | Confirma dados antes de enviar |
| 3 | `POST /api/v1/proposals/{id}/send` | Envia → `sent` |

---

### J2 — Aceite direto (venda ou locação sem análise)

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `GET /api/v1/proposals/{id}` | Consulta proposta em `sent` |
| 2 | `POST /api/v1/proposals/{id}/accept` | Aceita → `accepted`; concorrentes → `cancelled` |

---

### J3 — Rejeição com motivo

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals/{id}/reject` | Rejeita → `rejected` (obriga `reason`) |
| 2 | `GET /api/v1/proposals/stats` | Atualiza contadores do painel |

---

### J4 — Contraproposta (negociação de valor)

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals/{id}/counter` | Contra-oferta → `negotiation` |
| 2 | *(cliente aceita/rejeita fora do sistema)* | — |
| 3 | `POST /api/v1/proposals/{id}/send` | Reenvio → `sent` |
| 4 | `POST /api/v1/proposals/{id}/accept` | Aceite final |

---

### J5 — Fila de prioridade (múltiplas propostas no imóvel)

| Passo | Endpoint | Descrição |
|---|---|---|
| 1 | `POST /api/v1/proposals` (×N) | N propostas criadas para o mesmo imóvel |
| 2 | `POST /api/v1/proposals/{id}/send` (×N) | 1ª → `sent`, 2ª+ → `queued` (FIFO) |
| 3 | `GET /api/v1/proposals/{id}/queue` | Consulta posição na fila |
| 4 | `POST /api/v1/proposals/{id}/reject` | 1ª rejeitada, fila promove a 2ª → `sent` |

---

### J6 — Análise de crédito (locação)

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
