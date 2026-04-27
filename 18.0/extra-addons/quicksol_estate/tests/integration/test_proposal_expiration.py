# -*- coding: utf-8 -*-
"""
Integration tests — Cron expiration (T063-T066)
Covers: US8 — _cron_expire_proposals(), expired state, promote queued after expire
"""
from datetime import date, timedelta
from odoo.tests import tagged

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_expiration')
class TestProposalExpiration(BaseProposalTest):

    def _send_with_validity(self, days_from_today):
        """Create and send a proposal with a specific valid_until."""
        valid = date.today() + timedelta(days=days_from_today)
        p = self._create_proposal(valid_until=valid)
        # Bypass FSM guard by writing state directly for test setup
        p.write({'state': 'sent', 'valid_until': valid})
        return p

    def _force_expired(self, proposal):
        """Bypass valid_until constraint to simulate an expired proposal in tests."""
        self.env.cr.execute(
            "UPDATE real_estate_proposal SET state = 'sent', valid_until = %s WHERE id = %s",
            [date.today() - timedelta(days=1), proposal.id]
        )
        proposal.invalidate_recordset()

    def test_cron_expires_overdue_sent_proposals(self):
        """US8/FR-026: Cron transitions sent→expired when valid_until < today."""
        p = self._create_proposal()
        self._force_expired(p)
        self.env['real.estate.proposal']._cron_expire_proposals()
        p.invalidate_recordset()
        self.assertEqual(p.state, 'expired')

    def test_cron_does_not_expire_future_proposals(self):
        """US8/FR-026: Proposals with valid_until in future are NOT expired."""
        p = self._send_with_validity(days_from_today=10)
        self.env['real.estate.proposal']._cron_expire_proposals()
        p.invalidate_recordset()
        self.assertNotEqual(p.state, 'expired')

    def test_cron_does_not_expire_terminal_proposals(self):
        """US8/FR-026: Terminal proposals are excluded from expiry cron."""
        p = self._create_proposal()
        self.env.cr.execute(
            "UPDATE real_estate_proposal SET state = 'cancelled', valid_until = %s WHERE id = %s",
            [date.today() - timedelta(days=1), p.id]
        )
        p.invalidate_recordset()
        self.env['real.estate.proposal']._cron_expire_proposals()
        p.invalidate_recordset()
        self.assertEqual(p.state, 'cancelled')  # unchanged

    def test_expire_promotes_queued(self):
        """FR-015+FR-026: When active proposal expires, oldest queued → draft."""
        p1 = self._create_proposal()
        self._force_expired(p1)

        client2 = self.env['res.partner'].create({'name': 'C2', 'vat': '11144477735'})
        p2 = self._create_proposal(partner_id=client2.id)
        p2.write({'state': 'queued'})

        self.env['real.estate.proposal']._cron_expire_proposals()
        p1.invalidate_recordset()
        p2.invalidate_recordset()

        self.assertEqual(p1.state, 'expired')
        self.assertEqual(p2.state, 'draft')
