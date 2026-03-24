# -*- coding: utf-8 -*-
from . import tracer
from . import log_filter
from . import db_instrumentor

# Auto-initialize database instrumentation (PostgreSQL + Redis)
db_instrumentor.auto_initialize()
