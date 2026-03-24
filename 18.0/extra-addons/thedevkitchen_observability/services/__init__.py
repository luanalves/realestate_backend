# -*- coding: utf-8 -*-
from . import tracer
from . import log_filter
from . import db_instrumentor
from . import celery_instrumentor

# Auto-initialize database instrumentation (PostgreSQL + Redis)
db_instrumentor.auto_initialize()

# Auto-initialize Celery client instrumentation (trace context propagation)
celery_instrumentor.initialize_celery_instrumentation()
