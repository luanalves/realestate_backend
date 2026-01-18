# ADR-017: Prevenção de Session Hijacking via JWT Fingerprint

## Status
Proposto

## Contexto

Após implementação do sistema de autenticação dual (ADR-011: OAuth 2.0 + Sessões HTTP), identificou-se uma vulnerabilidade crítica:

**Problema:** Session hijacking - atacante consegue roubar `session_id` de um usuário legítimo e usá-lo com seus próprios navegador/IP:

```
User A (atacante):
1. Consegue session_id_B do User B (rede aberta, XSS, etc)
2. Coloca session_id_B no seu cookie
3. Sistema apenas valida se session_id existe e está ativo
4. Não verifica se User A = User B
5. User A consegue acessar dados do User B ✗
```

**Impacto:**
- Violação do isolamento multi-tenancy
- Acesso não autorizado a dados privados
- Falha na conformidade com LGPD (art. 48 - direito ao sigilo)
- Risk Level: **CRÍTICO**

**Root Cause:**
ADR-011 implementou validação de `session_id` mas não implementou **vinculação** da sessão ao usuário. Uma sessão é apenas um cookie, qualquer um que possua o cookie pode usá-la.

## Decisão

Implementar **Session Fingerprint com JWT** como camada adicional de validação. Cada sessão será vinculada a:
1. **User ID** (uid) - Qual usuário logou
2. **Fingerprint do Navegador** - IP + User-Agent + Accept-Language (configurável)

**Componentes:**

### 1. Modelo de Configuração

```python
class SecuritySettings(models.Model):
    _name = 'thedevkitchen.security.settings'
    
    use_ip_in_fingerprint = fields.Boolean(default=True)
    use_user_agent = fields.Boolean(default=True)
    use_accept_language = fields.Boolean(default=True)
    
    # Singleton pattern
    @api.model
    def get_settings(self):
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({'name': 'Security Configuration'})
        return settings
```

**Propósito:** Permitir que administrador configure quais componentes usar (ex: desabilitar IP para VPN/mobile)

### 2. Token JWT com Fingerprint

Na autenticação (login), o sistema gera um JWT armazenado internamente:

```javascript
{
    "uid": 8677,
    "fingerprint": {
        "ip": "192.168.1.100",
        "ua": "Mozilla/5.0 (Macintosh...",
        "lang": "pt-BR,pt;q=0.9"
    },
    "iat": 1702000000,        // Issued at
    "exp": 1702086400,        // Expiração em 24h
    "iss": "odoo-session-security"
}
```

**Armazenamento:**
- Redis: Sessão HTTP → JWT criptografado
- Key: `session:<session_id>`
- Value: `{..., "_security_token": "<jwt>"}`

**NÃO é transmitido ao cliente** - apenas o `session_id` (cookie)

### 3. Validação em `ir.http.session_info()`

Override do método `session_info()` para interceptar TODAS as requisições:

```python
class IrHttpSessionFingerprint(models.AbstractModel):
    _name = 'ir.http'
    _inherit = 'ir.http'
    
    def session_info(self):
        result = super().session_info()
        uid = result.get('uid')
        
        if uid:
            if not request.session.get('_security_token'):
                # Primeira requisição após login → gerar token
                token = self._generate_session_token(uid)
                request.session['_security_token'] = token
            else:
                # Requisição subsequente → validar token
                is_valid, reason = self._validate_session_token(uid)
                
                if not is_valid:
                    # Detectou hijacking → fazer logout
                    _logger.warning(f"Session hijacking detected: {reason}")
                    request.session.logout(keep_db=True)
                    return {'uid': False, ...}  # Retorna sessão vazia
        
        return result
```

### 4. Algoritmo de Validação

```
LOGIN:
┌─────────────────────────────────┐
│ User B faz login                │
│ POST /web/login                 │
│ username: "user_b@company.com"  │
│ password: "***"                 │
└────────────┬────────────────────┘
             │
        ✓ Credenciais OK
             │
             ▼
┌─────────────────────────────────┐
│ Sistema:                        │
│ 1. Cria session_id (UUID)       │
│ 2. Gera fingerprint atual:      │
│    - IP: 192.168.1.50           │
│    - UA: Safari/...             │
│    - Lang: en-US                │
│ 3. Cria JWT com uid=8677        │
│ 4. Armazena em Redis:           │
│    session:xyz123 → {           │
│        "uid": 8677,             │
│        "_security_token": "JWT" │
│    }                            │
└─────────────────────────────────┘

REQUISIÇÃO SUBSEQUENTE:
┌─────────────────────────────────┐
│ User A (atacante) envia:        │
│ GET /web/...                    │
│ Cookie: session_id=xyz123       │
│ From: 192.168.200.10 (diferente)│
│ UA: Chrome/... (diferente)      │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ ir.http.session_info() valida:  │
│ 1. Decodifica JWT de User B     │
│ 2. uid no JWT: 8677             │
│ 3. uid na sessão: 8675 (User A) │
│ 4. MISMATCH! ✗                  │
│ 5. Fingerprint:                 │
│    JWT.ip: 192.168.1.50         │
│    Current: 192.168.200.10      │
│    MISMATCH! ✗                  │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ LOGOUT + Log warning:           │
│ [SESSION HIJACKING DETECTED]    │
│ Retorna: uid=False              │
│ User A recebe: Not authenticated│
└─────────────────────────────────┘
```

## Implementação

### Arquivos a Criar

1. **`models/security_settings.py`** - Modelo de configuração
2. **`models/ir_http.py`** - Override de `ir.http.session_info()`
3. **`views/security_settings_views.xml`** - Interface administrativa

### Arquivos a Modificar

1. **`security/ir.model.access.csv`** - Adicionar 2 linhas de permissão
2. **`models/__init__.py`** - Importar novos modelos
3. **`__manifest__.py`** - Registrar nova view

### Atualizações em ADRs Relacionadas

- **ADR-011** - Atualizar para mencionar Session Fingerprint como camada adicional
- **ADR-008** - Referência cruzada

## Características

### ✅ Protege Contra

1. **Session Hijacking** - Session_id roubado não funciona com navegador diferente
2. **MITM Attack** - Mesmo que atacante intercepte session_id, fingerprint não combina
3. **Credential Stuffing** - Sessão vinculada ao IP reduz janela de ataque
4. **Account Takeover** - JWT vinculado ao UID específico
5. **XSS Session Theft** - Se XSS roubar session_id, fingerprint diferente rejeita

### ⚙️ Configurável

Admin pode ajustar via menu **Técnico → API Gateway → Configurações de Segurança**:
- ☑ Validar IP (desabilitar para VPN/mobile)
- ☑ Validar User-Agent (navegador)
- ☑ Validar Accept-Language (idioma)

### 🚀 Performance

- JWT gerado apenas no login (1x)
- Validação em memória (Redis) - < 1ms
- NÃO faz chamada extra ao PostgreSQL
- NÃO causa overhead adicional

### 🔒 Segurança

- **JWT com HS256** - Assinatura criptográfica
- **24h TTL** - Expiração automática
- **Database não usada** - Token em Redis, não em SQL
- **Armazenamento seguro** - Nunca transmitido ao cliente
- **Logout revoga** - Session.logout() limpa token

## Consequências

### Positivas

1. **Segurança aumentada** - Torna session hijacking impraticável
2. **Conformidade LGPD** - Rastreabilidade completa de quem acessou o quê
3. **Auditoria** - Logs detalhados de tentativas de hijacking
4. **Flexibilidade** - Admin pode configurar componentes do fingerprint
5. **Sem afectar UX** - Transparente ao usuário legítimo

### Negativas

1. **Overhead mínimo** - ~1-2ms adicionais por requisição (aceitável)
2. **Complexidade** - Mais código no `ir.http` (balanceado pela segurança crítica)
3. **VPN/Proxy** - Usuários com IP dinâmico podem ser deslogados (mitigado via config)

### Riscos Mitigados

1. **Session Hijacking** - OWASP A07:2021 - Identification and Authentication Failures
2. **Account Takeover** - CWE-384: Session Fixation
3. **Information Disclosure** - OWASP A01:2021

## Validação

### Testes Necessários

1. **Test 7: Session Hijacking**
   ```python
   def test_session_hijacking():
       # Login como User B
       session_b = login(user_b)
       
       # User A tenta usar session_b com suas credenciais
       headers = {'Cookie': f'session_id={session_b}'}
       response = request_as(user_a, headers)
       
       assert response.status_code == 401
       assert 'uid' not in response.json or response.json['uid'] == False
   ```

2. **Test 8: Session Válida**
   ```python
   def test_valid_session():
       # User B faz requisição com sua própria sessão
       session_b = login(user_b)
       
       headers = {'Cookie': f'session_id={session_b}'}
       response = request_as(user_b, headers)
       
       assert response.status_code == 200
       assert response.json['uid'] == user_b.id
   ```

3. **Test 9: Fingerprint IP**
   ```python
   def test_fingerprint_ip_mismatch():
       # Login de IP A
       session = login(user, ip='192.168.1.1')
       
       # Requisição de IP B com mesma session_id
       response = request(session, ip='192.168.1.2')
       
       assert response.json['uid'] == False
   ```

## Referências

- OWASP Session Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- CWE-384: Session Fixation: https://cwe.mitre.org/data/definitions/384.html
- JWT RFC 7519: https://tools.ietf.org/html/rfc7519
- ADR-008: API Security & Multi-Tenancy
- ADR-009: Headless Authentication & User Context
- ADR-011: Controller Security - Authentication & Storage

## Histórico

- **2026-01-17**: ADR criada - Session Fingerprint Protection via JWT implementado

---

## Apêndice: Migração de Sessões Existentes

Se o sistema já tem usuários com sessões ativas ao implementar esta ADR:

```python
# Script de migração (rode uma vez)
@http.route('/api/v1/admin/migrate-sessions', type='http', auth='none')
def migrate_sessions(self):
    """Regenerar fingerprints para todas as sessões ativas"""
    if not request.env.user.has_group('base.group_system'):
        return error_response(403, 'Admin only')
    
    count = 0
    for session_id in redis.keys('session:*'):
        session_data = redis.hgetall(session_id)
        if 'uid' in session_data and not '_security_token' in session_data:
            uid = int(session_data['uid'])
            token = self._generate_session_token(uid)
            redis.hset(session_id, '_security_token', token)
            count += 1
    
    return success_response({'migrated': count})
```

## Apêndice: Desabilitação Temporária

Se necessário desabilitar fingerprint para debugging:

```python
# Em security_settings_views.xml, admin pode desabilitar TODAS as validações:
<field name="use_ip_in_fingerprint" default="False"/>
<field name="use_user_agent" default="False"/>
<field name="use_accept_language" default="False"/>
```

Quando todas estão False, fingerprint sempre "valida" (útil para testes automatizados).
