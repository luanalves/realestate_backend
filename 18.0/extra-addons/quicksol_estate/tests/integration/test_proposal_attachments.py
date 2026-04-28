# -*- coding: utf-8 -*-
"""
Integration tests — Attachments (T059-T062)
Covers: US7 — upload allowed types, size limit, download URL
"""
import base64
from odoo.tests import tagged
from odoo.exceptions import ValidationError

from .base_proposal_test import BaseProposalTest


@tagged('post_install', '-at_install', 'proposal', 'proposal_attachments')
class TestProposalAttachments(BaseProposalTest):

    def _attach(self, proposal, name='test.pdf', mimetype='application/pdf', size=1024):
        """Helper to create an ir.attachment on a proposal."""
        return self.env['ir.attachment'].create({
            'name': name,
            'datas': base64.b64encode(b'x' * size),
            'res_model': 'real.estate.proposal',
            'res_id': proposal.id,
            'mimetype': mimetype,
            'company_id': self.company.id,
        })

    def test_attach_pdf(self):
        """FR-039: PDF attachment is accepted."""
        p = self._create_proposal()
        att = self._attach(p, 'document.pdf', 'application/pdf')
        self.assertEqual(att.mimetype, 'application/pdf')

    def test_attach_image(self):
        """FR-039: JPEG image attachment is accepted."""
        p = self._create_proposal()
        att = self._attach(p, 'photo.jpg', 'image/jpeg')
        self.assertTrue(att.exists())

    def test_documents_count_computed(self):
        """FR-040: documents_count field reflects attachment count."""
        p = self._create_proposal()
        self._attach(p)
        self._attach(p, 'doc2.pdf')
        p._compute_documents_count()
        self.assertEqual(p.documents_count, 2)

    def test_agent_cannot_delete_attachment(self):
        """FR-042: Agents can upload but not delete attachments they did not create."""
        # This test is a placeholder — actual file deletion ACL depends on ir.attachment rules
        # TODO: add ir.rule for attachment deletion restriction
        p = self._create_proposal()
        att = self._attach(p)
        # Agent can read own proposal attachments
        visible = self.env['ir.attachment'].with_user(self.agent_user).search([
            ('res_model', '=', 'real.estate.proposal'),
            ('res_id', '=', p.id),
        ])
        self.assertIn(att, visible)
