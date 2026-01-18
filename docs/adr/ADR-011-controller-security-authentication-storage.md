# ADR-011: Segurança de Controllers - Autenticação Dual e Armazenamento

## Status
Aceito

## Contexto

O projeto implementa APIs REST que precisam ser acessadas tanto por aplicações headless (mobile, SPAs) quanto pela interface web do Odoo. Isso requer:

- **Autenticação robusta** para aplicações externas via OAuth 2.0
- **Manutenção de contexto** do usuário através de sessões HTTP
- **Isolamento multi-tenancy** por empresa
- **Performance** através de cache distribuído
- **Auditoria completa** de todas as operações

A arquitetura tradicional do Odoo usa apenas sessões HTTP, mas aplicações modernas headless exigem autenticação stateless via tokens JWT. Precisávamos de uma solução que combinasse ambos os modelos sem comprometer a segurança.

## Decisão

### 1. Sistema de Autenticação Dual

Implementamos **dois mecanismos de autenticação complementares** que trabalham em conjunto:

#### 1.1 OAuth 2.0 com JWT (Autenticação da Aplicação)

**Propósito**: Autenticar aplicações externas e garantir que apenas clientes autorizados acessem a API.

**Implementação**:
- Módulo: `thedevkitchen_apigateway`
- Grant types suportados: `password`, `authorization_code`
- Tokens JWT com assinatura HS256
- Refresh tokens para renovação
- Scopes para controle granular de permissões

**Fluxo**:
```
1. Aplicação registra-se via OAuth Application
   → Recebe client_id e client_secret

2. Aplicação solicita token
   POST /oauth2/token
   grant_type=password&username=...&password=...&client_id=...
   
3. Recebe JWT access_token + refresh_token
   
4. Usa em todas as requisições
   Authorization: Bearer <jwt_token>
```

#### 1.2 Sessão HTTP (Contexto do Usuário)

**Propósito**: Manter estado do usuário, preferências, empresa ativa e contexto de execução.

**Implementação**:
- Armazenamento no Redis (DB index 1)
- Session ID via cookie HTTP
- TTL de 2 horas de inatividade
- Auto-renovação em cada requisição

**Fluxo**:
```
1. Usuário faz login
   POST /web/login ou POST /api/v1/auth/login
   
2. Odoo valida credenciais (PostgreSQL)
   
3. Gera session_id único (UUID)
   
4. Armazena no Redis com contexto completo
   
5. Retorna cookie
   Set-Cookie: session_id=...; HttpOnly; SameSite=Lax
```

### 2. Arquitetura de Armazenamento

#### 2.1 PostgreSQL (Persistência)

**Database**: `realestate`
**Porta**: `5432`

**Armazena**:
- `oauth.access_token` - Tokens OAuth e refresh tokens
- `oauth.application` - Aplicações OAuth registradas
- `res.users` - Dados de usuários
- `res.company` - Dados de empresas
- `auditlog.log` e `auditlog.log.line` - Logs de auditoria
- Todos os modelos de negócio (properties, agents, etc.)

**Estrutura da tabela oauth.access_token**:
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `token` | VARCHAR | Hash SHA256 do JWT |
| `user_id` | INTEGER | FK para res.users |
| `application_id` | INTEGER | FK para oauth.application |
| `expires` | TIMESTAMP | Data/hora de expiração |
| `scope` | VARCHAR | Permissões (read, write, etc.) |
| `refresh_token` | VARCHAR | Token para renovação |

#### 2.2 Redis (Cache e Sessões)

**Versão**: `7-alpine`
**Porta**: `6379`
**DB Index**: `1`
**Volume**: `odoo18-redis`

**Configuração**:
```
maxmemory: 256MB
maxmemory-policy: allkeys-lru
appendonly: yes (AOF)
```

**Armazena**:
1. **Sessões HTTP** (chave principal):
   ```
   Key: session:<session_id>
   Value: {
       "uid": 2,
       "login": "admin",
       "context": {
           "lang": "pt_BR",
           "tz": "America/Sao_Paulo",
           "allowed_company_ids": [1]
       },
       "company_id": 1,
       "last_activity": <timestamp>,
       "_security_token": "<jwt>"  // ← ADR-017: JWT fingerprint para prevenir hijacking
   }
   TTL: 7200s
   ```
   
   **Nota:** O campo `_security_token` (JWT com fingerprint) é adicionado pela ADR-017 como camada adicional de segurança contra session hijacking. Ver [ADR-017](ADR-017-session-hijacking-prevention-jwt-fingerprint.md) para detalhes.

2. **Cache ORM do Odoo**
3. **Cache de assets estáticos** (CSS, JS)
4. **Message bus** (notificações em tempo real)

### 3. Decoradores de Segurança Obrigatórios

Todos os endpoints de API **DEVEM** usar três decoradores:

```python
from odoo.addons.thedevkitchen_apigateway.decorators import (
    require_jwt,
    require_session,
    require_company
)

@http.route('/api/v1/endpoint', type='http', auth='none', 
            methods=['GET'], csrf=False, cors='*')
@require_jwt       # Valida JWT do Authorization header
@require_session   # Valida session_id do header/cookie/body
@require_company   # Valida X-Company-ID e aplica isolamento
def endpoint(self, **kwargs):
    # request.session.uid - ID do usuário
    # request.session.context - Contexto completo
    # Filtragem automática por company_id
    pass
```

**IMPORTANTE**: A transmissão de `session_id` depende do tipo de endpoint:
- **`type='http'`** (GET): session_id via header `X-Openerp-Session-Id` ou query string
- **`type='json'`** (POST/PUT): session_id no body JSON

O decorator `@require_session` suporta ambos os métodos automaticamente (ver [api-authentication.md](../api-authentication.md#session-id-transmission) para detalhes).

**Por que os três decoradores?**

| Decorador | O que valida | Fonte | Previne |
|-----------|--------------|-------|---------|
| `@require_jwt` | Token OAuth válido e não expirado | Header `Authorization` + PostgreSQL | Aplicações não autorizadas |
| `@require_session` | Session ID válido e ativo | Header/Cookie/Body + Redis | Session hijacking, perda de contexto |
| `@require_company` | Company ID válido e autorizado | Header `X-Company-ID` + PostgreSQL | Data leakage entre empresas |

**NÃO são redundantes**: JWT autentica a **aplicação externa**, session_id autentica o **usuário e seu contexto**, company_id garante **isolamento multi-tenancy**.

### 4. Endpoints Públicos (Exceção)

Endpoints que não requerem autenticação **DEVEM** ser marcados explicitamente:

```python
@http.route('/api/v1/health', type='http', auth='none', methods=['GET'])
# public endpoint - health check sem autenticação
def health_check(self, **kwargs):
    return Response(json.dumps({'status': 'healthy'}))
```

## Consequências

### Positivas

1. **Segurança em Camadas**
   - Dois fatores de autenticação independentes
   - Dificulta ataques de session hijacking e token theft
   - Auditoria completa via módulo `auditlog`

2. **Performance**
   - Redis cache reduz carga no PostgreSQL
   - Sessões em memória (< 1ms de acesso)
   - TTL automático evita limpeza manual

3. **Compatibilidade**
   - Aplicações headless usam JWT
   - Interface web usa sessões tradicionais
   - Ambos funcionam simultaneamente

4. **Multi-tenancy Robusto**
   - Isolamento garantido por `@require_company`
   - Impossível acessar dados de outra empresa
   - Validação em três camadas (JWT, sessão, company)

5. **Developer Experience**
   - Decoradores simples e declarativos
   - Contexto do usuário sempre disponível via `request.session`
   - Mensagens de erro claras

### Negativas

1. **Complexidade Adicional**
   - Desenvolvedores precisam entender dois sistemas
   - Três decoradores obrigatórios em cada endpoint
   - Mais pontos de falha possíveis

2. **Overhead de Validação**
   - Cada requisição valida JWT (PostgreSQL) + sessão (Redis)
   - ~2-5ms adicionais por requisição
   - Mitigado pelo cache do Redis

3. **Dependência do Redis**
   - Se Redis cair, todas as sessões são perdidas
   - Usuários precisam fazer login novamente
   - Mitigado por AOF persistence

4. **Manutenção de Tokens**
   - Tokens OAuth precisam ser renovados periodicamente
   - Limpeza de tokens expirados necessária (cron job)
   - Gestão de refresh tokens

### Riscos Aceitos

1. **Redis como SPOF**
   - Aceitável para ambiente atual
   - Futuramente: Redis Cluster ou Sentinel

2. **Expiração de Sessões**
   - 2 horas de inatividade pode frustrar usuários
   - Aceitável por razões de segurança
   - Configurável via `odoo.conf`

### Comandos de Monitoramento

**Verificar sessões no Redis**:
```bash
docker compose exec redis redis-cli
KEYS session:*
GET session:<id>
MONITOR  # Ver operações em tempo real
```

**Verificar tokens no PostgreSQL**:
```sql
docker compose exec db psql -U odoo -d realestate

SELECT t.token, u.login, a.name, t.expires, t.scope
FROM oauth_access_token t
JOIN res_users u ON t.user_id = u.id
JOIN oauth_application a ON t.application_id = a.id
WHERE t.expires > NOW()
ORDER BY t.create_date DESC;
```

**Verificar logs de auditoria**:
```sql
SELECT l.create_date, u.login, m.model, l.method, l.name
FROM auditlog_log l
JOIN res_users u ON l.user_id = u.id
JOIN ir_model m ON l.model_id = m.id
WHERE l.create_date > NOW() - INTERVAL '1 day'
ORDER BY l.create_date DESC;
```

## Referências

- [ADR-008: API Security & Multi-Tenancy](ADR-008-api-security-multi-tenancy.md)
- [ADR-009: Headless Authentication & User Context](ADR-009-headless-authentication-user-context.md)
- [ADR-017: Session Hijacking Prevention](ADR-017-session-hijacking-prevention-jwt-fingerprint.md) - Complementa este ADR com proteção contra session hijacking
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [Odoo External API Documentation](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)
- [Redis Session Management Best Practices](https://redis.io/docs/manual/keyspace/)

## Histórico

- **2025-12-13**: ADR criada - Sistema de autenticação dual implementado e documentado
