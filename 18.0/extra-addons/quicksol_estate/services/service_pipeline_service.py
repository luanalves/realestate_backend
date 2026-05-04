# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timezone

from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


def change_stage(service, target_stage, comment=None, lost_reason=None):

    origin_stage = service.stage

    write_vals = {'stage': target_stage}
    if target_stage == 'lost' and lost_reason:
        write_vals['lost_reason'] = lost_reason

    # write() triggers @api.constrains — will raise if gates not met
    service.write(write_vals)

    _post_stage_change_message(service, origin_stage, target_stage, comment)
    _logger.info(
        'Service %s (id=%d) stage %s → %s by user %d',
        service.name, service.id, origin_stage, target_stage,
        service.env.uid,
    )


def reassign(service, new_agent_id, reason=None):

    TERMINAL_STAGES = {'won', 'lost'}

    if service.stage in TERMINAL_STAGES:
        raise UserError(
            f'Cannot reassign a service in terminal stage "{service.stage}".'
        )

    ResUsers = service.env['res.users']
    new_agent = ResUsers.browse(new_agent_id)
    if not new_agent.exists():
        raise UserError(f'Agent with id={new_agent_id} not found.')

    # Validate same company
    company = service.env.company
    if company not in new_agent.company_ids:
        raise UserError(
            f'Agent {new_agent.name} does not belong to company {company.name}.'
        )

    previous_agent = service.agent_id
    service.write({'agent_id': new_agent_id})

    # Audit trail message
    reason_text = f' Reason: {reason}' if reason else ''
    body = (
        f'Service reassigned from <b>{previous_agent.name}</b> to '
        f'<b>{new_agent.name}</b>.{reason_text}'
    )
    service.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

    # FR-024b: mail.activity notifications to both agents
    activity_type = service.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
    activity_type_id = activity_type.id if activity_type else False

    if previous_agent and previous_agent.id != new_agent_id:
        _notify_agent(service, previous_agent, 'Atendimento foi reatribuído a outro agente.',
                      activity_type_id)
    _notify_agent(service, new_agent,
                  f'Você foi atribuído ao atendimento {service.name}.', activity_type_id)

    _logger.info(
        'Service %s (id=%d) reassigned from agent %d to agent %d',
        service.name, service.id,
        previous_agent.id if previous_agent else 0,
        new_agent_id,
    )


def _notify_agent(service, agent, note, activity_type_id):
    """Create a mail.activity for an agent on a service."""
    try:
        service.activity_schedule(
            activity_type_id=activity_type_id,
            summary=note[:80],
            user_id=agent.id,
        )
    except Exception:
        _logger.exception('Failed to create mail.activity for agent %d', agent.id)


def compute_summary(env, company_id=None, agent_id=None):

    company_id = company_id or env.company.id

    Service = env['real.estate.service']
    base_domain = [('company_id', '=', company_id)]
    if agent_id:
        base_domain.append(('agent_id', '=', agent_id))

    groups = Service.read_group(
        domain=base_domain,
        fields=['stage'],
        groupby=['stage'],
    )

    by_stage = {g['stage']: g['stage_count'] for g in groups}
    total = sum(by_stage.values())

    orphan_count = Service.search_count(base_domain + [('is_orphan_agent', '=', True)])

    return {
        'total': total,
        'orphan_agent': orphan_count,
        'by_stage': by_stage,
    }


def _post_stage_change_message(service, origin_stage, new_stage, comment=None):
    """Post an audit message on the service when stage changes."""
    body = f'Stage changed from <b>{origin_stage}</b> to <b>{new_stage}</b>.'
    if comment:
        body += f'<br/>Comment: {comment}'
    service.message_post(
        body=body,
        message_type='comment',
        subtype_xmlid='mail.mt_note',
    )
