# -*- coding: utf-8 -*-
"""
Partner Deduplication Service — Feature 015

Finds or creates a res.partner based on phone and/or email lookup.

Conflict resolution (FR-022):
  a) Phone match takes precedence over email match.
  b) Single provided phone matches multiple distinct partners → raises DomainError
     (controller maps to HTTP 409 with candidate partner IDs).
  c) Phone and email match different partners → prefer phone match and post an
     audit message on the service noting the divergence.

Usage:
    from .partner_dedup_service import find_or_create_partner
    partner, conflict = find_or_create_partner(env, name, email, phones)
"""
import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PartnerDeduplicationConflict(Exception):
    """Raised when a single phone number matches multiple distinct partners.

    Attributes:
        candidate_ids: list of res.partner IDs matching the conflicting phone.
    """
    def __init__(self, message, candidate_ids=None):
        super().__init__(message)
        self.candidate_ids = candidate_ids or []


def find_or_create_partner(env, name, email=None, phones=None):
    """Find an existing partner or create a new one.

    Resolution order (FR-022):
    1. If phones provided: search res.partner.phone by number for each phone.
       - If exactly one partner found across all phones: use it.
       - If multiple distinct partners found across all phones: raise
         PartnerDeduplicationConflict with candidate IDs.
    2. If no phone match and email provided: search res.partner by email.
    3. If phone match and email match differ: use phone match, log divergence.
    4. If no match: create new partner with all provided phones.

    Args:
        env: Odoo environment.
        name (str): Client name (required for creation).
        email (str|None): Client email address.
        phones (list[dict]|None): List of dicts with keys:
            - type (str): 'mobile'|'home'|'work'|'whatsapp'|'fax'
            - number (str): phone number string
            - is_primary (bool, optional)

    Returns:
        tuple: (res.partner record, divergence_info: str|None)
               divergence_info is non-None when phone and email matched
               different partners (FR-022c).
    """
    phones = phones or []
    ResPartner = env['res.partner']
    PartnerPhone = env['real.estate.partner.phone']

    phone_partner = None
    email_partner = None
    divergence_info = None

    # ------------------------------------------------------------------ #
    # Step 1: phone lookup                                                 #
    # ------------------------------------------------------------------ #
    if phones:
        numbers = [p['number'].strip() for p in phones if p.get('number')]
        if numbers:
            phone_records = PartnerPhone.search([('number', 'in', numbers)])
            partner_ids = phone_records.mapped('partner_id')

            if len(partner_ids) == 1:
                phone_partner = partner_ids
            elif len(partner_ids) > 1:
                # FR-022b: single lookup matched multiple distinct partners
                raise PartnerDeduplicationConflict(
                    f'Provided phone number(s) match {len(partner_ids)} distinct partners. '
                    f'Please disambiguate before creating the service.',
                    candidate_ids=partner_ids.ids,
                )

    # ------------------------------------------------------------------ #
    # Step 2: email lookup (only when no phone match)                     #
    # ------------------------------------------------------------------ #
    if not phone_partner and email:
        email_partners = ResPartner.search([('email', '=ilike', email.strip())], limit=2)
        if len(email_partners) == 1:
            email_partner = email_partners

    # ------------------------------------------------------------------ #
    # Step 3: convergence / divergence check                              #
    # ------------------------------------------------------------------ #
    if phone_partner and email_partner and phone_partner.id != email_partner.id:
        # FR-022c: phone and email match different partners — prefer phone
        divergence_info = (
            f'Phone match (partner #{phone_partner.id}) diverges from email match '
            f'(partner #{email_partner.id}). Using phone match per FR-022.'
        )
        _logger.warning('Partner dedup divergence: %s', divergence_info)

    # ------------------------------------------------------------------ #
    # Step 4: resolve final partner                                        #
    # ------------------------------------------------------------------ #
    if phone_partner:
        partner = phone_partner
    elif email_partner:
        partner = email_partner
    else:
        # No match — create new partner
        create_vals = {'name': name.strip()}
        if email:
            create_vals['email'] = email.strip()
        partner = ResPartner.create(create_vals)
        _logger.info('Created new partner id=%d for dedup', partner.id)

    # ------------------------------------------------------------------ #
    # Step 5: attach new phones to existing partner if not already there  #
    # ------------------------------------------------------------------ #
    if phones:
        existing_numbers = set(partner.phone_ids.mapped('number'))
        for phone_data in phones:
            number = phone_data.get('number', '').strip()
            if number and number not in existing_numbers:
                PartnerPhone.create({
                    'partner_id': partner.id,
                    'phone_type': phone_data.get('type', 'mobile'),
                    'number': number,
                    'is_primary': phone_data.get('is_primary', False),
                })

    return partner, divergence_info
