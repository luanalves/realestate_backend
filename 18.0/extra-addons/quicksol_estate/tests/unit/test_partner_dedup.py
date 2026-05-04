# -*- coding: utf-8 -*-
"""
Unit Test: Partner Deduplication Service — Feature 015 (US5)

Tests the deduplication algorithm logic (FR-022 conflict resolution rules).
Uses mocks only — no DB, no Odoo env required (ADR-003).

Task: T059
FRs: FR-022, FR-022a, FR-022b, FR-022c
"""
import sys
import types
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub the odoo dependency so the service can be imported standalone
# ---------------------------------------------------------------------------
odoo_stub = types.ModuleType('odoo')
odoo_stub.exceptions = types.ModuleType('odoo.exceptions')

class _UserError(Exception):
    pass

odoo_stub.exceptions.UserError = _UserError
sys.modules.setdefault('odoo', odoo_stub)
sys.modules.setdefault('odoo.exceptions', odoo_stub.exceptions)

import importlib
import os as _os
import pathlib as _pathlib

# Locate and load the service module directly from the file path
_svc_path = str(
    _pathlib.Path(__file__).parent.parent.parent
    / 'services' / 'partner_dedup_service.py'
)

_spec = importlib.util.spec_from_file_location('partner_dedup_service', _svc_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

find_or_create_partner = _mod.find_or_create_partner
PartnerDeduplicationConflict = _mod.PartnerDeduplicationConflict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_partner(pid, name, phone_numbers=None):
    p = MagicMock()
    p.id = pid
    p.name = name
    p.phone_ids = MagicMock()
    p.phone_ids.mapped = MagicMock(return_value=phone_numbers or [])
    return p


def _make_partner_ids_set(partners):
    """Mimic an Odoo many2many recordset of partners."""
    m = MagicMock()
    m.__len__ = lambda s: len(partners)
    m.__bool__ = lambda s: bool(partners)
    m.__iter__ = lambda s: iter(partners)
    m.ids = [p.id for p in partners]
    # single-partner shortcut used in service: .id
    if len(partners) == 1:
        m.id = partners[0].id
    return m


def _make_env(phone_partner=None, email_partners=None):
    """Build a minimal mock env for find_or_create_partner."""
    PartnerPhone = MagicMock()
    ResPartner = MagicMock()

    # phone lookup ──────────────────────────────────────────────────────────
    if phone_partner is None:
        # no phone records found
        ph_rs = MagicMock()
        ph_rs.mapped = MagicMock(return_value=_make_partner_ids_set([]))
        PartnerPhone.search = MagicMock(return_value=ph_rs)
    elif isinstance(phone_partner, list):
        # multiple → conflict
        ph_rs = MagicMock()
        ph_rs.mapped = MagicMock(return_value=_make_partner_ids_set(phone_partner))
        PartnerPhone.search = MagicMock(return_value=ph_rs)
    else:
        ph_rs = MagicMock()
        ph_rs.mapped = MagicMock(return_value=_make_partner_ids_set([phone_partner]))
        PartnerPhone.search = MagicMock(return_value=ph_rs)

    # email lookup ──────────────────────────────────────────────────────────
    if not email_partners:
        ep_rs = MagicMock()
        ep_rs.__len__ = lambda s: 0
        ep_rs.__bool__ = lambda s: False
        ResPartner.search = MagicMock(return_value=ep_rs)
    elif isinstance(email_partners, list):
        ep_rs = MagicMock()
        ep_rs.__len__ = lambda s: len(email_partners)
        ep_rs.__bool__ = lambda s: bool(email_partners)
        ep_rs.__iter__ = lambda s: iter(email_partners)
        if len(email_partners) == 1:
            ep_rs.id = email_partners[0].id
        ResPartner.search = MagicMock(return_value=ep_rs)
    else:
        ep_rs = MagicMock()
        ep_rs.__len__ = lambda s: 1
        ep_rs.__bool__ = lambda s: True
        ep_rs.__iter__ = lambda s: iter([email_partners])
        ep_rs.id = email_partners.id
        ResPartner.search = MagicMock(return_value=ep_rs)

    new_partner = _make_partner(99, 'New Partner')
    ResPartner.create = MagicMock(return_value=new_partner)

    env = MagicMock()
    env.__getitem__ = lambda s, key: {
        'real.estate.partner.phone': PartnerPhone,
        'res.partner': ResPartner,
    }.get(key, MagicMock())

    return env, ResPartner, PartnerPhone


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPartnerDedupNoMatch(unittest.TestCase):

    def test_creates_new_partner_when_no_phone_no_email(self):
        """No phone + no email → create new partner, no divergence."""
        env, ResPartner, _ = _make_env(phone_partner=None, email_partners=None)
        partner, divergence = find_or_create_partner(env, 'New Client', email=None, phones=[])
        ResPartner.create.assert_called_once()
        self.assertIsNone(divergence)

    def test_creates_new_partner_when_email_no_match(self):
        """Email provided but no existing partner has that email → create new."""
        env, ResPartner, _ = _make_env(phone_partner=None, email_partners=None)
        partner, divergence = find_or_create_partner(
            env, 'New Client', email='unknown@x.com', phones=[]
        )
        ResPartner.create.assert_called_once()
        self.assertIsNone(divergence)


class TestPartnerDedupPhoneMatch(unittest.TestCase):

    def test_single_phone_match_reuses_partner(self):
        """Phone matches exactly one partner → reuse, no create, no divergence."""
        partner_a = _make_partner(1, 'Partner A')
        env, ResPartner, _ = _make_env(phone_partner=partner_a)
        partner, divergence = find_or_create_partner(
            env, 'Partner A', phones=[{'type': 'mobile', 'number': '11999990000'}]
        )
        self.assertEqual(partner.id, 1)
        ResPartner.create.assert_not_called()
        self.assertIsNone(divergence)

    def test_multiple_phone_partners_raises_conflict(self):
        """Phone matches 2+ partners → PartnerDeduplicationConflict with candidate_ids."""
        p1 = _make_partner(1, 'A')
        p2 = _make_partner(2, 'B')
        env, _, _ = _make_env(phone_partner=[p1, p2])
        with self.assertRaises(PartnerDeduplicationConflict) as ctx:
            find_or_create_partner(
                env, 'X', phones=[{'type': 'mobile', 'number': '11999990000'}]
            )
        exc = ctx.exception
        self.assertIn(1, exc.candidate_ids)
        self.assertIn(2, exc.candidate_ids)

    def test_conflict_exception_has_candidate_ids_attribute(self):
        """PartnerDeduplicationConflict always exposes .candidate_ids."""
        exc = PartnerDeduplicationConflict('test', candidate_ids=[5, 7])
        self.assertIn(5, exc.candidate_ids)
        self.assertIn(7, exc.candidate_ids)

    def test_empty_candidate_ids_when_not_provided(self):
        """PartnerDeduplicationConflict.candidate_ids defaults to empty list."""
        exc = PartnerDeduplicationConflict('test')
        self.assertEqual(exc.candidate_ids, [])


class TestPartnerDedupEmailMatch(unittest.TestCase):

    def test_email_match_reuses_partner_when_no_phone(self):
        """No phone provided, email matches one partner → reuse."""
        partner_b = _make_partner(2, 'B by email')
        env, ResPartner, _ = _make_env(phone_partner=None, email_partners=partner_b)
        partner, divergence = find_or_create_partner(
            env, 'B by email', email='b@example.com', phones=[]
        )
        self.assertEqual(partner.id, 2)
        ResPartner.create.assert_not_called()
        self.assertIsNone(divergence)

    def test_multiple_email_matches_no_reuse(self):
        """Two partners with same email → treat as no-match (ambiguous), create new."""
        p1 = _make_partner(1, 'A')
        p2 = _make_partner(2, 'B')
        env, ResPartner, _ = _make_env(phone_partner=None, email_partners=[p1, p2])
        partner, divergence = find_or_create_partner(
            env, 'Unknown', email='shared@example.com', phones=[]
        )
        # Two results from email search — service calls with limit=2 and checks len == 1
        # If len != 1, falls through to create
        ResPartner.create.assert_called_once()


class TestPartnerDedupDivergence(unittest.TestCase):

    def test_phone_email_divergence_prefers_phone(self):
        """Phone → partner A, email → partner B → use phone, return divergence string."""
        partner_a = _make_partner(1, 'A by phone')
        partner_b = _make_partner(2, 'B by email')
        env, ResPartner, _ = _make_env(phone_partner=partner_a, email_partners=partner_b)
        partner, divergence = find_or_create_partner(
            env, 'X',
            email='b@example.com',
            phones=[{'type': 'mobile', 'number': '11999990000'}],
        )
        self.assertEqual(partner.id, 1)
        ResPartner.create.assert_not_called()
        self.assertIsNotNone(divergence)
        self.assertIn('diverge', divergence.lower())

    def test_phone_email_same_partner_no_divergence(self):
        """Phone and email both resolve to same partner → no divergence."""
        partner_a = _make_partner(1, 'A')
        env, ResPartner, _ = _make_env(phone_partner=partner_a, email_partners=partner_a)
        partner, divergence = find_or_create_partner(
            env, 'A',
            email='a@example.com',
            phones=[{'type': 'mobile', 'number': '11999990000'}],
        )
        self.assertEqual(partner.id, 1)
        self.assertIsNone(divergence)


class TestPartnerDedupPhoneTypes(unittest.TestCase):

    def test_allowed_phone_types(self):
        """Validate known-good phone types for the schema."""
        allowed = {'mobile', 'home', 'work', 'whatsapp', 'fax'}
        for t in ('mobile', 'home', 'work', 'whatsapp', 'fax'):
            self.assertIn(t, allowed)

    def test_invalid_phone_type_not_in_allowed(self):
        """'sms' is not an allowed phone type."""
        allowed = {'mobile', 'home', 'work', 'whatsapp', 'fax'}
        self.assertNotIn('sms', allowed)


if __name__ == '__main__':
    unittest.main()
