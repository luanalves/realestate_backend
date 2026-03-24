# -*- coding: utf-8 -*-
"""
OTLP Proxy Controller

Receives OTLP/HTTP traces from browser and forwards to Tempo backend.
This is necessary because browsers cannot directly send cross-origin
requests to Tempo (CORS issue).

Architecture:
    Browser → POST /api/otel/traces → Odoo (this proxy) → Tempo:4318
"""

from odoo import http
from odoo.http import request, Response
import requests
import logging
import os

_logger = logging.getLogger(__name__)


class OTLPProxyController(http.Controller):
    """
    Proxy OTLP/HTTP traces from browser to Tempo backend.
    
    This endpoint is intentionally public (no authentication required)
    because browser-side tracing must work before user login.
    """

    # public endpoint
    @http.route('/api/otel/traces', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    def proxy_otlp_traces(self, **kwargs):
        """
        Receive OTLP/HTTP traces from browser and forward to Tempo.
        
        Request body: Protobuf serialized traces (application/x-protobuf)
        Response: 200 OK on success, 500 on Tempo error
        """
        try:
            # Get the raw request body (protobuf binary)
            data = request.httprequest.get_data()
            
            # Get content type
            content_type = request.httprequest.headers.get('Content-Type', 'application/x-protobuf')
            
            # Tempo endpoint from environment
            tempo_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://tempo:4318')
            
            # Ensure HTTP protocol and /v1/traces path
            if not tempo_endpoint.startswith('http'):
                tempo_endpoint = f'http://{tempo_endpoint}'
            if not tempo_endpoint.endswith('/v1/traces'):
                # Remove port if present in gRPC format (4317) and use HTTP (4318)
                tempo_endpoint = tempo_endpoint.replace(':4317', ':4318')
                tempo_endpoint = f'{tempo_endpoint}/v1/traces' if tempo_endpoint.endswith('/v1') else f'{tempo_endpoint.rstrip("/")}/v1/traces'
            
            # Forward request to Tempo
            response = requests.post(
                tempo_endpoint,
                data=data,
                headers={
                    'Content-Type': content_type,
                },
                timeout=5,
            )
            
            # Check response
            if response.status_code >= 400:
                _logger.warning(
                    f'Tempo returned error: status={response.status_code}, '
                    f'body={response.text[:200]}'
                )
            
            # Return Tempo's response to browser
            return Response(
                response=response.content,
                status=response.status_code,
                headers={
                    'Content-Type': response.headers.get('Content-Type', 'application/json'),
                    'Access-Control-Allow-Origin': '*',
                },
            )
            
        except requests.exceptions.RequestException as e:
            _logger.error(f'Failed to forward traces to Tempo: {e}')
            return Response(
                response='{"error": "Failed to forward traces to backend"}',
                status=500,
                headers={
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
            )
        except Exception as e:
            _logger.error(f'Unexpected error in OTLP proxy: {e}', exc_info=True)
            return Response(
                response='{"error": "Internal server error"}',
                status=500,
                headers={
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                },
            )

    # public endpoint
    @http.route('/api/otel/traces', type='http', auth='none', methods=['OPTIONS'], csrf=False, cors='*')
    def proxy_otlp_traces_preflight(self, **kwargs):
        """Handle CORS preflight requests."""
        return Response(
            response='',
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, traceparent, tracestate',
                'Access-Control-Max-Age': '86400',
            },
        )
