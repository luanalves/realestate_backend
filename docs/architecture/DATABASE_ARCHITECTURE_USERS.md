# Arquitetura de Banco de Dados - Usuários e Pessoas da Imobiliária

**Data:** 05/02/2026  
**Versão:** 1.0  
**Módulo:** quicksol_estate + thedevkitchen_apigateway

---

## 1. Visão Geral da Arquitetura

O sistema utiliza uma **arquitetura multi-tenant** com separação clara entre:
- **Usuários do Sistema** (res.users) - Autenticação e permissões
- **Imobiliárias** (thedevkitchen.estate.company) - Entidades multi-tenant
- **Pessoas Operacionais** (agentes, proprietários, inquilinos) - Dados de negócio

### Modelo de Dados Hierárquico

```
res.users (Odoo Core)
    ↓ (herança: res_users.py)
    estate_company_ids (Many2many)
    ↓
thedevkitchen.estate.company
    ↓ (relacionamentos Many2many)
    ├── real.estate.agent (Agentes/Corretores)
    ├── real.estate.property.owner (Proprietários)
    ├── real.estate.tenant (Inquilinos)
    └── real.estate.property (Imóveis)
```

---

## 2. Tabelas Principais

### 2.1 Tabela: `res_users` (Odoo Core + Extensão)

**Modelo:** `res.users`  
**Herança:** Extende modelo padrão do Odoo  
**Arquivo:** `18.0/extra-addons/quicksol_estate/models/res_users.py`

#### Campos Adicionados (Customização):

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `estate_company_ids` | Many2many | Imobiliárias que o usuário tem acesso |
| `main_estate_company_id` | Many2one | Imobiliária principal do usuário |

#### Tabela de Relacionamento:
```sql
thedevkitchen_user_company_rel (
    user_id INTEGER → res_users.id,
    company_id INTEGER → thedevkitchen_estate_company.id
)
```

#### Regras de Negócio:
- **Admin (System Administrator)**: Acessa TODAS as imobiliárias
- **Usuários Normais**: Acessam apenas suas `estate_company_ids`
- **Auto-sincronização**: Mudanças em `estate_company_ids` atualizam agentes relacionados
- **Eventos LGPD**: Auditoria de alterações de grupos (T135)

---

### 2.2 Tabela: `thedevkitchen_estate_company`

**Modelo:** `thedevkitchen.estate.company`  
**Descrição:** Imobiliárias (multi-tenancy)  
**Arquivo:** `18.0/extra-addons/quicksol_estate/models/company.py`

#### Estrutura:

| Campo | Tipo | Requerido | Índice | Descrição |
|-------|------|-----------|--------|-----------|
| `id` | Integer | Sim | PK | ID único |
| `name` | Char | Sim | - | Nome da imobiliária |
| `cnpj` | Char(18) | Sim | Único | CNPJ formatado (XX.XXX.XXX/XXXX-XX) |
| `legal_name` | Char | - | - | Razão social |
| `creci` | Char | - | - | CRECI da empresa |
| `email` | Char | - | - | Email de contato |
| `phone` | Char | - | - | Telefone |
| `mobile` | Char | - | - | Celular |
| `website` | Char | - | - | Website |
| `street` | Char | - | - | Endereço |
| `city` | Char | - | - | Cidade |
| `state_id` | Many2one | - | - | → real.estate.state |
| `zip_code` | Char | - | - | CEP |
| `country_id` | Many2one | - | - | → res.country |
| `active` | Boolean | - | - | Soft-delete (ADR-015) |
| `foundation_date` | Date | - | - | Data de fundação |
| `logo` | Binary | - | - | Logotipo |

#### Validações:
```python
@api.constrains('cnpj')
def _check_cnpj(self):
    # Validação completa de CNPJ com dígitos verificadores
    # Formato: XX.XXX.XXX/XXXX-XX (14 dígitos)
```

#### Relacionamentos Many2many:

```sql
-- Agentes
thedevkitchen_company_agent_rel (
    company_id → thedevkitchen_estate_company.id,
    agent_id → real_estate_agent.id
)

-- Proprietários (via properties)
thedevkitchen_company_property_rel (
    company_id → thedevkitchen_estate_company.id,
    property_id → real_estate_property.id
)

-- Inquilinos
thedevkitchen_company_tenant_rel (
    company_id → thedevkitchen_estate_company.id,
    tenant_id → real_estate_tenant.id
)

-- Aluguéis
thedevkitchen_company_lease_rel (
    company_id → thedevkitchen_estate_company.id,
    lease_id → real_estate_lease.id
)

-- Vendas
thedevkitchen_company_sale_rel (
    company_id → thedevkitchen_estate_company.id,
    sale_id → real_estate_sale.id
)
```

---

### 2.3 Tabela: `real_estate_agent`

**Modelo:** `real.estate.agent`  
**Descrição:** Agentes/Corretores de imóveis  
**Arquivo:** `18.0/extra-addons/quicksol_estate/models/agent.py`

#### Estrutura:

| Campo | Tipo | Requerido | Índice | Descrição |
|-------|------|-----------|--------|-----------|
| `id` | Integer | Sim | PK | ID único |
| `name` | Char | Sim | - | Nome completo |
| `cpf` | Char(14) | Sim | Sim | CPF (formatado) |
| `creci` | Char(50) | - | - | CRECI (formato flexível) |
| `creci_normalized` | Char(20) | - | Sim | CRECI normalizado (CRECI/UF NNNNN) |
| `creci_state` | Char(2) | - | - | UF do CRECI (computado) |
| `creci_number` | Char(8) | - | - | Número do CRECI (computado) |
| `email` | Char | - | - | Email |
| `phone` | Char(20) | - | - | Telefone |
| `mobile` | Char(20) | - | - | Celular |
| `company_id` | Many2one | Sim | - | → thedevkitchen.estate.company |
| `company_ids` | Many2many | - | - | **Deprecated** (backward compat) |
| `user_id` | Many2one | - | - | → res.users (acesso ao sistema) |
| `active` | Boolean | - | - | Soft-delete (ADR-015) |
| `hire_date` | Date | Sim | - | Data de contratação |
| `deactivation_date` | Date | - | - | Data de desativação |
| `deactivation_reason` | Text | - | - | Motivo da desativação |
| `bank_name` | Char | - | - | Nome do banco |
| `bank_account` | Char(20) | - | - | Conta bancária |
| `pix_key` | Char | - | - | Chave PIX |

#### Relacionamentos:

```python
# Propriedades (legado)
properties → One2many('real.estate.property', 'agent_id')

# Atribuições (US3)
assignment_ids → One2many('real.estate.agent.property.assignment', 'agent_id')
agent_property_ids → Many2many (computed via assignments)

# Comissões (US4)
commission_rule_ids → One2many('real.estate.commission.rule', 'agent_id')
commission_transaction_ids → One2many('real.estate.commission.transaction', 'agent_id')
```

#### Constraints SQL:

```sql
CONSTRAINT cpf_company_unique 
    UNIQUE(cpf, company_id)
    -- Garante CPF único por imobiliária (multi-tenancy)
```

#### Validações:

```python
@api.constrains('cpf')
def _check_cpf_format(self):
    # Validação CPF usando validate_docbr
    # Formato: XXX.XXX.XXX-XX (11 dígitos)

@api.constrains('creci')
def _check_creci_format(self):
    # Validação CRECI usando CreciValidator
    # Formatos aceitos:
    #   - CRECI/SP 12345
    #   - CRECI-RJ-67890
    #   - 12345-MG
```

#### Campos Computados (Performance):

```python
# US5 - Métricas de desempenho
total_sales_count → Integer (count de transactions)
total_commissions → Float (sum de commission_amount)
average_commission → Float (média)
active_properties_count → Integer (count assignments ativos)
```

---

### 2.4 Tabela: `real_estate_property_owner`

**Modelo:** `real.estate.property.owner`  
**Descrição:** Proprietários de imóveis  
**Arquivo:** `18.0/extra-addons/quicksol_estate/models/property_owner.py`

#### Estrutura:

| Campo | Tipo | Requerido | Descrição |
|-------|------|-----------|-----------|
| `id` | Integer | Sim | ID único |
| `name` | Char | Sim | Nome do proprietário |
| `partner_id` | Many2one | - | → res.partner (Portal) |
| `cpf` | Char(14) | - | CPF (Pessoa Física) |
| `cnpj` | Char(18) | - | CNPJ (Pessoa Jurídica) |
| `rg` | Char(20) | - | RG |
| `email` | Char | - | Email principal |
| `phone` | Char | - | Telefone |
| `mobile` | Char | - | Celular |
| `whatsapp` | Char | - | WhatsApp |
| `address` | Text | - | Endereço completo |
| `city` | Char | - | Cidade |
| `state_id` | Many2one | - | → real.estate.state |
| `zip_code` | Char | - | CEP |
| `country_id` | Many2one | - | → res.country (default: BR) |
| `birth_date` | Date | - | Data de nascimento |
| `marital_status` | Selection | - | Estado civil |
| `nationality` | Char | - | Nacionalidade |
| `active` | Boolean | - | Soft-delete |

#### Relacionamentos:

```python
property_ids → One2many('real.estate.property', 'owner_id')
property_count → Integer (computed)
```

#### Validações:

```python
@api.constrains('cpf')
def _check_cpf(self):
    # CPF deve ter 11 dígitos

@api.constrains('cnpj')
def _check_cnpj(self):
    # CNPJ deve ter 14 dígitos
```

#### Observações:
- **Pessoa Física ou Jurídica**: Pode ter CPF OU CNPJ (ambos opcionais)
- **Portal**: Vincula a `res.partner` para acesso ao portal do proprietário
- **Isolamento**: Não tem ligação direta com imobiliária (via property)

---

### 2.5 Tabela: `real_estate_tenant`

**Modelo:** `real.estate.tenant`  
**Descrição:** Inquilinos  
**Arquivo:** `18.0/extra-addons/quicksol_estate/models/tenant.py`

#### Estrutura:

| Campo | Tipo | Requerido | Descrição |
|-------|------|-----------|-----------|
| `id` | Integer | Sim | ID único |
| `name` | Char | Sim | Nome do inquilino |
| `partner_id` | Many2one | - | → res.partner (Portal) |
| `phone` | Char | - | Telefone |
| `email` | Char | - | Email |
| `company_ids` | Many2many | - | → thedevkitchen.estate.company |
| `occupation` | Char | - | Profissão |
| `birthdate` | Date | - | Data de nascimento |
| `profile_picture` | Binary | - | Foto de perfil |

#### Relacionamentos:

```python
leases → One2many('real.estate.lease', 'tenant_id')
company_ids → Many2many via 'thedevkitchen_company_tenant_rel'
```

#### Validações:

```python
@api.constrains('email')
def _validate_email(self):
    # Validação de formato de email usando regex
    # Padrão: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
```

---

## 3. Tabelas de Relacionamento (Many2many)

### 3.1 Usuário ↔ Imobiliária

```sql
CREATE TABLE thedevkitchen_user_company_rel (
    user_id INTEGER REFERENCES res_users(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, company_id)
);
```

**Uso:** Controla quais imobiliárias cada usuário pode acessar (multi-tenancy).

---

### 3.2 Imobiliária ↔ Agente

```sql
CREATE TABLE thedevkitchen_company_agent_rel (
    company_id INTEGER REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    agent_id INTEGER REFERENCES real_estate_agent(id) ON DELETE CASCADE,
    PRIMARY KEY (company_id, agent_id)
);
```

**Observação:** Atualmente **DEPRECATED**. O modelo foi alterado para `company_id` (Many2one) em `real_estate_agent`, permitindo que cada agente pertença a **apenas uma imobiliária**.

---

### 3.3 Imobiliária ↔ Inquilino

```sql
CREATE TABLE thedevkitchen_company_tenant_rel (
    company_id INTEGER REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES real_estate_tenant(id) ON DELETE CASCADE,
    PRIMARY KEY (company_id, tenant_id)
);
```

**Uso:** Permite que inquilinos sejam compartilhados entre múltiplas imobiliárias (multi-tenancy).

---

### 3.4 Imobiliária ↔ Propriedade

```sql
CREATE TABLE thedevkitchen_company_property_rel (
    company_id INTEGER REFERENCES thedevkitchen_estate_company(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES real_estate_property(id) ON DELETE CASCADE,
    PRIMARY KEY (company_id, property_id)
);
```

---

## 4. Estratégias de Multi-Tenancy

### 4.1 Isolamento por Imobiliária

O sistema utiliza **multi-tenancy baseado em relacionamentos Many2many** com as seguintes estratégias:

#### Nível 1: Usuário → Imobiliárias
```python
# res.users
estate_company_ids = fields.Many2many('thedevkitchen.estate.company')
```

- Usuários **não-admin**: Veem apenas dados das suas `estate_company_ids`
- Usuários **admin**: Veem TODOS os dados (bypass multi-tenancy)

#### Nível 2: Dados → Imobiliárias

**Modelo A (Many2many):** Inquilinos, Aluguéis, Vendas
```python
company_ids = fields.Many2many('thedevkitchen.estate.company', ...)
```

**Modelo B (Many2one - Nova Arquitetura):** Agentes
```python
company_id = fields.Many2one('thedevkitchen.estate.company', required=True)
```

**Modelo C (Indireto):** Proprietários
- Não têm ligação direta com imobiliária
- Isolamento via `property_id.company_ids`

---

### 4.2 Record Rules (Segurança Odoo)

O sistema utiliza **Record Rules** para aplicar isolamento automático:

```xml
<!-- Exemplo: Agentes só veem agentes da sua imobiliária -->
<record id="rule_agent_company_isolation" model="ir.rule">
    <field name="name">Agent: Company Isolation</field>
    <field name="model_id" ref="model_real_estate_agent"/>
    <field name="domain_force">
        [('company_id', 'in', user.estate_company_ids.ids)]
    </field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

---

## 5. Perfis de Usuário (RBAC)

### 5.1 Grupos de Segurança

Arquivo: `18.0/extra-addons/quicksol_estate/security/ir.model.access.csv`

| Grupo | Nome Técnico | Permissões |
|-------|--------------|------------|
| **Estate Owner** | `group_real_estate_owner` | CRUD completo em tudo |
| **Director** | `group_real_estate_director` | Leitura em tudo, CRUD em properties/sales |
| **Manager** | `group_real_estate_manager` | CRUD em agents, properties, leases, tenants |
| **Agent** | `group_real_estate_agent` | CRUD em properties atribuídos, leads |
| **Prospector** | `group_real_estate_prospector` | Criar properties, read-only em agents |
| **Receptionist** | `group_real_estate_receptionist` | CRUD em leases, keys, tenants |
| **Financial** | `group_real_estate_financial` | CRUD em commission rules/transactions |
| **Legal** | `group_real_estate_legal` | Read-only em sales, leases, documents |
| **System Admin** | `base.group_system` | Acesso total (Odoo core) |

---

### 5.2 Matriz de Permissões (Pessoas)

| Grupo | res.users | estate.company | agent | owner | tenant |
|-------|-----------|----------------|-------|-------|--------|
| **Owner** | CRU | CRUD | CRUD | CRUD | CRUD |
| **Director** | R | RU | R | R | R |
| **Manager** | R | CRUD | CRUD | CRUD | CRUD |
| **Agent** | R | R | R | R | R |
| **Receptionist** | R | R | R | R | U |
| **System Admin** | CRUD | CRUD | CRUD | CRUD | CRUD |

**Legenda:**
- C = Create
- R = Read
- U = Update
- D = Delete

---

## 6. API REST - Endpoints de Pessoas

### 6.1 Agentes (`agent_api.py`)

```
GET    /api/v1/agents              # Listar agentes (paginado)
POST   /api/v1/agents              # Criar agente
GET    /api/v1/agents/{id}         # Detalhes do agente
PUT    /api/v1/agents/{id}         # Atualizar agente
DELETE /api/v1/agents/{id}         # Soft-delete (deactivate)
POST   /api/v1/agents/{id}/deactivate  # Desativar agente
```

**Autenticação:**
```python
@require_jwt          # Token JWT válido
@require_session      # Sessão de usuário
@require_company      # Imobiliária padrão configurada
```

**Isolamento Multi-tenant:**
```python
# Filtro automático por company_id
if not company_id:
    if user.estate_default_company_id:
        domain.append(('company_id', '=', user.estate_default_company_id.id))
```

---

### 6.2 Imobiliárias (`company_api.py`)

```
GET    /api/v1/companies           # Listar imobiliárias
POST   /api/v1/companies           # Criar imobiliária
GET    /api/v1/companies/{id}      # Detalhes da imobiliária
PUT    /api/v1/companies/{id}      # Atualizar imobiliária
DELETE /api/v1/companies/{id}      # Soft-delete (archive)
```

**Validações:**
- **CNPJ:** Validação completa com dígitos verificadores
- **Unicidade:** CNPJ único no sistema (incluindo arquivados)
- **Permissões:** Apenas **Owner** e **SystemAdmin** podem criar

**Auto-associação:**
```python
# T024: Adiciona nova company ao usuário automaticamente
user.sudo().write({
    'estate_company_ids': [(4, new_company.id)]
})
```

---

## 7. Diagrama ER (Entity-Relationship)

```
┌─────────────────┐
│   res.users     │
│ (Odoo Core)     │
└────────┬────────┘
         │ Many2many (estate_company_ids)
         ↓
┌──────────────────────────┐
│ thedevkitchen.           │
│ estate.company           │
│ ─────────────────        │
│ + cnpj (UNIQUE)          │
│ + legal_name             │
│ + creci                  │
└───┬──────────────────┬───┘
    │                  │
    │ Many2many        │ Many2many
    ↓                  ↓
┌───────────────┐  ┌──────────────────┐
│ real.estate.  │  │ real.estate.     │
│ agent         │  │ tenant           │
│ ─────────     │  │ ────────         │
│ + cpf         │  │ + email          │
│ + creci       │  │ + phone          │
│ + company_id  │  │ + company_ids    │
│   (Many2one)  │  │   (Many2many)    │
└───────────────┘  └──────────────────┘
         │
         │ One2many (assignments)
         ↓
┌──────────────────────────────┐
│ real.estate.agent.           │
│ property.assignment          │
│ ──────────────────────       │
│ + agent_id → agent           │
│ + property_id → property     │
│ + assigned_date              │
└──────────────────────────────┘
         │
         ↓
┌──────────────────────────┐
│ real.estate.property     │
│ ──────────────           │
│ + owner_id (Many2one)    │
│ + company_ids (M2m)      │
└───────┬──────────────────┘
        │ Many2one
        ↓
┌──────────────────────────┐
│ real.estate.             │
│ property.owner           │
│ ──────────────           │
│ + cpf / cnpj             │
│ + partner_id (Portal)    │
└──────────────────────────┘
```

---

## 8. Fluxos de Dados Principais

### 8.1 Criação de Agente via API

```
1. POST /api/v1/agents
   ↓
2. @require_jwt → Valida token JWT
   ↓
3. @require_session → Carrega usuário
   ↓
4. @require_company → Verifica company padrão
   ↓
5. Validação de permissão (Manager ou Admin)
   ↓
6. SchemaValidator.validate_agent_create(data)
   ↓
7. CompanyValidator.validate_company_ids([company_id])
   ↓
8. Agent.sudo().create(agent_vals)
   ↓
9. Validações do modelo:
   - _check_cpf_format()
   - _check_creci_format()
   ↓
10. SQL Constraint: cpf_company_unique
   ↓
11. Retorna HTTP 201 + agent_data
```

---

### 8.2 Listagem de Agentes (Multi-tenant)

```
1. GET /api/v1/agents?company_id=5
   ↓
2. Autenticação (JWT + Session + Company)
   ↓
3. Construção de domain:
   domain = []
   
4. Se company_id fornecido:
   domain.append(('company_id', '=', int(company_id)))
   
5. Senão, usar company padrão do usuário:
   if user.estate_default_company_id:
       domain.append(('company_id', '=', user.estate_default_company_id.id))
   
6. Agent.sudo().search(domain, limit=20, offset=0)
   ↓
7. Record Rules aplicadas automaticamente
   ↓
8. Serialização + HATEOAS (_links)
   ↓
9. Retorna JSON com paginação
```

---

## 9. Padrões de Nomenclatura (ADR-004)

### 9.1 Modelos

| Tipo | Padrão | Exemplo |
|------|--------|---------|
| Pessoa (empresa) | `thedevkitchen.estate.{entity}` | `thedevkitchen.estate.company` |
| Pessoa (operacional) | `real.estate.{entity}` | `real.estate.agent` |
| Propriedade | `real.estate.property.{entity}` | `real.estate.property.owner` |
| Transação | `real.estate.{type}` | `real.estate.lease` |

---

### 9.2 Tabelas

| Modelo | Tabela |
|--------|--------|
| `thedevkitchen.estate.company` | `thedevkitchen_estate_company` |
| `real.estate.agent` | `real_estate_agent` |
| `real.estate.property.owner` | `real_estate_property_owner` |
| `real.estate.tenant` | `real_estate_tenant` |

**Regra:** Substituir `.` por `_` no nome do modelo.

---

### 9.3 Tabelas de Relacionamento (Many2many)

**Padrão:**
```
{prefix}_{entity1}_{entity2}_rel
```

**Exemplos:**
- `thedevkitchen_user_company_rel`
- `thedevkitchen_company_agent_rel`
- `thedevkitchen_company_tenant_rel`

---

## 10. Soft-Delete (ADR-015)

Todos os modelos de pessoas implementam **soft-delete** via campo `active`:

```python
active = fields.Boolean(default=True)
```

### Comportamento:

1. **DELETE via API** → `write({'active': False})`
2. **Consultas padrão** → Filtram `active=True` automaticamente
3. **Histórico preservado** → Registros inativos permanecem no BD
4. **Reativação possível** → `write({'active': True})`

### Campos de Auditoria (Agentes):

```python
deactivation_date = fields.Date(readonly=True)
deactivation_reason = fields.Text(readonly=True)
```

---

## 11. Observações Técnicas

### 11.1 Mudança de Arquitetura (Agentes)

**Antes:**
```python
company_ids = fields.Many2many('thedevkitchen.estate.company')  # Múltiplas empresas
```

**Depois (Nova Arquitetura):**
```python
company_id = fields.Many2one('thedevkitchen.estate.company', required=True)  # Empresa única
company_ids = fields.Many2many(...)  # DEPRECATED (backward compatibility)
```

**Motivo:** Simplificar lógica de multi-tenancy. Cada agente pertence a **uma única imobiliária**.

---

### 11.2 Validações Brasileiras

#### CPF (11 dígitos):
```python
from validate_docbr import CPF
cpf_validator = CPF()
cpf_validator.validate(cpf_clean)
```

#### CNPJ (14 dígitos):
```python
# Validação completa com dígitos verificadores
Company._validate_cnpj(cnpj)
Company._normalize_cnpj(cnpj)  # → "XX.XXX.XXX/XXXX-XX"
```

#### CRECI (formato flexível):
```python
# Aceita:
# - CRECI/SP 12345
# - CRECI-RJ-67890
# - 12345-MG
CreciValidator.normalize(creci)  # → "CRECI/SP 12345"
```

---

### 11.3 Performance

#### Índices Criados:

```sql
-- Agentes
CREATE INDEX idx_agent_cpf ON real_estate_agent(cpf);
CREATE INDEX idx_agent_creci_normalized ON real_estate_agent(creci_normalized);

-- Usuários (Odoo Core)
CREATE INDEX idx_user_login ON res_users(login);
```

#### Campos Computados com Store:

```python
# Evita recalcular a cada consulta
creci_normalized = fields.Char(compute='...', store=True, index=True)
creci_state = fields.Char(compute='...', store=True)
creci_number = fields.Char(compute='...', store=True)
```

---

## 12. Eventos e Auditoria (ADR-020)

### 12.1 Eventos Emitidos (res.users)

```python
# Antes de criar usuário
self.env['quicksol.event.bus'].emit('user.before_create', {...})

# Antes de atualizar usuário
self.env['quicksol.event.bus'].emit('user.before_write', {...})

# Após atualizar usuário
self.env['quicksol.event.bus'].emit('user.updated', {...})

# Mudanças de grupos de segurança (LGPD - T135)
self.env['quicksol.event.bus'].emit('user.groups_changed', {
    'user': user,
    'added_groups': ['Estate Agent'],
    'removed_groups': ['Estate Manager'],
    'changed_by': admin_user
})
```

---

## 13. Resumo da Arquitetura

### ✅ Pontos Fortes:

1. **Multi-tenancy robusto** com isolamento por imobiliária
2. **RBAC completo** com 9 perfis de usuário
3. **Validações brasileiras** (CPF, CNPJ, CRECI)
4. **Soft-delete** para preservação de histórico
5. **API RESTful** com autenticação JWT + Session
6. **Auditoria completa** via Observer Pattern
7. **Performance** com índices e campos computados armazenados

### ⚠️ Pontos de Atenção:

1. **Migração Many2many → Many2one** (agentes) em andamento
2. **Tabelas `_rel` legadas** ainda existem (compatibilidade)
3. **Proprietários** não têm ligação direta com imobiliária (via property)
4. **Dependência** de biblioteca externa (`validate_docbr`)

---

**Fim do Documento**
