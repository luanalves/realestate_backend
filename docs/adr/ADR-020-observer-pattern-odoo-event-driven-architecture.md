# ADR-020: Observer Pattern para Arquitetura Event-Driven em Odoo

## Status
Aceito

## Data
2026-01-20

## Contexto

### Problema Atual

No desenvolvimento do sistema RBAC (ADR-019), identificamos várias situações onde a lógica de negócio está fortemente acoplada aos métodos `create()`, `write()` e outros hooks do ORM:

1. **Auto-populate prospector_id**: Quando um usuário com perfil Prospector cria uma propriedade, precisamos automaticamente associá-lo como prospector
2. **Validação de companies**: Quando um Owner cria/edita usuários, precisamos validar que as empresas atribuídas são subset das empresas do owner
3. **Cálculo de comissão split**: Quando uma venda é finalizada, precisamos calcular e notificar a divisão de comissão entre prospector e agente
4. **Auditoria de alterações**: Precisamos registrar mudanças críticas em grupos de segurança para compliance (LGPD)

**Exemplo de código acoplado (anti-pattern)**:
```python
# ❌ PROBLEMA: Lógica acoplada diretamente no create()
class Property(models.Model):
    _name = 'real.estate.property'
    
    @api.model
    def create(self, vals):
        # Lógica 1: Auto-populate prospector
        if self.env.user.has_group('quicksol_estate.group_real_estate_prospector'):
            agent = self.env['real.estate.agent'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1)
            if agent:
                vals['prospector_id'] = agent.id
        
        # Lógica 2: Validação de preço mínimo
        if vals.get('sale_price', 0) < 10000:
            raise ValidationError("Preço mínimo R$ 10.000")
        
        # Lógica 3: Notificar manager por email
        self._send_property_created_email(vals)
        
        # Lógica 4: Criar log de auditoria
        self._create_audit_log('create', vals)
        
        return super().create(vals)
```

**Problemas desta abordagem**:
- ❌ Violação do **Single Responsibility Principle** (SRP) - método `create()` tem múltiplas responsabilidades
- ❌ **Difícil testar** - precisa mockar 4 lógicas diferentes em cada teste
- ❌ **Difícil manter** - adicionar nova regra exige modificar método central
- ❌ **Acoplamento alto** - mudar uma lógica pode quebrar outras
- ❌ **Não reutilizável** - lógica duplicada em `write()`, `unlink()`, etc.

### Forças em Jogo

1. **Odoo ORM**: Já possui sistema de eventos via decoradores `@api.model_create_multi`, `@api.onchange`, `@api.constrains`
2. **Extensibilidade**: Novos módulos precisam adicionar comportamentos sem modificar código existente (Open/Closed Principle)
3. **Testabilidade**: Cada lógica de negócio deve ser testável isoladamente
4. **Performance**: Observers síncronos podem impactar performance em operações em lote
5. **Manutenibilidade**: Desenvolvedores devem encontrar facilmente onde cada regra está implementada

### Alternativas Consideradas

#### Opção 1: Manter lógica inline nos métodos (Status Quo)
- ✅ Simples de entender inicialmente
- ✅ Menos arquivos para gerenciar
- ❌ Viola SRP
- ❌ Dificulta testes unitários
- ❌ Código cresce descontroladamente

#### Opção 2: Usar hooks nativos do Odoo (`@api.model_create_multi`, `@api.constrains`)
- ✅ Padrão nativo do framework
- ✅ Familiar para desenvolvedores Odoo
- ❌ Hooks ainda ficam no mesmo arquivo do modelo
- ❌ Não resolve o problema de acoplamento entre lógicas diferentes
- ⚠️ Limitado aos eventos que Odoo já suporta

#### Opção 3: Implementar Observer Pattern com Event Bus
- ✅ Desacopla completamente lógicas de negócio
- ✅ Fácil adicionar novos observers sem modificar código existente
- ✅ Cada observer é testável isoladamente
- ✅ Reutilizável em múltiplos eventos
- ❌ Adiciona complexidade arquitetural
- ❌ Requer disciplina para não criar observers demais
- ⚠️ Performance: pode ser impacto em operações em lote

#### Opção 4: Usar biblioteca externa (OCA `component`)
- ✅ Solução já testada pela comunidade
- ✅ Documentação e exemplos disponíveis
- ❌ Dependência externa
- ❌ Curva de aprendizado
- ❌ Pode não se integrar perfeitamente com nossos casos de uso

## Decisão

**Adotamos o Observer Pattern (Opção 3) usando Event Bus nativo do Odoo** com as seguintes diretrizes:

### 1. Arquitetura Event-Driven

Implementar um sistema de eventos centralizado usando o padrão Observer, aproveitando o mecanismo de herança do Odoo:

```python
# models/event_bus.py
"""
Event Bus centralizado para desacoplar lógicas de negócio.
Baseado no Observer Pattern (Gang of Four).
"""

class EventBus(models.AbstractModel):
    _name = 'quicksol.event.bus'
    _description = 'Event Bus for decoupled business logic'
    
    @api.model
    def emit(self, event_name, data):
        """
        Emite um evento para todos os observers registrados.
        
        Args:
            event_name (str): Nome do evento (ex: 'property.created')
            data (dict): Dados do evento
            
        Usage:
            self.env['quicksol.event.bus'].emit('property.created', {
                'property_id': property.id,
                'user_id': self.env.user.id
            })
        """
        observers = self._get_observers(event_name)
        for observer in observers:
            observer.handle(event_name, data)
    
    @api.model
    def _get_observers(self, event_name):
        """Retorna lista de observers registrados para o evento."""
        # Implementação: busca por métodos que herdam de AbstractObserver
        # e estão registrados para este evento
        pass
```

### 2. Abstract Observer Base Class

```python
# models/observers/abstract_observer.py

class AbstractObserver(models.AbstractModel):
    _name = 'quicksol.abstract.observer'
    _description = 'Base class for all observers'
    
    # Lista de eventos que este observer escuta
    _observe_events = []
    
    @api.model
    def handle(self, event_name, data):
        """
        Método chamado quando evento é emitido.
        Subclasses devem implementar.
        """
        raise NotImplementedError("Subclasses must implement handle()")
    
    @api.model
    def can_handle(self, event_name):
        """Verifica se observer está registrado para este evento."""
        return event_name in self._observe_events
```

### 3. Implementação de Observers Concretos

#### Observer 1: Auto-populate Prospector

```python
# models/observers/prospector_auto_assign_observer.py

class ProspectorAutoAssignObserver(models.AbstractModel):
    _name = 'quicksol.observer.prospector.auto.assign'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Auto-assigns prospector when property is created'
    
    _observe_events = ['property.before_create']
    
    @api.model
    def handle(self, event_name, data):
        """
        Se usuário atual é prospector, auto-atribui como prospector_id.
        
        ADR-019: Prospectors ganham 30% comissão em propriedades prospectadas.
        """
        if not self.env.user.has_group('quicksol_estate.group_real_estate_prospector'):
            return
        
        agent = self.env['real.estate.agent'].search([
            ('user_id', '=', self.env.user.id)
        ], limit=1)
        
        if agent and 'vals' in data:
            data['vals']['prospector_id'] = agent.id
```

#### Observer 2: Commission Split Calculator

```python
# models/observers/commission_split_observer.py

class CommissionSplitObserver(models.AbstractModel):
    _name = 'quicksol.observer.commission.split'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Calculates commission split when sale is completed'
    
    _observe_events = ['sale.completed']
    
    @api.model
    def handle(self, event_name, data):
        """
        Calcula split 30/70 entre prospector e agente.
        
        ADR-019: Prospector recebe 30%, agente vendedor 70%.
        ADR-013: Usa regras de comissão configuráveis.
        """
        sale = self.env['real.estate.sale'].browse(data['sale_id'])
        property_record = sale.property_id
        
        if not property_record.prospector_id:
            return  # Sem split se não há prospector
        
        commission_rule = sale.commission_rule_id
        split = commission_rule.calculate_split_commission(
            property_record, 
            sale.sale_price
        )
        
        # Cria transações de comissão separadas
        self._create_commission_transactions(sale, split)
    
    def _create_commission_transactions(self, sale, split):
        """Cria registros de comissão para prospector e agente."""
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        # Comissão do prospector
        CommissionTransaction.create({
            'sale_id': sale.id,
            'agent_id': sale.property_id.prospector_id.id,
            'amount': split['prospector_commission'],
            'type': 'prospector',
            'status': 'pending'
        })
        
        # Comissão do agente vendedor
        CommissionTransaction.create({
            'sale_id': sale.id,
            'agent_id': sale.agent_id.id,
            'amount': split['agent_commission'],
            'type': 'agent',
            'status': 'pending'
        })
```

#### Observer 3: User Company Validator

```python
# models/observers/user_company_validator_observer.py

class UserCompanyValidatorObserver(models.AbstractModel):
    _name = 'quicksol.observer.user.company.validator'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Validates owner can only assign users to their companies'
    
    _observe_events = ['user.before_create', 'user.before_write']
    
    @api.model
    def handle(self, event_name, data):
        """
        ADR-019: Owners podem criar usuários apenas para suas empresas.
        ADR-008: Multi-tenancy isolation enforcement.
        """
        if not self.env.user.has_group('quicksol_estate.group_real_estate_owner'):
            return  # Validação só para owners
        
        vals = data.get('vals', {})
        if 'estate_company_ids' not in vals:
            return
        
        user_companies = set(self.env.user.estate_company_ids.ids)
        new_user_companies = set(vals['estate_company_ids'][0][2])  # Command (6, 0, [ids])
        
        if not new_user_companies.issubset(user_companies):
            raise AccessError(
                "Você só pode atribuir usuários às suas próprias empresas. "
                "ADR-019: Multi-tenancy isolation."
            )
```

### 4. Integração com Modelos

```python
# models/property.py

class Property(models.Model):
    _name = 'real.estate.property'
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Emite evento para observers antes de criar.
        Observers podem modificar vals_list.
        """
        for vals in vals_list:
            # Emite evento - observers podem modificar vals
            self.env['quicksol.event.bus'].emit('property.before_create', {
                'vals': vals,
                'model': self._name
            })
        
        properties = super().create(vals_list)
        
        # Emite evento pós-criação
        for prop in properties:
            self.env['quicksol.event.bus'].emit('property.created', {
                'property_id': prop.id,
                'user_id': self.env.user.id
            })
        
        return properties
```

### 5. Diretrizes de Implementação

#### ✅ Quando usar Observer Pattern:

1. **Lógica de negócio que responde a eventos do sistema**
   - Auto-population de campos baseado em contexto do usuário
   - Validações que dependem de múltiplas condições
   - Notificações (email, webhook, logs)
   - Cálculos derivados (comissões, totais, estatísticas)

2. **Quando há risco de violação do SRP**
   - Método `create()` com >50 linhas
   - Método com >3 responsabilidades distintas
   - Lógica que seria duplicada em `write()`, `unlink()`

3. **Para funcionalidades que serão estendidas por outros módulos**
   - Plugins de terceiros precisam adicionar comportamento
   - Funcionalidades opcionais que podem ser ativadas/desativadas

#### ❌ Quando NÃO usar Observer Pattern:

1. **Validações simples do modelo**
   - Use `@api.constrains` nativo do Odoo
   - Exemplo: validar que preço > 0

2. **Cálculos de campos computados**
   - Use `@api.depends` + `compute` method
   - Exemplo: calcular área total = área construída + área terreno

3. **Lógica extremamente crítica para performance**
   - Operações em lote com milhares de registros
   - Considerar usar SQL direto ou operações em background

4. **Lógica trivial de 1-2 linhas**
   - Overhead não justifica benefício
   - Exemplo: vals['status'] = 'draft'

### 6. Naming Conventions (ADR-004)

**Events**:
```
<model>.<action>
<model>.before_<action>
<model>.after_<action>
```

Exemplos:
- `property.created`
- `property.before_create`
- `sale.completed`
- `user.company_changed`

**Observers**:
```
quicksol.observer.<domain>.<action>
```

Exemplos:
- `quicksol.observer.prospector.auto.assign`
- `quicksol.observer.commission.split`
- `quicksol.observer.user.company.validator`

### 7. Testing Strategy (ADR-003)

```python
# tests/test_prospector_auto_assign_observer.py

class TestProspectorAutoAssignObserver(TransactionCase):
    """
    Testes isolados do observer, sem dependência do modelo Property.
    Segue padrão AAA (Arrange, Act, Assert).
    """
    
    def setUp(self):
        super().setUp()
        self.observer = self.env['quicksol.observer.prospector.auto.assign']
        self.prospector_user = self._create_prospector_user()
    
    def test_prospector_auto_assign_success(self):
        """Observer deve adicionar prospector_id quando usuário é prospector."""
        # Arrange
        data = {'vals': {'name': 'Test Property'}}
        
        # Act
        with self.env.cr.savepoint():
            self.env = self.env(user=self.prospector_user)
            self.observer.handle('property.before_create', data)
        
        # Assert
        self.assertTrue('prospector_id' in data['vals'])
        self.assertEqual(
            data['vals']['prospector_id'], 
            self.prospector_user.agent_id.id
        )
    
    def test_non_prospector_no_auto_assign(self):
        """Observer NÃO deve adicionar prospector_id se usuário não é prospector."""
        # Arrange
        manager_user = self._create_manager_user()
        data = {'vals': {'name': 'Test Property'}}
        
        # Act
        with self.env.cr.savepoint():
            self.env = self.env(user=manager_user)
            self.observer.handle('property.before_create', data)
        
        # Assert
        self.assertFalse('prospector_id' in data['vals'])
```

**Cobertura mínima por observer**: 80% (ADR-003)

### 8. Performance Guidelines

**Batching**: Observers devem suportar operações em lote
```python
@api.model
def handle(self, event_name, data):
    """Handle pode receber lista de IDs para batch processing."""
    if 'ids' in data:  # Batch operation
        records = self.env['real.estate.property'].browse(data['ids'])
        for record in records:
            self._process_single(record)
    else:  # Single operation
        self._process_single(data)
```

**Async quando possível**: Para observers não críticos (emails, webhooks)
```python
# Use queue_job ou celery para operações assíncronas
self.with_delay().handle(event_name, data)
```

**Medir impacto**: Adicionar logging de performance
```python
import time
start = time.time()
self.handle(event_name, data)
_logger.debug(f"Observer {self._name} took {time.time() - start:.3f}s")
```

## Consequências

### Positivas ✅

1. **Separation of Concerns**
   - Cada observer tem uma responsabilidade única
   - Fácil entender o que cada observer faz
   - Código do modelo (`property.py`, `res_users.py`) fica limpo

2. **Testabilidade**
   - Cada observer é testável isoladamente
   - Mocks mais simples (só mockar dependências do observer)
   - Testes mais rápidos (não precisa criar propriedades reais para testar validação)

3. **Extensibilidade (Open/Closed Principle)**
   - Novos módulos podem adicionar observers sem modificar código existente
   - Fácil ativar/desativar funcionalidades (instalar/desinstalar módulo com observer)

4. **Reusabilidade**
   - Mesmo observer pode reagir a múltiplos eventos
   - Exemplo: `AuditLogObserver` escuta `property.created`, `property.updated`, `user.created`

5. **Debugging**
   - Logs centralizados no Event Bus
   - Fácil ver quais observers foram executados
   - Stack traces mais claras (cada observer é uma classe separada)

### Negativas ❌

1. **Complexidade Arquitetural**
   - Desenvolvedores precisam entender Observer pattern
   - Mais arquivos para gerenciar (1 arquivo por observer)
   - Curva de aprendizado inicial

2. **Indireção**
   - Não é óbvio olhando `property.py` que há lógica de auto-assign
   - Precisa buscar observers registrados para o evento
   - IDEs podem não reconhecer relação entre evento e observer

3. **Performance (se mal usado)**
   - Overhead de dispatch de eventos
   - Observers síncronos em operações de lote podem ser lentos
   - **Mitigação**: Ver **ADR-021** (Async Messaging com RabbitMQ/Celery) para resolver bulk operations

4. **Ordem de execução**
   - Se múltiplos observers modificam mesmos dados, ordem importa
   - Precisa documentar dependências entre observers
   - Mitigação: usar eventos granulares (`before_validate`, `after_validate`, etc.)

5. **Debugging de observers**
   - Erro em um observer pode não ser óbvio qual observer falhou
   - Mitigação: logging extensivo, try/except com contexto

### Riscos Aceitos ⚠️

1. **Risco de overengineering**: Aceito para features complexas do RBAC. Para features triviais, usar hooks nativos do Odoo.
2. **Risco de performance em bulk operations**: Observers síncronos podem bloquear servidor. **Solução**: Ver **ADR-021** (Async Messaging).
3. **Risco de curva de aprendizado**: Aceito. Investir em documentação e exemplos. Benefício a longo prazo compensa.

### Implicações para ADR-019 (RBAC)

**Observers a serem criados**:

1. ✅ `ProspectorAutoAssignObserver` - Auto-populate prospector_id
2. ✅ `CommissionSplitObserver` - Cálculo de split 30/70
3. ✅ `UserCompanyValidatorObserver` - Validação de multi-tenancy
4. ✅ `SecurityGroupAuditObserver` - Log de mudanças em grupos de segurança (LGPD)
5. ⚠️ `PropertyAssignmentNotifierObserver` - Notificar agente quando propriedade é atribuída (opcional)

**Eventos a serem emitidos**:

- `property.before_create` → ProspectorAutoAssignObserver
- `property.created` → SecurityGroupAuditObserver
- `sale.completed` → CommissionSplitObserver
- `user.before_create` → UserCompanyValidatorObserver
- `user.before_write` → UserCompanyValidatorObserver

### Compatibilidade com ADRs Existentes

- ✅ **ADR-001**: Código limpo sem comentários desnecessários (self-documenting observers)
- ✅ **ADR-003**: Testabilidade (observers 100% testáveis isoladamente)
- ✅ **ADR-004**: Naming conventions (eventos e observers seguem padrão)
- ✅ **ADR-008**: Multi-tenancy (observer valida isolation)
- ✅ **ADR-019**: RBAC (implementa auto-assign, commission split, validação)

## Decisões Relacionadas

- **ADR-021**: Async Messaging (RabbitMQ/Celery) - **EXTENSÃO** - Resolve limitação de performance deste ADR
- **ADR-019**: RBAC User Profiles - Este ADR implementa os padrões arquiteturais para RBAC
- **ADR-001**: Clean Code - Observers seguem princípio de código autoexplicativo
- **ADR-003**: Test Coverage - Observers devem ter 80%+ cobertura
- **ADR-004**: Naming Conventions - Define padrões de nomes para eventos e observers
- **ADR-008**: Multi-Tenancy - Observer `UserCompanyValidatorObserver` implementa validação

## Referências

- [Observer Pattern - Refactoring Guru](https://refactoring.guru/design-patterns/observer)
- [Gang of Four - Design Patterns](https://en.wikipedia.org/wiki/Design_Patterns)
- [Odoo ORM Events Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html#model-reference)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Event-Driven Architecture - Martin Fowler](https://martinfowler.com/articles/201701-event-driven.html)

## Checklist de Implementação

Para cada observer criado:

- [ ] Herda de `quicksol.abstract.observer`
- [ ] Define `_observe_events` com lista de eventos escutados
- [ ] Implementa `handle(event_name, data)` com lógica isolada
- [ ] Tem testes unitários com ≥80% cobertura (ADR-003)
- [ ] Documenta qual ADR justifica a existência do observer
- [ ] Adiciona logging para debugging
- [ ] Considera performance para operações em lote
- [ ] Nome do arquivo: `models/observers/<domain>_<action>_observer.py`
- [ ] Nome do modelo: `quicksol.observer.<domain>.<action>`

## Histórico de Revisões

| Data | Versão | Autor | Mudanças |
|------|--------|-------|----------|
| 2026-01-20 | 1.0 | AI Assistant | Versão inicial - Observer Pattern para RBAC (ADR-019) |
