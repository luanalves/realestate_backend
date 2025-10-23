# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.image import image_process
from .file_validator import FileValidator


class PropertyPhoto(models.Model):
    _name = 'real.estate.property.photo'
    _description = 'Property Photo'
    _order = 'sequence, id'

    name = fields.Char(string='Photo Name', required=True)
    image = fields.Binary(string='Photo', required=True, attachment=True)
    image_medium = fields.Binary(string='Medium Photo', compute='_compute_images', store=True)
    image_small = fields.Binary(string='Small Photo', compute='_compute_images', store=True)
    description = fields.Text(string='Description')
    is_main = fields.Boolean(string='Main Photo', default=False)
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    @api.constrains('image', 'name')
    def _check_image_constraints(self):
        """Valida tamanho e extensão da imagem usando FileValidator"""
        for photo in self:
            if photo.image and photo.name:
                FileValidator.validate_image(photo.image, photo.name)

    @api.depends('image')
    def _compute_images(self):
        for photo in self:
            if photo.image:
                # Resize to medium (max 512x512) and small (max 256x256) dimensions
                photo.image_medium = image_process(photo.image, size=(512, 512))
                photo.image_small = image_process(photo.image, size=(256, 256))
            else:
                photo.image_medium = False
                photo.image_small = False
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ensures property_id is filled from context and enforces is_main uniqueness"""
        # Process each vals dict to set property_id from context if missing
        for vals in vals_list:
            if not vals.get('property_id') and self._context.get('default_property_id'):
                vals['property_id'] = self._context.get('default_property_id')
            
            # Validation: property_id is mandatory
            if not vals.get('property_id'):
                raise ValidationError('A foto deve estar associada a uma propriedade.')
        
        # Create the photos
        photos = super().create(vals_list)
        
        # Enforce is_main uniqueness for each photo
        for photo in photos:
            if photo.is_main and photo.property_id:
                # Remove main flag from other photos
                self.search([
                    ('property_id', '=', photo.property_id.id),
                    ('id', '!=', photo.id),
                    ('is_main', '=', True)
                ]).write({'is_main': False})
        
        return photos

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_main'):
            for photo in self:
                if photo.property_id:
                    # Remove main flag from other photos
                    self.search([
                        ('property_id', '=', photo.property_id.id),
                        ('id', '!=', photo.id),
                        ('is_main', '=', True)
                    ]).write({'is_main': False})
        return res


class PropertyDocument(models.Model):
    _name = 'real.estate.property.document'
    _description = 'Property Document'
    _order = 'sequence, id'

    name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection([
        ('matricula', 'Matrícula'),
        ('iptu', 'IPTU'),
        ('escritura', 'Escritura'),
        ('contrato', 'Contrato'),
        ('procuracao', 'Procuração'),
        ('declaracao', 'Declaração'),
        ('certidao', 'Certidão'),
        ('planta', 'Planta/Blueprint'),
        ('fotos', 'Fotos'),
        ('laudo', 'Laudo Técnico'),
        ('habite_se', 'Habite-se'),
        ('alvara', 'Alvará'),
        ('other', 'Other'),
    ], string='Document Type')
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    description = fields.Text(string='Description')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    is_confidential = fields.Boolean(string='Confidential', default=False)
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    @api.constrains('file', 'file_name')
    def _check_file_constraints(self):
        """Valida tamanho e extensão do arquivo usando FileValidator"""
        for document in self:
            if document.file and document.file_name:
                FileValidator.validate_document(document.file, document.file_name)

    @api.model
    def create(self, vals):
        """Garante que property_id seja preenchido do contexto"""
        if not vals.get('property_id') and self._context.get('default_property_id'):
            vals['property_id'] = self._context.get('default_property_id')
        
        # Validação: property_id é obrigatório
        if not vals.get('property_id'):
            raise ValidationError('O documento deve estar associado a uma propriedade.')
        
        return super(PropertyDocument, self).create(vals)
