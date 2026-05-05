# -*- coding: utf-8 -*-

PROPERTY_MODEL = 'real.estate.property'

PROPERTY_SELECTION_FIELDS = {
    'source_medium': 'origin_media',
    'zoning': 'zoning_type',
    'property_purpose': 'property_purpose',
    'property_status': 'property_status',
    'condition': 'condition',
    'activity_notification': 'activity_notification',
    'sign_type': 'sign_type',
}

PROPERTY_COLLECTION_OPTIONS = [
    {
        'field': 'tags',
        'type': 'many2many',
        'accepted_values': ['string', 'integer'],
        'options_endpoint': '/api/v1/tags',
    },
    {
        'field': 'property_images',
        'type': 'array',
        'accepted_values': ['object'],
        'options_endpoint': None,
    },
    {
        'field': 'property_files',
        'type': 'array',
        'accepted_values': ['object'],
        'options_endpoint': None,
    },
]

PROPERTY_RELATED_OPTIONS = {
    'property_type_id': '/api/v1/property-types',
    'location_type_id': '/api/v1/location-types',
    'state_id': '/api/v1/states',
    'tags': '/api/v1/tags',
    'amenities': '/api/v1/amenities',
}


def get_selection_options(env, model_name, field_name):
    return [
        {
            'value': value,
            'label': label,
        }
        for value, label in env[model_name]._fields[field_name].selection
    ]


def get_selection_values(env, model_name, field_name):
    return [
        option['value']
        for option in get_selection_options(env, model_name, field_name)
    ]


def build_property_options(env):
    options = {
        api_field: get_selection_options(env, PROPERTY_MODEL, model_field)
        for api_field, model_field in PROPERTY_SELECTION_FIELDS.items()
    }
    options['multi_value_fields'] = PROPERTY_COLLECTION_OPTIONS
    options['related_options'] = PROPERTY_RELATED_OPTIONS
    return options


def get_property_status_values(env):
    return get_selection_values(
        env,
        PROPERTY_MODEL,
        PROPERTY_SELECTION_FIELDS['property_status'],
    )
