from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    # Relacionamento com imobiliárias
    estate_company_ids = fields.Many2many(
        'thedevkitchen.estate.company', 
        'thedevkitchen_user_company_rel', 
        'user_id', 
        'company_id',
        string='Real Estate Companies',
        help='Imobiliárias que este usuário tem acesso'
    )
    
    # Imobiliária principal do usuário
    main_estate_company_id = fields.Many2one(
        'thedevkitchen.estate.company',
        string='Main Real Estate Company',
        help='Imobiliária principal do usuário para filtros padrão'
    )
    
    @api.model
    def get_user_companies(self):
        """Retorna as imobiliárias do usuário atual"""
        if self.env.user.has_group('base.group_system'):
            # Admin vê todas as imobiliárias
            return self.env['thedevkitchen.estate.company'].search([])
        else:
            # Usuário comum vê apenas suas imobiliárias
            return self.env.user.estate_company_ids

    def has_estate_company_access(self, company_id):
        """Verifica se o usuário tem acesso à imobiliária especificada"""
        if self.env.user.has_group('base.group_system'):
            return True
        return company_id in self.env.user.estate_company_ids.ids
    
    @api.onchange('main_estate_company_id')
    def _onchange_main_estate_company(self):
        """Garante que a imobiliária principal esteja nas imobiliárias do usuário"""
        if self.main_estate_company_id and self.main_estate_company_id not in self.estate_company_ids:
            self.estate_company_ids = [(4, self.main_estate_company_id.id)]
    
    def write(self, vals):
        """Override write para sincronizar agentes quando usuário é modificado"""
        result = super().write(vals)
        
        # Se as imobiliárias do usuário mudaram, atualizar agentes relacionados
        if 'estate_company_ids' in vals:
            for user in self:
                agents = self.env['real.estate.agent'].search([('user_id', '=', user.id)])
                if agents and user.estate_company_ids:
                    agents.write({'company_ids': [(6, 0, user.estate_company_ids.ids)]})
        
        return result