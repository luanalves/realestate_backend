# ADR 009: Autenticação Headless com Contexto de Usuário

## Status

Aceito (revisado Abr/2026)

## Contexto

O sistema opera com **autenticação dual** (ADR-011):

- **Camada de aplicação (serviço-a-serviço):** OAuth 2.0 Client Credentials gerenciado exclusivamente pelo Kong API Gateway. O frontend **nunca vê nem envia** este token.
- **Camada de usuário (sessão):** Login do usuário retorna um `session_id` que o frontend usa em todos os requests subsequentes via header `X-Openerp-Session-Id`.

O Kong **remove** qualquer `Authorization` enviado pelo cliente e **injeta** o Bearer token de serviço antes de encaminhar ao Odoo. Isto garante que:

1. Nenhum `client_secret` é exposto ao browser
2. O Odoo sempre recebe um token válido de serviço (JWT validado por `@require_jwt`)
3. O contexto do usuário é transportado pelo `session_id` (validado por `@require_session`)

**Requisitos atendidos:**

1. Frontend autentica com email/senha e recebe `session_id`
2. Backend identifica o usuário via `session_id` (Redis → `thedevkitchen.api.session`)
3. Isolamento multi-tenant garantido pelo header `X-Company-ID` (`@require_company`)
4. Proteção contra session hijacking via JWT fingerprint armazenado no lado do servidor (ADR-017)

## Decisão

**Fluxo de autenticação adotado (implementado):**

```
1. Frontend → POST /api/v1/users/login
   Body: { "email": "user@empresa.com", "password": "***" }
   (SEM Authorization — Kong injeta o Bearer de serviço)

2. Kong injeta: Authorization: Bearer <service_token>
   Kong encaminha para Odoo

3. Odoo:
   - @require_jwt valida o service token
   - Autentica credenciais via request.session.authenticate()
   - Cria registro em thedevkitchen.api.session
   - Gera security_token (JWT fingerprint — ADR-017), armazenado no servidor
   - Retorna { session_id, user }

4. Frontend armazena em localStorage:
   - session_id  (chave: STORAGE_KEYS.SESSION_ID)
   - company_id  (chave: STORAGE_KEYS.COMPANY_ID, extraído de user.current_company.id)
   - user        (chave: STORAGE_KEYS.USER, dados de exibição)

5. Todas as requisições autenticadas subsequentes:
   X-Openerp-Session-Id: <session_id>
   X-Company-ID: <company_id>
   (SEM Authorization — Kong continua injetando)

6. Odoo valida com os três decoradores obrigatórios:
   @require_jwt      → valida Bearer injetado pelo Kong
   @require_session  → valida session_id + JWT fingerprint (anti-hijacking)
   @require_company  → valida X-Company-ID e aplica isolamento de dados

7. Logout:
   POST /api/v1/users/logout
   → Odoo desativa thedevkitchen.api.session (is_active=False)
   → Frontend remove session_id, company_id e user do localStorage
```

### Transmissão do session_id

O `@require_session` aceita o `session_id` nas seguintes fontes (por prioridade):

| Prioridade | Fonte                    | Formato                     |
| ---------- | ------------------------ | --------------------------- |
| 1ª         | Query param / form param | `?session_id=...`           |
| 2ª         | JSON body                | `{ "session_id": "..." }`   |
| 3ª         | Header HTTP              | `X-Openerp-Session-Id: ...` |
| 4ª         | Cookie                   | `session_id=...`            |

**Padrão recomendado para SPA (Web):** header `X-Openerp-Session-Id`.

### Responsabilidades por camada

| Responsabilidade                 | Quem                                       |
| -------------------------------- | ------------------------------------------ |
| Token OAuth (client_credentials) | Kong — exclusivo, nunca exposto ao browser |
| Autenticação do usuário          | Odoo — `request.session.authenticate()`    |
| Armazenar session_id             | Frontend — `localStorage`                  |
| Enviar session_id                | Frontend — header `X-Openerp-Session-Id`   |
| Enviar company_id                | Frontend — header `X-Company-ID`           |
| Validar sessão + fingerprint     | Odoo — `@require_session` + ADR-017        |
| Isolamento multi-tenant          | Odoo — `@require_company`                  |

### Segurança

#### Auditoria de Sessões

- Logar TODAS as tentativas de login (sucesso e falha)
- Registrar IP, User-Agent, timestamp
- Permitir user ver sessões ativas e revogar remotamente
- Alertar user sobre login de novo dispositivo/localização

## Regras de Implementação

### ✅ SEMPRE (Frontend Web)

- Armazenar `session_id` retornado pelo login em `localStorage`
- Armazenar `company_id` (`user.current_company.id`) em `localStorage`
- Enviar `X-Openerp-Session-Id: <session_id>` em toda requisição autenticada
- Enviar `X-Company-ID: <company_id>` em toda requisição autenticada
- Limpar `session_id`, `company_id` e `user` do localStorage no logout e no 401

### ❌ NUNCA (Frontend Web)

- Enviar header `Authorization` — o Kong o remove e injeta o próprio token
- Armazenar ou lidar com tokens OAuth (client_id / client_secret)
- Aceitar `user_id` ou `company_id` de outra fonte sem validação
- Reutilizar `session_id` de outra sessão/usuário

### ✅ SEMPRE (Backend Odoo — controllers)

- Aplicar os três decoradores: `@require_jwt` + `@require_session` + `@require_company`
- Logar tentativas de login (sucesso e falha) com IP e User-Agent via `AuditLogger`
- Desativar `thedevkitchen.api.session` no logout (`is_active=False`)
- Invalidar sessões anteriores do usuário ao fazer novo login

### ❌ NUNCA (Backend Odoo)

- Aceitar `user_id` ou `company_id` do request body (sempre extrair da sessão validada)
- Criar endpoint de login sem `@require_jwt` (token de serviço Kong obrigatório)
- Retornar mensagem diferente para "usuário não existe" vs "senha incorreta" (anti-enumeração)

## Consequências

### Positivas

- **Contexto de usuário em todas as requisições** — `request.env.user` representa usuário real via sessão Odoo
- **Token de serviço nunca exposto ao browser** — gerenciado exclusivamente pelo Kong
- **Revogação imediata** — desativar `thedevkitchen.api.session` invalida o acesso instantaneamente
- **Proteção anti-hijacking** — JWT fingerprint (ADR-017) vincula sessão ao IP/UA do browser
- **Multi-tenancy funcional** — isolamento garantido por `@require_company`
- **Auditoria completa** — todos os acessos registrados com usuário real, IP e timestamps

### Negativas

- **session_id em localStorage** — sujeito a XSS (mitigado pelo fingerprint ADR-017 e HTTPS obrigatório)
- **Sessão stateful** — Redis deve estar disponível para validação das sessões
- **TTL de sessão** — expiração de 2h de inatividade pode surpreender usuários em fluxos longos

### Alternativas Consideradas e Rejeitadas

| Alternativa                        | Motivo da rejeição                                                                                                     |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Password Grant JWT para o frontend | Expõe token JWT ao browser sem benefício adicional; `session_id` já provê contexto de usuário com proteção equivalente |
| HttpOnly cookie para session_id    | Kong remove/sobrescreve headers; header explícito `X-Openerp-Session-Id` é mais confiável no contexto do API Gateway   |
| Authorization Code Flow            | Requer servidor OAuth separado — complexidade excessiva para MVP                                                       |

## Referências

- ADR-011: Decoradores obrigatórios (`@require_jwt`, `@require_session`, `@require_company`)
- ADR-017: Proteção anti-session-hijacking via JWT fingerprint
- ADR-008: Segurança de APIs e multi-tenancy
- `thedevkitchen_apigateway/middleware.py` — implementação de `require_session`
- `thedevkitchen_apigateway/controllers/user_auth_controller.py` — implementação do login
- `frontend/src/services/api.ts` — `buildHeaders()` com injeção de X-Openerp-Session-Id
- `frontend/src/services/authService.ts` — persistência de session_id no login/logout

- ADR-008: API Security Multi-Tenancy
