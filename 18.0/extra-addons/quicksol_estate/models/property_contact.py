# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class PropertyPhone(models.Model):
    _name = 'real.estate.property.phone'
    _description = 'Property Contact Phone'
    _rec_name = 'phone'

    phone = fields.Char(string='Phone Number', required=True, size=15)
    phone_type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mobile', 'Mobile'),
        ('whatsapp', 'WhatsApp'),
        ('fax', 'Fax'),
        ('other', 'Other'),
    ], string='Phone Type', required=True, default='mobile')
    notes = fields.Char(string='Notes')
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.constrains('phone')
    def _check_phone(self):
        """
        Valida telefones brasileiros no backend:
        - Telefone fixo: (XX) XXXX-XXXX (10 dígitos)
        - Celular: (XX) 9XXXX-XXXX (11 dígitos)
        """
        for rec in self:
            if not rec.phone:
                continue
            
            # Remove caracteres não numéricos
            phone_digits = re.sub(r'\D', '', rec.phone)
            
            # Valida quantidade de dígitos (10 ou 11)
            if len(phone_digits) not in [10, 11]:
                raise ValidationError(
                    f'Telefone inválido: {rec.phone}\n\n'
                    'O telefone deve ter:\n'
                    '• Fixo: 10 dígitos - (XX) XXXX-XXXX\n'
                    '• Celular: 11 dígitos - (XX) 9XXXX-XXXX\n\n'
                    f'Você digitou apenas {len(phone_digits)} dígitos.'
                )
            
            # Valida DDD (código de área entre 11 e 99)
            try:
                ddd = int(phone_digits[:2])
                if ddd < 11 or ddd > 99:
                    raise ValidationError(
                        f'DDD inválido: {phone_digits[:2]}\n\n'
                        'O DDD deve estar entre 11 e 99.\n'
                        'Exemplos válidos: 11 (SP), 21 (RJ), 47 (SC), 85 (CE)'
                    )
            except ValueError:
                raise ValidationError(
                    'DDD inválido. Os dois primeiros dígitos devem formar um número entre 11 e 99.'
                )
            
            # Se for celular (11 dígitos), valida se o terceiro dígito é 9
            if len(phone_digits) == 11 and phone_digits[2] != '9':
                raise ValidationError(
                    f'Número de celular inválido: {rec.phone}\n\n'
                    'Celulares brasileiros devem começar com 9 após o DDD.\n'
                    f'Formato correto: ({phone_digits[:2]}) 9XXXX-XXXX'
                )
            
            # Se for fixo (10 dígitos), valida se o terceiro dígito não é 9
            if len(phone_digits) == 10 and phone_digits[2] == '9':
                raise ValidationError(
                    f'Número de telefone fixo inválido: {rec.phone}\n\n'
                    'Telefones fixos não devem começar com 9 após o DDD.\n'
                    f'Se for celular, adicione mais um dígito: ({phone_digits[:2]}) {phone_digits[2:7]}-{phone_digits[7:]}'
                )

    @api.onchange('phone')
    def _onchange_phone(self):
        """
        Normaliza o formato do telefone.
        A máscara é aplicada pelo widget JavaScript no frontend.
        """
        if self.phone:
            # Remove tudo que não é número
            phone_digits = re.sub(r'\D', '', self.phone)
            
            # Limita a 11 dígitos
            phone_digits = phone_digits[:11]
            
            # Aplica formatação padrão brasileira
            if len(phone_digits) == 11:
                # Celular: (XX) 9XXXX-XXXX
                self.phone = f'({phone_digits[:2]}) {phone_digits[2:7]}-{phone_digits[7:]}'
            elif len(phone_digits) == 10:
                # Fixo: (XX) XXXX-XXXX
                self.phone = f'({phone_digits[:2]}) {phone_digits[2:6]}-{phone_digits[6:]}'
            elif len(phone_digits) >= 2:
                # Em progresso - mantém o que foi digitado
                if len(phone_digits) > 6:
                    self.phone = f'({phone_digits[:2]}) {phone_digits[2:6]}-{phone_digits[6:]}'
                elif len(phone_digits) > 2:
                    self.phone = f'({phone_digits[:2]}) {phone_digits[2:]}'
                else:
                    self.phone = f'({phone_digits}'


class PropertyEmail(models.Model):
    _name = 'real.estate.property.email'
    _description = 'Property Contact Email'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True, size=100)
    email_type = fields.Selection([
        ('personal', 'Personal'),
        ('work', 'Work'),
        ('other', 'Other'),
    ], string='Email Type', required=True, default='personal')
    notes = fields.Char(string='Notes')
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    @api.constrains('email')
    def _check_email(self):
        """
        Valida formato de e-mail:
        - Deve conter @
        - Deve ter texto antes do @
        - Deve ter domínio após o @
        - Domínio deve ter pelo menos um ponto
        - Não pode ter espaços
        """
        # Regex simples mas eficaz para validação de email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        for rec in self:
            if not rec.email:
                continue
            
            # Remove espaços em branco
            email_clean = rec.email.strip()
            
            # Valida se tem @
            if '@' not in email_clean:
                raise ValidationError(
                    f'E-mail inválido: {rec.email}\n\n'
                    'O e-mail deve conter o símbolo @\n'
                    'Exemplo: usuario@exemplo.com'
                )
            
            # Valida formato completo
            if not re.match(email_regex, email_clean):
                parts = email_clean.split('@')
                
                if len(parts) != 2:
                    raise ValidationError(
                        f'E-mail inválido: {rec.email}\n\n'
                        'O e-mail deve ter apenas um @\n'
                        'Exemplo: usuario@exemplo.com'
                    )
                
                usuario, dominio = parts
                
                if not usuario:
                    raise ValidationError(
                        f'E-mail inválido: {rec.email}\n\n'
                        'O e-mail deve ter um nome de usuário antes do @\n'
                        'Exemplo: usuario@exemplo.com'
                    )
                
                if not dominio or '.' not in dominio:
                    raise ValidationError(
                        f'E-mail inválido: {rec.email}\n\n'
                        'O domínio deve conter pelo menos um ponto (.)\n'
                        'Exemplos válidos:\n'
                        '• usuario@exemplo.com\n'
                        '• contato@empresa.com.br\n'
                        '• nome.sobrenome@dominio.org'
                    )
                
                if ' ' in email_clean:
                    raise ValidationError(
                        f'E-mail inválido: {rec.email}\n\n'
                        'O e-mail não pode conter espaços'
                    )
                
                # Valida caracteres especiais inválidos
                if re.search(r'[<>()[\]\\,;:\s]', email_clean):
                    raise ValidationError(
                        f'E-mail inválido: {rec.email}\n\n'
                        'O e-mail contém caracteres inválidos.\n'
                        'Use apenas letras, números e os caracteres: . _ % + -'
                    )

    @api.onchange('email')
    def _onchange_email(self):
        """Normaliza o e-mail (remove espaços e converte para minúsculas)"""
        if self.email:
            # Remove espaços em branco
            self.email = self.email.strip()
            # Converte para minúsculas (padrão de e-mail)
            self.email = self.email.lower()
