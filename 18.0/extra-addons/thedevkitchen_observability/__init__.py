# -*- coding: utf-8 -*-
from . import models
from . import services

import logging
_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Initialize OpenTelemetry tracer after module installation.
    
    This hook is called after the module is installed/upgraded.
    It initializes the global TracerProvider and configures the OTLP exporter.
    """
    from odoo.addons.thedevkitchen_observability.services.tracer import initialize_tracer
    
    try:
        initialize_tracer()
        _logger.info("✅ OpenTelemetry tracer initialized successfully")
    except Exception as e:
        _logger.error(f"❌ Failed to initialize OpenTelemetry tracer: {e}", exc_info=True)
