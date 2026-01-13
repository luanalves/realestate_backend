# -*- coding: utf-8 -*-


def serialize_property(property_record):
    """
    Converts a real.estate.property record to JSON dict.
    
    Args:
        property_record: real.estate.property record
        
    Returns:
        dict: JSON-serializable dictionary with property details
        
    Example:
        property = env['real.estate.property'].browse(1)
        data = serialize_property(property)
    """
    if not property_record:
        return None
    
    return {
        'id': property_record.id,
        'name': property_record.name or '',
        'description': property_record.description or '',
        'price': float(property_record.price) if property_record.price else 0.0,
        'price_formatted': f"R$ {property_record.price:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.') if property_record.price else 'R$ 0,00',
        'status': property_record.property_status or 'available',
        'property_type': {
            'id': property_record.property_type_id.id,
            'name': property_record.property_type_id.name
        } if property_record.property_type_id else None,
        'agent': {
            'id': property_record.agent_id.id,
            'name': property_record.agent_id.name,
            'email': property_record.agent_id.email or ''
        } if property_record.agent_id else None,
        'company': {
            'id': property_record.company_ids[0].id if property_record.company_ids else None,
            'name': property_record.company_ids[0].name if property_record.company_ids else None
        },
        'address': {
            'street': property_record.street or '',
            'number': property_record.street_number or '',
            'complement': property_record.complement or '',
            'neighborhood': property_record.neighborhood or '',
            'city': property_record.city or '',
            'state': {
                'id': property_record.state_id.id,
                'name': property_record.state_id.name,
                'code': property_record.state_id.code
            } if property_record.state_id else None,
            'zip_code': property_record.zip_code or '',
            'location_type': {
                'id': property_record.location_type_id.id,
                'name': property_record.location_type_id.name,
                'code': property_record.location_type_id.code
            } if property_record.location_type_id else None
        },
        'features': {
            'bedrooms': property_record.num_rooms or 0,
            'suites': property_record.num_suites or 0,
            'bathrooms': property_record.num_bathrooms or 0,
            'parking_spaces': property_record.num_parking or 0,
            'area': float(property_record.area) if property_record.area else 0.0,
            'total_area': float(property_record.total_area) if property_record.total_area else 0.0
        },
        'created_date': property_record.create_date.isoformat() if property_record.create_date else None,
        'updated_date': property_record.write_date.isoformat() if property_record.write_date else None
    }


def validate_property_access(property_record, user, operation='read'):
    """
    Validates if user has access to the property based on security groups.
    
    Args:
        property_record: real.estate.property record
        user: res.users record
        operation: 'read', 'write', 'delete'
        
    Returns:
        tuple: (bool, str) - (has_access, error_message)
        
    Example:
        has_access, error = validate_property_access(property, request.env.user, 'write')
        if not has_access:
            return error_response(403, error)
    """
    # Admin has full access
    if user.has_group('base.group_system'):
        return True, None
    
    # Manager: access to properties of their companies
    if user.has_group('quicksol_estate.group_real_estate_manager'):
        user_companies = set(user.company_ids.ids)
        property_companies = set(property_record.company_ids.ids)
        
        if property_companies & user_companies:
            return True, None
        return False, 'Property does not belong to your companies'
    
    # Agent: access only to properties they manage
    if user.has_group('quicksol_estate.group_real_estate_agent'):
        if operation == 'delete':
            return False, 'Agents cannot delete properties'
        
        if property_record.agent_id and property_record.agent_id.user_id == user:
            return True, None
        return False, 'You can only access your own properties'
    
    # User: read/write access to properties of their companies
    if user.has_group('quicksol_estate.group_real_estate_user'):
        if operation == 'delete':
            return False, 'Users cannot delete properties'
        
        user_companies = set(user.company_ids.ids)
        property_companies = set(property_record.company_ids.ids)
        
        if property_companies & user_companies:
            return True, None
        return False, 'Property does not belong to your companies'
    
    # Portal users have no access
    return False, 'Insufficient permissions'
