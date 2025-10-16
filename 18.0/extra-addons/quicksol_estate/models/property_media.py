# -*- coding: utf-8 -*-
from odoo import models, fields, api


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
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    @api.depends('image')
    def _compute_images(self):
        for photo in self:
            photo.image_medium = photo.image
            photo.image_small = photo.image

    @api.model_create_multi
    def create(self, vals_list):
        photos = super().create(vals_list)
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
    ], string='Document Type', required=True)
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    description = fields.Text(string='Description')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    is_confidential = fields.Boolean(string='Confidential', default=False)
    property_id = fields.Many2one('real.estate.property', string='Property', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
