# -*- coding: utf-8 -*-
import base64
import os
from odoo.exceptions import ValidationError


class FileValidator:
    """Helper class for file validation (size and extension)"""
    
    # Configurações padrão
    DEFAULT_MAX_SIZE = 5 * 1024 * 1024  # 5MB em bytes
    
    # Extensões por categoria
    IMAGE_EXTENSIONS = ['.png', '.jpeg', '.jpg']
    DOCUMENT_EXTENSIONS = [
        '.png', '.jpeg', '.jpg', '.txt', '.xls', '.xlsx', 
        '.doc', '.docx', '.pdf', '.ppt', '.pptx', '.zip', 
        '.msg', '.kmz'
    ]
    
    @classmethod
    def validate_file(cls, file_binary, file_name, allowed_extensions=None, max_size=None):

        if not file_binary or not file_name:
            return None, None
            
        # Usar valores padrão se não fornecidos
        if allowed_extensions is None:
            allowed_extensions = cls.DOCUMENT_EXTENSIONS
        if max_size is None:
            max_size = cls.DEFAULT_MAX_SIZE
            
        # Validar extensão
        file_ext = os.path.splitext(file_name)[1].lower()
        if file_ext not in allowed_extensions:
            allowed = ', '.join(allowed_extensions)
            raise ValidationError(
                f'Extensão de arquivo não permitida: {file_ext}\n'
                f'Extensões permitidas: {allowed}'
            )
        
        # Validar tamanho
        try:
            file_size = len(base64.b64decode(file_binary))
        except Exception as e:
            raise ValidationError(f'Erro ao decodificar arquivo: {str(e)}')
            
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            current_size_mb = file_size / (1024 * 1024)
            raise ValidationError(
                f'Arquivo muito grande: {current_size_mb:.2f}MB\n'
                f'Tamanho máximo permitido: {max_size_mb:.0f}MB'
            )
        
        return file_size, file_ext
    
    @classmethod
    def validate_image(cls, image_binary, image_name, max_size=None):

        return cls.validate_file(
            image_binary, 
            image_name, 
            allowed_extensions=cls.IMAGE_EXTENSIONS,
            max_size=max_size
        )
    
    @classmethod
    def validate_document(cls, document_binary, document_name, max_size=None):

        return cls.validate_file(
            document_binary, 
            document_name, 
            allowed_extensions=cls.DOCUMENT_EXTENSIONS,
            max_size=max_size
        )
    
    @classmethod
    def get_max_size_mb(cls):
        """Retorna o tamanho máximo em MB"""
        return cls.DEFAULT_MAX_SIZE / (1024 * 1024)
    
    @classmethod
    def get_allowed_extensions_string(cls, extension_type='document'):

        if extension_type == 'image':
            extensions = cls.IMAGE_EXTENSIONS
        else:
            extensions = cls.DOCUMENT_EXTENSIONS
        return ', '.join(extensions)
