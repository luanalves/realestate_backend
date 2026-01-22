# ADR-021: Mensageria Assíncrona com RabbitMQ e Celery

## Status
Aceito

## Data
2026-01-20

## Supersede
Estende **ADR-020** (Observer Pattern) com capacidade de processamento assíncrono

## Contexto

### Fundamento: ADR-020 (Observer Pattern)

O **ADR-020** estabeleceu a arquitetura Event-Driven usando Observer Pattern para desacoplar lógica de negócio. Porém, identificamos uma **limitação crítica de performance** em operações em lote (bulk operations).

### Problema Atual

No desenvolvimento do sistema RBAC (ADR-019) com Observer Pattern (ADR-020), identificamos que **observers síncronos bloqueiam** o servidor em operações de lote:

1. **Auto-populate prospector_id**: Quando prospector cria propriedade, associá-lo automaticamente
2. **Validação de companies**: Owner só pode criar usuários para suas empresas
3. **Cálculo de comissão split**: Venda finalizada → calcular e criar transações de comissão
4. **Auditoria de alterações**: Registrar mudanças em grupos de segurança (LGPD compliance)
5. **Performance em bulk operations**: Importação de 1000 propriedades bloqueia servidor

**Exemplo de código acoplado (anti-pattern)**:
```python
# ❌ PROBLEMA: SRP violation, difícil testar, não escala
class Property(models.Model):
    @api.model
    def create(self, vals):
        # Lógica 1: Auto-populate prospector
        if self.env.user.has_group('quicksol_estate.group_real_estate_prospector'):
            agent = self.env['real.estate.agent'].search([('user_id', '=', self.env.user.id)], limit=1)
            if agent:
                vals['prospector_id'] = agent.id
        
        # Lógica 2: Validação
        if vals.get('sale_price', 0) < 10000:
            raise ValidationError("Preço mínimo R$ 10.000")
        
        # Lógica 3: Notificar manager (BLOQUEIA REQUEST!)
        self._send_property_created_email(vals)  # 2-5 segundos
        
        # Lógica 4: Audit log
        self._create_audit_log('create', vals)
        
        return super().create(vals)
```

**Problemas**:
- ❌ Violação SRP - múltiplas responsabilidades
- ❌ Difícil testar - mockar 4 lógicas diferentes
- ❌ Não escala - bulk create de 1000 registros = 1000 emails síncronos = 50+ minutos
- ❌ Acoplamento alto - mudar uma lógica pode quebrar outras

### Forças em Jogo

1. **Odoo ORM nativo**: `@api.model_create_multi`, `@api.onchange`, `@api.constrains`
2. **Extensibilidade**: Novos módulos devem adicionar comportamentos sem modificar código (Open/Closed)
3. **Testabilidade**: Cada lógica testável isoladamente
4. **Performance crítica**: Bulk operations (importações, migrações) não podem bloquear servidor
5. **Eventual consistency aceitável**: Audit logs podem demorar 5-10 segundos

### Alternativas Consideradas

#### Opção 1: Manter lógica inline (Status Quo)
- ✅ Simples inicialmente
- ❌ Viola SRP
- ❌ Performance terrível em bulk operations
- ❌ Código cresce descontroladamente

#### Opção 1: Observer Pattern Síncrono (ADR-020)
- ✅ Desacopla lógicas
- ✅ Testável isoladamente
- ⚠️ **Bloqueia em bulk operations** (1000 propriedades = 1000 events síncronos = 50+ minutos)

#### Opção 2: Observer + Mensageria Assíncrona (ESCOLHIDA - ADR-021)
- ✅ Desacoplamento total
- ✅ Performance: bulk operations não bloqueiam
- ✅ Escalável horizontalmente (múltiplos workers)
- ✅ Resiliente (retry automático, dead letter queue)
- ❌ Complexidade: RabbitMQ + Celery
- ❌ Eventual consistency (aceitável para audit/notificação)

#### Opção 4: OCA `component` library
- ✅ Solução comunitária
- ❌ Dependência externa
- ❌ Não resolve problema de performance síncrona

## Decisão

**Estendemos o ADR-020 (Observer Pattern) com Event Bus híbrido**, adicionando suporte assíncrono via **RabbitMQ + Celery** para operações não-críticas:

### 1. Arquitetura Event-Driven Híbrida

```python
# models/event_bus.py

class EventBus(models.AbstractModel):
    _name = 'quicksol.event.bus'
    _description = 'Hybrid Event Bus (sync + async via RabbitMQ)'
    
    # Configuração de eventos assíncronos
    ASYNC_EVENTS = {
        'user.created': 'audit_events',           # Fila: audit_events
        'user.updated': 'audit_events',
        'property.created': 'audit_events',
        'commission.split.calculated': 'commission_events',  # Fila: commission_events
        'property.assignment.changed': 'notification_events' # Fila: notification_events
    }
    
    @api.model
    def emit(self, event_name, data, force_sync=False):
        """
        Emite evento síncrono ou assíncrono baseado em configuração.
        
        Args:
            event_name (str): 'property.before_create', 'commission.split.calculated'
            data (dict): Dados do evento
            force_sync (bool): Força processamento síncrono (para testes)
        """
        # Eventos 'before_*' SEMPRE síncronos (validações críticas)
        if event_name.startswith(('before_', 'validate_')):
            return self._emit_sync(event_name, data)
        
        # Eventos assíncronos configurados
        if event_name in self.ASYNC_EVENTS and not force_sync:
            return self._emit_async(event_name, data)
        
        # Default: síncrono
        return self._emit_sync(event_name, data)
    
    def _emit_sync(self, event_name, data):
        """Processa eventos síncronos (validações, auto-populate)."""
        observers = self._get_observers(event_name)
        for observer in observers:
            try:
                observer.handle(event_name, data)
            except Exception as e:
                _logger.error(f"Observer {observer._name} failed: {e}", exc_info=True)
                raise
    
    def _emit_async(self, event_name, data):
        """
        Envia evento para fila RabbitMQ via Celery.
        Não bloqueia request - retorna imediatamente.
        """
        queue_name = self.ASYNC_EVENTS[event_name]
        
        # Celery task assíncrono
        from odoo.addons.thedevkitchen_celery.celery_client import process_event_task
        
        task = process_event_task.apply_async(
            args=[event_name, data],
            queue=queue_name,
            priority=self._get_priority(event_name),
            retry=True,
            retry_policy={
                'max_retries': 3,
                'interval_start': 5,
                'interval_step': 10,
                'interval_max': 60
            }
        )
        
        # Registrar task_id para tracking (opcional)
        self._log_async_task(event_name, task.id, queue_name)
        
        return task.id
    
    def _get_priority(self, event_name):
        """Define prioridade da task na fila."""
        HIGH_PRIORITY = ['commission.split.calculated']
        MEDIUM_PRIORITY = ['property.created', 'user.created']
        
        if event_name in HIGH_PRIORITY:
            return 9  # Celery priority 0-10
        elif event_name in MEDIUM_PRIORITY:
            return 5
        return 1  # Low priority (audit logs, notifications)
```

### 2. Divisão de Filas RabbitMQ (Multi-Queue Strategy)

**Rationale**: Evitar "head-of-line blocking" - task lenta não bloqueia tasks rápidas

```yaml
# docker-compose.yml - RabbitMQ Queues Configuration

rabbitmq:
  image: rabbitmq:3-management-alpine
  environment:
    # Pré-criar filas com diferentes prioridades
    RABBITMQ_QUEUES: |
      security_events:durable=true,max_priority=10
      commission_events:durable=true,max_priority=10
      audit_events:durable=true,max_priority=5
      notification_events:durable=true,max_priority=3
```

**Queue Assignment**:

| Queue | Eventos | Características | Workers |
|-------|---------|-----------------|---------|
| **security_events** | `user.before_create`, `user.before_write` | Síncrono/Crítico | N/A (processado inline) |
| **commission_events** | `commission.split.calculated` | Assíncrono/Alta prioridade | 2 workers dedicados |
| **audit_events** | `user.created`, `property.created` | Assíncrono/Média prioridade | 1 worker |
| **notification_events** | `property.assignment.changed`, emails | Assíncrono/Baixa prioridade | 1 worker |

**Benefícios**:
- ✅ Isolamento de falhas (fila de notificações parada não afeta comissões)
- ✅ Escalabilidade independente (mais workers para comissões, menos para audit)
- ✅ Priorização (comissões processadas antes de audit logs)

### 3. Abstract Observer com Suporte Assíncrono

```python
# models/observers/abstract_observer.py

class AbstractObserver(models.AbstractModel):
    _name = 'quicksol.abstract.observer'
    _description = 'Base class for all observers (sync/async support)'
    
    _observe_events = []
    _async_capable = False  # Observer suporta execução assíncrona?
    
    @api.model
    def handle(self, event_name, data):
        """
        SÍNCRONO: Chamado diretamente pelo Event Bus.
        Subclasses implementam.
        """
        raise NotImplementedError(f"{self._name} must implement handle()")
    
    @api.model
    def handle_async(self, event_name, data):
        """
        ASSÍNCRONO: Chamado por Celery worker.
        Default: chama handle() (compatibilidade backward).
        Override para otimizações (ex: batch processing).
        """
        return self.handle(event_name, data)
    
    @api.model
    def can_handle(self, event_name):
        return event_name in self._observe_events
```

### 4. Observers Concretos - Síncrono vs Assíncrono

#### Observer Síncrono (Validação Crítica)

```python
# models/observers/user_company_validator_observer.py

class UserCompanyValidatorObserver(models.AbstractModel):
    _name = 'quicksol.observer.user.company.validator'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Validates multi-tenancy isolation (SYNC ONLY)'
    
    _observe_events = ['user.before_create', 'user.before_write']
    _async_capable = False  # SEMPRE síncrono
    
    @api.model
    def handle(self, event_name, data):
        """
        ADR-019: Owners só podem criar usuários para suas empresas.
        DEVE FALHAR ANTES DE CRIAR - NUNCA ASSÍNCRONO.
        """
        if not self.env.user.has_group('quicksol_estate.group_real_estate_owner'):
            return
        
        vals = data.get('vals', {})
        if 'estate_company_ids' not in vals:
            return
        
        user_companies = set(self.env.user.estate_company_ids.ids)
        new_companies = set(vals['estate_company_ids'][0][2])
        
        if not new_companies.issubset(user_companies):
            raise AccessError(
                "Você só pode atribuir usuários às suas próprias empresas. "
                "ADR-019: Multi-tenancy isolation."
            )
```

#### Observer Assíncrono (Audit Log)

```python
# models/observers/security_group_audit_observer.py

class SecurityGroupAuditObserver(models.AbstractModel):
    _name = 'quicksol.observer.security.group.audit'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Logs security changes for LGPD compliance (ASYNC)'
    
    _observe_events = ['user.created', 'user.updated']
    _async_capable = True  # Pode ser assíncrono
    
    @api.model
    def handle(self, event_name, data):
        """
        Executado SÍNCRONAMENTE se emit() chamado sem async.
        Usado em testes ou quando Celery indisponível (fallback).
        """
        self._log_audit_trail(event_name, data)
    
    @api.model
    def handle_async(self, event_name, data):
        """
        Executado por Celery worker em background.
        Pode fazer operações lentas (escrever em S3, enviar webhook).
        """
        # Reconectar ao Odoo via XML-RPC (Celery worker não tem acesso direto ao env)
        import xmlrpc.client
        
        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        db = self.env.cr.dbname
        uid = SUPERUSER_ID
        password = os.environ['ODOO_MASTER_PASSWORD']
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        uid = common.authenticate(db, uid, password, {})
        
        # Executar audit log
        models.execute_kw(db, uid, password, 'quicksol.audit.log', 'create', [{
            'event_name': event_name,
            'user_id': data.get('user_id'),
            'timestamp': fields.Datetime.now(),
            'data': json.dumps(data)
        }])
        
        _logger.info(f"ASYNC: Audit log created for {event_name}")
```

#### Observer Híbrido (Commission Split)

```python
# models/observers/commission_split_observer.py

class CommissionSplitObserver(models.AbstractModel):
    _name = 'quicksol.observer.commission.split'
    _inherit = 'quicksol.abstract.observer'
    _description = 'Creates commission transactions (HYBRID: sync for single, async for bulk)'
    
    _observe_events = ['commission.split.calculated']
    _async_capable = True
    
    @api.model
    def handle(self, event_name, data):
        """SÍNCRONO: Venda individual."""
        self._create_commission_transactions(data)
    
    @api.model
    def handle_async(self, event_name, data):
        """
        ASSÍNCRONO: Bulk import de vendas.
        Otimizado para batch processing.
        """
        # Se há múltiplos splits, processar em batch
        if 'splits' in data:  # Lista de splits
            self._create_bulk_commission_transactions(data['splits'])
        else:
            self._create_commission_transactions(data)
    
    def _create_commission_transactions(self, data):
        """Cria transação individual."""
        split = data['split']
        property_id = data['property_id']
        
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        if split['prospector_commission'] > 0:
            CommissionTransaction.create({
                'agent_id': data['prospector_id'],
                'amount': split['prospector_commission'],
                'type': 'prospector'
            })
        
        CommissionTransaction.create({
            'agent_id': data['agent_id'],
            'amount': split['agent_commission'],
            'type': 'agent'
        })
    
    def _create_bulk_commission_transactions(self, splits):
        """Cria transações em lote (1 query SQL)."""
        CommissionTransaction = self.env['real.estate.commission.transaction']
        
        vals_list = []
        for split_data in splits:
            if split_data['split']['prospector_commission'] > 0:
                vals_list.append({
                    'agent_id': split_data['prospector_id'],
                    'amount': split_data['split']['prospector_commission'],
                    'type': 'prospector'
                })
            vals_list.append({
                'agent_id': split_data['agent_id'],
                'amount': split_data['split']['agent_commission'],
                'type': 'agent'
            })
        
        CommissionTransaction.create(vals_list)  # Bulk create
```

### 5. Celery Worker (Executor Assíncrono)

```python
# celery_worker/tasks.py

from celery import Celery
import xmlrpc.client
import os

app = Celery(
    'odoo_events',
    broker='amqp://odoo:password@rabbitmq:5672//',
    backend='redis://redis:6379/1'
)

# Configuração de filas
app.conf.task_routes = {
    'process_event_task': {'queue': 'audit_events'},  # Default
}

@app.task(bind=True, max_retries=3)
def process_event_task(self, event_name, data):
    """
    Task Celery que processa eventos assíncronos.
    Conecta ao Odoo via XML-RPC e chama observer.handle_async().
    """
    try:
        # Conectar ao Odoo
        url = os.environ['ODOO_URL']
        db = os.environ['ODOO_DB']
        username = os.environ['ODOO_USER']
        password = os.environ['ODOO_PASSWORD']
        
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        uid = common.authenticate(db, username, password, {})
        
        # Buscar observers para o evento
        observer_ids = models.execute_kw(
            db, uid, password,
            'quicksol.abstract.observer',
            'search',
            [[('_observe_events', 'in', [event_name])]]
        )
        
        # Executar handle_async de cada observer
        for observer_id in observer_ids:
            models.execute_kw(
                db, uid, password,
                observer_id,
                'handle_async',
                [event_name, data]
            )
        
        return f"Processed {event_name} with {len(observer_ids)} observers"
    
    except Exception as exc:
        # Retry com exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### 6. Docker Compose - RabbitMQ + Celery Workers

```yaml
# 18.0/docker-compose.yml

services:
  # ... db, redis, odoo existentes ...
  
  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: rabbitmq
    env_file: .env
    ports:
      - "5672:5672"   # AMQP protocol
      - "15672:15672" # Management UI (http://localhost:15672)
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
      RABBITMQ_DEFAULT_VHOST: /
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    networks:
      - odoo-net
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
  
  # Worker dedicado para comissões (high priority)
  celery_commission_worker:
    build: ./celery_worker
    container_name: celery_commission_worker
    env_file: .env
    depends_on:
      rabbitmq:
        condition: service_healthy
      redis:
        condition: service_healthy
      odoo:
        condition: service_started
    command: celery -A tasks worker --loglevel=info --queues=commission_events --concurrency=2
    environment:
      ODOO_URL: http://odoo:8069
      ODOO_DB: ${DB_NAME}
      ODOO_USER: admin
      ODOO_PASSWORD: admin
      CELERY_BROKER_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672//
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    networks:
      - odoo-net
  
  # Worker para audit logs (medium priority)
  celery_audit_worker:
    build: ./celery_worker
    container_name: celery_audit_worker
    env_file: .env
    depends_on:
      rabbitmq:
        condition: service_healthy
    command: celery -A tasks worker --loglevel=info --queues=audit_events --concurrency=1
    environment:
      CELERY_BROKER_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672//
      CELERY_RESULT_BACKEND: redis://redis:6379/1
    networks:
      - odoo-net
  
  # Worker para notificações (low priority)
  celery_notification_worker:
    build: ./celery_worker
    container_name: celery_notification_worker
    env_file: .env
    depends_on:
      rabbitmq:
        condition: service_healthy
    command: celery -A tasks worker --loglevel=info --queues=notification_events --concurrency=1
    environment:
      CELERY_BROKER_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672//
    networks:
      - odoo-net
  
  # Flower: Monitoramento de Celery
  flower:
    image: mher/flower:2.0
    container_name: flower
    env_file: .env
    depends_on:
      - rabbitmq
      - redis
    ports:
      - "5555:5555"  # UI: http://localhost:5555
    command: celery --broker=amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672// flower --port=5555
    environment:
      CELERY_BROKER_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASSWORD}@rabbitmq:5672//
      CELERY_RESULT_BACKEND: redis://redis:6379/1
      FLOWER_BASIC_AUTH: ${FLOWER_USER}:${FLOWER_PASSWORD}
    networks:
      - odoo-net

volumes:
  # ... volumes existentes ...
  rabbitmq-data:

networks:
  odoo-net:
    driver: bridge
```

### 7. Variáveis de Ambiente (.env)

```bash
# .env

# ------------------------------------------------------------------------------
# RABBITMQ MESSAGE BROKER
# ------------------------------------------------------------------------------
RABBITMQ_USER=odoo
RABBITMQ_PASSWORD=odoo_rabbitmq_secret_2026

# ------------------------------------------------------------------------------
# CELERY ASYNC WORKERS
# ------------------------------------------------------------------------------
CELERY_BROKER_URL=amqp://odoo:odoo_rabbitmq_secret_2026@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/1

# ------------------------------------------------------------------------------
# FLOWER MONITORING
# ------------------------------------------------------------------------------
FLOWER_USER=admin
FLOWER_PASSWORD=flower_admin_2026
```

### 8. Diretrizes de Uso

#### ✅ Quando usar Observers Assíncronos:

1. **Audit Logs** - LGPD compliance, não bloqueia operação
2. **Notificações** - Emails, webhooks, push notifications
3. **Processamento pesado** - Relatórios, PDFs, processamento de imagens
4. **Bulk operations** - Importação de 1000+ registros
5. **Integrações externas** - APIs third-party (Timeout risk)

**Exemplo**:
```python
# Emitir evento assíncrono
self.env['quicksol.event.bus'].emit('property.created', {
    'property_id': property.id,
    'user_id': self.env.user.id
})
# Retorna task_id imediatamente, não espera processamento
```

#### ❌ Quando NÃO usar Assíncrono (manter síncrono):

1. **Validações** - DEVEM falhar antes de criar/atualizar
2. **Auto-populate crítico** - Dados devem estar prontos imediatamente
3. **Cálculos financeiros** - Em operações individuais (vendas únicas)
4. **Modificações de vals** - `before_create` events que alteram dados

**Exemplo**:
```python
# Emitir evento síncrono (validação)
self.env['quicksol.event.bus'].emit('user.before_create', {
    'vals': vals
}, force_sync=True)
# Bloqueia até validação concluir, levanta exceção se inválido
```

### 9. Testing Strategy

```python
# tests/test_event_bus_async.py

class TestEventBusAsync(TransactionCase):
    """Testa comportamento assíncrono do Event Bus."""
    
    def test_async_event_returns_task_id(self):
        """Evento assíncrono retorna task_id Celery."""
        task_id = self.env['quicksol.event.bus'].emit('property.created', {
            'property_id': 123
        })
        
        self.assertTrue(isinstance(task_id, str))
        self.assertTrue(len(task_id) > 0)
    
    def test_sync_fallback_when_celery_unavailable(self):
        """Se Celery indisponível, fallback para síncrono."""
        # Mockar Celery como indisponível
        with patch('celery.app.base.Celery.send_task', side_effect=ConnectionError):
            # Deve processar síncronamente sem falhar
            result = self.env['quicksol.event.bus'].emit('property.created', {
                'property_id': 123
            })
            
            self.assertIsNone(result)  # Processou síncronamente
    
    def test_force_sync_overrides_async_config(self):
        """force_sync=True processa síncronamente mesmo para eventos async."""
        result = self.env['quicksol.event.bus'].emit(
            'property.created',  # Configurado como async
            {'property_id': 123},
            force_sync=True
        )
        
        self.assertIsNone(result)  # Não retornou task_id
```

## Consequências

### Positivas ✅

1. **Separation of Concerns**
   - Models emitem eventos, observers processam
   - Cada observer tem responsabilidade única

2. **Performance**
   - Bulk operations: 1000 propriedades = ~5 segundos (vs 50+ minutos síncronamente)
   - Request não bloqueia esperando audit logs / emails

3. **Escalabilidade Horizontal**
   - Adicionar workers Celery = processar mais eventos/segundo
   - Filas separadas = escalar comissões independentemente de audit

4. **Resiliência**
   - Retry automático em falhas transientes
   - Dead Letter Queue para eventos problemáticos
   - Graceful degradation (fallback síncrono se RabbitMQ offline)

5. **Monitoramento**
   - Flower UI: visualizar filas, tasks, workers em tempo real
   - Métricas: latência, throughput, taxa de erro por fila

6. **Testabilidade**
   - Testar observers isoladamente (mock event bus)
   - Testar com force_sync=True (sem depender de RabbitMQ)

### Negativas ❌

1. **Complexidade Operacional**
   - +3 serviços Docker (RabbitMQ + 3 Celery workers + Flower)
   - Monitorar saúde de RabbitMQ, filas, workers
   - Curva de aprendizado: Celery, AMQP, async patterns

2. **Eventual Consistency**
   - Audit log pode demorar 5-10 segundos
   - Cliente não vê confirmação imediata de notificação enviada
   - Pode confundir usuários se não comunicado

3. **Debugging Distribuído**
   - Erro em observer assíncrono não aparece no request
   - Precisa consultar logs do Celery worker
   - Correlacionar task_id com request_id

4. **Custo de Infraestrutura**
   - RabbitMQ: +512MB RAM
   - 3 Celery workers: +1.5GB RAM
   - Flower: +256MB RAM
   - Total: ~2.3GB adicionais

### Riscos Aceitos ⚠️

1. **Risco de dados órfãos**: Se Celery worker crashar durante processamento de comissão
   - **Mitigação**: Retry automático, idempotência em observers
2. **Risco de fila infinita**: Enfileirar eventos mais rápido que workers processam
   - **Mitigação**: Monitoring via Flower, alertas se fila > 10000 mensagens
3. **Risco de eventual consistency**: Usuário não vê audit log imediatamente
   - **Mitigação**: Aceito - LGPD não exige auditoria em tempo real

## Decisões Relacionadas

- **ADR-020**: Observer Pattern - **FUNDAMENTO** - Este ADR (021) estende ADR-020 com async processing
- **ADR-019**: RBAC User Profiles - Implementa observers para auto-assign, commission split, validação
- **ADR-001**: Clean Code - Observers seguem SRP
- **ADR-003**: Test Coverage - Observers testáveis com 80%+ cobertura
- **ADR-008**: Multi-Tenancy - Observer valida isolation
- **PLANO-CELERY-RABBITMQ.md**: Detalhamento técnico de implementação Celery

## Referências

- [Observer Pattern - Refactoring Guru](https://refactoring.guru/design-patterns/observer)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#best-practices)
- [RabbitMQ Queues](https://www.rabbitmq.com/queues.html)
- [Event-Driven Architecture - Martin Fowler](https://martinfowler.com/articles/201701-event-driven.html)
- [Odoo Queue Job (OCA)](https://github.com/OCA/queue) - Alternativa ao Celery

## Checklist de Implementação

**Infraestrutura**:
- [ ] Adicionar RabbitMQ ao docker-compose.yml com healthcheck
- [ ] Criar 4 filas: security_events, commission_events, audit_events, notification_events
- [ ] Adicionar 3 Celery workers (commission, audit, notification)
- [ ] Adicionar Flower para monitoramento (porta 5555)
- [ ] Configurar variáveis .env (RABBITMQ_USER, RABBITMQ_PASSWORD, CELERY_BROKER_URL)

**Código**:
- [ ] Implementar EventBus com emit_async() usando Celery
- [ ] Criar AbstractObserver com handle_async() method
- [ ] Implementar 4 observers concretos (prospector, commission, user validator, audit)
- [ ] Configurar ASYNC_EVENTS dict no EventBus
- [ ] Criar celery_worker/tasks.py com process_event_task

**Testes**:
- [ ] Testar cada observer isoladamente com force_sync=True
- [ ] Testar bulk operations (1000 registros) não bloqueiam request
- [ ] Testar fallback síncrono quando RabbitMQ offline
- [ ] Testar retry automático em falhas transientes
- [ ] Testar isolamento de filas (audit bloqueada não afeta commission)

**Documentação**:
- [ ] Atualizar data-model.md com observers assíncronos
- [ ] Criar docs/architecture/event-driven-rbac.md
- [ ] Atualizar Swagger com endpoints de monitoring
- [ ] Atualizar Postman collection com testes assíncronos
- [ ] Documentar em README.md como monitorar Flower UI

## Histórico de Revisões

| Data | Versão | Autor | Mudanças |
|------|--------|-------|----------|
| 2026-01-20 | 1.0 | AI Assistant | Versão inicial - Extensão do ADR-020 com RabbitMQ/Celery para async processing |
