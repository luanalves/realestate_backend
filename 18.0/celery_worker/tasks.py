from celery import Celery
import xmlrpc.client
import os

app = Celery(
    'odoo_events',
    broker=os.getenv('CELERY_BROKER_URL', 'amqp://odoo:password@rabbitmq:5672//'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
)

# Configuração de filas
app.conf.task_routes = {
    'process_event_task': {'queue': 'audit_events'},
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


if __name__ == '__main__':
    app.start()
