# -*- coding: utf-8 -*-
"""
Celery producer client (ADR-021).

Odoo only ever needs to *enqueue* tasks by name - it must never import the
worker's task code directly (odoo.addons.quicksol_estate.celery_tasks never
existed; celery tasks live in the separate celery_worker image/process).
This module builds a client-only Celery app, configured with just the broker
URL, and exposes send_task() so producers can dispatch by task name.
"""
import logging
import os

from celery import Celery

_logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Celery(
            "quicksol_estate_producer",
            broker=os.environ["CELERY_BROKER_URL"],
        )
    return _client


def send_task(name, kwargs, queue):
    """Enqueue a Celery task by name. Raises on failure - callers are
    expected to catch and log per ADR-021 (never block the DB transaction)."""
    _get_client().send_task(name, kwargs=kwargs, queue=queue)
