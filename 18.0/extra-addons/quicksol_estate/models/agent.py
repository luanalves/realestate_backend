from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import email_normalize

class Agent(models.Model):
    _name = 'real.estate.agent'
    _description = 'Agent'

    name = fields.Char(string='Agent Name', required=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email')
    user_id = fields.Many2one('res.users', string='Related User', 
                              help='System user associated with this agent')
    company_ids = fields.Many2many('thedevkitchen.estate.company', 
                                   'thedevkitchen_company_agent_rel', 
                                   'agent_id', 'company_id', 
                                   string='Real Estate Companies')
    properties = fields.One2many('real.estate.property', 'agent_id', string='Properties')
    agency_name = fields.Char('Agency Name')
    years_experience = fields.Integer('Years of Experience')
    profile_picture = fields.Binary('Profile Picture')

    @api.constrains('email')
    def _validate_email(self):
        """Validate email format using Odoo's email_normalize function"""
        for record in self:
            if record.email:
                try:
                    email_normalize(record.email)
                except ValueError:
                    raise ValidationError("Please enter a valid email address.")

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """Sync agent data with user data when user is selected"""
        if self.user_id:
            if not self.name:
                self.name = self.user_id.name
            if not self.email:
                self.email = self.user_id.email
            # Sync companies from user to agent (only if agent has no companies yet)
            if self.user_id.estate_company_ids and not self.company_ids:
                self.company_ids = self.user_id.estate_company_ids

    @api.model
    def create(self, vals):
        """Override create to sync user data"""
        agent = super().create(vals)
        if agent.user_id and not vals.get('company_ids'):
            # Auto-assign user's companies to agent
            agent.company_ids = agent.user_id.estate_company_ids
        return agent

    def write(self, vals):
        """Override write to maintain synchronization"""
        result = super().write(vals)
        # Only sync company_ids when user_id is changed and company_ids was NOT explicitly provided
        if 'user_id' in vals and 'company_ids' not in vals:
            for agent in self:
                if agent.user_id:
                    # Guard against missing estate_company_ids on the user
                    user_estate_companies = getattr(agent.user_id, 'estate_company_ids', None)
                    if user_estate_companies:
                        agent.company_ids = user_estate_companies
        return result