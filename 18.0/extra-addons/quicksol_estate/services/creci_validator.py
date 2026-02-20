# -*- coding: utf-8 -*-

import re
from odoo.exceptions import ValidationError
from odoo import _

class CreciValidator:
    
    # Brazilian states
    VALID_STATES = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
        'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    # Regex patterns for flexible input
    PATTERNS = [
        # CRECI/SP 12345 or CRECI/SP-12345
        r'^CRECI[/\-\s]([A-Z]{2})[/\-\s](\d{4,8})$',
        # 12345-SP or 12345/SP
        r'^(\d{4,8})[/\-]([A-Z]{2})$',
        # CRECI SP 12345
        r'^CRECI\s+([A-Z]{2})\s+(\d{4,8})$',
    ]
    
    @classmethod
    def normalize(cls, creci_input):
        if not creci_input:
            return False
            
        # Remove extra spaces and convert to uppercase
        creci_clean = ' '.join(creci_input.upper().split())
        
        state = None
        number = None
        
        # Try each pattern
        for pattern in cls.PATTERNS:
            match = re.match(pattern, creci_clean)
            if match:
                groups = match.groups()
                # Pattern determines group order (state, number) or (number, state)
                if groups[0].isdigit():
                    number, state = groups
                else:
                    state, number = groups
                break
        
        if not state or not number:
            raise ValidationError(
                _('Formato de CRECI inválido: %s. Formatos aceitos: CRECI/UF 12345, CRECI-UF-12345, 12345-UF') 
                % creci_input
            )
        
        # Validate state
        if state not in cls.VALID_STATES:
            raise ValidationError(
                _('Estado inválido no CRECI: %s. Estados válidos: %s') 
                % (state, ', '.join(cls.VALID_STATES))
            )
        
        # Validate number (4-8 digits)
        if not number.isdigit() or len(number) < 4 or len(number) > 8:
            raise ValidationError(
                _('Número CRECI inválido: %s. Deve conter entre 4 e 8 dígitos') 
                % number
            )
        
        # Return normalized format
        return f"CRECI/{state} {number}"
    
    @classmethod
    def validate(cls, creci_normalized):

        if not creci_normalized:
            return True  # Empty CRECI is allowed (optional field)
        
        # Should be in format CRECI/UF NNNNN
        pattern = r'^CRECI/([A-Z]{2})\s+(\d{4,8})$'
        match = re.match(pattern, creci_normalized)
        
        if not match:
            raise ValidationError(
                _('CRECI normalizado inválido: %s') % creci_normalized
            )
        
        state, number = match.groups()
        
        if state not in cls.VALID_STATES:
            raise ValidationError(
                _('Estado inválido no CRECI: %s') % state
            )
        
        return True
    
    @classmethod
    def extract_state(cls, creci_normalized):

        if not creci_normalized:
            return False
            
        match = re.match(r'^CRECI/([A-Z]{2})\s+(\d{4,8})$', creci_normalized)
        return match.group(1) if match else False
    
    @classmethod
    def extract_number(cls, creci_normalized):

        if not creci_normalized:
            return False
            
        match = re.match(r'^CRECI/([A-Z]{2})\s+(\d{4,8})$', creci_normalized)
        return match.group(2) if match else False
