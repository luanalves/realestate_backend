# ADR-019: Sistema de Perfis de Acesso (RBAC) em Ambiente Multi-Tenancy

## Status
Aceito

## Contexto

O sistema precisa atender diferentes papéis dentro de imobiliárias em um ambiente **multi-tenancy** (multi-imobiliária), onde:

- **Múltiplas imobiliárias** compartilham a mesma infraestrutura
- **Cada usuário** pode estar vinculado a uma ou mais imobiliárias via `estate_company_ids`
- **Isolamento de dados** deve ser garantido entre imobiliárias (ADR-008)
- **Diferentes perfis** têm responsabilidades e níveis de acesso distintos

### Perfis Identificados (baseado em RBAC-plan.md)

**Nível 1 - Administrativo:**
- **Owner/Proprietário**: Dono da imobiliária, cadastra usuários e configura sistema
- **Director/Diretor**: Relatórios executivos, dashboards completos, BI
- **Manager/Gerente**: Gestão operacional diária, leads, equipe

**Nível 2 - Operacional:**
- **Corretor**: Vendas, captação de imóveis, atendimento a leads
- **Captador**: Prospecção de imóveis (comissão compartilhada com corretor)
- **Atendente**: Contratos, gestão de chaves, renovações
- **Financeiro**: Comissões, pagamentos, relatórios financeiros
- **Jurídico**: Validação de contratos

**Nível 3 - Externo:**
- **Portal Cliente**: Comprador/Locatário com acesso limitado

### Dilema

**Implementar perfis fixos em código** ou **criar sistema flexível de gestão de permissões?**

- **Perfis fixos**: Rápido de implementar, fácil de testar, mas menos flexível
- **Sistema flexível**: Maior valor para clientes, mas complexo e arriscado sem validação de mercado

## Decisão

**Abordagem híbrida em 2 fases:**

### Fase 1 - MVP (Lançamento)
- **9 perfis pré-definidos** via `res.groups` do Odoo
- **Permissões fixas** via record rules, ACLs e field-level security
- **Segurança multi-tenant** garantida por record rules baseadas em `estate_company_ids`
- **Sem customização** de permissões por imobiliária (perfis padronizados)

### Fase 2 - Pós-lançamento (Condicional)
- Avaliar demanda real por customização após 6 meses
- Se validado, implementar UI para habilitar/desabilitar menus e campos por perfil
- **Não** permitir alteração de record rules (mantém segurança multi-tenant)

## Perfis Pré-definidos (Fase 1)

### Convenção de Nomenclatura

**XML ID**: `group_real_estate_<role>` (padrão Odoo para evitar colisões)  
**Display Name**: `Real Estate <Role>` (visível na interface)

**Motivos:**
- Evita conflito com outros módulos (`group_manager` vs `group_real_estate_manager`)
- Clareza ao referenciar em código (`quicksol_estate.group_real_estate_manager`)
- Padrão seguido por módulos oficiais Odoo (`sale.group_sale_manager`)

---

### 1. Owner/Proprietário da Imobiliária

**Grupo Odoo**: `group_real_estate_owner`  
**Nome de Exibição**: `Real Estate Owner`

**Responsabilidades:**
- Criar e configurar a imobiliária (primeira vez)
- Cadastrar e gerenciar usuários da imobiliária
- Definir configurações de integração (portais, APIs)
- Acesso total aos dados da imobiliária

**Permissões:**
- CRUD completo em todos os modelos da imobiliária
- Gerenciar usuários (`res.users`) vinculados à sua imobiliária
- Configurar integrações externas
- Visualizar relatórios e dashboards

**Record Rule**: Acesso a registros de `estate_company_ids` onde está vinculado

**Jornada:**
1. SaaS Admin cria conta e vincula à nova imobiliária
2. Owner cadastra equipe (Manager, Corretor, etc.)
3. Owner configura integrações (Zap Imóveis, OLX)

---

### 2. Director/Diretor

**Grupo Odoo**: `group_real_estate_director`  
**Nome de Exibição**: `Real Estate Director`  
**Herda**: `group_real_estate_manager` (acesso completo + relatórios avançados)

**Responsabilidades:**
- Relatórios executivos e dashboards completos
- Business Intelligence (BI) e análises avançadas
- Gestão estratégica (não operacional)

**Permissões:**
- Todas as permissões do Manager
- Acesso a relatórios financeiros completos
- Dashboards executivos (métricas consolidadas)

**Record Rule**: Mesma do Manager (todas empresas vinculadas)

---

### 3. Manager/Gerente

**Grupo Odoo**: `group_real_estate_manager`  
**Nome de Exibição**: `Real Estate Manager`  
**Herda**: `group_real_estate_user`

**Responsabilidades:**
- Gestão operacional diária
- CRM de leads (atribuir, monitorar, reatribuir)
- Dashboards de desempenho da equipe
- Gerenciar propriedades e contratos

**Permissões:**
- CRUD em propriedades, agentes, contratos, leads
- Atribuir leads aos corretores
- Gerar relatórios de desempenho
- **NÃO** criar/excluir usuários (apenas Owner)

**Record Rule**: `[('company_ids', 'in', user.estate_company_ids.ids)]`

---

### 4. Corretor

**Grupo Odoo**: `group_real_estate_agent`  
**Nome de Exibição**: `Real Estate Agent`  
**Herda**: `group_real_estate_user`

**Responsabilidades:**
- Cadastrar e gerenciar imóveis (próprios ou atribuídos)
- Gerenciar leads próprios (CRM pessoal)
- Agendar e registrar visitas
- Criar propostas e contratos (sujeito a aprovação)

**Permissões:**
- CRUD em imóveis onde `agent_id.user_id = user.id`
- CRUD em leads próprios
- Visualizar propostas ativas (não editar cliente da proposta)
- Atualizar status de negociações

**Record Rule**: 
```python
[
    '|',
    ('agent_id.user_id', '=', user.id),
    ('assignment_ids.agent_id.user_id', '=', user.id),
    ('company_ids', 'in', user.estate_company_ids.ids)
]
```

**Restrições:**
- **NÃO** pode alterar cliente da proposta (proposta é do cliente, não do corretor)
- **NÃO** pode editar comissões
- Visualiza valor do imóvel (leitura)

---

### 5. Captador/Prospector

**Grupo Odoo**: `group_real_estate_prospector`  
**Nome de Exibição**: `Real Estate Prospector`

**Responsabilidades:**
- Prospectar e cadastrar novos imóveis
- Receber comissão compartilhada (split com corretor de vendas)

**Permissões:**
- Cadastrar imóveis (campo `prospector_id` preenchido)
- Visualizar imóveis captados (apenas os seus)
- **NÃO** gerenciar leads ou vendas

**Record Rule**:
```python
[
    ('prospector_id.user_id', '=', user.id),
    ('company_ids', 'in', user.estate_company_ids.ids)
]
```

**Cálculo de Comissão**:
- Sistema calcula automaticamente split entre captador e corretor
- Percentual definido em `commission_rule` (ex: 30% captador, 70% corretor)

---

### 6. Atendente/Receptionist

**Grupo Odoo**: `group_real_estate_receptionist`  
**Nome de Exibição**: `Real Estate Receptionist`  
**Herda**: `group_real_estate_user`

**Responsabilidades:**
- Criar e editar contratos
- Gestão de chaves (check-in/check-out)
- Renovações de aluguéis
- Suporte administrativo

**Permissões:**
- Visualizar todos imóveis da imobiliária (read-only)
- CRUD em contratos (`real.estate.lease`)
- Gestão de chaves (modelo futuro: `real.estate.key`)
- **NÃO** editar comissões ou leads

**Record Rule**: `[('company_ids', 'in', user.estate_company_ids.ids)]` (leitura ampla)

---

### 7. Financeiro

**Grupo Odoo**: `group_real_estate_financial`  
**Nome de Exibição**: `Real Estate Financial`  
**Herda**: `group_real_estate_user`

**Responsabilidades:**
- Processar comissões
- Gerar relatórios financeiros
- Acompanhar pagamentos e repasses

**Permissões:**
- Visualizar todas vendas e aluguéis (read-only)
- CRUD em comissões (`real.estate.commission`)
- Gerar relatórios de faturamento
- **NÃO** editar propriedades ou leads

**Record Rule**: `[('company_ids', 'in', user.estate_company_ids.ids)]`

---

### 8. Jurídico

**Grupo Odoo**: `group_real_estate_legal`  
**Nome de Exibição**: `Real Estate Legal`  
**Herda**: `group_real_estate_user`

**Responsabilidades:**
- Validar contratos
- Análise jurídica de documentos
- Garantir conformidade legal

**Permissões:**
- Visualizar todos contratos da imobiliária (read-only)
- Adicionar pareceres jurídicos (comentários/notas)
- **NÃO** editar valores ou comissões

**Record Rule**: `[('company_ids', 'in', user.estate_company_ids.ids)]`

---

### 9. Portal Cliente/Locatário

**Grupo Odoo**: `group_real_estate_portal_user`  
**Nome de Exibição**: `Real Estate Portal User`  
**Herda**: `base.group_portal`

**Responsabilidades:**
- Acompanhar próprios contratos
- Visualizar propostas
- Upload de documentos

**Permissões:**
- Visualizar apenas registros onde `partner_id = user.partner_id`
- Upload de documentos pessoais
- Assinar contratos eletronicamente (futuro)

**Record Rule**:
```python
[('partner_id', '=', user.partner_id.id)]
```

---

## Implementação Técnica

### Estrutura de Arquivos

```
quicksol_estate/
├── security/
│   ├── groups.xml              # Definição dos 9 grupos
│   ├── record_rules.xml        # Record rules por perfil
│   └── ir.model.access.csv     # ACLs (CRUD permissions)
├── models/
│   ├── property.py             # Adicionar campo prospector_id
│   ├── commission_rule.py      # Lógica split captador/corretor
│   └── res_users.py            # Já existe (estate_company_ids)
└── data/
    └── default_groups.xml      # Dados iniciais (opcional)
```

### Hierarquia de Grupos (Implied Groups)

```
base.group_user (Odoo base - acesso interno)
├── group_real_estate_user (base comum)
│   ├── group_real_estate_manager
│   │   └── group_real_estate_director
│   ├── group_real_estate_agent
│   ├── group_real_estate_receptionist
│   ├── group_real_estate_financial
│   └── group_real_estate_legal
├── group_real_estate_prospector (standalone)
└── group_real_estate_owner (standalone - acesso total)

base.group_portal (Odoo portal - acesso externo)
└── group_real_estate_portal_user
```

### Exemplo: Record Rule para Corretor

```xml
<!-- security/record_rules.xml -->
<record id="rule_property_agent_own" model="ir.rule">
    <field name="name">Property: Agent Own Properties</field>
    <field name="model_id" ref="model_real_estate_property"/>
    <field name="domain_force">[
        '|',
            ('agent_id.user_id', '=', user.id),
            ('assignment_ids.agent_id.user_id', '=', user.id),
        ('company_ids', 'in', user.estate_company_ids.ids)
    ]</field>
    <field name="groups" eval="[(4, ref('group_real_estate_agent'))]"/>
</record>
```

### Exemplo: ACL para Captador

```csv
# ir.model.access.csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_property_prospector,access_property_prospector,model_real_estate_property,group_real_estate_prospector,1,0,1,0
```

**Interpretação**: Captador pode **ler** e **criar** propriedades, mas **não editar ou deletar**.

---

## Jornada de Onboarding

### 1. Cadastro da Imobiliária (SaaS Admin)

```
1. SaaS Admin cria registro em thedevkitchen.estate.company
2. Cria usuário Owner e vincula via estate_company_ids
3. Owner recebe credenciais e faz primeiro login
```

### 2. Owner Cadastra Equipe

```
Owner acessa: Configurações > Usuários
├── Criar Novo Usuário
│   ├── Nome: "João Silva"
│   ├── Email: joao@imobiliaria.com
│   ├── Perfil: [x] Real Estate Agent (Corretor)
│   └── Imobiliária: [x] Imobiliária ABC
└── Salvar

Sistema automaticamente:
├── Cria res.users
├── Atribui estate_company_ids = [Imobiliária ABC]
└── Aplica record rules de Corretor
```

### 3. Corretor Faz Login

```
1. Acessa via web interface do Odoo
2. Vê apenas:
   ├── Imóveis onde ele é agent_id
   ├── Leads próprios
   └── Propostas ativas
3. Multi-tenancy garante isolamento (não vê outras imobiliárias)
```

---

## Alternativas Consideradas

### Opção Avaliada: Módulo `base_user_role` (OCA)

**Repositório**: https://github.com/OCA/server-tools/tree/18.0/base_user_role

#### Descrição

Módulo da OCA (Odoo Community Association) que adiciona camada de abstração sobre grupos nativos do Odoo, permitindo criar **roles dinâmicos** compostos por múltiplos grupos.

#### Arquitetura

```python
res.users
└── role_line_ids (One2many)
    └── res.users.role.line
        ├── role_id → res.users.role
        │   └── group_ids (computed from role_line_ids)
        ├── date_from (gestão temporal)
        ├── date_to (expiração automática)
        └── is_enabled (ativo no período)
```

#### Funcionalidades Principais

1. **Roles Compostos**: Agrupa múltiplos grupos em um role reutilizável
2. **Gestão Temporal**: Roles com validade (`date_from`, `date_to`)
3. **Múltiplos Roles**: Usuário pode ter vários roles simultaneamente
4. **Interface Web**: UI dedicada para gerenciar roles
5. **Auditoria**: Histórico automático de atribuições/revogações
6. **Multi-empresa**: `company_id` no role

#### Comparação

| Critério | Grupos Nativos (Decisão) | `base_user_role` (OCA) |
|----------|--------------------------|------------------------|
| **Tempo implementação** | 2 semanas | 4 semanas (+integração) |
| **Complexidade** | Baixa (padrão Odoo) | Média (3 modelos novos) |
| **Manutenibilidade** | Alta (código core) | Média (depende OCA) |
| **Flexibilidade** | Baixa | Alta (roles dinâmicos) |
| **Interface web** | Grupos nativos | UI dedicada roles |
| **Gestão temporal** | ❌ Manual | ✅ Automático |
| **Múltiplos roles** | ❌ Via grupos | ✅ Nativo |
| **Multi-empresa** | ✅ Via `estate_company_ids` | ✅ Via `company_id` |
| **Auditoria** | ❌ Manual | ✅ Built-in |
| **Performance** | ⚡ Rápido | 🐢 Overhead (cron) |
| **Dependências** | Zero | +1 módulo externo |

#### Decisão

**Rejeitado para Fase 1** pelos seguintes motivos:

1. **Over-engineering para MVP** - Funcionalidades avançadas (temporal, herança) não são necessárias
2. **Time-to-market** - Adiciona 2 semanas de integração e testes
3. **Dependência externa** - Introduz ponto de falha adicional
4. **Complexidade desnecessária** - Record rules ainda requerem grupos nativos
5. **Curva de aprendizado** - Equipe precisa aprender novo paradigma

**Considerado para Fase 2** se houver demanda validada por:
- Roles temporários (estagiários, contratos temporários)
- Usuários com múltiplos papéis simultâneos
- Interface web para Owner gerenciar permissões
- Auditoria detalhada de mudanças de acesso

---

## Fase 2 - Customização (Condicional)

### Critérios de Validação

Implementar **somente se**:
- ≥30% dos clientes solicitarem ajustes de permissões
- Houver 5+ casos reais onde perfis padrão não atendem
- Budget aprovado para 2 semanas de desenvolvimento

### Opções para Fase 2

#### Opção A: Integração com `base_user_role` (OCA)

**Quando escolher:**
- Necessidade de roles temporários validada
- Múltiplos papéis por usuário são comuns
- Interface web para gestão é prioridade

**Esforço:** 2 semanas (integração + testes + migration)

**Implementação:**
```python
# Migration: converter grupos existentes → roles
def migrate_groups_to_roles(env):
    role_mapping = {
        'group_real_estate_owner': 'Real Estate Owner',
        'group_real_estate_director': 'Real Estate Director',
        # ... outros grupos
    }
    
    for group_xmlid, role_name in role_mapping.items():
        group = env.ref(f'quicksol_estate.{group_xmlid}')
        role = env['res.users.role'].create({
            'name': role_name,
            'role_line_ids': [(0, 0, {'group_id': group.id})]
        })
        
        # Migrar usuários
        users = env['res.users'].search([('groups_id', 'in', group.ids)])
        for user in users:
            user.role_line_ids = [(0, 0, {'role_id': role.id})]
```

#### Opção B: Sistema Próprio Minimalista

**Quando escolher:**
- Apenas precisa habilitar/desabilitar menus/campos
- Não precisa de gestão temporal
- Quer manter controle total do código

**Esforço:** 1 semana

**Implementação:**
```python
# Apenas configuração de visibilidade
class EstateRoleCustomization(models.Model):
    _name = 'quicksol.estate.role.customization'
    
    company_id = fields.Many2one('thedevkitchen.estate.company')
    group_id = fields.Many2one('res.groups')  # ref aos grupos existentes
    
    # Apenas configuração de UI
    hidden_menu_ids = fields.Many2many('ir.ui.menu')
    readonly_field_ids = fields.Many2many('ir.model.fields')
```

### Escopo Fase 2

**Permitido:**
- Habilitar/desabilitar menus específicos por perfil
- Tornar campos read-only ou editáveis
- (Se Opção A) Gestão temporal de roles
- (Se Opção A) Múltiplos roles por usuário

**NÃO permitido:**
- Alterar record rules (quebra segurança multi-tenant ADR-008)
- Criar perfis completamente customizados sem base nos grupos
- Modificar permissões CRUD em modelos (mantém ACLs fixas)

---

## Consequências

### Positivas
- **Lançamento rápido** - Perfis prontos, testados e documentados
- **Segurança garantida** - Record rules auditadas e aderentes ao ADR-008
- **Manutenibilidade** - Código padrão Odoo, fácil debugar e evoluir
- **Escalável** - Base sólida para futuras customizações

### Negativas
- **Menos flexível inicialmente** - Clientes devem se adaptar aos perfis
- **Pode requerer ajustes** - Feedback de campo pode revelar gaps

### Riscos Mitigados
- **Scope creep** - Evita construir funcionalidade complexa sem validação
- **Bugs de segurança** - Perfis fixos são mais fáceis de auditar
- **Over-engineering** - Não construir o que não será usado

---

## Referências

### Documentação Oficial
- **Odoo Security**: https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html
- **Odoo Groups & Access Rights**: https://www.odoo.com/documentation/18.0/developer/howtos/rdtraining/12_securityintro.html

### ADRs Relacionados
- **ADR-008**: API Security Multi-Tenancy - Base para isolamento multi-tenant
- **ADR-003**: Mandatory Test Coverage - Padrões de testes aplicáveis
- **ADR-001**: Development Guidelines - Estrutura de arquivos de segurança

### Comunidade & Padrões
- **OWASP RBAC**: https://owasp.org/www-community/Access_Control
- **OCA base_user_role**: https://github.com/OCA/server-tools/tree/18.0/base_user_role (referência para Fase 2)
- **OCA base_user_role_profile**: https://github.com/OCA/server-tools/tree/18.0/base_user_role_profile

### Documentos de Origem
- **RBAC-plan.md**: Requisitos originais de perfis de usuário (substituído por este ADR)

---

## Notas de Implementação

### Campo Novo: `prospector_id`

```python
# models/property.py
prospector_id = fields.Many2one(
    'real.estate.agent',
    string='Prospector',
    help='Agent who prospected this property (commission split)',
    tracking=True,
    groups='quicksol_estate.group_real_estate_manager'  # só manager edita
)
```

### Comissão Compartilhada

```python
# models/commission_rule.py
def calculate_split_commission(self, property_id):
    """Calculate commission split between prospector and agent"""
    property = self.env['real.estate.property'].browse(property_id)
    
    if property.prospector_id and property.agent_id:
        # Split: 30% prospector, 70% agent (configurável)
        total_commission = property.sale_price * self.commission_rate
        prospector_share = total_commission * 0.30
        agent_share = total_commission * 0.70
        return {
            'prospector': prospector_share,
            'agent': agent_share
        }
    
    # Sem captador, 100% para o corretor
    return {
        'agent': property.sale_price * self.commission_rate
    }
```

---

## Cronograma de Implementação

**FDecisões Documentadas

### Decisão Principal
- **Usar grupos nativos do Odoo** (`res.groups`) para Fase 1
- **9 perfis pré-definidos** fixos em código
- **Sem customização** de permissões por imobiliária no MVP

### Decisões Rejeitadas
- ❌ **`base_user_role` (OCA) para Fase 1**: Over-engineering, dependência externa desnecessária
- ❌ **Perfis totalmente flexíveis**: Complexidade sem validação de mercado
- ❌ **UI de gestão de roles no MVP**: Scope creep, não é prioritário

### Decisões Adiadas (Fase 2)
- ⏸️ **Integração com `base_user_role`**: Avaliar após 6 meses com feedback real
- ⏸️ **Customização de menus/campos**: Implementar apenas se validado
- ⏸️ **Gestão temporal de permissões**: Só se houver demanda

---

## Aprovação

**Data**: 19/01/2026  
**Autor**: AI Agent (GitHub Copilot)  
**Revisores**: Equipe de Desenvolvimento  
**Status**: Aceito (implementação iniciada)

---

## Notas de Migração

### Do RBAC-plan.md para este ADR

Este ADR **substitui completamente** o arquivo `docs/RBAC-plan.md`, consolidando:
- ✅ Todos os perfis identificados (Owner, Director, Manager, Corretor, Captador, etc.)
- ✅ Responsabilidades e permissões de cada perfil
- ✅ Jornadas de usuário (onboarding, cadastro de equipe)
- ✅ Estrutura hierárquica de grupos
- ✅ Decisão técnica de implementação

**Ação recomendada**: Deletar `docs/RBAC-plan.md` após aprovação deste ADR para evitar documentação duplicada.
**Fase 2 (condicional):**
- Após 6 meses de produção + análise de feedback

---

## Aprovação

**Data**: 19/01/2026  
**Autor**: AI Agent (GitHub Copilot)  
**Revisores**: Equipe de Desenvolvimento  
**Status**: Aceito (implementação iniciada)
