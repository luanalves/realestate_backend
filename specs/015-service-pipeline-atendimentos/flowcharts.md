# Fluxogramas de Atendimentos — Spec 015

Este documento contém os fluxogramas visuais do ciclo de vida de um **Atendimento** (`thedevkitchen.service`), cobrindo todas as jornadas definidas em [service-flow.md](./service-flow.md). Use estes diagramas para entender quais endpoints chamar, em qual ordem e quais condições de erro tratar.

---

## Máquina de Estados do Atendimento

```mermaid
stateDiagram-v2
    direction LR

    [*] --> no_service : POST /api/v1/services

    no_service --> in_service : PATCH /services/{id}/stage\nstage="in_service"
    in_service --> visit : PATCH /services/{id}/stage\nstage="visit"
    visit --> proposal : PATCH /services/{id}/stage\nstage="proposal"\n⚠ gate: property_ids obrigatório
    proposal --> formalization : PATCH /services/{id}/stage\nstage="formalization"\n⚠ gate: proposta aceita
    formalization --> won : PATCH /services/{id}/stage\nstage="won"

    no_service --> lost : PATCH /services/{id}/stage\nstage="lost" + lost_reason
    in_service --> lost : PATCH /services/{id}/stage\nstage="lost" + lost_reason
    visit --> lost : PATCH /services/{id}/stage\nstage="lost" + lost_reason
    proposal --> lost : PATCH /services/{id}/stage\nstage="lost" + lost_reason
    formalization --> lost : PATCH /services/{id}/stage\nstage="lost" + lost_reason

    in_service --> no_service : rollback permitido
    visit --> in_service : rollback permitido
    proposal --> visit : rollback permitido
    formalization --> proposal : rollback permitido

    won --> [*]
    lost --> [*]

    state won {
        direction LR
        [*] --> terminal_won : 🔒 Imutável
    }
    state lost {
        direction LR
        [*] --> terminal_lost : 🔒 Imutável
    }
```

---

## J1 — Corretor registra e evolui atendimento pelo pipeline

```mermaid
flowchart TD
    Start([👤 Corretor logado\nrecebe cliente interessado]) --> C1

    C1["**1. Criar atendimento**\nPOST /api/v1/services\n\n{\n  client: { name, phones },\n  operation_type: 'rent',\n  source_id: ...\n}"] --> C1R{Resposta}
    C1R -->|201 Created\nestage=no_service| C2
    C1R -->|409 Conflict\nmesmo cliente+operação+corretor ativo| ERR1([❌ Atendimento duplicado\nreutilizar ou escolher outro cliente])

    C2["**2. Confirmar atendimento**\nGET /api/v1/services/{id}"] -->|200 OK| C3

    C3["**3. Avançar para 'Em atendimento'**\nPATCH /api/v1/services/{id}/stage\n\n{ stage: 'in_service' }"] -->|200 OK| C4

    C4["**4. Agendar visita**\nPATCH /api/v1/services/{id}/stage\n\n{ stage: 'visit' }"] -->|200 OK| C4b

    C4b["**5. Vincular imóvel de interesse**\nPUT /api/v1/services/{id}\n\n{ property_ids: [X] }"] -->|200 OK| C5

    C5["**6. Avançar para 'Proposta'**\nPATCH /api/v1/services/{id}/stage\n\n{ stage: 'proposal' }"] --> C5R{Gate}
    C5R -->|✅ property_ids preenchido\n200 OK| C6
    C5R -->|❌ sem imóvel vinculado\n422 Unprocessable| C4b

    C6["**7. Negócio fechado**\nPATCH /api/v1/services/{id}/stage\n\n{ stage: 'won' }"] -->|200 OK| Won([🏆 WON — Estado terminal\nnegócio fechado])
```

---

## J2 — Atendimento marcado como perdido

```mermaid
flowchart TD
    Start([🔴 Cliente desistiu\nem qualquer etapa]) --> L1

    L1["**1. Consultar atendimento atual**\nGET /api/v1/services/{id}"] -->|200 OK| L2

    L2["**2. Registrar perda com motivo**\nPATCH /api/v1/services/{id}/stage\n\n{\n  stage: 'lost',\n  lost_reason: 'Cliente desistiu'\n}"] --> L2R{Resposta}

    L2R -->|200 OK| Lost([💔 LOST — Estado terminal\natendimento encerrado])
    L2R -->|422 Unprocessable\nlost_reason ausente| ERR1([❌ Informe o motivo\nde perda obrigatório])
    L2R -->|422 Unprocessable\netapa terminal won/lost| ERR2([❌ Estado imutável\nnão é possível alterar])
    L2R -->|423 Locked\ntag sistema 'closed'| ERR3([❌ Atendimento bloqueado\npor etiqueta 'closed'])
```

---

## J3 — Rollback de etapa

```mermaid
flowchart TD
    Start([↩️ Atendimento avançou cedo\nciente precisa voltar]) --> R1

    R1["**1. Confirmar etapa atual**\nGET /api/v1/services/{id}\n\n➜ stage atual: 'proposal'"] -->|200 OK| R2

    R2["**2. Reverter para etapa anterior**\nPATCH /api/v1/services/{id}/stage\n\n{\n  stage: 'visit',\n  comment: 'Cliente quer rever o imóvel'\n}"] --> R2R{Resposta}

    R2R -->|200 OK\nstage=visit| R3
    R2R -->|422 Unprocessable\netapa terminal won/lost| ERR1([❌ Estados terminais\nnão aceitam rollback])
    R2R -->|422 Unprocessable\ncorretor desativado| ERR2([❌ Reatribuir antes\nde qualquer transição])

    R3["**3. Confirmar rollback**\nGET /api/v1/services/{id}\n\n➜ stage agora: 'visit'\n➜ transição registrada no timeline"] --> Done([✅ Rollback concluído\ntransição auditada])
```

---

## J4 — Gestor visualiza, filtra e reatribui atendimentos

```mermaid
flowchart TD
    Start([👔 Gestor / Owner\nprecisa de visão da equipe]) --> M1

    M1["**1. Listar por pendência**\nGET /api/v1/services?ordering=pendency\n\n➜ sem interação há mais tempo primeiro"] -->|200 OK| M2

    M2["**2. Resumo do kanban**\nGET /api/v1/services/summary\n\n➜ contadores por etapa"] -->|200 OK| M3

    M3{Identificou\ncorretor sobrecarregado?}
    M3 -->|Sim| M4
    M3 -->|Não, revisar por corretor| M3b

    M3b["**3a. Filtrar por corretor e etapa**\nGET /api/v1/services?agent_id={id}&stage=in_service\n\n➜ atendimentos do corretor específico"] -->|200 OK| M4

    M4["**4. Reatribuir atendimento**\nPATCH /api/v1/services/{id}/reassign\n\n{\n  new_agent_id: Y,\n  reason: 'Balanceamento de carga'\n}"] --> M4R{Resposta}

    M4R -->|200 OK| Done([✅ Atendimento reatribuído\nnovo corretor responsável])
    M4R -->|403 Forbidden\nCorretor tentou reatribuir| ERR1([❌ Apenas Owner/Manager\npodem reatribuir])
    M4R -->|409 Conflict\nestado terminal won/lost| ERR2([❌ Reatribuição bloqueada\nem estados terminais])
    M4R -->|422 Unprocessable\nnew_agent_id inativo| ERR3([❌ Corretor alvo\ndesativado ou inválido])

    note1["⚠️ Isolamento multi-tenancy:\nGestor A nunca enxerga\natendimentos da Imobiliária B"]
```

---

## J5 — Filtros e busca no pipeline

```mermaid
flowchart TD
    Start([🔍 Precisa encontrar\natendimentos específicos]) --> F0{Tipo de busca}

    F0 -->|Por nome / telefone / email| F1
    F0 -->|Por filtros combinados| F2
    F0 -->|Por pendência| F3
    F0 -->|Atendimentos órfãos| F4

    F1["**Busca livre**\nGET /api/v1/services?q=João\n\n➜ nome, telefone ou e-mail\n   do cliente"] -->|200 OK| Result([📋 Lista de atendimentos])

    F2["**Filtros combinados**\nGET /api/v1/services\n  ?operation_type=rent\n  &stage=visit\n  &is_pending=true\n\n➜ locações em visita com pendência"] -->|200 OK| Result

    F3["**Ordenação por pendência**\nGET /api/v1/services?ordering=pendency\n\n➜ mais antigo sem interação\n   primeiro"] -->|200 OK| Result

    F4["**Atendimentos sem corretor ativo**\nGET /api/v1/services?orphan_agent=true\n\n➜ FR-024a: corretor foi desativado"] -->|200 OK| Result

    Result --> F5{Encontrou o\natendimento?}
    F5 -->|Sim| F6["GET /api/v1/services/{id}\n\nDetalhes completos"]
    F5 -->|Não| F0
```

---

## J6 — Etiquetas e origens configuráveis

```mermaid
flowchart TD
    Start([⚙️ Owner / Manager\nprecisa configurar etiquetas e origens]) --> TAB{O que configurar?}

    TAB -->|Origens de captação| S1
    TAB -->|Etiquetas| T1

    S1["**1. Listar origens existentes**\nGET /api/v1/service-sources"] -->|200 OK| S2

    S2{Precisa criar\nnova origem?}
    S2 -->|Não| Done1([✅ Origem disponível\nselecionar ao criar atendimento])
    S2 -->|Sim| S3

    S3["**2. Criar nova origem**\nPOST /api/v1/service-sources\n\n{\n  name: 'WhatsApp',\n  code: 'whatsapp'\n}"] -->|201 Created| Done1

    T1["**1. Listar etiquetas existentes**\nGET /api/v1/service-tags"] -->|200 OK| T2

    T2{Precisa criar\nnova etiqueta?}
    T2 -->|Não| T4
    T2 -->|Sim| T3

    T3["**2. Criar nova etiqueta**\nPOST /api/v1/service-tags\n\n{\n  name: 'Follow Up',\n  color: '#FF6B35'\n}"] -->|201 Created| T4

    T4["**3. Associar etiqueta ao atendimento**\nPUT /api/v1/services/{id}\n\n{ tag_ids: [tag_id] }"] -->|200 OK| T5

    T5{Etiqueta\nobsoleta?}
    T5 -->|Sim| T6
    T5 -->|Não| Done2([✅ Etiqueta aplicada])

    T6["**4. Arquivar etiqueta (soft delete)**\nDELETE /api/v1/service-tags/{id}\n\n➜ histórico preservado\n   atendimentos existentes mantêm a tag"] -->|200 OK| Done2

    note1["⚠️ Isolamento: Etiquetas e origens\nda Imobiliária A não aparecem\npara a Imobiliária B"]
```

---

## J7 — Múltiplos telefones e deduplicação de cliente

```mermaid
flowchart TD
    Start([📱 Atendimento com\nmúltiplos contatos do cliente]) --> P1

    P1["**1. Criar atendimento com múltiplos telefones**\nPOST /api/v1/services\n\n{\n  client: {\n    name: 'João Silva',\n    phones: [\n      { type: 'mobile', number: '11999990001' },\n      { type: 'whatsapp', number: '11999990002' }\n    ]\n  },\n  operation_type: 'rent'\n}"] --> P1R{Deduplicação}

    P1R -->|✅ Parceiro novo\n201 Created| P2
    P1R -->|✅ Telefone único encontrado\n201 Created — parceiro reutilizado| P3
    P1R -->|❌ Telefone ambíguo\n409 Conflict + candidate_ids| ERR1

    P2["**2. Verificar telefones gravados**\nGET /api/v1/services/{id}\n\n➜ client.phones com todos os contatos\n   gravados em partner.phone_ids"] --> Done([✅ Atendimento criado\nclient.id vinculado])

    P3["Mesmo client.id reutilizado\n(FR-022a: deduplicação por telefone)\n\nGET /api/v1/services/{id}"] --> Done

    ERR1(["❌ 409 — Dois parceiros com\no mesmo número (FR-022b)\n\n→ Retorna candidate_ids\n   para resolução manual"])
    ERR1 --> P4["**Resolução manual**\nPOST /api/v1/services\n\n{ client: { id: <partner_id_correto> } }"] --> Done

    note1["FR-022c: Conflito telefone vs e-mail\n→ sistema prefere telefone"]
```

---

## J8 — Atendimento com corretor desativado (Orphan Agent)

```mermaid
flowchart TD
    Start([⚠️ Corretor responsável\nfoi desativado no sistema]) --> O1

    O1["**1. Localizar atendimentos órfãos**\nGET /api/v1/services?orphan_agent=true\n\n➜ FR-024a: is_orphan_agent=true"] -->|200 OK| O2

    O2["**2. Confirmar estado do atendimento**\nGET /api/v1/services/{id}\n\n➜ is_orphan_agent: true\n   Qualquer transição de etapa bloqueada"] --> O3

    O3{Tentar avançar etapa\nsem reatribuir?}
    O3 -->|Sim| ERR1([❌ 422 Unprocessable\n'Corretor desativado — reatribua\nantes de qualquer transição'])
    O3 -->|Não, reatribuir primeiro| O4

    O4["**3. Reatribuir para corretor ativo**\nPATCH /api/v1/services/{id}/reassign\n\n{\n  new_agent_id: Z\n}"] --> O4R{Resposta}

    O4R -->|200 OK\nis_orphan_agent=false| O5
    O4R -->|403 Forbidden\ncorretor tentou reatribuir| ERR2([❌ Apenas Owner/Manager\npodem reatribuir])
    O4R -->|422 Unprocessable\nnew_agent_id inativo| ERR3([❌ Novo corretor\ntambém está desativado])

    O5["**4. Retomar o pipeline**\nPATCH /api/v1/services/{id}/stage\n\n{ stage: '...' }"] -->|200 OK| Done([✅ Atendimento desbloqueado\ntransições normais restauradas])
```

---

## Resumo de Erros por Endpoint

| Endpoint | Código | Causa |
|---|---|---|
| `POST /api/v1/services` | 409 | Mesmo cliente + operação + corretor com atendimento ativo |
| `POST /api/v1/services` | 409 | Telefone ambíguo — dois parceiros com mesmo número |
| `PATCH /services/{id}/stage` | 422 | `lost_reason` ausente na transição para `lost` |
| `PATCH /services/{id}/stage` | 422 | Gate `proposal`: sem `property_ids` vinculado |
| `PATCH /services/{id}/stage` | 422 | Gate `formalization`: sem proposta aceita |
| `PATCH /services/{id}/stage` | 422 | Corretor desativado (`is_orphan_agent=true`) |
| `PATCH /services/{id}/stage` | 422 | Estado terminal (`won`/`lost`) — imutável |
| `PATCH /services/{id}/stage` | 423 | Etiqueta de sistema `closed` trava transições |
| `PATCH /services/{id}/reassign` | 403 | Corretor tentou reatribuir (precisa Owner/Manager) |
| `PATCH /services/{id}/reassign` | 409 | Atendimento em estado terminal (`won`/`lost`) |
| `DELETE /api/v1/service-tags/{id}` | 404 | Corretor fora do escopo (anti-enumeração) |
| Qualquer endpoint autenticado | 404 | Atendimento fora do escopo do corretor (anti-enumeração) |
