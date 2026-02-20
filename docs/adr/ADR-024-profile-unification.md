# ADR-024: Unificação de Perfis em Modelo Normalizado

## Status
Aceito

## Data
Original: 2026-02-19  
Última Atualização: 2026-02-20 (v2 - Adicionado property_owner como 10º tipo)

## Contexto

O sistema de gerenciamento imobiliário possui **10 perfis RBAC** definidos em ADR-019 (Owner, Director, Manager, Agent, Prospector, Receptionist, Financial, Legal, Portal, Property Owner), mas sua implementação no banco de dados era **inconsistente e não normalizada**:

### Problemas Identificados

**1. Implementação fragmentada:**
- **2 perfis** com tabelas dedicadas:
  - `real.estate.agent` (611 LOC, campos de negócio + cadastrais)
  - `real.estate.tenant` (35 LOC, apenas cadastrais)
- **8 perfis** apenas como `res.groups` do Odoo, sem dados cadastrais próprios

**2. Violação de multi-tenancy:**
- Tenant tinha `UNIQUE(document)` **global**, impedindo mesma pessoa em múltiplas empresas
- Agent tinha `UNIQUE(cpf, company_id)` corretamente (company-scoped), mas isolado

**3. Redundância de dados:**
- Feature 009 (invite flow) forçava **re-envio de dados cadastrais** na API de convite
- Nome, documento, email enviados duas vezes: no perfil e no convite
- Violação do princípio DRY (Don't Repeat Yourself)

**4. Inconsistência arquitetural:**
- Agent tinha 18 endpoints dedicados (`/api/v1/agents/*`)
- Tenant tinha API limitada
- Outros 7 perfis não tinham cadastro via API

**5. Violação de normalização (3NF):**
- Mesmos atributos (name, document, email, phone) duplicados em tabelas diferentes
- Risco de anomalias de atualização (atualizar em uma tabela, esquecer em outra)

### Referências

- **ADR-004**: Nomenclatura de módulos e tabelas (`thedevkitchen_` prefix)
- **ADR-008**: Segurança multi-tenancy (isolamento por `company_id`)
- **ADR-019**: Sistema RBAC com 10 perfis pré-definidos
- **KB-09**: Database Best Practices (enums > 5 items → lookup table, 3NF compliance)

## Decisão

### 1. Tabela Lookup para Tipos de Perfil

**Modelo**: `thedevkitchen.profile.type`  
**Tabela**: `thedevkitchen_profile_type`

```python
class ProfileType(models.Model):
    _name = 'thedevkitchen.profile.type'
    _description = 'Profile Type (Lookup Table for 10 RBAC Roles)'
    
    code = fields.Char(required=True, index=True)  # 'owner', 'agent', 'portal'
    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    is_active = fields.Boolean(default=True)
    odoo_group_id = fields.Many2one('res.groups')  # Link to Odoo security group
```

**Seed Data**: 10 registros fixos via `profile_type_data.xml`

**Motivo**: KB-09 §2.1 recomenda lookup table para enums > 5 items (extensibilidade, i18n, UI-friendly)

---

### 2. Tabela Unificada de Perfis

**Modelo**: `thedevkitchen.estate.profile`  
**Tabela**: `thedevkitchen_estate_profile`

```python
class EstateProfile(models.Model):
    _name = 'thedevkitchen.estate.profile'
    _description = 'Unified Profile (10 RBAC Types)'
    _sql_constraints = [
        ('unique_document_company_type',
         'UNIQUE(document, company_id, profile_type_id)',
         'Document must be unique per company and profile type')
    ]
    
    # Identificação
    name = fields.Char(required=True)
    document = fields.Char(required=True, index=True)  # CPF/CNPJ
    profile_type_id = fields.Many2one('thedevkitchen.profile.type', required=True)
    company_id = fields.Many2one('thedevkitchen.estate.company', required=True)
    partner_id = fields.Many2one('res.partner')  # Link to Odoo contact
    
    # Cadastrais
    email = fields.Char(required=True)
    phone = fields.Char()
    mobile = fields.Char()
    birthdate = fields.Date()
    
    # Controle
    active = fields.Boolean(default=True)
    created_at = fields.Datetime(default=fields.Datetime.now)
    updated_at = fields.Datetime()
    deactivation_date = fields.Datetime()
    deactivation_reason = fields.Text()
```

**Constraint compound unique**: Permite mesma pessoa (document) em:
- Múltiplas empresas (multi-tenancy)
- Múltiplos tipos de perfil na mesma empresa (ex: Agent + Owner)

---

### 3. Agent como Extensão de Negócio

**Modelo**: `real.estate.agent` (mantido)  
**Mudança**: Adicionar FK `profile_id`

```python
class Agent(models.Model):
    _name = 'real.estate.agent'
    
    profile_id = fields.Many2one('thedevkitchen.estate.profile', required=True)
    
    # Campos de negócio específicos (mantidos)
    creci = fields.Char()
    commission_percentage = fields.Float()
    hire_date = fields.Date()
    # ... 611 LOC de lógica de domínio
```

**Motivo**: Agent possui **lógica de negócio complexa** (comissões, CRECI, propriedades atribuídas). Mantê-lo como extensão preserva 611 LOC de domínio sem reescrever.

**Estratégia Phase 1**: `create()` override copia dados cadastrais de `profile` → `agent` (mantém compatibilidade com 18 endpoints existentes)

---

### 4. Tenant Absorvido como Profile Type

**Modelo**: `real.estate.tenant` (removido)  
**Substituição**: `profile_type='portal'` na tabela unificada

**Motivo**: Tenant tinha apenas 35 LOC, sem lógica de negócio. Seus dados cadastrais são idênticos aos de outros perfis.

**Migração**: 
- Registros de `real.estate.tenant` → `thedevkitchen.estate.profile` com `profile_type_id='portal'`
- FKs em `real.estate.lease` apontam para `profile_id`

---

### 5. Property Owner como 10º Profile Type (v2 - 2026-02-20)

**Problema Identificado**: Ambiguidade semântica entre `owner` (Company Owner) e Property Owner (cliente).

**Contexto**:
- `profile_type='owner'` originalmente definido para **Company Owner** (administrator da imobiliária)
- Feature 009 especificava que Agent pode convidar **Property Owner** (cliente dono do imóvel)
- Model `real.estate.property.owner` existia separadamente sem integração ao sistema de profiles

**Solução**: Adicionar `profile_type='property_owner'` como 10º tipo (level=external)

**Distinção Clara**:

| Conceito | Profile Type | Modelo | Descrição |
|----------|--------------|--------|-----------|
| **Company Owner** | `owner` | `res.users` + grupo | Dono/sócio da imobiliária (admin) |
| **Property Owner** | `property_owner` | `thedevkitchen.estate.profile` | Cliente dono do imóvel |

**Migração Futura** (Phase 2):
- Migrar registros de `real.estate.property.owner` → `thedevkitchen.estate.profile` com `profile_type_id='property_owner'`
- Atualizar FK `real.estate.property.owner_id` → apontar para `profile_id`
- Feature 009: Agent convida `property_owner` (não `owner`)

**Referências**:
- Investigation Report: `.investigate-property-owner.md`
- DEC-011 (Feature 007): Company Owner vs Property Owner terminology
- Migration: `migrations/18.0.3.0.0/README.md`

---

### 6. API Unificada

**Endpoint**: `POST /api/v1/profiles`

```json
{
  "name": "João da Silva",
  "document": "12345678901",
  "email": "joao@example.com",
  "phone": "+5511999998888",
  "birthdate": "1990-01-01",
  "company_id": 1,
  "profile_type": "agent"  // ← Discriminador de tipo
}
```

**RBAC Authorization Matrix**:
- **Owner** → pode criar todos os 10 tipos
- **Manager** → pode criar 5 tipos operacionais (agent, prospector, receptionist, financial, legal)
- **Agent** → pode criar 2 tipos externos (property_owner, portal)

**Implementação**: `quicksol_estate/controllers/profile_api.py`

---

### 7. Integração com Feature 009 (Invite Flow)

**Fluxo two-step**:
1. **Criar perfil** via `POST /api/v1/profiles` (dados cadastrais completos)
2. **Convidar para acesso** via `POST /api/v1/users/invite` (referencia `profile_id`, apenas dados de autenticação)

**Antes** (Feature 009 standalone):
```json
POST /api/v1/users/invite
{
  "name": "João da Silva",         // Redundante
  "document": "12345678901",       // Redundante
  "email": "joao@example.com",     // Redundante
  "profile": "agent"
}
```

**Depois** (Feature 009 + Feature 010):
```json
POST /api/v1/profiles
{ "name": "João", "document": "123...", "profile_type": "agent" }
→ Response: { "id": 42 }

POST /api/v1/users/invite
{ "profile_id": 42 }  // ← Apenas referência, sem dados duplicados
```

---

## Consequências

### Positivas

**1. Consistência arquitetural:**
- ✅ Todos os 10 perfis RBAC possuem cadastro normalizado
- ✅ Mesma estrutura de dados, mesma API, mesmas regras de validação

**2. Multi-tenancy correto:**
- ✅ Compound unique `(document, company_id, profile_type_id)` permite mesma pessoa em múltiplas empresas
- ✅ Isolamento de dados garantido por `company_id` em todos os perfis

**3. DRY (Don't Repeat Yourself):**
- ✅ Feature 009 (invite) referencia `profile_id`, sem re-envio de dados cadastrais
- ✅ Atualização de email/telefone em um lugar só

**4. 3NF Compliance:**
- ✅ Eliminação de redundância (document, name, email não duplicados)
- ✅ Prevenção de anomalias de atualização

**5. Extensibilidade:**
- ✅ Novo tipo de perfil = inserir registro em `profile_type` (sem migração de schema)
- ✅ Campos específicos de negócio = criar extensão como `agent` (FK para `profile`)

**6. Testabilidade:**
- ✅ 8 testes E2E (T21-T28) validam CRUD, RBAC, multi-tenancy, integrate Feature 009
- ✅ Constraint compound unique testado com dados reais (3 empresas, 10 tipos)

---

### Negativas

**1. Complexidade de migração:**
- ⚠️ Dados de tenant/agent precisam ser movidos para tabela unificada
- ⚠️ FKs em lease/sale precisam ser redirecionadas
- **Mitigação**: Ambiente de desenvolvimento (não produção), remoção direta aceita

**2. Agent com campos duplicados temporariamente:**
- ⚠️ Phase 1 mantém `agent.name`, `agent.document` sincronizados com `profile.*`
- ⚠️ Override de `write()` necessário para manter consistência
- **Mitigação**: Phase 2 removerá campos duplicados, 18 endpoints de agent usarão `profile_id`

**3. Queries podem ficar mais complexas:**
- ⚠️ Antes: `SELECT * FROM real_estate_agent`
- ⚠️ Depois: `SELECT * FROM thedevkitchen_estate_profile JOIN real_estate_agent ON profile_id`
- **Mitigação**: Performance não é problema (volume < 1000 perfis/empresa), índices em FKs

**4. Alteração de contratos de API pré-existentes:**
- ⚠️ Endpoints de tenant (`/api/v1/tenants/*`) serão descontinuados
- ⚠️ Clientes precisam migrar para `/api/v1/profiles?profile_type=portal`
- **Mitigação**: Documentação de migração, versioning de API (v2 no futuro)

---

## Implementação

### Arquivos Criados/Modificados

**Models** (`18.0/extra-addons/quicksol_estate/models/`):
- ✅ `profile_type.py` (novo) — Lookup table com 10 tipos
- ✅ `profile.py` (novo) — Tabela unificada com 230 LOC
- ✅ `agent.py` (modificado) — Adicionado FK `profile_id`, sincronização

**Controllers** (`18.0/extra-addons/quicksol_estate/controllers/`):
- ✅ `profile_api.py` (novo) — 530 LOC, 5 endpoints REST
  * POST /api/v1/profiles (create com RBAC matrix)
  * GET /api/v1/profiles (list com paginação)
  * GET /api/v1/profiles/<id> (detail)
  * PUT /api/v1/profiles/<id> (update, campos imutáveis)
  * DELETE /api/v1/profiles/<id> (soft delete)
  * GET /api/v1/profile-types (lista tipos disponíveis)

**Data** (`18.0/extra-addons/quicksol_estate/data/`):
- ✅ `profile_type_data.xml` (novo) — Seed data com 10 registros

**Security** (`18.0/extra-addons/quicksol_estate/security/`):
- ✅ `ir.model.access.csv` (modificado) — Permissões CRUD por grupo
- ✅ `record_rules.xml` (novo) — Isolamento multi-tenant

**Tests** (`integration_tests/`):
- ✅ T21: `test_us10_s1_create_profile.sh` — CRUD creation
- ✅ T22: `test_us10_s2_list_profiles.sh` — Pagination, filters
- ✅ T23: `test_us10_s3_update_profile.sh` — Update, immutable fields
- ✅ T24: `test_us10_s4_deactivate_profile.sh` — Soft delete
- ✅ T25: `test_us10_s5_feature009_integration.sh` — Invite flow integration
- ✅ T26: `test_us10_s6_rbac_matrix.sh` — Authorization matrix (Owner, Manager, Agent)
- ✅ T27: `test_us10_s7_multitenancy.sh` — Cross-company isolation
- ✅ T28: `test_us10_s8_compound_unique.sh` — Constraint validation

**Utilitários** (`integration_tests/`):
- ✅ `run_feature010_tests.sh` — Test runner com cleanup automático
- ✅ `cleanup_test_data.sh` — Limpeza seletiva de dados de teste

---

## Validação

### Status de Implementação
✅ **100% Completo** (8/8 testes E2E passando)

### Cobertura de Testes

| Test ID | Cenário | Status |
|---------|---------|--------|
| T21 | Create profile (10 tipos) | ✅ PASS |
| T22 | List profiles (paginação, filtros) | ✅ PASS |
| T23 | Update profile (imutabilidade) | ✅ PASS |
| T24 | Soft delete (cascade) | ✅ PASS |
| T25 | Feature 009 integration (invite) | ✅ PASS |
| T26 | RBAC matrix (Owner 9/9, Manager 5+4, Agent 2+7) | ✅ PASS |
| T27 | Multi-tenancy isolation (3 empresas) | ✅ PASS |
| T28 | Compound unique constraint | ✅ PASS |

### RBAC Authorization Matrix Validado

| Role | Allowed Profile Types | Forbidden | Test Coverage |
|------|----------------------|-----------|---------------|
| **Owner** | 10/10 (all) | 0 | ✅ 10/10 = 100% |
| **Manager** | 5/10 (agent, prospector, receptionist, financial, legal) | 5/10 → 403 | ✅ 5+5 = 100% |
| **Agent** | 2/10 (property_owner, portal) | 8/10 → 403 | ✅ 2+8 = 100% |

### Multi-Tenancy Validado

- ✅ Same document in different companies → **201 Created**
- ✅ Cross-company read → **404 Not Found** (anti-enumeration)
- ✅ Unauthorized company_ids → **403 Forbidden**
- ✅ Duplicate in same company → **409 Conflict**

---

## Evolução Futura

### Phase 2 (Pós-MVP)
- Remover campos duplicados de `agent` (name, document, email)
- Migrar 18 endpoints de agent para usar `profile_id` como fonte única
- Criar views no Odoo UI para gestão unificada de perfis

### Phase 3 (Feature 011+)
- Extensões específicas para outros perfis (prospector, receptionist)
- Histórico de mudanças de perfil (audit trail)
- API de busca avançada (full-text search em perfis)

---

## Referências

- **Specification**: `specs/010-profile-unification/spec.md`
- **Data Model**: `specs/010-profile-unification/data-model.md`
- **Technical Plan**: `specs/010-profile-unification/plan.md`
- **ADR-004**: Nomenclatura de módulos e tabelas
- **ADR-008**: Segurança multi-tenancy
- **ADR-015**: Soft-delete strategies
- **ADR-018**: Input validation and schema validation
- **ADR-019**: Sistema RBAC com 9 perfis
- **KB-09**: Database Best Practices (3NF, lookup tables)

---

## Autores
- **Decisão**: Equipe de Arquitetura
- **Implementação**: Feature 010 Sprint (Feb 2026)
- **Testes**: 8 testes E2E (100% coverage)
- **Documentação**: ADR-024, Spec 010, Data Model 010
