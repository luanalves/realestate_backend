# -*- coding: utf-8 -*-
import json
from odoo.http import Response


def _cms_error(http_status, error_code, detail=None, **extra):

    payload = {"error": error_code}
    if detail is not None:
        payload["detail"] = detail
    payload.update(extra)
    return Response(
        json.dumps(payload),
        status=http_status,
        content_type="application/json",
    )
