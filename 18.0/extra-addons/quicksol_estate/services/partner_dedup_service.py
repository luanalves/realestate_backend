# -*- coding: utf-8 -*-

import logging

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PartnerDeduplicationConflict(Exception):

    def __init__(self, message, candidate_ids=None):
        super().__init__(message)
        self.candidate_ids = candidate_ids or []


def find_or_create_partner(env, name, email=None, phones=None):

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
    # Step 2: email lookup                                                #
    # Always performed when email provided — needed for divergence check  #
    # (FR-022c) even when phone already matched.                          #
    # ------------------------------------------------------------------ #
    if email:
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
