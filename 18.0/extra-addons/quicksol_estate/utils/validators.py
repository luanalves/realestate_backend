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


def normalize_document(document):
    """
    Strip all non-digit characters from a document string (CPF or CNPJ).
    
    Args:
        document (str): CPF/CNPJ with or without formatting
        
    Returns:
        str: Digits-only string
        
    Example:
        >>> normalize_document('123.456.789-01')
        '12345678901'
        >>> normalize_document('12.345.678/0001-95')
        '12345678000195'
        >>> normalize_document('')
        ''
    """
    if not document:
        return ''
    
    return re.sub(r'[^0-9]', '', document)


def is_cpf(document):
    """
    Validate Brazilian CPF with checksum verification.
    
    Args:
        document (str): CPF string (digits only, 11 characters)
        
    Returns:
        bool: True if valid CPF, False otherwise
        
    Example:
        >>> is_cpf('12345678901')  # Valid structure (assuming correct checksum)
        True
        >>> is_cpf('11111111111')  # All same digits
        False
        >>> is_cpf('123')  # Wrong length
        False
    
    Note:
        Must be called with normalized document (digits only).
        Use normalize_document() first if needed.
    """
    if not document:
        return False
    
    # Must have exactly 11 digits
    if len(document) != 11:
        return False
    
    # Cannot be all same digits
    if document == document[0] * 11:
        return False
    
    # Calculate first check digit
    sum_first = sum(int(document[i]) * (10 - i) for i in range(9))
    first_digit = (sum_first * 10) % 11
    if first_digit == 10:
        first_digit = 0
    
    if int(document[9]) != first_digit:
        return False
    
    # Calculate second check digit
    sum_second = sum(int(document[i]) * (11 - i) for i in range(10))
    second_digit = (sum_second * 10) % 11
    if second_digit == 10:
        second_digit = 0
    
    if int(document[10]) != second_digit:
        return False
    
    return True


def is_cnpj(document):
    """
    Validate Brazilian CNPJ with checksum verification.
    
    Delegates to existing validate_cnpj() after format check.
    
    Args:
        document (str): CNPJ string (digits only, 14 characters)
        
    Returns:
        bool: True if valid CNPJ, False otherwise
        
    Example:
        >>> is_cnpj('11222333000181')  # Valid structure
        True
        >>> is_cnpj('00000000000000')  # All zeros
        False
        >>> is_cnpj('123')  # Wrong length
        False
    
    Note:
        Must be called with normalized document (digits only).
        Use normalize_document() first if needed.
    """
    if not document:
        return False
    
    # Must have exactly 14 digits
    if len(document) != 14:
        return False
    
    # Delegate to existing validate_cnpj which handles checksum
    return validate_cnpj(document)


def validate_document(document):
    """
    Validate a document as CPF (11 digits) or CNPJ (14 digits).
    
    Dispatches to is_cpf() or is_cnpj() based on length.
    
    Args:
        document (str): Document string (digits only, call normalize_document first)
        
    Returns:
        bool: True if valid CPF or CNPJ, False otherwise
        
    Example:
        >>> validate_document('12345678901')  # CPF
        True
        >>> validate_document('12345678000195')  # CNPJ
        True
        >>> validate_document('123')  # Invalid length
        False
    
    Note:
        This function expects a normalized document (digits only).
        If you have formatted input, call normalize_document() first:
        
        >>> doc = normalize_document('123.456.789-01')
        >>> validate_document(doc)
        True
    """
    if not document:
        return False
    
    if len(document) == 11:
        return is_cpf(document)
    elif len(document) == 14:
        return is_cnpj(document)
    
    return False
