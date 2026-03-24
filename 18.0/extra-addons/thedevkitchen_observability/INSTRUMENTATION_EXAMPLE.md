# Instrumentation Example

Example of how to instrument an existing Odoo controller with OpenTelemetry tracing.

## Before (Without Tracing)

```python
# controllers/invite_controller.py
import json
import logging
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
from ..services.invite_service import InviteService

_logger = logging.getLogger(__name__)


class InviteController(http.Controller):
    @http.route(
        "/api/v1/users/invite",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    def invite_user(self, **kwargs):
        """Invite a user - no tracing"""
        data = json.loads(request.httprequest.data.decode("utf-8"))
        profile_id = data.get("profile_id")
        
        # Business logic...
        invite_service = InviteService(request.env)
        user = invite_service.create_user_from_profile(profile_record)
        token = invite_service.generate_invitation_token(user)
        
        return request.make_json_response({
            'user_id': user.id,
            'token': token,
        })
```

## After (With Automatic Tracing)

```python
# controllers/invite_controller.py
import json
import logging
from odoo import http
from odoo.http import request
from odoo.addons.thedevkitchen_apigateway.middleware import (
    require_jwt,
    require_session,
    require_company,
)
# 👇 ADD: Import tracing decorator
from odoo.addons.thedevkitchen_observability.services.tracer import trace_http_request

from ..services.invite_service import InviteService

_logger = logging.getLogger(__name__)


class InviteController(http.Controller):
    @http.route(
        "/api/v1/users/invite",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
        cors="*",
    )
    @require_jwt
    @require_session
    @require_company
    @trace_http_request  # 👈 ADD: Automatic tracing decorator
    def invite_user(self, **kwargs):
        """
        Invite a user - automatically traced
        
        Span automatically includes:
        - http.method: POST
        - http.route: /api/v1/users/invite
        - http.url: Full URL
        - http.status_code: 200, 400, 500, etc.
        - http.user_agent: User agent header
        - http.client_ip: Client IP address
        - enduser.id: Authenticated user ID
        - enduser.name: Authenticated user name
        
        Logs automatically include:
        - trace_id: For correlation with Tempo
        - span_id: For linking to specific span
        
        In Grafana:
        - Loki: Click "View Trace" button → Opens Tempo
        - Tempo: Click span → "View Logs" → Opens Loki filtered by trace_id
        """
        data = json.loads(request.httprequest.data.decode("utf-8"))
        profile_id = data.get("profile_id")
        
        # Business logic...
        invite_service = InviteService(request.env)
        user = invite_service.create_user_from_profile(profile_record)
        token = invite_service.generate_invitation_token(user)
        
        # Logs now include trace_id automatically!
        _logger.info(f"User invited: {user.id}, profile: {profile_id}")
        # Output: 2024-03-24 10:15:30 INFO [trace_id=abc123...] [span_id=def456...]
        #         User invited: 42, profile: 123
        
        return request.make_json_response({
            'user_id': user.id,
            'token': token,
        })
```

## Advanced: Manual Instrumentation

For complex operations, add manual spans with custom attributes:

```python
# controllers/invite_controller.py
from odoo.addons.thedevkitchen_observability.services.tracer import (
    trace_http_request,
    get_tracer,
    add_span_attribute,
    add_span_event,
    create_child_span,
)

class InviteController(http.Controller):
    @http.route("/api/v1/users/invite", ...)
    @require_jwt
    @require_session
    @require_company
    @trace_http_request
    def invite_user(self, **kwargs):
        """Invite a user with detailed tracing"""
        data = json.loads(request.httprequest.data.decode("utf-8"))
        profile_id = data.get("profile_id")
        
        # Add custom attributes to current span
        add_span_attribute("profile.id", profile_id)
        add_span_attribute("operation.type", "user_invitation")
        
        # Load profile with event markers
        add_span_event("fetch.profile.start")
        profile_record = request.env['thedevkitchen.estate.profile'].browse(profile_id)
        add_span_event("fetch.profile.complete", {
            "profile.type": profile_record.profile_type_id.code,
            "profile.company": profile_record.company_id.name,
        })
        
        # Create user with child span
        with create_child_span("create.user") as span:
            span.set_attribute("user.email", profile_record.email)
            span.set_attribute("user.role", profile_record.profile_type_id.code)
            
            invite_service = InviteService(request.env)
            user = invite_service.create_user_from_profile(profile_record)
            
            span.set_attribute("user.id", user.id)
            add_span_event("user.created", {"user_id": user.id})
        
        # Generate token with child span
        with create_child_span("generate.token") as span:
            token = invite_service.generate_invitation_token(user)
            span.set_attribute("token.type", "invitation")
            span.set_attribute("token.expiry", "24h")
        
        # Send email with child span
        with create_child_span("send.invitation.email") as span:
            span.set_attribute("email.to", user.email)
            span.set_attribute("email.template", "user_invitation")
            
            try:
                invite_service.send_invitation_email(user, token)
                span.set_attribute("email.sent", True)
                add_span_event("email.sent.success")
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("email.sent", False)
                add_span_event("email.sent.failed", {"error": str(e)})
                raise
        
        _logger.info(f"User invited successfully: {user.id}")
        
        return request.make_json_response({
            'user_id': user.id,
            'email': user.email,
        })
```

## Service Layer Instrumentation

You can also instrument service methods:

```python
# services/invite_service.py
from odoo.addons.thedevkitchen_observability.services.tracer import (
    get_tracer,
    add_span_attribute,
    add_span_event,
)

class InviteService:
    def __init__(self, env):
        self.env = env
        self.tracer = get_tracer()
    
    def create_user_from_profile(self, profile_record):
        """Create user with tracing"""
        with self.tracer.start_as_current_span("InviteService.create_user") as span:
            # Add context
            span.set_attribute("profile.id", profile_record.id)
            span.set_attribute("profile.type", profile_record.profile_type_id.code)
            span.set_attribute("profile.email", profile_record.email)
            
            # Create partner
            add_span_event("create.partner.start")
            partner = self._create_partner(profile_record)
            add_span_event("create.partner.complete", {"partner_id": partner.id})
            
            # Create user
            add_span_event("create.user.start")
            user = self._create_user(partner, profile_record)
            add_span_event("create.user.complete", {"user_id": user.id})
            
            # Link profile to partner
            add_span_event("link.profile.start")
            profile_record.write({'partner_id': partner.id})
            add_span_event("link.profile.complete")
            
            span.set_attribute("user.id", user.id)
            span.set_attribute("partner.id", partner.id)
            
            return user
    
    def _create_partner(self, profile_record):
        """Create partner with detailed tracing"""
        with self.tracer.start_as_current_span("create_partner") as span:
            span.set_attribute("partner.name", profile_record.person_name)
            span.set_attribute("partner.email", profile_record.email)
            
            partner_vals = {
                'name': profile_record.person_name,
                'email': profile_record.email,
                'phone': profile_record.phone,
                'company_id': profile_record.company_id.id,
            }
            
            partner = self.env['res.partner'].sudo().create(partner_vals)
            span.set_attribute("partner.id", partner.id)
            
            return partner
    
    def _create_user(self, partner, profile_record):
        """Create user with detailed tracing"""
        with self.tracer.start_as_current_span("create_user") as span:
            # Determine groups based on profile type
            add_span_event("resolve.groups.start")
            groups = self._resolve_groups(profile_record.profile_type_id.code)
            add_span_event("resolve.groups.complete", {
                "groups.count": len(groups),
                "groups.names": [g.name for g in groups],
            })
            
            span.set_attribute("user.login", profile_record.email)
            span.set_attribute("groups.count", len(groups))
            
            user_vals = {
                'partner_id': partner.id,
                'login': profile_record.email,
                'name': profile_record.person_name,
                'email': profile_record.email,
                'company_id': profile_record.company_id.id,
                'company_ids': [(6, 0, [profile_record.company_id.id])],
                'groups_id': [(6, 0, groups.ids)],
            }
            
            user = self.env['res.users'].sudo().create(user_vals)
            span.set_attribute("user.id", user.id)
            
            return user
```

## Result: Grafana Tempo Trace

After instrumenting your code, you'll see traces like this in Grafana Tempo:

```
POST /api/v1/users/invite                              [1.24s]  ← Root span
├─ fetch.profile.start                                 [2ms]    ← Event
├─ fetch.profile.complete                              [15ms]   ← Event
├─ create.user                                         [450ms]  ← Child span
│  ├─ create.partner                                   [120ms]  ← Grandchild span
│  │  └─ partner.id: 789
│  ├─ create.user                                      [250ms]  ← Grandchild span
│  │  ├─ resolve.groups.start                        [1ms]
│  │  ├─ resolve.groups.complete                     [50ms]
│  │  └─ user.id: 42
│  └─ link.profile.complete                            [80ms]
├─ generate.token                                      [35ms]   ← Child span
│  └─ token.type: invitation
└─ send.invitation.email                               [740ms]  ← Child span
   ├─ email.to: user@example.com
   ├─ email.template: user_invitation
   └─ email.sent: true

Attributes:
  http.method: POST
  http.route: /api/v1/users/invite
  http.status_code: 200
  enduser.id: 2
  enduser.name: Admin
  profile.id: 123
  profile.type: agent
  operation.type: user_invitation
  user.id: 42
  partner.id: 789
```

## Benefits

1. **Request Visibility**: See exact execution time of each operation
2. **Bottleneck Identification**: Identify slow database queries, email sending, etc.
3. **Error Tracking**: See exactly where exceptions occur in the trace
4. **Log Correlation**: Click trace_id in logs → Jump to trace in Tempo
5. **Cross-Service Tracing**: If you call external APIs, traces propagate via W3C Trace Context
6. **Production Debugging**: Sample 10% of requests with `OTEL_TRACES_SAMPLER=traceidratio:0.1`

## Grafana Queries

### Find slow invitations (>2 seconds)
```traceql
{name="POST /api/v1/users/invite" && duration>2s}
```

### Find failed invitations
```traceql
{name="POST /api/v1/users/invite" && status=error}
```

### Find invitations for specific profile type
```traceql
{name="POST /api/v1/users/invite" && span.profile.type="agent"}
```

### Find email send failures
```traceql
{name="send.invitation.email" && span.email.sent=false}
```

## Next Steps

1. **Instrument critical endpoints**: Start with high-traffic or slow endpoints
2. **Add custom attributes**: Include business context (property_id, contract_id, etc.)
3. **Create dashboards**: Use Grafana to visualize request rates, latencies, errors
4. **Set up alerts**: Alert on high error rates or slow requests
5. **Sample in production**: Use `OTEL_TRACES_SAMPLER=traceidratio:0.1` for 10% sampling

---

**Documentation**: See [README.md](README.md) for full module documentation and configuration options.
