# -*- coding: utf-8 -*-
"""
Post-init hook: Feature 015 — Service Pipeline (Atendimentos)

Creates per-company defaults on module install/upgrade:
  - thedevkitchen.service.settings singleton
  - System tag 'closed' (is_system=True)
  - 4 default non-system tags (Follow Up, Qualificado, Lançamento, Parceria)
  - 5 default service sources (Site, Indicação, Portal Imobiliário, WhatsApp, Plantão)

All operations are idempotent (checked via xml_id or domain search).

Research: R6 (specs/015-service-pipeline-atendimentos/research.md)
data-model.md: E2 (tag), E3 (source), E5 (settings)
"""
import logging

_logger = logging.getLogger(__name__)

# --- Default sources per company -----------------------------------------
DEFAULT_SOURCES = [
    {'name': 'Site',                'code': 'site'},
    {'name': 'Indicação',           'code': 'indicacao'},
    {'name': 'Portal Imobiliário',  'code': 'portal'},
    {'name': 'WhatsApp',            'code': 'whatsapp'},
    {'name': 'Plantão',             'code': 'plantao'},
]

# --- Default non-system tags per company ---------------------------------
DEFAULT_TAGS = [
    {'name': 'Follow Up',   'color': '#3498db'},
    {'name': 'Qualificado', 'color': '#2ecc71'},
    {'name': 'Lançamento',  'color': '#e67e22'},
    {'name': 'Parceria',    'color': '#9b59b6'},
]


def post_init(env):
    """Create per-company defaults for Feature 015 on install."""
    companies = env['res.company'].sudo().search([])
    _logger.info('Feature 015 post_init: bootstrapping %d companies', len(companies))

    for company in companies:
        _ensure_settings(env, company)
        _ensure_system_tag_closed(env, company)
        _ensure_default_tags(env, company)
        _ensure_default_sources(env, company)

    _logger.info('Feature 015 post_init: done')


# --------------------------------------------------------------------------

def _ensure_settings(env, company):
    """Create thedevkitchen.service.settings singleton for company if missing."""
    existing = env['thedevkitchen.service.settings'].sudo().search(
        [('company_id', '=', company.id)], limit=1
    )
    if not existing:
        env['thedevkitchen.service.settings'].sudo().create({
            'company_id': company.id,
            'pendency_threshold_days': 3,
        })
        _logger.debug('Feature 015: created settings for company %s', company.name)


def _ensure_system_tag_closed(env, company):
    """Create the immutable system tag 'closed' for company if missing."""
    Tag = env['real.estate.service.tag'].sudo()
    existing = Tag.search([
        ('company_id', '=', company.id),
        ('is_system', '=', True),
        ('name', '=', 'Encerrado'),
    ], limit=1)
    if not existing:
        # Use context flag so _check_system_tag_immutable is bypassed on creation
        Tag.with_context(**{'service.tag_admin': True}).create({
            'name': 'Encerrado',
            'color': '#7f8c8d',
            'is_system': True,
            'company_id': company.id,
        })
        _logger.debug('Feature 015: created system tag Encerrado for company %s', company.name)


def _ensure_default_tags(env, company):
    """Create default non-system tags for company if missing."""
    Tag = env['real.estate.service.tag'].sudo()
    for tag_vals in DEFAULT_TAGS:
        existing = Tag.search([
            ('company_id', '=', company.id),
            ('name', '=', tag_vals['name']),
        ], limit=1)
        if not existing:
            Tag.create({
                'name': tag_vals['name'],
                'color': tag_vals['color'],
                'is_system': False,
                'company_id': company.id,
            })
            _logger.debug(
                'Feature 015: created tag "%s" for company %s',
                tag_vals['name'], company.name,
            )


def _ensure_default_sources(env, company):
    """Create default service sources for company if missing."""
    Source = env['real.estate.service.source'].sudo()
    for src_vals in DEFAULT_SOURCES:
        existing = Source.search([
            ('company_id', '=', company.id),
            ('code', '=', src_vals['code']),
        ], limit=1)
        if not existing:
            Source.create({
                'name': src_vals['name'],
                'code': src_vals['code'],
                'company_id': company.id,
            })
            _logger.debug(
                'Feature 015: created source "%s" for company %s',
                src_vals['name'], company.name,
            )
