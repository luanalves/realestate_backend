# -*- coding: utf-8 -*-
import unittest
import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SERIALIZERS_PATH = (
    Path(__file__).parent.parent.parent / 'controllers' / 'utils' / 'serializers.py'
)
SPEC = importlib.util.spec_from_file_location('property_mapping_serializers', SERIALIZERS_PATH)
serializers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(serializers)

build_property_mapping_values = serializers.build_property_mapping_values
serialize_property_mapping_fields = serializers.serialize_property_mapping_fields


class TestPropertyMappingValues(unittest.TestCase):
    def test_build_values_accepts_valid_mapping_fields(self):
        vals, errors = build_property_mapping_values({
            'owner_email': 'Owner@Example.COM',
            'send_activities_to_owner': True,
            'included_in_commission_date': '2026-05-04',
            'year_of_renovation': '2020',
            'tags': ['Premium'],
        })

        self.assertEqual(errors, [])
        self.assertEqual(vals['owner_email'], 'owner@example.com')
        self.assertTrue(vals['send_activities_to_owner'])
        self.assertEqual(vals['included_in_commission_date'], date(2026, 5, 4))
        self.assertEqual(vals['reform_year'], 2020)

    def test_build_values_rejects_invalid_mapping_fields(self):
        _vals, errors = build_property_mapping_values({
            'owner_email': 'invalid',
            'send_activities_to_owner': 'true',
            'included_in_commission_date': '04/05/2026',
            'tags': 'Premium',
        })

        self.assertEqual(
            {error['field'] for error in errors},
            {'owner_email', 'send_activities_to_owner', 'included_in_commission_date', 'tags'},
        )


class TestSerializePropertyMappingFields(unittest.TestCase):
    def test_serialize_mapping_fields_uses_stable_defaults(self):
        property_record = _property_record()

        result = serialize_property_mapping_fields(property_record)

        self.assertIsNone(result['owner_email'])
        self.assertFalse(result['send_activities_to_owner'])
        self.assertEqual(result['tags'], [])
        self.assertEqual(result['property_images'], [])
        self.assertEqual(result['property_files'], [])

    def test_serialize_mapping_fields_returns_values_and_metadata(self):
        property_record = _property_record(
            owner_email='owner@example.com',
            send_activities_to_owner=True,
            included_in_commission_date=date(2026, 5, 4),
            tag_ids=[SimpleNamespace(name='Premium')],
            photo_ids=[
                SimpleNamespace(
                    id=10,
                    name='fachada.jpg',
                    display_name='fachada.jpg',
                    image='aGVsbG8=',
                )
            ],
            document_ids=[
                SimpleNamespace(
                    id=20,
                    name='Matricula',
                    display_name='Matricula',
                    file_name='matricula.pdf',
                    file='aGVsbG8=',
                )
            ],
        )

        result = serialize_property_mapping_fields(property_record)

        self.assertEqual(result['owner_email'], 'owner@example.com')
        self.assertTrue(result['send_activities_to_owner'])
        self.assertEqual(result['included_in_commission_date'], '2026-05-04')
        self.assertEqual(result['tags'], ['Premium'])
        self.assertEqual(result['property_images'][0]['mimetype'], 'image/jpeg')
        self.assertEqual(result['property_images'][0]['size'], 5)
        self.assertNotIn('image', result['property_images'][0])
        self.assertEqual(result['property_files'][0]['mimetype'], 'application/pdf')
        self.assertNotIn('file', result['property_files'][0])


def _property_record(**overrides):
    fields = {
        'owner_email': False,
        'owner_home_phone': False,
        'owner_business_phone': False,
        'owner_mobile_phone': False,
        'origin_media': False,
        'send_activities_to_owner': False,
        'street': False,
        'registered_by': False,
        'alternative_reference': False,
        'intention': False,
        'iptu_payment_condition': False,
        'iptu_value': False,
        'rental_guarantee_insurance': False,
        'fire_insurance': False,
        'exclusivity': False,
        'property_situation': False,
        'reform_year': False,
        'zoning_type': False,
        'internal_notes': False,
        'key_location': False,
        'publish_website': False,
        'publish_featured': False,
        'virtual_tour_url': False,
        'has_sign': False,
        'publish_super_featured': False,
        'youtube_video_url': False,
        'commission_type': False,
        'captured_intention': False,
        'included_in_commission_date': False,
        'commercial_condition': False,
        'iptu_code': False,
        'matricula_number': False,
        'electricity_network_code': False,
        'water_network_code': False,
        'titles_rights': False,
        'approved_environmental_agency': False,
        'approved_project': False,
        'documentation_observations': False,
        'tag_ids': [],
        'photo_ids': [],
        'document_ids': [],
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


if __name__ == '__main__':
    unittest.main(verbosity=2)
