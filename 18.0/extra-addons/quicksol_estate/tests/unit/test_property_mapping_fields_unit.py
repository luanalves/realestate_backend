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

PROPERTY_OPTIONS_PATH = (
    Path(__file__).parent.parent.parent / 'controllers' / 'utils' / 'property_options.py'
)
OPTIONS_SPEC = importlib.util.spec_from_file_location('property_mapping_options', PROPERTY_OPTIONS_PATH)
property_options = importlib.util.module_from_spec(OPTIONS_SPEC)
OPTIONS_SPEC.loader.exec_module(property_options)

build_property_mapping_values = serializers.build_property_mapping_values
serialize_property = serializers.serialize_property
serialize_property_mapping_fields = serializers.serialize_property_mapping_fields


class TestPropertyOptions(unittest.TestCase):
    def test_property_options_and_status_values_share_selection_source(self):
        env = _FakeSelectionEnv()

        options = property_options.build_property_options(env)
        status_values = property_options.get_property_status_values(env)

        self.assertEqual(
            options['property_status'],
            [
                {'value': 'available', 'label': 'Available'},
                {'value': 'maintenance', 'label': 'Under Maintenance'},
            ],
        )
        self.assertEqual(
            options['property_situation'],
            [
                {'value': 'Não Informado', 'label': 'Não Informado'},
                {'value': 'Desocupado', 'label': 'Desocupado'},
                {'value': 'Ocupado', 'label': 'Ocupado'},
                {'value': 'Reservado', 'label': 'Reservado'},
                {'value': 'Em construção', 'label': 'Em construção'},
                {'value': 'Lançamento', 'label': 'Lançamento'},
                {'value': 'Novo', 'label': 'Novo'},
            ],
        )
        self.assertEqual(status_values, ['available', 'maintenance'])
        self.assertEqual(options['related_options']['tags'], '/api/v1/tags')


class TestPropertyMappingValues(unittest.TestCase):
    def test_build_values_accepts_valid_mapping_fields(self):
        vals, errors = build_property_mapping_values({
            'send_activities_to_owner': True,
            'included_in_commission_date': '2026-05-04',
            'year_of_renovation': '2020',
            'tags': ['Premium'],
            'commercial_condition': 'Condição comercial padrão',
        })

        self.assertEqual(errors, [])
        self.assertTrue(vals['send_activities_to_owner'])
        self.assertEqual(vals['included_in_commission_date'], date(2026, 5, 4))
        self.assertEqual(vals['reform_year'], 2020)
        self.assertEqual(vals['commercial_condition'], 'Condição comercial padrão')

    def test_build_values_rejects_non_string_commercial_condition(self):
        _vals, errors = build_property_mapping_values({
            'commercial_condition': ['Condição comercial padrão'],
        })

        self.assertEqual(
            errors,
            [
                {
                    'field': 'commercial_condition',
                    'message': 'Must be a string',
                },
            ],
        )

    def test_build_values_rejects_invalid_mapping_fields(self):
        _vals, errors = build_property_mapping_values({
            'send_activities_to_owner': 'true',
            'included_in_commission_date': '04/05/2026',
            'tags': 'Premium',
        })

        self.assertEqual(
            {error['field'] for error in errors},
            {'send_activities_to_owner', 'included_in_commission_date', 'tags'},
        )

    def test_build_values_rejects_legacy_owner_contact_fields(self):
        _vals, errors = build_property_mapping_values({
            'owner_email': 'owner@example.com',
            'owner_mobile_phone': '+55 11 98888-7777',
        })

        self.assertEqual(
            errors,
            [
                {
                    'field': 'owner_email',
                    'message': 'Use owner_id to link a property owner',
                },
                {
                    'field': 'owner_mobile_phone',
                    'message': 'Use owner_id to link a property owner',
                },
            ],
        )


class TestSerializePropertyMappingFields(unittest.TestCase):
    def test_serialize_property_includes_sale_and_rent_flags(self):
        property_record = _property_record(for_sale=True, for_rent=False)

        result = serialize_property(property_record)

        self.assertTrue(result['for_sale'])
        self.assertFalse(result['for_rent'])
        self.assertEqual(result['property_status'], 'available')

    def test_serialize_property_situation_defaults_from_status(self):
        property_record = _property_record(
            property_status='available',
            property_situation=False,
        )

        result = serialize_property(property_record)

        self.assertEqual(result['property_situation'], 'Desocupado')

    def test_serialize_property_situation_preserves_explicit_value(self):
        property_record = _property_record(
            property_status='available',
            property_situation='Lançamento',
        )

        result = serialize_property(property_record)

        self.assertEqual(result['property_situation'], 'Lançamento')

    def test_serialize_property_includes_owner_from_relationship(self):
        property_record = _property_record(
            owner_id=SimpleNamespace(
                id=9,
                name='Maria Proprietaria',
                email='maria@example.com',
                phone='1130001000',
                mobile='11999990000',
                whatsapp='11988887777',
                partner_id=SimpleNamespace(id=44),
                address='Rua do Proprietario',
                city='Sao Paulo',
                state_id=SimpleNamespace(id=35, name='Sao Paulo', code='SP'),
                zip_code='01000-000',
            ),
        )

        result = serialize_property(property_record)

        self.assertEqual(result['owner']['id'], 9)
        self.assertEqual(result['owner']['name'], 'Maria Proprietaria')
        self.assertEqual(result['owner']['email'], 'maria@example.com')
        self.assertEqual(result['owner']['partner_id'], 44)
        self.assertEqual(result['owner']['state']['code'], 'SP')

    def test_serialize_mapping_fields_uses_stable_defaults(self):
        property_record = _property_record()

        result = serialize_property_mapping_fields(property_record)

        self.assertFalse(result['send_activities_to_owner'])
        self.assertEqual(result['tags'], [])
        self.assertEqual(result['property_images'], [])
        self.assertEqual(result['property_files'], [])

    def test_serialize_mapping_fields_returns_values_and_metadata(self):
        property_record = _property_record(
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

        self.assertTrue(result['send_activities_to_owner'])
        self.assertEqual(result['included_in_commission_date'], '2026-05-04')
        self.assertEqual(result['tags'], ['Premium'])
        self.assertEqual(result['property_images'][0]['mimetype'], 'image/jpeg')
        self.assertEqual(result['property_images'][0]['size'], 5)
        self.assertNotIn('image', result['property_images'][0])
        self.assertEqual(result['property_files'][0]['mimetype'], 'application/pdf')
        self.assertNotIn('file', result['property_files'][0])


class TestReplacePropertyAttachments(unittest.TestCase):
    def test_replace_property_files_rejects_missing_file_before_unlink(self):
        property_record = _property_record_with_relations()

        errors = serializers._replace_property_files(property_record, [
            {
                'name': 'missing-file.pdf',
                'file_name': 'missing-file.pdf',
            },
        ])

        self.assertEqual(errors, [
            {'field': 'property_files[0].file', 'message': 'File content is required'},
        ])
        self.assertFalse(property_record.document_ids.unlinked)
        self.assertEqual(property_record.env['real.estate.property.document'].created, [])

    def test_replace_property_images_rejects_invalid_item_before_unlink(self):
        property_record = _property_record_with_relations()

        errors = serializers._replace_property_images(property_record, ['not-an-object'])

        self.assertEqual(errors, [
            {'field': 'property_images', 'message': 'Items must be objects'},
        ])
        self.assertFalse(property_record.photo_ids.unlinked)
        self.assertEqual(property_record.env['real.estate.property.photo'].created, [])


def _property_record(**overrides):
    fields = {
        'id': 17,
        'name': 'Casa Moderna',
        'description': '<p>Descricao</p>',
        'price': 850000.0,
        'property_status': 'available',
        'for_sale': True,
        'for_rent': False,
        'property_type_id': SimpleNamespace(id=1, name='House'),
        'agent_id': False,
        'owner_id': False,
        'company_id': SimpleNamespace(id=1, name='Company'),
        'street_number': '100',
        'complement': False,
        'neighborhood': 'Centro',
        'city': 'Sao Jose dos Campos',
        'state_id': SimpleNamespace(id=1, name='Sao Paulo', code='SP'),
        'zip_code': '12200-000',
        'location_type_id': SimpleNamespace(id=1, name='Urban', code='urban'),
        'num_rooms': 3,
        'num_suites': 1,
        'num_bathrooms': 2,
        'num_parking': 2,
        'area': 180.0,
        'total_area': 220.0,
        'create_date': date(2026, 5, 4),
        'write_date': date(2026, 5, 5),
        'env': _FakeEnv(),
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
        'tag_ids': _FakeRecordList(),
        'photo_ids': _FakeRecordList(),
        'document_ids': _FakeRecordList(),
    }
    fields.update(overrides)
    for relation_field in ('tag_ids', 'photo_ids', 'document_ids'):
        if not isinstance(fields[relation_field], _FakeRecordList):
            fields[relation_field] = _FakeRecordList(fields[relation_field])
    return SimpleNamespace(**fields)


def _property_record_with_relations():
    env = _FakeEnv()
    return SimpleNamespace(
        id=42,
        env=env,
        photo_ids=_FakeRelation(),
        document_ids=_FakeRelation(),
    )


class _FakeRelation:
    def __init__(self):
        self.unlinked = False

    def unlink(self):
        self.unlinked = True


class _FakeModel:
    def __init__(self):
        self.created = []

    def sudo(self):
        return self

    def create(self, vals):
        self.created.append(vals)
        return SimpleNamespace(**vals)


class _FakeAttachmentModel:
    def sudo(self):
        return self

    def search(self, _domain):
        return []


class _FakeEnv(dict):
    def __init__(self):
        super().__init__({
            'ir.attachment': _FakeAttachmentModel(),
            'real.estate.property.photo': _FakeModel(),
            'real.estate.property.document': _FakeModel(),
        })


class _FakeRecordList(list):
    @property
    def ids(self):
        return [record.id for record in self]


class _FakeField:
    def __init__(self, selection):
        self.selection = selection


class _FakeSelectionModel:
    _fields = {
        'origin_media': _FakeField([('website', 'Website')]),
        'zoning_type': _FakeField([('residential', 'Residential')]),
        'property_purpose': _FakeField([('residential', 'Residential')]),
        'property_status': _FakeField([
            ('available', 'Available'),
            ('maintenance', 'Under Maintenance'),
        ]),
        'property_situation': _FakeField([
            ('Não Informado', 'Não Informado'),
            ('Desocupado', 'Desocupado'),
            ('Ocupado', 'Ocupado'),
            ('Reservado', 'Reservado'),
            ('Em construção', 'Em construção'),
            ('Lançamento', 'Lançamento'),
            ('Novo', 'Novo'),
        ]),
        'condition': _FakeField([('good', 'Good')]),
        'activity_notification': _FakeField([('important', 'Important Only')]),
        'sign_type': _FakeField([('sale', 'For Sale')]),
    }


class _FakeSelectionEnv(dict):
    def __init__(self):
        super().__init__({
            'real.estate.property': _FakeSelectionModel(),
        })


if __name__ == '__main__':
    unittest.main(verbosity=2)
