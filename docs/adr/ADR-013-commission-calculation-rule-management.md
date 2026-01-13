# ADR-013: Real Estate Commission Calculation and Rule Management

## Status
Proposto

## Contexto

O sistema de gestão imobiliária necessita de um mecanismo robusto para:
1. Calcular comissões de agentes sobre vendas e locações
2. Gerenciar regras de comissionamento por agente e tipo de transação
3. Garantir não-retroatividade (regras não afetam transações passadas)
4. Suportar múltiplos agentes em uma mesma transação (divisão de comissão)
5. Manter auditoria completa de mudanças nas regras
6. Lidar com casos extremos (comissão > valor da transação, valores zerados, limites de valores)

### Forças em jogo:
- **Multi-tenancy**: Diferentes imobiliárias (companies) podem ter políticas de comissionamento distintas
- **Flexibilidade**: Agentes podem ter regras diferentes para vendas vs. locações
- **Auditoria**: Necessidade de rastreabilidade completa para compliance e análise financeira
- **Performance**: Cálculos devem ser rápidos mesmo com grande volume de transações
- **Integridade**: Mudanças de regras não podem afetar transações já concluídas (FR-031)

### Estrutura atual:
O modelo `real.estate.property.commission` está vinculado à propriedade (`property_id`), não ao agente. Isso dificulta:
- Definir regras padrão por agente (tem que criar comissão para cada propriedade)
- Versionar regras ao longo do tempo
- Aplicar regras automaticamente em novas transações

## Decisão

### 1. **Padrão de armazenamento**: Separate Commission Rules Table com versionamento

Criar tabela **`real.estate.commission.rule`** separada para definir regras de comissionamento por agente:

```python
class CommissionRule(models.Model):
    _name = 'real.estate.commission.rule'
    _description = 'Commission Rule for Agents'
    _order = 'valid_from desc'

    # Identification
    name = fields.Char(string='Rule Name', required=True)
    agent_id = fields.Many2one('real.estate.agent', string='Agent', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('thedevkitchen.estate.company', string='Company', required=True, index=True)
    
    # Rule configuration
    transaction_type = fields.Selection([
        ('sale', 'Sale'),
        ('rental', 'Rental'),
    ], string='Transaction Type', required=True, index=True)
    
    # Commission structure
    structure_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('tiered', 'Tiered (Progressive)'),
    ], string='Commission Structure', required=True, default='percentage')
    
    # Simple percentage/fixed
    percentage = fields.Float(string='Percentage (%)', digits=(5, 2))  # e.g., 6.50%
    fixed_amount = fields.Monetary(string='Fixed Amount', currency_field='currency_id')
    
    # Constraints
    min_transaction_value = fields.Monetary(string='Min Transaction Value', currency_field='currency_id')
    max_transaction_value = fields.Monetary(string='Max Transaction Value', currency_field='currency_id')
    min_commission = fields.Monetary(string='Min Commission', currency_field='currency_id')
    max_commission = fields.Monetary(string='Max Commission', currency_field='currency_id')
    
    # Tiered structure (JSON field for progressive tiers)
    tier_config = fields.Json(string='Tier Configuration')
    # Example: [
    #   {"up_to": 100000, "percentage": 5.0},
    #   {"up_to": 300000, "percentage": 4.0},
    #   {"above": 300000, "percentage": 3.0}
    # ]
    
    # Versioning & audit
    valid_from = fields.Datetime(string='Valid From', required=True, default=fields.Datetime.now, index=True)
    valid_until = fields.Datetime(string='Valid Until', index=True)  # None = currently active
    is_active = fields.Boolean(string='Active', compute='_compute_is_active', store=True, index=True)
    replaced_by_id = fields.Many2one('real.estate.commission.rule', string='Replaced By', ondelete='set null')
    replaces_id = fields.Many2one('real.estate.commission.rule', string='Replaces', ondelete='set null')
    
    # Metadata
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)  # Soft delete
    
    # Audit fields (automatic via auditlog module)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    create_date = fields.Datetime(string='Created on', readonly=True)
    write_uid = fields.Many2one('res.users', string='Last Updated by', readonly=True)
    write_date = fields.Datetime(string='Last Updated on', readonly=True)

    @api.depends('valid_from', 'valid_until')
    def _compute_is_active(self):
        now = fields.Datetime.now()
        for rule in self:
            rule.is_active = (
                rule.valid_from <= now and 
                (not rule.valid_until or rule.valid_until > now)
            )
    
    @api.constrains('percentage', 'structure_type')
    def _check_percentage(self):
        for rule in self:
            if rule.structure_type == 'percentage' and rule.percentage:
                if rule.percentage < 0 or rule.percentage > 100:
                    raise ValidationError(_('Percentage must be between 0 and 100.'))
    
    @api.constrains('min_transaction_value', 'max_transaction_value')
    def _check_transaction_value_range(self):
        for rule in self:
            if rule.min_transaction_value and rule.max_transaction_value:
                if rule.min_transaction_value > rule.max_transaction_value:
                    raise ValidationError(_('Min transaction value cannot exceed max transaction value.'))
    
    @api.constrains('min_commission', 'max_commission')
    def _check_commission_range(self):
        for rule in self:
            if rule.min_commission and rule.max_commission:
                if rule.min_commission > rule.max_commission:
                    raise ValidationError(_('Min commission cannot exceed max commission.'))
    
    def create_new_version(self, vals):
        """Create a new version of this rule, marking current as replaced"""
        self.ensure_one()
        
        # Mark current rule as replaced
        now = fields.Datetime.now()
        self.write({
            'valid_until': now,
        })
        
        # Create new rule
        new_vals = {
            'agent_id': self.agent_id.id,
            'company_id': self.company_id.id,
            'transaction_type': self.transaction_type,
            'replaces_id': self.id,
            'valid_from': now,
        }
        new_vals.update(vals)
        
        new_rule = self.create(new_vals)
        
        # Link back
        self.replaced_by_id = new_rule.id
        
        return new_rule

    _sql_constraints = [
        ('percentage_range', 'CHECK(percentage IS NULL OR (percentage >= 0 AND percentage <= 100))', 
         'Percentage must be between 0 and 100'),
        ('positive_fixed_amount', 'CHECK(fixed_amount IS NULL OR fixed_amount >= 0)', 
         'Fixed amount must be positive'),
    ]
```

### 2. **Transaction-Rule Linking**: Snapshot at transaction creation

Criar tabela **`real.estate.commission.transaction`** que registra comissões calculadas no momento da transação:

```python
class CommissionTransaction(models.Model):
    _name = 'real.estate.commission.transaction'
    _description = 'Commission Transaction Record'
    _order = 'transaction_date desc'

    # Transaction identification
    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    transaction_type = fields.Selection([
        ('sale', 'Sale'),
        ('rental', 'Rental'),
    ], string='Type', required=True, index=True)
    
    # Relationships
    sale_id = fields.Many2one('real.estate.sale', string='Sale', ondelete='cascade', index=True)
    lease_id = fields.Many2one('real.estate.lease', string='Lease', ondelete='cascade', index=True)
    property_id = fields.Many2one('real.estate.property', string='Property', required=True, index=True)
    agent_id = fields.Many2one('real.estate.agent', string='Agent', required=True, index=True)
    company_id = fields.Many2one('thedevkitchen.estate.company', string='Company', required=True, index=True)
    
    # Snapshot of rule used (immutable after creation)
    rule_id = fields.Many2one('real.estate.commission.rule', string='Rule Applied', required=True)
    rule_snapshot = fields.Json(string='Rule Snapshot', help='Frozen copy of rule at transaction time')
    
    # Transaction values
    transaction_value = fields.Monetary(string='Transaction Value', required=True, currency_field='currency_id')
    transaction_date = fields.Datetime(string='Transaction Date', required=True, default=fields.Datetime.now, index=True)
    
    # Commission calculation
    commission_amount = fields.Monetary(string='Commission Amount', required=True, currency_field='currency_id')
    commission_percentage_applied = fields.Float(string='Percentage Applied (%)', digits=(5, 2))
    split_percentage = fields.Float(string='Split %', default=100.0, help='If multiple agents, percentage of total commission')
    
    # Payment tracking
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Payment Status', default='pending', index=True)
    payment_date = fields.Date(string='Payment Date')
    
    # Metadata
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    notes = fields.Text(string='Notes')
    
    @api.depends('agent_id', 'transaction_type', 'transaction_date')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.agent_id.name or 'Agent'} - {rec.transaction_type or 'N/A'} - {rec.transaction_date or ''}"
    
    @api.constrains('split_percentage')
    def _check_split_percentage(self):
        for rec in self:
            if rec.split_percentage < 0 or rec.split_percentage > 100:
                raise ValidationError(_('Split percentage must be between 0 and 100.'))
```

### 3. **Algoritmo de cálculo**:

```python
class RealEstateAgent(models.Model):
    _name = 'real.estate.agent'
    # ... existing fields ...
    
    commission_rule_ids = fields.One2many('real.estate.commission.rule', 'agent_id', string='Commission Rules')
    commission_transaction_ids = fields.One2many('real.estate.commission.transaction', 'agent_id', string='Commission History')
    
    def calculate_commission(self, transaction_value, transaction_type, transaction_date=None):
        """
        Calculate commission for an agent based on active rules.
        
        Args:
            transaction_value (float): Value of the transaction
            transaction_type (str): 'sale' or 'rental'
            transaction_date (datetime): Date of transaction (default: now)
        
        Returns:
            dict: {
                'commission_amount': float,
                'rule_id': int,
                'rule_snapshot': dict,
                'percentage_applied': float,
                'capped': bool,
                'warnings': list
            }
        """
        self.ensure_one()
        
        if not transaction_date:
            transaction_date = fields.Datetime.now()
        
        warnings = []
        
        # Find active rule at transaction date
        rule = self.env['real.estate.commission.rule'].search([
            ('agent_id', '=', self.id),
            ('transaction_type', '=', transaction_type),
            ('valid_from', '<=', transaction_date),
            '|',
            ('valid_until', '=', False),
            ('valid_until', '>', transaction_date),
            ('active', '=', True)
        ], limit=1, order='valid_from desc')
        
        if not rule:
            warnings.append(f"No active commission rule found for {transaction_type}")
            return {
                'commission_amount': 0.0,
                'rule_id': None,
                'rule_snapshot': None,
                'percentage_applied': 0.0,
                'capped': False,
                'warnings': warnings
            }
        
        # Check transaction value constraints
        if rule.min_transaction_value and transaction_value < rule.min_transaction_value:
            warnings.append(f"Transaction value below minimum ({rule.min_transaction_value})")
        
        if rule.max_transaction_value and transaction_value > rule.max_transaction_value:
            warnings.append(f"Transaction value above maximum ({rule.max_transaction_value})")
        
        # Calculate based on structure type
        commission_amount = 0.0
        percentage_applied = 0.0
        
        if rule.structure_type == 'percentage':
            percentage_applied = rule.percentage
            commission_amount = transaction_value * (rule.percentage / 100.0)
        
        elif rule.structure_type == 'fixed':
            commission_amount = rule.fixed_amount
        
        elif rule.structure_type == 'tiered':
            commission_amount, percentage_applied = self._calculate_tiered_commission(
                transaction_value, rule.tier_config
            )
        
        # Apply min/max caps
        capped = False
        if rule.min_commission and commission_amount < rule.min_commission:
            commission_amount = rule.min_commission
            capped = True
            warnings.append(f"Commission capped to minimum ({rule.min_commission})")
        
        if rule.max_commission and commission_amount > rule.max_commission:
            commission_amount = rule.max_commission
            capped = True
            warnings.append(f"Commission capped to maximum ({rule.max_commission})")
        
        # Edge case: commission > transaction value
        if commission_amount > transaction_value:
            warnings.append(f"Commission ({commission_amount}) exceeds transaction value ({transaction_value})")
        
        # Create rule snapshot
        rule_snapshot = {
            'rule_id': rule.id,
            'structure_type': rule.structure_type,
            'percentage': rule.percentage,
            'fixed_amount': rule.fixed_amount,
            'tier_config': rule.tier_config,
            'min_commission': rule.min_commission,
            'max_commission': rule.max_commission,
            'valid_from': rule.valid_from.isoformat() if rule.valid_from else None,
        }
        
        return {
            'commission_amount': commission_amount,
            'rule_id': rule.id,
            'rule_snapshot': rule_snapshot,
            'percentage_applied': percentage_applied,
            'capped': capped,
            'warnings': warnings
        }
    
    def _calculate_tiered_commission(self, transaction_value, tier_config):
        """
        Calculate commission using tiered/progressive structure.
        
        Example tier_config:
        [
            {"up_to": 100000, "percentage": 5.0},
            {"up_to": 300000, "percentage": 4.0},
            {"above": 300000, "percentage": 3.0}
        ]
        """
        if not tier_config:
            return 0.0, 0.0
        
        total_commission = 0.0
        remaining_value = transaction_value
        
        for tier in tier_config:
            if 'up_to' in tier:
                tier_max = tier['up_to']
                tier_percentage = tier['percentage']
                
                if remaining_value <= 0:
                    break
                
                # Calculate commission for this tier
                tier_value = min(remaining_value, tier_max)
                tier_commission = tier_value * (tier_percentage / 100.0)
                total_commission += tier_commission
                remaining_value -= tier_value
            
            elif 'above' in tier:
                # Last tier - all remaining value
                tier_percentage = tier['percentage']
                if remaining_value > 0:
                    total_commission += remaining_value * (tier_percentage / 100.0)
                break
        
        # Calculate effective percentage
        effective_percentage = (total_commission / transaction_value * 100.0) if transaction_value > 0 else 0.0
        
        return total_commission, effective_percentage


class RealEstateSale(models.Model):
    _name = 'real.estate.sale'
    _inherit = ['real.estate.sale']
    
    commission_transaction_ids = fields.One2many('real.estate.commission.transaction', 'sale_id', string='Commissions')
    
    def action_confirm_sale(self):
        """Override to auto-create commission transactions"""
        res = super().action_confirm_sale()
        self._create_commission_transactions()
        return res
    
    def _create_commission_transactions(self):
        """Create commission transaction records for all agents involved"""
        for sale in self:
            # Get all agents on the property
            agents = sale.property_id.agent_id  # Could be many2many if multiple agents
            
            if not agents:
                continue
            
            # If multiple agents, split commission equally (or use custom split logic)
            agent_count = len(agents) if hasattr(agents, '__iter__') else 1
            split_percentage = 100.0 / agent_count
            
            for agent in agents:
                # Calculate commission
                calc_result = agent.calculate_commission(
                    transaction_value=sale.sale_price,
                    transaction_type='sale',
                    transaction_date=sale.sale_date
                )
                
                # Create commission transaction record
                self.env['real.estate.commission.transaction'].create({
                    'transaction_type': 'sale',
                    'sale_id': sale.id,
                    'property_id': sale.property_id.id,
                    'agent_id': agent.id,
                    'company_id': sale.company_ids[0].id if sale.company_ids else False,
                    'rule_id': calc_result['rule_id'],
                    'rule_snapshot': calc_result['rule_snapshot'],
                    'transaction_value': sale.sale_price,
                    'transaction_date': sale.sale_date,
                    'commission_amount': calc_result['commission_amount'] * (split_percentage / 100.0),
                    'commission_percentage_applied': calc_result['percentage_applied'],
                    'split_percentage': split_percentage,
                    'currency_id': sale.property_id.currency_id.id,
                })
```

### 4. **Casos extremos (edge cases)**:

| Edge Case | Tratamento |
|-----------|-----------|
| **Comissão > Valor da Transação** | Sistema calcula e gera warning; não bloqueia. Permite revisão manual. |
| **Comissão zero/negativa** | Validação impede valores negativos. Zero é permitido (ex: isenção temporária). |
| **Múltiplos agentes na mesma propriedade** | Divisão igualitária por padrão; campo `split_percentage` permite divisão customizada. |
| **Sem regra ativa no momento da transação** | Comissão = 0, warning gerado, transação não bloqueada. |
| **Mudança de regra durante período de negociação** | Regra aplicada é a vigente na data de `transaction_date` (confirmação da venda/locação). |
| **Valor da transação fora dos limites (min/max)** | Warning gerado, mas comissão é calculada normalmente (não bloqueia). |
| **Comissão calculada fora dos limites (min/max_commission)** | Auto-aplicação do cap (mínimo ou máximo), flag `capped=True`. |
| **Agent desativado após transação** | Registro de comissão permanece; histórico preservado. |
| **Regra deletada (soft-delete)** | `rule_snapshot` preserva dados; cálculo continua disponível. |

### 5. **Performance & Indexação**:

```sql
-- Índices críticos para performance
CREATE INDEX idx_commission_rule_active_lookup 
ON real_estate_commission_rule(agent_id, transaction_type, valid_from DESC, valid_until) 
WHERE active = true;

CREATE INDEX idx_commission_transaction_agent_date 
ON real_estate_commission_transaction(agent_id, transaction_date DESC);

CREATE INDEX idx_commission_transaction_company_status 
ON real_estate_commission_transaction(company_id, payment_status);
```

## Consequências

### Positivas:

1. **Não-retroatividade garantida**: Snapshot de regras no momento da transação garante que mudanças futuras não afetam comissões já calculadas (FR-031)

2. **Auditoria completa**: 
   - Histórico de regras (versioning via `valid_from`/`valid_until`)
   - Snapshot imutável em cada transação
   - Integração com módulo `auditlog` para tracking de mudanças

3. **Flexibilidade**:
   - Suporta percentual, fixo e tiered (progressivo)
   - Constraints customizáveis (min/max valores e comissões)
   - Divisão de comissão entre múltiplos agentes

4. **Multi-tenancy completo**:
   - Regras isoladas por company
   - Comissões calculadas no contexto da company

5. **Performance otimizada**:
   - Cálculo acontece apenas uma vez (na confirmação da transação)
   - Índices otimizados para queries de listagem e agregação
   - Cache de valores calculados

6. **Edge cases cobertos**: Warnings informativos sem bloquear operações críticas

### Negativas:

1. **Complexidade adicional**:
   - Três modelos inter-relacionados (Rule, Transaction, Property/Sale/Lease)
   - Lógica de versioning de regras requer cuidado na API

2. **Migração de dados existentes**:
   - `real.estate.property.commission` atual está vinculado a propriedades
   - Migração necessária para converter em regras por agente

3. **Storage overhead**:
   - Snapshot JSON em cada transação aumenta uso de storage
   - Justificado para auditoria, mas pode crescer significativamente

4. **Cálculos manuais complexos**:
   - Tiered commission requer configuração JSON (não há UI amigável por padrão)
   - Possível necessidade de wizard/helper para criar tiers

### Riscos mitigados:

- **Inconsistência temporal**: Snapshot elimina race conditions entre mudança de regra e criação de transação
- **Perda de histórico**: Soft-delete + versioning preservam dados mesmo após mudanças
- **Performance em consultas**: Índices compostos garantem queries rápidas mesmo com milhares de transações

## Alternativas consideradas

### Alternativa 1: Embedded rules in Agent model
**Abordagem**: Campos de comissão diretamente no modelo `real.estate.agent`.

**Prós**: Simples, sem tabelas adicionais.

**Contras**: 
- Sem histórico/versioning
- Difícil suportar múltiplas regras por agente (venda vs. locação)
- Não atende FR-031 (não-retroatividade)

**Rejeição**: Insuficiente para requisitos de auditoria e flexibilidade.

---

### Alternativa 2: Property-centric commission (modelo atual)
**Abordagem**: Manter `real.estate.property.commission` vinculado à propriedade.

**Prós**: Já implementado, granularidade por propriedade.

**Contras**:
- Não há regras padrão por agente (requer criar comissão para cada propriedade)
- Dificulta análise de performance por agente
- Sem versionamento ou histórico

**Rejeição**: Não escala para cenário de múltiplas transações e análise de agentes.

---

### Alternativa 3: Event sourcing puro
**Abordagem**: Armazenar eventos de mudança de regras e recalcular comissões sob demanda.

**Prós**: Histórico completo, flexibilidade total.

**Contras**:
- Overhead de performance (recalcular a cada consulta)
- Complexidade de implementação
- Odoo ORM não é otimizado para event sourcing

**Rejeição**: Over-engineering para o caso de uso atual.

---

### Alternativa 4: Computed fields sem snapshot
**Abordagem**: Comissão como campo computed que busca regra ativa dinamicamente.

**Prós**: Simples, sem storage adicional.

**Contras**:
- **Viola FR-031**: Mudança de regra afetaria transações passadas
- Sem auditoria de regra aplicada no passado
- Performance ruim (recomputa a cada acesso)

**Rejeição**: Inaceitável para compliance e auditoria financeira.

## Referências

- **FR-031** (spec 004-agent-management): Non-retroactive rule application
- **ADR-004**: Nomenclatura de módulos/tabelas (seguido: `real.estate.commission.rule`)
- **ADR-003**: Mandatory test coverage (testes de comissão obrigatórios)
- **ADR-008**: API Security & Multi-tenancy (isolamento por company aplicado)
- Brazilian real estate commission practices: typically 5-8% for sales, 1 month rent (8.33%) for rentals
- Odoo Best Practices: Computed fields, constraints, and auditlog integration

## Notas de implementação

1. **Migração de dados**: Criar script para converter `real.estate.property.commission` em `real.estate.commission.rule`
2. **API Endpoints**:
   - `POST /api/v1/agents/{id}/commission-rules` - Criar regra
   - `PUT /api/v1/agents/{id}/commission-rules/{rule_id}` - Atualizar (cria nova versão)
   - `GET /api/v1/agents/{id}/commission-rules` - Listar regras (incluir histórico)
   - `POST /api/v1/agents/{id}/calculate-commission` - Simular cálculo
3. **Tests obrigatórios** (ADR-003):
   - Unit tests para `calculate_commission()` com todos os edge cases
   - Integration tests para criação de transações em vendas/locações
   - Isolation tests para multi-tenancy (company separation)
4. **Documentação OpenAPI** (ADR-005): Schemas completos para Rule e Transaction models
5. **UI/UX**: Wizard para criação de regras tiered (simplificar JSON config)

---

## Appendix A: Quick Reference Summary

### TL;DR

**Decision**: Use separate `real.estate.commission.rule` table with versioning + snapshot-based `real.estate.commission.transaction` table.

**Why**: Guarantees non-retroactivity (FR-031), full audit trail, multi-agent support, and flexible rule structures.

### Key Components

#### 1. Commission Rule (Template)
- **Table**: `real.estate.commission.rule`
- **Purpose**: Define agent-specific commission rules
- **Versioning**: `valid_from` / `valid_until` for historical tracking
- **Supports**: Percentage, Fixed, Tiered (progressive)

#### 2. Commission Transaction (Snapshot)
- **Table**: `real.estate.commission.transaction`
- **Purpose**: Immutable record of commission calculated at transaction time
- **Key feature**: `rule_snapshot` (JSON) - frozen copy of rule
- **Linked to**: Sale or Lease

#### 3. Calculation Algorithm
- **Input**: `transaction_value`, `agent_id`, `transaction_type`, `transaction_date`
- **Output**: Commission amount + metadata (warnings, caps applied, etc.)
- **Location**: `RealEstateAgent.calculate_commission()`

### Data Model

```
┌─────────────────────────────┐
│ real.estate.commission.rule │  ← Agent-specific rules
│ ─────────────────────────── │     (versioned, can have multiple)
│ - agent_id                  │
│ - transaction_type          │
│ - structure_type            │
│ - percentage / fixed_amount │
│ - valid_from / valid_until  │
│ - min/max constraints       │
└─────────────────────────────┘
           ↓ (used by)
┌──────────────────────────────────┐
│ real.estate.commission.transaction│ ← Immutable transaction records
│ ─────────────────────────────────│    (created on sale/lease confirm)
│ - agent_id                       │
│ - sale_id / lease_id             │
│ - rule_id                        │
│ - rule_snapshot (JSON)           │    ← Frozen copy!
│ - transaction_value              │
│ - commission_amount              │
│ - split_percentage               │
│ - payment_status                 │
└──────────────────────────────────┘
```

### How It Works

**Creating a new rule:**
```python
# Manager creates 6% commission rule for sales
rule = env['real.estate.commission.rule'].create({
    'name': 'Standard Sales Commission',
    'agent_id': agent.id,
    'company_id': company.id,
    'transaction_type': 'sale',
    'structure_type': 'percentage',
    'percentage': 6.0,
    'valid_from': '2026-01-01 00:00:00',
})
```

**Updating a rule (creates new version):**
```python
# Change to 7% - creates new rule, marks old as replaced
new_rule = old_rule.create_new_version({
    'percentage': 7.0,
    'name': 'Updated Sales Commission',
})
# old_rule.valid_until = now
# old_rule.replaced_by_id = new_rule.id
```

**Automatic calculation on sale:**
```python
# When sale is confirmed
sale.action_confirm_sale()
  ↓
  _create_commission_transactions()
  ↓
  agent.calculate_commission(
      transaction_value=300000,
      transaction_type='sale',
      transaction_date='2026-06-15'
  )
  ↓
  # Finds rule active on 2026-06-15
  # Calculates: 300000 * 6% = 18000
  # Creates commission.transaction with snapshot
```

**Non-retroactivity in action:**
```
Timeline:
2026-01-01: Rule A created (6%)
2026-03-15: Sale 1 confirmed → uses Rule A (6%)
2026-05-01: Rule B created (7%), Rule A expires
2026-07-20: Sale 2 confirmed → uses Rule B (7%)

Result:
- Sale 1: commission = 6% (forever, even after rule change)
- Sale 2: commission = 7%
```

### Edge Cases Handled

| Scenario | Solution |
|----------|----------|
| **Commission > Transaction** | Allow + warning (manual review) |
| **No active rule** | Commission = 0 + warning |
| **Multiple agents** | Split via `split_percentage` field |
| **Rule change mid-negotiation** | Rule applied = rule active at `transaction_date` |
| **Min/max caps** | Auto-apply, set `capped` flag |
| **Tiered progressive** | JSON config: `[{up_to: 100k, %: 5}, {above: 100k, %: 3}]` |

### Benefits

✅ **Non-retroactive**: Snapshots prevent past changes  
✅ **Full audit**: Version history + `auditlog` module  
✅ **Flexible**: Percentage, fixed, tiered structures  
✅ **Multi-agent**: Built-in commission splitting  
✅ **Multi-tenant**: Company isolation enforced  
✅ **Performance**: Calculated once, cached forever  

### Integration Points

**API Endpoints (to be created):**
- `POST /api/v1/agents/{id}/commission-rules`
- `PUT /api/v1/agents/{id}/commission-rules/{rule_id}` (creates new version)
- `GET /api/v1/agents/{id}/commission-rules?include_history=true`
- `POST /api/v1/agents/{id}/calculate-commission` (simulation)
- `GET /api/v1/commission-transactions?agent_id={id}&status=pending`

**Models to extend:**
- ✅ `real.estate.agent` - Add `calculate_commission()` method
- ✅ `real.estate.sale` - Override `action_confirm_sale()`
- ✅ `real.estate.lease` - Override confirm method

**Tests required (ADR-003):**
- ✅ Unit: `test_calculate_commission_percentage()`
- ✅ Unit: `test_calculate_commission_tiered()`
- ✅ Unit: `test_commission_caps()`
- ✅ Integration: `test_sale_creates_commission_transaction()`
- ✅ Integration: `test_multiple_agents_split()`
- ✅ Isolation: `test_commission_company_isolation()`

### Migration Plan

**Phase 1: Create new tables**
```bash
# Add models to __init__.py
# Upgrade module
odoo -u quicksol_estate
```

**Phase 2: Migrate existing data**
```python
# Script to convert property.commission → commission.rule
for prop_comm in env['real.estate.property.commission'].search([]):
    if prop_comm.agent_id:
        env['real.estate.commission.rule'].create({
            'name': f'Migrated: {prop_comm.name}',
            'agent_id': prop_comm.agent_id.id,
            'transaction_type': 'sale' if prop_comm.applies_to == 'sale' else 'rental',
            'structure_type': prop_comm.commission_type,
            'percentage': prop_comm.value if prop_comm.commission_type == 'percentage' else 0,
            'fixed_amount': prop_comm.value if prop_comm.commission_type == 'fixed' else 0,
            'valid_from': '2024-01-01',  # Historical date
        })
```

**Phase 3: Deprecate old model**
- Mark `real.estate.property.commission` as deprecated
- Keep for 6 months, then remove

---

## Appendix B: Executive Summary for Stakeholders

### Business Problem

Real estate agencies need to:
1. **Calculate commissions automatically** when agents close sales or rental deals
2. **Support flexible commission structures** (percentage, fixed amount, progressive tiers)
3. **Track commission changes over time** without affecting past transactions
4. **Handle multiple agents** on the same property (commission splitting)
5. **Maintain compliance** with complete audit trail for financial reporting

**Current limitation**: Commissions are tied to properties, not agents. No versioning, no historical tracking, manual calculation required.

### Proposed Solution Components

```
┌──────────────────────────┐
│  Commission Rule         │  ← Define once per agent
│  (Template/Policy)       │     (e.g., "6% on sales")
└────────────┬─────────────┘
             │ Applied when transaction occurs
             ▼
┌──────────────────────────┐
│  Commission Transaction  │  ← Created automatically
│  (Immutable Record)      │     (e.g., "Agent A earned $18k")
└──────────────────────────┘
```

**Workflow:**
1. **Setup**: Manager creates commission rule for Agent A: "6% on all sales"
2. **Transaction**: Agent A closes a sale for $300,000
3. **Auto-calculation**: System calculates $18,000 commission (300k × 6%)
4. **Snapshot**: Creates permanent record with frozen rule (non-retroactive)
5. **Payment**: Manager marks commission as paid when processed

**Non-Retroactivity Example:**
```
Jan 1: Rule created → 6% on sales
Mar 15: Sale confirmed → Commission = $18,000 (6%)
May 1: Rule updated → 7% on sales
Jul 20: New sale confirmed → Commission = $28,000 (7%)

✅ March sale remains at $18,000 forever (frozen snapshot)
```

### Business Benefits

| Benefit | Impact |
|---------|--------|
| **Automation** | Eliminate manual commission calculation errors |
| **Transparency** | Agents can see commission history and calculations |
| **Compliance** | Complete audit trail for accounting and tax purposes |
| **Flexibility** | Support any commission structure (%, fixed, tiered) |
| **Fairness** | Rule changes don't affect past deals (non-retroactive) |
| **Scalability** | Handle multiple agents per property, thousands of transactions |

### Supported Commission Structures

1. **Simple Percentage**: 6% on all sales
2. **Fixed Amount**: $5,000 per rental deal
3. **Tiered (Progressive)**: First $100k → 5%, Next $200k → 4%, Above $300k → 3%
4. **Constraints**: Min transaction value, max commission caps

### Security & Multi-Tenancy

- ✅ **Company isolation**: Company A cannot see Company B's commission data
- ✅ **Role-based access**: Managers can edit rules, agents can only view
- ✅ **API authentication**: All endpoints protected with JWT + session
- ✅ **Audit logging**: Every change tracked (who, when, what)

### Performance

- **Calculation speed**: < 100ms per transaction (one-time calculation)
- **Query speed**: < 500ms to list 1,000 commission records
- **Scalability**: Supports 10,000+ transactions per company
- **Storage**: ~1KB per transaction (includes rule snapshot)

### Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1**: Data models & core logic | 2 weeks | Database tables, calculation algorithm |
| **Phase 2**: API & integration | 2 weeks | REST endpoints, sale/lease integration |
| **Phase 3**: UI & views | 1 week | Admin screens, agent dashboards |
| **Phase 4**: Testing & QA | 1 week | 100% test coverage, E2E tests |
| **Phase 5**: Documentation & training | 1 week | User guides, API docs, training |
| **Phase 6**: Deployment | 1 week | Migration, rollout, monitoring |
| **Total** | **8 weeks** | Full production-ready system |

### Future Enhancements (Post-MVP)

- 📊 Commission analytics dashboard: Top performers, trends, forecasting
- 🔔 Automated payment reminders: Notify when commissions are due
- 📧 Email notifications: Alert agents when commissions are earned/paid
- 🏆 Gamification: Leaderboards, achievement badges for top agents
- 📱 Mobile app integration: View commissions on mobile
- 🤖 AI-powered recommendations: Suggest optimal commission structures

### Success Criteria

The commission system will be considered successful when:
- ✅ 100% of sales/rentals auto-calculate commissions
- ✅ Zero manual calculation errors reported
- ✅ Complete audit trail for all commission changes
- ✅ < 500ms response time for commission queries
- ✅ 95%+ user satisfaction (managers + agents)
- ✅ Passes all security/isolation tests (multi-tenancy)

### Frequently Asked Questions

**Q: What happens if we change a commission rule?**  
A: A new version is created. Old transactions keep the old rate, new transactions use the new rate.

**Q: Can we have different rules for sales vs. rentals?**  
A: Yes! Each agent can have separate rules for sales and rentals.

**Q: What if two agents work on the same property?**  
A: Each agent's commission is calculated separately, then split (default 50/50, customizable).

**Q: Can we set commission caps?**  
A: Yes! You can set min/max transaction values and min/max commission amounts.

**Q: How do we track who changed commission rules?**  
A: Every change is logged with user ID, timestamp, and what changed (via auditlog module).

**Q: What if an agent is deleted?**  
A: Agents are soft-deleted (deactivated). Historical commissions remain accessible.

### Stakeholder Sign-Off

| Role | Name | Approval | Date |
|------|------|----------|------|
| Product Owner | [Pending] | ☐ Approved | ___ |
| Tech Lead | [Pending] | ☐ Approved | ___ |
| Finance Manager | [Pending] | ☐ Approved | ___ |
| Security Officer | [Pending] | ☐ Approved | ___ |

---

## Appendix C: Implementation Checklist

### Phase 1: Data Models (Priority: HIGH)

- [ ] **Create `real.estate.commission.rule` model**
  - [ ] Add to `models/__init__.py`
  - [ ] Create `models/commission_rule.py`
  - [ ] Fields: agent_id, company_id, transaction_type, structure_type, percentage, fixed_amount, tier_config
  - [ ] Versioning: valid_from, valid_until, is_active, replaced_by_id, replaces_id
  - [ ] Constraints: min/max transaction values, min/max commission
  - [ ] SQL constraints: percentage range, positive amounts
  - [ ] Computed field: `_compute_is_active()`
  - [ ] Method: `create_new_version(vals)`
  - [ ] Add security/ir.model.access.csv rules

- [ ] **Create `real.estate.commission.transaction` model**
  - [ ] Create `models/commission_transaction.py`
  - [ ] Fields: transaction_type, sale_id, lease_id, property_id, agent_id, company_id
  - [ ] Snapshot: rule_id, rule_snapshot (JSON)
  - [ ] Values: transaction_value, transaction_date, commission_amount, split_percentage
  - [ ] Payment tracking: payment_status, payment_date
  - [ ] Computed field: `_compute_name()`
  - [ ] Constraint: `_check_split_percentage()`
  - [ ] Add security/ir.model.access.csv rules

- [ ] **Update `real.estate.agent` model**
  - [ ] Add field: `commission_rule_ids = One2many('real.estate.commission.rule', 'agent_id')`
  - [ ] Add field: `commission_transaction_ids = One2many('real.estate.commission.transaction', 'agent_id')`
  - [ ] Add method: `calculate_commission(transaction_value, transaction_type, transaction_date)`
  - [ ] Add method: `_calculate_tiered_commission(transaction_value, tier_config)`

- [ ] **Update `real.estate.sale` model**
  - [ ] Add field: `commission_transaction_ids = One2many('real.estate.commission.transaction', 'sale_id')`
  - [ ] Override/create: `action_confirm_sale()`
  - [ ] Add method: `_create_commission_transactions()`

- [ ] **Update `real.estate.lease` model**
  - [ ] Add field: `commission_transaction_ids = One2many('real.estate.commission.transaction', 'lease_id')`
  - [ ] Override/create: `action_confirm_lease()` or similar
  - [ ] Add method: `_create_commission_transactions()`

### Phase 2: Database & Migrations (Priority: HIGH)

- [ ] **Create database indices**
  ```sql
  CREATE INDEX idx_commission_rule_active_lookup 
  ON real_estate_commission_rule(agent_id, transaction_type, valid_from DESC, valid_until) 
  WHERE active = true;

  CREATE INDEX idx_commission_transaction_agent_date 
  ON real_estate_commission_transaction(agent_id, transaction_date DESC);

  CREATE INDEX idx_commission_transaction_company_status 
  ON real_estate_commission_transaction(company_id, payment_status);
  ```

- [ ] **Create data migration script**
  - [ ] Script to convert `real.estate.property.commission` → `real.estate.commission.rule`
  - [ ] Set default `valid_from` date (e.g., 2024-01-01)
  - [ ] Preserve agent_id, commission_type, value, applies_to
  - [ ] Test on dev database first
  - [ ] Document migration steps in module upgrade

- [ ] **Deprecation plan for old model**
  - [ ] Mark `real.estate.property.commission` as deprecated (add warning in docstring)
  - [ ] Keep for 6 months for backward compatibility
  - [ ] Schedule removal for version 2.0

### Phase 3: Views & UI (Priority: MEDIUM)

- [ ] **Commission Rule views**
  - [ ] Create `views/commission_rule_views.xml`
  - [ ] Tree view: name, agent_id, transaction_type, percentage/fixed_amount, valid_from, is_active
  - [ ] Form view: all fields, with notebook for constraints and tiered config
  - [ ] Search view: filter by agent, transaction_type, active status
  - [ ] Action: `action_commission_rule_list`
  - [ ] Menu: Real Estate > Configuration > Commission Rules

- [ ] **Commission Transaction views**
  - [ ] Create `views/commission_transaction_views.xml`
  - [ ] Tree view: agent_id, transaction_type, transaction_value, commission_amount, payment_status
  - [ ] Form view: all fields (readonly after creation)
  - [ ] Kanban view: group by payment_status
  - [ ] Search view: filter by agent, payment_status, date range
  - [ ] Action: `action_commission_transaction_list`
  - [ ] Menu: Real Estate > Commissions > Commission History

- [ ] **Agent form view enhancements**
  - [ ] Add notebook tab "Commission Rules"
  - [ ] Add notebook tab "Commission History"
  - [ ] Add button "Configure Commission" → wizard
  - [ ] Add smart button "Pending Commissions" (count)

- [ ] **Commission setup wizard** (optional, nice-to-have)
  - [ ] Wizard to create commission rules with validation
  - [ ] Simplify tiered structure creation (avoid raw JSON editing)
  - [ ] Preview calculation examples

### Phase 4: API Endpoints (Priority: HIGH)

- [ ] **POST `/api/v1/agents/{id}/commission-rules`**
  - [ ] Controller: `CommissionRuleController.create_rule()`
  - [ ] Decorators: `@require_jwt`, `@require_session`, `@require_company`
  - [ ] Validate: percentage range, transaction_type, min/max values
  - [ ] Response: HTTP 201 + rule object
  - [ ] OpenAPI schema (ADR-005)

- [ ] **PUT `/api/v1/agents/{id}/commission-rules/{rule_id}`**
  - [ ] Controller: `CommissionRuleController.update_rule()`
  - [ ] Logic: Call `rule.create_new_version(vals)` (non-destructive update)
  - [ ] Response: HTTP 200 + new rule object
  - [ ] OpenAPI schema

- [ ] **GET `/api/v1/agents/{id}/commission-rules`**
  - [ ] Controller: `CommissionRuleController.list_rules()`
  - [ ] Query params: `?include_history=true`, `?transaction_type=sale`
  - [ ] Response: HTTP 200 + list of rules
  - [ ] HATEOAS links (ADR-007)
  - [ ] OpenAPI schema

- [ ] **DELETE `/api/v1/agents/{id}/commission-rules/{rule_id}`**
  - [ ] Controller: `CommissionRuleController.delete_rule()`
  - [ ] Logic: Soft delete (set active=False)
  - [ ] Validate: Cannot delete if used in pending transactions
  - [ ] Response: HTTP 204

- [ ] **POST `/api/v1/agents/{id}/calculate-commission`**
  - [ ] Controller: `CommissionRuleController.simulate_commission()`
  - [ ] Body: `{transaction_value, transaction_type, transaction_date?}`
  - [ ] Response: HTTP 200 + calculation result (amount, warnings, rule_id)
  - [ ] OpenAPI schema

- [ ] **GET `/api/v1/commission-transactions`**
  - [ ] Controller: `CommissionTransactionController.list_transactions()`
  - [ ] Query params: `?agent_id=X`, `?status=pending`, `?from_date=...`
  - [ ] Response: HTTP 200 + paginated list
  - [ ] HATEOAS links
  - [ ] OpenAPI schema

- [ ] **PUT `/api/v1/commission-transactions/{id}/mark-paid`**
  - [ ] Controller: `CommissionTransactionController.mark_paid()`
  - [ ] Body: `{payment_date}`
  - [ ] Response: HTTP 200
  - [ ] OpenAPI schema

### Phase 5: Tests (Priority: MANDATORY - ADR-003)

**Unit Tests - Commission Rule Model:**
- [ ] `test_commission_rule_creation()`
- [ ] `test_commission_rule_validation_percentage_range()`
- [ ] `test_commission_rule_validation_min_max_transaction()`
- [ ] `test_commission_rule_validation_min_max_commission()`
- [ ] `test_commission_rule_is_active_computed()`
- [ ] `test_commission_rule_create_new_version()`
- [ ] `test_commission_rule_version_chain()`

**Unit Tests - Commission Calculation:**
- [ ] `test_calculate_commission_percentage_simple()`
- [ ] `test_calculate_commission_fixed_amount()`
- [ ] `test_calculate_commission_tiered_single_tier()`
- [ ] `test_calculate_commission_tiered_multiple_tiers()`
- [ ] `test_calculate_commission_with_min_cap()`
- [ ] `test_calculate_commission_with_max_cap()`
- [ ] `test_calculate_commission_no_active_rule()`
- [ ] `test_calculate_commission_exceeds_transaction_value()`
- [ ] `test_calculate_commission_at_specific_date()`

**Unit Tests - Commission Transaction:**
- [ ] `test_commission_transaction_creation()`
- [ ] `test_commission_transaction_snapshot_immutable()`
- [ ] `test_commission_transaction_split_percentage_validation()`
- [ ] `test_commission_transaction_payment_status_workflow()`

**Integration Tests - Sale/Lease Flow:**
- [ ] `test_sale_confirm_creates_commission_transaction()`
- [ ] `test_sale_with_multiple_agents_creates_split_transactions()`
- [ ] `test_lease_confirm_creates_commission_transaction()`
- [ ] `test_commission_uses_rule_active_at_transaction_date()`
- [ ] `test_rule_change_does_not_affect_existing_transactions()` ← **KEY TEST**

**Integration Tests - API:**
- [ ] `test_api_create_commission_rule_success()`
- [ ] `test_api_create_commission_rule_invalid_percentage()`
- [ ] `test_api_update_commission_rule_creates_version()`
- [ ] `test_api_list_commission_rules_with_history()`
- [ ] `test_api_calculate_commission_simulation()`
- [ ] `test_api_list_commission_transactions_filtered()`
- [ ] `test_api_mark_commission_paid()`

**Isolation Tests - Multi-tenancy (ADR-008):**
- [ ] `test_commission_rule_company_isolation()`
- [ ] `test_commission_transaction_company_isolation()`
- [ ] `test_api_cannot_access_other_company_rules()`
- [ ] `test_api_cannot_access_other_company_transactions()`

**Cypress E2E Tests (ADR-002):**
- [ ] `test_manager_creates_commission_rule_via_ui.cy.js`
- [ ] `test_agent_completes_sale_commission_calculated.cy.js`
- [ ] `test_manager_views_pending_commissions.cy.js`
- [ ] `test_rule_change_does_not_affect_old_sales.cy.js`

### Phase 6: Documentation (Priority: HIGH)

- [ ] **Update `__manifest__.py`**
  - [ ] Add "Commission Rule Management" to description
  - [ ] Update version number
  - [ ] Add new data files (views, security, etc.)

- [ ] **OpenAPI documentation** (ADR-005)
  - [ ] Document all commission endpoints
  - [ ] Request/Response schemas for Rule and Transaction
  - [ ] Include examples for tiered structure JSON
  - [ ] Document query parameters and filters

- [ ] **User documentation**
  - [ ] Create `docs/commission-setup-guide.md`
  - [ ] How to create commission rules
  - [ ] How to interpret tiered structures
  - [ ] How to view commission history
  - [ ] FAQ for edge cases

- [ ] **Developer documentation**
  - [ ] Update `README.md` in module
  - [ ] Document `calculate_commission()` API
  - [ ] Document rule versioning workflow
  - [ ] Document migration steps

- [ ] **Translation files**
  - [ ] Update `i18n/pt_BR.po` with new strings
  - [ ] Translate all field labels and help texts

### Phase 7: Security & Permissions (Priority: HIGH)

- [ ] **Access rights (`security/ir.model.access.csv`)**
  - [ ] `access_commission_rule_manager` - Full access
  - [ ] `access_commission_rule_agent` - Read only
  - [ ] `access_commission_transaction_manager` - Full access
  - [ ] `access_commission_transaction_agent` - Read only (own records)

- [ ] **Record rules (`security/commission_security.xml`)**
  - [ ] Company isolation for commission rules
  - [ ] Company isolation for commission transactions
  - [ ] Agents can only see own commission transactions

- [ ] **API endpoint protection**
  - [ ] All endpoints: `@require_jwt` + `@require_session` + `@require_company`
  - [ ] Validate company context in all operations
  - [ ] Prevent cross-company data access

### Phase 8: Performance Optimization (Priority: MEDIUM)

- [ ] **Database optimization**
  - [ ] Verify all indices are created
  - [ ] Run EXPLAIN on common queries
  - [ ] Optimize ORM queries (avoid N+1)

- [ ] **Caching strategy**
  - [ ] Cache active rules per agent (TTL: 1 hour)
  - [ ] Invalidate cache on rule update
  - [ ] Cache commission totals per agent/period

- [ ] **Batch operations**
  - [ ] Bulk commission transaction creation for mass sales
  - [ ] Batch payment status updates

### Phase 9: Deployment & Rollout (Priority: HIGH)

- [ ] **Pre-deployment checklist**
  - [ ] All tests passing (unit, integration, isolation, E2E)
  - [ ] Code review completed
  - [ ] OpenAPI documentation reviewed
  - [ ] Migration script tested on staging

- [ ] **Deployment steps**
  1. [ ] Backup production database
  2. [ ] Deploy code to staging
  3. [ ] Run migration script on staging
  4. [ ] Run full test suite on staging
  5. [ ] Deploy to production (low-traffic window)
  6. [ ] Run migration script on production
  7. [ ] Verify data integrity post-migration
  8. [ ] Monitor for 48 hours

- [ ] **Rollback plan**
  - [ ] Document rollback SQL scripts
  - [ ] Keep old model active for 1 week (just in case)
  - [ ] Monitor error logs for migration issues

### Phase 10: Training & Support (Priority: MEDIUM)

- [ ] **Internal training**
  - [ ] Train managers on commission rule setup
  - [ ] Train agents on viewing commission history
  - [ ] Train accounting on payment tracking

- [ ] **Support documentation**
  - [ ] Create FAQ for common questions
  - [ ] Document troubleshooting steps
  - [ ] Create video tutorial (optional)

### Definition of Done

A phase is considered complete when:
- ✅ All checkboxes in the phase are marked complete
- ✅ All related tests are passing (unit + integration + E2E)
- ✅ Code review approved by at least 1 senior developer
- ✅ OpenAPI documentation updated and validated
- ✅ Security review completed (no cross-company data leakage)
- ✅ Performance benchmarks met (calculation < 100ms, list < 500ms)

### Progress Tracking

| Phase | Status | Completed | Total | % Complete |
|-------|--------|-----------|-------|------------|
| Phase 1: Models | 🔴 Not Started | 0 | 12 | 0% |
| Phase 2: Database | 🔴 Not Started | 0 | 5 | 0% |
| Phase 3: Views | 🔴 Not Started | 0 | 11 | 0% |
| Phase 4: API | 🔴 Not Started | 0 | 8 | 0% |
| Phase 5: Tests | 🔴 Not Started | 0 | 31 | 0% |
| Phase 6: Docs | 🔴 Not Started | 0 | 9 | 0% |
| Phase 7: Security | 🔴 Not Started | 0 | 6 | 0% |
| Phase 8: Performance | 🔴 Not Started | 0 | 5 | 0% |
| Phase 9: Deployment | 🔴 Not Started | 0 | 11 | 0% |
| Phase 10: Training | 🔴 Not Started | 0 | 4 | 0% |
| **TOTAL** | 🔴 | **0** | **102** | **0%** |

Legend:
- 🔴 Not Started (0%)
- 🟡 In Progress (1-99%)
- 🟢 Complete (100%)

### Quick Start Commands

```bash
# 1. Create models
cd 18.0/extra-addons/quicksol_estate
touch models/commission_rule.py
touch models/commission_transaction.py

# 2. Update module
docker compose exec odoo odoo -u quicksol_estate --stop-after-init

# 3. Run tests
docker compose exec odoo odoo -u quicksol_estate --test-enable --stop-after-init

# 4. Check lint
cd 18.0
./lint.sh extra-addons/quicksol_estate/models/commission_rule.py
```

---

## Appendix D: Visual Flow Diagrams

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMMISSION CALCULATION FLOW                      │
└─────────────────────────────────────────────────────────────────────┘

STEP 1: RULE SETUP
┌─────────────────────┐
│   Manager/Admin     │
└──────────┬──────────┘
           │ POST /api/v1/agents/{id}/commission-rules
           ▼
┌─────────────────────────────────┐
│ real.estate.commission.rule     │
│ ─────────────────────────────── │
│ agent_id: 42                    │
│ transaction_type: 'sale'        │
│ structure_type: 'percentage'    │
│ percentage: 6.0                 │
│ valid_from: 2026-01-01          │
│ valid_until: NULL (active)      │
└─────────────────────────────────┘


STEP 2: TRANSACTION OCCURS
┌─────────────────────┐
│   Agent/Manager     │
└──────────┬──────────┘
           │ Creates/confirms sale
           ▼
┌─────────────────────────────────┐
│ real.estate.sale                │
│ ─────────────────────────────── │
│ property_id: 100                │
│ sale_price: 300,000             │
│ sale_date: 2026-06-15           │
│ agent_id: 42                    │
└──────────┬──────────────────────┘
           │ action_confirm_sale()
           ▼


STEP 3: AUTO-CALCULATION
┌────────────────────────────────────────────────────────────┐
│ agent.calculate_commission()                               │
│ ────────────────────────────────────────────────────────── │
│                                                            │
│ INPUT:                                                     │
│   transaction_value: 300,000                               │
│   transaction_type: 'sale'                                 │
│   transaction_date: 2026-06-15                             │
│   agent_id: 42                                             │
│                                                            │
│ PROCESS:                                                   │
│ 1. Find active rule at 2026-06-15                          │
│    → Query: valid_from <= date AND valid_until > date      │
│                                                            │
│ 2. Apply structure:                                        │
│    ├─ percentage: 300,000 * 6% = 18,000                    │
│    ├─ fixed: use fixed_amount                              │
│    └─ tiered: progressive calculation                      │
│                                                            │
│ 3. Check constraints:                                      │
│    ├─ min_transaction_value: PASS                          │
│    ├─ max_transaction_value: PASS                          │
│    ├─ min_commission: PASS (or cap to min)                 │
│    └─ max_commission: PASS (or cap to max)                 │
│                                                            │
│ 4. Handle edge cases:                                      │
│    ├─ Commission > transaction? → Warning                  │
│    ├─ No active rule? → commission = 0                     │
│    └─ Multiple agents? → Split percentage                  │
│                                                            │
│ OUTPUT:                                                    │
│   commission_amount: 18,000                                │
│   rule_id: 15                                              │
│   rule_snapshot: {...}  ← Frozen JSON                      │
│   percentage_applied: 6.0                                  │
│   capped: false                                            │
│   warnings: []                                             │
└────────────────────────────────────────────────────────────┘
           │
           ▼


STEP 4: CREATE IMMUTABLE RECORD
┌─────────────────────────────────────────────┐
│ real.estate.commission.transaction          │
│ ─────────────────────────────────────────── │
│ transaction_type: 'sale'                    │
│ sale_id: 500                                │
│ property_id: 100                            │
│ agent_id: 42                                │
│ company_id: 1                               │
│                                             │
│ rule_id: 15                                 │
│ rule_snapshot: {                            │  ← FROZEN
│   "structure_type": "percentage",           │     SNAPSHOT
│   "percentage": 6.0,                        │
│   "valid_from": "2026-01-01",               │
│   ...                                       │
│ }                                           │
│                                             │
│ transaction_value: 300,000                  │
│ transaction_date: 2026-06-15                │
│ commission_amount: 18,000                   │
│ commission_percentage_applied: 6.0          │
│ split_percentage: 100.0                     │
│                                             │
│ payment_status: 'pending'                   │
│ payment_date: NULL                          │
└─────────────────────────────────────────────┘


STEP 5: FUTURE RULE CHANGE (Non-Retroactive)
┌─────────────────────┐
│   Manager           │
└──────────┬──────────┘
           │ PUT /api/v1/agents/{id}/commission-rules/{rule_id}
           │ Change percentage to 7%
           ▼
┌─────────────────────────────────┐
│ OLD rule (id: 15)               │
│ ─────────────────────────────── │
│ percentage: 6.0                 │
│ valid_from: 2026-01-01          │
│ valid_until: 2026-08-01 ← SET   │
│ replaced_by_id: 20 ← SET        │
└─────────────────────────────────┘
           │ create_new_version()
           ▼
┌─────────────────────────────────┐
│ NEW rule (id: 20)               │
│ ─────────────────────────────── │
│ percentage: 7.0 ← UPDATED       │
│ valid_from: 2026-08-01          │
│ valid_until: NULL               │
│ replaces_id: 15 ← LINK          │
└─────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Commission transaction (sale_id: 500)       │
│ ─────────────────────────────────────────── │
│ commission_amount: 18,000                   │  ← UNCHANGED!
│ rule_snapshot: {"percentage": 6.0, ...}     │  ← FROZEN
│                                             │
│ ✅ Non-retroactive guarantee                │
└─────────────────────────────────────────────┘


STEP 6: NEW TRANSACTION AFTER RULE CHANGE
┌─────────────────────┐
│   Agent             │
└──────────┬──────────┘
           │ New sale on 2026-09-10
           ▼
┌─────────────────────────────────┐
│ real.estate.sale                │
│ sale_price: 400,000             │
│ sale_date: 2026-09-10           │
└──────────┬──────────────────────┘
           │ calculate_commission(date=2026-09-10)
           │ → Finds rule_id: 20 (7%)
           │ → Calculates: 400,000 * 7% = 28,000
           ▼
┌─────────────────────────────────────────────┐
│ Commission transaction (NEW)                │
│ ─────────────────────────────────────────── │
│ commission_amount: 28,000                   │  ← Uses 7%
│ rule_id: 20                                 │
│ rule_snapshot: {"percentage": 7.0, ...}     │
└─────────────────────────────────────────────┘

✅ Different transactions → Different rules → Different amounts
```

### Multi-Agent Split Example

```
┌─────────────────────────────────────────────────────────────────┐
│  SCENARIO: 2 agents on same property sale                      │
└─────────────────────────────────────────────────────────────────┘

Sale: $500,000
Agents: Agent A (id: 10), Agent B (id: 20)

┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│ Agent A Rule                    │     │ Agent B Rule                    │
│ ─────────────────────────────── │     │ ─────────────────────────────── │
│ transaction_type: 'sale'        │     │ transaction_type: 'sale'        │
│ percentage: 6.0%                │     │ percentage: 5.0%                │
└─────────────────────────────────┘     └─────────────────────────────────┘
           │                                         │
           ▼                                         ▼
   Calculate:                                Calculate:
   500,000 * 6% = 30,000                     500,000 * 5% = 25,000
   Split: 50% = 15,000                       Split: 50% = 12,500
           │                                         │
           ▼                                         ▼
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│ Commission Transaction A        │     │ Commission Transaction B        │
│ ─────────────────────────────── │     │ ─────────────────────────────── │
│ agent_id: 10                    │     │ agent_id: 20                    │
│ commission_amount: 15,000       │     │ commission_amount: 12,500       │
│ split_percentage: 50.0          │     │ split_percentage: 50.0          │
└─────────────────────────────────┘     └─────────────────────────────────┘

Total paid: $27,500 (15,000 + 12,500)
```

### Tiered Commission Example

```
┌─────────────────────────────────────────────────────────────────┐
│  TIERED STRUCTURE: Progressive percentage                      │
└─────────────────────────────────────────────────────────────────┘

Rule configuration (JSON):
[
  {"up_to": 100000, "percentage": 5.0},
  {"up_to": 300000, "percentage": 4.0},
  {"above": 300000, "percentage": 3.0}
]

Sale: $450,000

Calculation:
┌──────────────────┬────────────────┬─────────────────┬──────────────┐
│ Tier             │ Range          │ Calculation     │ Commission   │
├──────────────────┼────────────────┼─────────────────┼──────────────┤
│ Tier 1           │ 0 - 100k       │ 100k * 5%       │ $5,000       │
│ Tier 2           │ 100k - 300k    │ 200k * 4%       │ $8,000       │
│ Tier 3           │ 300k+          │ 150k * 3%       │ $4,500       │
├──────────────────┴────────────────┴─────────────────┼──────────────┤
│ TOTAL                                               │ $17,500      │
└─────────────────────────────────────────────────────┴──────────────┘

Effective percentage: 17,500 / 450,000 = 3.89%

Commission Transaction:
┌─────────────────────────────────────────────┐
│ commission_amount: 17,500                   │
│ commission_percentage_applied: 3.89         │ ← Effective %
│ rule_snapshot: {                            │
│   "structure_type": "tiered",               │
│   "tier_config": [...]                      │
│ }                                           │
└─────────────────────────────────────────────┘
```

### Query Examples

**Get active rule for agent at specific date:**
```python
rule = env['real.estate.commission.rule'].search([
    ('agent_id', '=', agent_id),
    ('transaction_type', '=', 'sale'),
    ('valid_from', '<=', transaction_date),
    '|',
    ('valid_until', '=', False),
    ('valid_until', '>', transaction_date),
    ('active', '=', True)
], limit=1, order='valid_from desc')
```

**Get commission history for agent:**
```python
transactions = env['real.estate.commission.transaction'].search([
    ('agent_id', '=', agent_id),
    ('transaction_date', '>=', start_date),
    ('transaction_date', '<=', end_date),
], order='transaction_date desc')

total_commission = sum(t.commission_amount for t in transactions)
```

**Get pending payments:**
```python
pending = env['real.estate.commission.transaction'].search([
    ('company_id', '=', company_id),
    ('payment_status', '=', 'pending'),
], order='transaction_date asc')
```

**Get all rule versions for agent:**
```python
all_rules = env['real.estate.commission.rule'].search([
    ('agent_id', '=', agent_id),
    ('transaction_type', '=', 'sale'),
], order='valid_from desc')

# Trace version chain
current_rule = all_rules[0]
while current_rule.replaces_id:
    print(f"Rule {current_rule.id} replaces {current_rule.replaces_id.id}")
    current_rule = current_rule.replaces_id
```

### Edge Case Handling

```
┌──────────────────────────┬────────────────────────────────────────┐
│ Edge Case                │ Behavior                               │
├──────────────────────────┼────────────────────────────────────────┤
│ Commission > Value       │ Allow + Warning (manual review)        │
│                          │ warnings: ["Commission exceeds value"] │
├──────────────────────────┼────────────────────────────────────────┤
│ No active rule           │ commission_amount = 0                  │
│                          │ warnings: ["No active rule found"]     │
├──────────────────────────┼────────────────────────────────────────┤
│ Value below min_trans    │ Calculate normally + Warning           │
│                          │ warnings: ["Below minimum value"]      │
├──────────────────────────┼────────────────────────────────────────┤
│ Commission below min     │ Auto-cap to min_commission             │
│                          │ capped: true                           │
├──────────────────────────┼────────────────────────────────────────┤
│ Commission above max     │ Auto-cap to max_commission             │
│                          │ capped: true                           │
├──────────────────────────┼────────────────────────────────────────┤
│ Multiple agents          │ Split by split_percentage (default 50%)│
│                          │ Each gets own transaction record       │
└──────────────────────────┴────────────────────────────────────────┘
```

### Best Practices

1. **Always use `calculate_commission()`** - Don't manually create commission transactions
2. **Never modify commission transactions** - They are immutable snapshots
3. **Use `create_new_version()`** to update rules - Preserves history
4. **Set `valid_from` to future date** for scheduled rule changes
5. **Always query with `transaction_date`** - Not "now", but actual transaction date
6. **Check `warnings` array** - May contain important information about edge cases
7. **Use `payment_status`** for accounting workflows - Track paid vs. pending

---

**Data**: 2026-01-12  
**Autor**: GitHub Copilot (AI Assistant)  
**Revisores**: [Pending]
