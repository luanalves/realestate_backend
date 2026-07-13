# -*- coding: utf-8 -*-
"""
Integration tests closing @api.constrains / _sql_constraints gaps found in the
2026-07 ADR-003 validation-coverage audit of quicksol_estate.

Each constraint covered here previously had no automated test at all, or only
had a happy-path test (never a failure case) - i.e. it did not meet ADR-003's
"every validation needs a success test AND a failure test" rule.
"""
import json
from datetime import date, timedelta

from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class ValidationGapsBase(TransactionCase):
    """Shared minimal fixtures for the validation-gap tests below."""

    # Dedicated, unused-in-seed-data CNPJs (valid check digits per ADR-012).
    _CNPJ_1 = "12.345.670/0020-91"
    _CNPJ_2 = "12.345.670/0030-63"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Every subclass runs its own setUpClass in the same overall test
        # transaction, so a hardcoded CNPJ created per-class would collide
        # with res_company_cnpj_unique. Search-or-create instead (same
        # pattern used elsewhere in this test suite, e.g. test_assignment.py).
        cls.company = cls.env["res.company"].search(
            [("cnpj", "=", cls._CNPJ_1)], limit=1
        ) or cls.env["res.company"].create(
            {"name": "Validation Gaps Co", "cnpj": cls._CNPJ_1}
        )
        cls.other_company = cls.env["res.company"].search(
            [("cnpj", "=", cls._CNPJ_2)], limit=1
        ) or cls.env["res.company"].create(
            {"name": "Validation Gaps Co 2", "cnpj": cls._CNPJ_2}
        )

    def setUp(self):
        super().setUp()
        # Odoo's --test-enable transaction is not guaranteed to be rolled
        # back between separate `odoo -u ... --test-enable` invocations (as
        # opposed to between test *methods* within one run), so uniqueness
        # tests below purge their own fixtures first to stay idempotent
        # across repeated manual runs against the same dev database.
        self.env["real.estate.service.tag"].search(
            [("name", "in", ["Hot Lead", "Hot Lead Cross Co"])]
        ).unlink()
        self.env["thedevkitchen.service.settings"].search(
            [("company_id", "in", [self.company.id, self.other_company.id])]
        ).unlink()
        self.env["real.estate.service.source"].search(
            [
                ("code", "in", ["site", "site2"]),
                ("company_id", "in", [self.company.id, self.other_company.id]),
            ]
        ).unlink()

    @classmethod
    def _location_type(cls):
        location_type = cls.env["real.estate.location.type"].search(
            [("code", "=", "URB")], limit=1
        )
        return location_type or cls.env["real.estate.location.type"].create(
            {"name": "Urban", "code": "URB", "sequence": 10}
        )

    @classmethod
    def _property_type(cls):
        property_type = cls.env["real.estate.property.type"].search(
            [("name", "=", "House")], limit=1
        )
        return property_type or cls.env["real.estate.property.type"].create(
            {"name": "House"}
        )

    @classmethod
    def _state(cls):
        return cls.env["res.country.state"].search(
            [("country_id.code", "=", "BR")], limit=1
        )

    @classmethod
    def _create_property(cls, **overrides):
        vals = {
            "name": "Validation Test Property",
            "company_id": cls.company.id,
            "property_type_id": cls._property_type().id,
            "location_type_id": cls._location_type().id,
            "state_id": cls._state().id,
            "price": 250000.00,
            "area": 100.0,
            "zip_code": "12345-678",
            "city": "São Paulo",
            "street": "Avenida Paulista",
            "street_number": "1000",
        }
        vals.update(overrides)
        return cls.env["real.estate.property"].create(vals)


class TestPropertyAuthorizationDates(ValidationGapsBase):
    """real.estate.property::_check_authorization_dates"""

    def test_authorization_end_before_start_raises(self):
        with self.assertRaises(ValidationError):
            self._create_property(
                authorization_start_date=date(2026, 6, 1),
                authorization_end_date=date(2026, 5, 1),
            )

    def test_authorization_end_after_start_passes(self):
        prop = self._create_property(
            authorization_start_date=date(2026, 5, 1),
            authorization_end_date=date(2026, 6, 1),
        )
        self.assertTrue(prop.id)


class TestPropertyIntentions(ValidationGapsBase):
    """real.estate.property::_check_intentions"""

    def test_neither_for_sale_nor_for_rent_raises(self):
        with self.assertRaises(ValidationError):
            self._create_property(for_sale=False, for_rent=False)

    def test_for_sale_only_passes(self):
        prop = self._create_property(for_sale=True, for_rent=False)
        self.assertTrue(prop.id)


class TestPropertyYears(ValidationGapsBase):
    """real.estate.property::_check_years"""

    def test_reform_year_before_construction_year_raises(self):
        with self.assertRaises(ValidationError):
            self._create_property(construction_year=2020, reform_year=2015)

    def test_reform_year_after_construction_year_passes(self):
        prop = self._create_property(construction_year=2015, reform_year=2020)
        self.assertTrue(prop.id)


class TestServiceTagColorFormat(ValidationGapsBase):
    """real.estate.service.tag::_check_color_format.

    Note: the model also has a DB-level CHECK (valid_color_format), which
    fires before the Python constrains on create() - so the observable
    failure here is an IntegrityError, not a ValidationError.
    """

    def test_invalid_hex_color_raises(self):
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["real.estate.service.tag"].create(
                    {
                        "name": "Invalid Color Tag",
                        "color": "not-a-color",
                        "company_id": self.company.id,
                    }
                )

    def test_valid_hex_color_passes(self):
        tag = self.env["real.estate.service.tag"].create(
            {
                "name": "Valid Color Tag",
                "color": "#FF00AA",
                "company_id": self.company.id,
            }
        )
        self.assertTrue(tag.id)


class TestServiceTagUniqueNamePerCompany(ValidationGapsBase):
    """real.estate.service.tag: unique_tag_name_per_company (sql constraint)"""

    def test_duplicate_name_same_company_raises(self):
        self.env["real.estate.service.tag"].create(
            {"name": "Hot Lead", "company_id": self.company.id}
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["real.estate.service.tag"].create(
                    {"name": "Hot Lead", "company_id": self.company.id}
                )

    def test_same_name_different_company_passes(self):
        self.env["real.estate.service.tag"].create(
            {"name": "Hot Lead Cross Co", "company_id": self.company.id}
        )
        tag_other_co = self.env["real.estate.service.tag"].create(
            {"name": "Hot Lead Cross Co", "company_id": self.other_company.id}
        )
        self.assertTrue(tag_other_co.id)


class TestServiceSettingsAutoCloseDays(ValidationGapsBase):
    """thedevkitchen.service.settings::_check_auto_close_days"""

    def test_auto_close_days_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            self.env["thedevkitchen.service.settings"].create(
                {"company_id": self.company.id, "auto_close_after_days": 400}
            )

    def test_auto_close_days_in_range_passes(self):
        settings = self.env["thedevkitchen.service.settings"].create(
            {"company_id": self.company.id, "auto_close_after_days": 90}
        )
        self.assertTrue(settings.id)


class TestServiceSettingsPendencyThreshold(ValidationGapsBase):
    """thedevkitchen.service.settings::_check_pendency_threshold"""

    def test_pendency_threshold_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            self.env["thedevkitchen.service.settings"].create(
                {"company_id": self.company.id, "pendency_threshold_days": 45}
            )

    def test_pendency_threshold_in_range_passes(self):
        settings = self.env["thedevkitchen.service.settings"].create(
            {"company_id": self.company.id, "pendency_threshold_days": 5}
        )
        self.assertTrue(settings.id)


class TestServiceSettingsUniquePerCompany(ValidationGapsBase):
    """thedevkitchen.service.settings: unique_settings_per_company (sql constraint)"""

    def test_duplicate_settings_same_company_raises(self):
        self.env["thedevkitchen.service.settings"].create(
            {"company_id": self.company.id}
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["thedevkitchen.service.settings"].create(
                    {"company_id": self.company.id}
                )

    def test_settings_different_company_passes(self):
        self.env["thedevkitchen.service.settings"].create(
            {"company_id": self.company.id}
        )
        settings_other_co = self.env["thedevkitchen.service.settings"].create(
            {"company_id": self.other_company.id}
        )
        self.assertTrue(settings_other_co.id)


class TestServiceSourceUniqueCodePerCompany(ValidationGapsBase):
    """real.estate.service.source: unique_source_code_per_company (sql constraint).

    Also the only test coverage this model has at all - it previously had no
    tests directory entry whatsoever.
    """

    def test_create_source_passes(self):
        source = self.env["real.estate.service.source"].create(
            {"name": "Website", "code": "site", "company_id": self.company.id}
        )
        self.assertTrue(source.id)

    def test_duplicate_code_same_company_raises(self):
        self.env["real.estate.service.source"].create(
            {"name": "Website", "code": "site", "company_id": self.company.id}
        )
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["real.estate.service.source"].create(
                    {
                        "name": "Website Duplicate",
                        "code": "site",
                        "company_id": self.company.id,
                    }
                )

    def test_same_code_different_company_passes(self):
        self.env["real.estate.service.source"].create(
            {"name": "Website", "code": "site2", "company_id": self.company.id}
        )
        source_other_co = self.env["real.estate.service.source"].create(
            {"name": "Website", "code": "site2", "company_id": self.other_company.id}
        )
        self.assertTrue(source_other_co.id)


class TestPropertyKeyQuantity(ValidationGapsBase):
    """real.estate.property.key::_check_quantity - model had zero tests."""

    def test_negative_quantity_raises(self):
        prop = self._create_property()
        with self.assertRaises(ValidationError):
            self.env["real.estate.property.key"].create(
                {
                    "key_code": "K-001",
                    "property_id": prop.id,
                    "quantity": -1,
                }
            )

    def test_non_negative_quantity_passes(self):
        prop = self._create_property()
        key = self.env["real.estate.property.key"].create(
            {
                "key_code": "K-002",
                "property_id": prop.id,
                "quantity": 2,
            }
        )
        self.assertTrue(key.id)


class TestCommissionTransactionPaymentConsistency(ValidationGapsBase):
    """real.estate.commission.transaction::_check_payment_consistency"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agent = cls.env["real.estate.agent"].search(
            [("cpf", "=", "11144477735"), ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["real.estate.agent"].create(
            {
                "name": "Validation Gaps Agent",
                "cpf": "11144477735",
                "email": "validation.gaps.agent@test.com",
                "company_id": cls.company.id,
            }
        )
        cls.rule = cls.env["real.estate.commission.rule"].create(
            {
                "agent_id": cls.agent.id,
                "company_id": cls.company.id,
                "transaction_type": "sale",
                "structure_type": "percentage",
                "percentage": 3.0,
                "fixed_amount": 0.0,
                "valid_from": date.today(),
                "valid_until": date.today() + timedelta(days=365),
            }
        )

    def _snapshot(self):
        return json.dumps(
            {
                "percentage": self.rule.percentage,
                "structure_type": self.rule.structure_type,
                "transaction_type": self.rule.transaction_type,
                "valid_from": str(self.rule.valid_from),
                "valid_until": str(self.rule.valid_until),
            }
        )

    def test_payment_date_without_paid_status_raises(self):
        with self.assertRaises(ValidationError):
            self.env["real.estate.commission.transaction"].create(
                {
                    "agent_id": self.agent.id,
                    "company_id": self.company.id,
                    "rule_id": self.rule.id,
                    "transaction_type": "sale",
                    "transaction_amount": 100000.00,
                    "commission_amount": 3000.00,
                    "rule_snapshot": self._snapshot(),
                    "payment_status": "pending",
                    "payment_date": date.today(),
                }
            )

    def test_paid_status_without_payment_date_raises(self):
        with self.assertRaises(ValidationError):
            self.env["real.estate.commission.transaction"].create(
                {
                    "agent_id": self.agent.id,
                    "company_id": self.company.id,
                    "rule_id": self.rule.id,
                    "transaction_type": "sale",
                    "transaction_amount": 100000.00,
                    "commission_amount": 3000.00,
                    "rule_snapshot": self._snapshot(),
                    "payment_status": "paid",
                    "payment_date": False,
                }
            )

    def test_paid_status_with_payment_date_passes(self):
        transaction = self.env["real.estate.commission.transaction"].create(
            {
                "agent_id": self.agent.id,
                "company_id": self.company.id,
                "rule_id": self.rule.id,
                "transaction_type": "sale",
                "transaction_amount": 100000.00,
                "commission_amount": 3000.00,
                "rule_snapshot": self._snapshot(),
                "payment_status": "paid",
                "payment_date": date.today(),
            }
        )
        self.assertTrue(transaction.id)

    def test_pending_status_without_payment_date_passes(self):
        transaction = self.env["real.estate.commission.transaction"].create(
            {
                "agent_id": self.agent.id,
                "company_id": self.company.id,
                "rule_id": self.rule.id,
                "transaction_type": "sale",
                "transaction_amount": 100000.00,
                "commission_amount": 3000.00,
                "rule_snapshot": self._snapshot(),
                "payment_status": "pending",
            }
        )
        self.assertTrue(transaction.id)
