from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    # CPF - Documento de pessoa física (obrigatório, único)
    cpf = fields.Char(
        string='CPF',
        size=14,  # Format: 123.456.789-01
        index=True,
        help='Brazilian individual taxpayer registry (CPF). Required for all users.'
    )
    
    # SQL constraint for CPF uniqueness
    _sql_constraints = [
        ('cpf_unique',
         'UNIQUE(cpf)',
         'CPF já cadastrado. Cada usuário deve ter um CPF único.')
    ]

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
    
    # Feature 007: Computed field for Owner's companies (T004)
    owner_company_ids = fields.Many2many(
        'thedevkitchen.estate.company',
        compute='_compute_owner_companies',
        string='Owned Companies',
        help='Companies where this user is an Owner (has group_real_estate_owner)'
    )
    
    @api.depends('groups_id', 'estate_company_ids')
    def _compute_owner_companies(self):
        """
        Compute companies owned by this user.
        Only users with group_real_estate_owner see their estate_company_ids as owner_company_ids.
        """
        owner_group = self.env.ref('quicksol_estate.group_real_estate_owner', raise_if_not_found=False)
        for user in self:
            if owner_group and owner_group in user.groups_id:
                user.owner_company_ids = user.estate_company_ids
            else:
                user.owner_company_ids = False
    
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
    
    @api.constrains('cpf')
    def _check_cpf_format(self):
        """Validate CPF format and checksum using validate_docbr"""
        try:
            from validate_docbr import CPF
            cpf_validator = CPF()
        except ImportError:
            # validate_docbr not installed - skip validation
            return
        
        for user in self:
            if user.cpf:
                # Remove formatting (dots and dashes)
                cpf_clean = ''.join(filter(str.isdigit, user.cpf))
                
                if not cpf_validator.validate(cpf_clean):
                    raise ValidationError(f'CPF inválido: {user.cpf}. Digite um CPF válido com 11 dígitos.')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Emit user.before_create event for validation (ADR-020)."""
        for vals in vals_list:
            self.env['quicksol.event.bus'].emit('user.before_create', {
                'vals': vals,
                'user_id': self.env.uid
            })
        
        return super().create(vals_list)
    
    def write(self, vals):
        """Emit user.before_write event for validation + sync agents (ADR-020)."""
        # Track security group changes for LGPD audit (T135)
        groups_changed = 'groups_id' in vals
        old_groups = {}
        
        if groups_changed:
            # Store old groups before write
            for user in self:
                old_groups[user.id] = set(user.groups_id.mapped('name'))
        
        self.env['quicksol.event.bus'].emit('user.before_write', {
            'vals': vals,
            'user_id': self.env.uid,
            'target_user_ids': self.ids
        })
        
        result = super().write(vals)
        
        # Se as imobiliárias do usuário mudaram, atualizar agentes relacionados
        if 'estate_company_ids' in vals:
            for user in self:
                agents = self.env['real.estate.agent'].search([('user_id', '=', user.id)])
                if agents and user.estate_company_ids:
                    agents.write({'company_ids': [(6, 0, user.estate_company_ids.ids)]})
        
        # Emit groups_changed event for LGPD audit logging (T135)
        if groups_changed:
            # Only emit events if EventBus model is available (skip during install)
            try:
                event_bus = self.env['quicksol.event.bus']
                
                for user in self:
                    new_groups = set(user.groups_id.mapped('name'))
                    user_old_groups = old_groups.get(user.id, set())
                    
                    added_groups = list(new_groups - user_old_groups)
                    removed_groups = list(user_old_groups - new_groups)
                    
                    if added_groups or removed_groups:
                        event_bus.emit('user.groups_changed', {
                            'user': user,
                            'added_groups': added_groups,
                            'removed_groups': removed_groups,
                            'changed_by': self.env.user,
                        })
            except (ImportError, AttributeError, KeyError):
                # EventBus not available during module installation
                pass
        
        # Emit async audit event (non-blocking)
        self.env['quicksol.event.bus'].emit('user.updated', {
            'user_ids': self.ids,
            'vals': vals,
            'updated_by': self.env.uid
        })
        
        return result