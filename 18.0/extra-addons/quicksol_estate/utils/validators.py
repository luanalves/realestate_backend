# -*- coding: utf-8 -*-
"""
Reusable validation functions for Company & Owner Management

Following ADR-009 (Brazilian market requirements) and ADR-004 (naming conventions).
All validators return True if valid, False otherwise.
"""
import re
from email_validator import validate_email, EmailNotValidError


def validate_cnpj(cnpj):
    """
    Validate Brazilian CNPJ format and check digits.
    
    Args:
        cnpj (str): CNPJ string (formatted or unformatted)
        
    Returns:
        bool: True if valid CNPJ, False otherwise
        
    Example:
        >>> validate_cnpj('11.222.333/0001-81')
        True
        >>> validate_cnpj('11222333000181')
        True
        >>> validate_cnpj('00.000.000/0000-00')
        False
    """
    if not cnpj:
        return True  # Empty CNPJ is allowed (optional field)
    
    # Remove any formatting
    cnpj_clean = re.sub(r'[^0-9]', '', cnpj)
    
    # Check if it has 14 digits
    if len(cnpj_clean) != 14:
        return False
    
    # Check for sequence of same digit (invalid CNPJ)
    if cnpj_clean == cnpj_clean[0] * 14:
        return False
    
    # Calculate check digits
    def calculate_digit(cnpj, weights):
        total = sum(int(digit) * weight for digit, weight in zip(cnpj, weights))
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)
    
    weights_first = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights_second = [6] + weights_first
    
    first_digit = calculate_digit(cnpj_clean[:12], weights_first)
    second_digit = calculate_digit(cnpj_clean[:12] + first_digit, weights_second)
    
    return cnpj_clean[-2:] == first_digit + second_digit


def format_cnpj(cnpj):
    """
    Format CNPJ to standard Brazilian format: XX.XXX.XXX/XXXX-XX
    
    Args:
        cnpj (str): Unformatted CNPJ (14 digits)
        
    Returns:
        str: Formatted CNPJ or original if invalid length
        
    Example:
        >>> format_cnpj('11222333000181')
        '11.222.333/0001-81'
    """
    if not cnpj:
        return cnpj
    
    cnpj_clean = re.sub(r'[^0-9]', '', cnpj)
    
    if len(cnpj_clean) != 14:
        return cnpj  # Return original if not 14 digits
    
    return f"{cnpj_clean[:2]}.{cnpj_clean[2:5]}.{cnpj_clean[5:8]}/{cnpj_clean[8:12]}-{cnpj_clean[12:14]}"


def validate_email_format(email):
    """
    Validate email format using email_validator library.
    
    Args:
        email (str): Email address
        
    Returns:
        bool: True if valid email format, False otherwise
        
    Example:
        >>> validate_email_format('user@example.com')
        True
        >>> validate_email_format('invalid.email')
        False
    """
    if not email:
        return True  # Empty email is allowed (optional field)
    
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_creci(creci, state_code=None):
    """
    Validate Brazilian CRECI format per state.
    
    CRECI format varies by state:
    - SP: CRECI/SP 123456 or CRECI-SP 123456 (6 digits)
    - RJ: CRECI/RJ 12345 or CRECI-RJ 12345 (5 digits)
    - MG: CRECI/MG 12345 or CRECI-MG 12345 (5 digits)
    - Others: Generally 5-6 digits
    
    Args:
        creci (str): CRECI registration number
        state_code (str, optional): Brazilian state code (SP, RJ, MG, etc.)
        
    Returns:
        bool: True if valid CRECI format, False otherwise
        
    Example:
        >>> validate_creci('CRECI/SP 123456', 'SP')
        True
        >>> validate_creci('CRECI-RJ 12345', 'RJ')
        True
        >>> validate_creci('12345')  # Without state - accepts any 4-7 digit number
        True
    """
    if not creci:
        return True  # Empty CRECI is allowed (optional field)
    
    # Remove common formatting
    creci_clean = re.sub(r'[^0-9A-Za-z]', '', creci).upper()
    
    # Extract state code from CRECI string if present (e.g., "CRECISP123456")
    match = re.match(r'CRECI([A-Z]{2})(\d+)', creci_clean)
    if match:
        extracted_state = match.group(1)
        number = match.group(2)
        
        # If state_code provided, verify it matches
        if state_code and extracted_state != state_code.upper():
            return False
        
        # Validate number length based on state
        if extracted_state == 'SP':
            return len(number) == 6
        elif extracted_state in ['RJ', 'MG']:
            return len(number) == 5
        else:
            return 4 <= len(number) <= 7  # General case
    
    # If no CRECI prefix, validate as plain number
    number_only = re.sub(r'[^0-9]', '', creci)
    if number_only:
        return 4 <= len(number_only) <= 7
    
    return False


def validate_phone(phone):
    """
    Validate Brazilian phone number format.
    
    Accepts formats:
    - (11) 98765-4321 (mobile)
    - (11) 3456-7890 (landline)
    - 11987654321 (unformatted mobile)
    - 1134567890 (unformatted landline)
    
    Args:
        phone (str): Phone number
        
    Returns:
        bool: True if valid phone format, False otherwise
        
    Example:
        >>> validate_phone('(11) 98765-4321')
        True
        >>> validate_phone('11987654321')
        True
        >>> validate_phone('123')
        False
    """
    if not phone:
        return True  # Empty phone is allowed (optional field)
    
    # Remove formatting
    phone_clean = re.sub(r'[^0-9]', '', phone)
    
    # Brazilian phone: 10 digits (landline) or 11 digits (mobile)
    # Format: DDD (2 digits) + Number (8 or 9 digits)
    if len(phone_clean) not in [10, 11]:
        return False
    
    # DDD must be between 11-99 (valid Brazilian area codes)
    ddd = int(phone_clean[:2])
    if not (11 <= ddd <= 99):
        return False
    
    return True


def format_phone(phone):
    """
    Format phone to Brazilian standard: (XX) XXXXX-XXXX or (XX) XXXX-XXXX
    
    Args:
        phone (str): Unformatted phone number
        
    Returns:
        str: Formatted phone or original if invalid
        
    Example:
        >>> format_phone('11987654321')
        '(11) 98765-4321'
        >>> format_phone('1134567890')
        '(11) 3456-7890'
    """
    if not phone:
        return phone
    
    phone_clean = re.sub(r'[^0-9]', '', phone)
    
    if len(phone_clean) == 11:
        # Mobile: (XX) 9XXXX-XXXX
        return f"({phone_clean[:2]}) {phone_clean[2:7]}-{phone_clean[7:]}"
    elif len(phone_clean) == 10:
        # Landline: (XX) XXXX-XXXX
        return f"({phone_clean[:2]}) {phone_clean[2:6]}-{phone_clean[6:]}"
    
    return phone  # Return original if invalid length
