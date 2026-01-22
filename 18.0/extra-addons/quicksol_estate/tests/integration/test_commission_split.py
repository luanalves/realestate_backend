"""
Test suite for Commission Split calculation.

Tests calculate_split_commission() method in commission_rule.py.
Coverage: 30/70 default split, configurable percentage, edge cases.
"""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestCommissionSplit(TransactionCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.Company = cls.env['thedevkitchen.estate.company']
        cls.Property = cls.env['real.estate.property']
        cls.Agent = cls.env['real.estate.agent']
        cls.CommissionRule = cls.env['real.estate.commission.rule']
        cls.IrConfigParameter = cls.env['ir.config_parameter'].sudo()
        
        cls.company_a = cls.Company.create({
            'name': 'Company A',
            'cnpj': '11.222.333/0001-81',
            'creci': 'CRECI-SP 12345',
        })
        
        # Create prospector agent
        cls.prospector_agent = cls.Agent.create({
            'name': 'Prospector Agent',
            'creci': 'CRECI-SP 99999',
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '222.333.444-15',
        })
        
        # Create selling agent
        cls.selling_agent = cls.Agent.create({
            'name': 'Selling Agent',
            'creci': 'CRECI-SP 88888',
            'company_ids': [(6, 0, [cls.company_a.id])],
            'cpf': '111.222.333-04',
        })
        
        # Create commission rule for selling agent (6% percentage)
        cls.commission_rule = cls.CommissionRule.create({
            'agent_id': cls.selling_agent.id,
            'company_id': cls.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'percentage',
            'percentage': 6.0,
            'valid_from': '2024-01-01',
        })
        
        # Create property with both prospector and agent
        # Create property type, state, location_type for testing
        cls.property_type = cls.env['real.estate.property.type'].search([('name', '=', 'House')], limit=1)
        if not cls.property_type:
            cls.property_type = cls.env['real.estate.property.type'].create({'name': 'House'})
        
        cls.location_type = cls.env['real.estate.location.type'].search([('name', '=', 'Urban')], limit=1)
        if not cls.location_type:
            cls.location_type = cls.env['real.estate.location.type'].create({'name': 'Urban', 'code': 'URB'})
        
        cls.country = cls.env['res.country'].search([('code', '=', 'BR')], limit=1)
        if not cls.country:
            cls.country = cls.env['res.country'].create({'name': 'Brazil', 'code': 'BR'})
        
        cls.state = cls.env['real.estate.state'].search([('code', '=', 'SP')], limit=1)
        if not cls.state:
            cls.state = cls.env['real.estate.state'].create({
                'name': 'São Paulo',
                'code': 'SP',
                'country_id': cls.country.id
            })
        
        cls.property_with_split = cls.Property.create({
            'name': 'Property with Split',
            'prospector_id': cls.prospector_agent.id,
            'agent_id': cls.selling_agent.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '1000',
            'area': 100.0,
        })
        
        # Create property with no prospector (no split)
        cls.property_no_split = cls.Property.create({
            'name': 'Property No Split',
            'agent_id': cls.selling_agent.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '2000',
            'area': 120.0,
        })
        
        # Create property where prospector == agent (no split)
        cls.property_same_agent = cls.Property.create({
            'name': 'Property Same Agent',
            'prospector_id': cls.selling_agent.id,
            'agent_id': cls.selling_agent.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'property_type_id': cls.property_type.id,
            'state_id': cls.state.id,
            'location_type_id': cls.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '3000',
            'area': 150.0,
        })
    
    def test_commission_split_default_30_70(self):
        """T094.1: Commission split with default 30% prospector / 70% agent."""
        # Sale price: R$ 500,000
        # Commission 6% = R$ 30,000
        # Split 30/70: Prospector R$ 9,000, Agent R$ 21,000
        
        result = self.commission_rule.calculate_split_commission(
            self.property_with_split,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['total_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['prospector_commission'], 9000.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 21000.00, places=2)
        self.assertAlmostEqual(result['split_percentage'], 0.30, places=2)
    
    def test_commission_split_configurable_percentage(self):
        """T095.1: Commission split with custom percentage (40%)."""
        # Change system parameter to 40%
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.40')
        
        # Sale price: R$ 500,000
        # Commission 6% = R$ 30,000
        # Split 40/60: Prospector R$ 12,000, Agent R$ 18,000
        
        result = self.commission_rule.calculate_split_commission(
            self.property_with_split,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['total_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['prospector_commission'], 12000.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 18000.00, places=2)
        self.assertAlmostEqual(result['split_percentage'], 0.40, places=2)
        
        # Reset to default
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.30')
    
    def test_commission_split_no_split_when_no_prospector(self):
        """T094.2: No commission split when property has no prospector."""
        # Sale price: R$ 500,000
        # Commission 6% = R$ 30,000
        # No split: Agent gets 100%
        
        result = self.commission_rule.calculate_split_commission(
            self.property_no_split,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['total_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['prospector_commission'], 0.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['split_percentage'], 0.0, places=2)
    
    def test_commission_split_no_split_when_same_agent(self):
        """T094.3: No commission split when prospector == agent (same person)."""
        # Sale price: R$ 500,000
        # Commission 6% = R$ 30,000
        # No split: Agent gets 100% (prospector and seller are the same)
        
        result = self.commission_rule.calculate_split_commission(
            self.property_same_agent,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['total_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['prospector_commission'], 0.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['split_percentage'], 0.0, places=2)
    
    def test_commission_split_fixed_amount_structure(self):
        """T095.2: Commission split works with fixed amount structure."""
        # Create fixed amount commission rule (R$ 15,000)
        fixed_rule = self.CommissionRule.create({
            'agent_id': self.selling_agent.id,
            'company_id': self.company_a.id,
            'transaction_type': 'sale',
            'structure_type': 'fixed',
            'fixed_amount': 15000.00,
            'valid_from': '2024-01-01',
        })
        
        # Commission R$ 15,000
        # Split 30/70: Prospector R$ 4,500, Agent R$ 10,500
        
        result = fixed_rule.calculate_split_commission(
            self.property_with_split,
            500000.00,  # Sale price (not used for fixed amount)
            'sale'
        )
        
        self.assertAlmostEqual(result['total_commission'], 15000.00, places=2)
        self.assertAlmostEqual(result['prospector_commission'], 4500.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 10500.00, places=2)
    
    def test_commission_split_invalid_percentage_raises_error(self):
        """T095.3: Invalid split percentage raises ValidationError."""
        # Set invalid percentage (> 1.0)
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '1.5')
        
        with self.assertRaises(ValidationError):
            self.commission_rule.calculate_split_commission(
                self.property_with_split,
                500000.00,
                'sale'
            )
        
        # Reset to default
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.30')
    
    def test_commission_split_zero_percentage(self):
        """T095.4: Zero split percentage (0%) gives all commission to agent."""
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.0')
        
        result = self.commission_rule.calculate_split_commission(
            self.property_with_split,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['prospector_commission'], 0.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 30000.00, places=2)
        
        # Reset to default
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.30')
    
    def test_commission_split_100_percentage(self):
        """T095.5: 100% split percentage gives all commission to prospector."""
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '1.0')
        
        result = self.commission_rule.calculate_split_commission(
            self.property_with_split,
            500000.00,
            'sale'
        )
        
        self.assertAlmostEqual(result['prospector_commission'], 30000.00, places=2)
        self.assertAlmostEqual(result['agent_commission'], 0.00, places=2)
        
        # Reset to default
        self.IrConfigParameter.set_param('quicksol_estate.prospector_commission_percentage', '0.30')
    
    def test_commission_split_requires_property_with_agent(self):
        """T095.6: calculate_split_commission requires property with agent_id."""
        property_no_agent = self.Property.create({
            'name': 'Property No Agent',
            'prospector_id': self.prospector_agent.id,
            'company_ids': [(6, 0, [self.company_a.id])],
            'property_type_id': self.property_type.id,
            'state_id': self.state.id,
            'location_type_id': self.location_type.id,
            'zip_code': '01310-100',
            'city': 'São Paulo',
            'street': 'Av Paulista',
            'street_number': '4000',
            'area': 80.0,
        })
        
        with self.assertRaises(ValidationError):
            self.commission_rule.calculate_split_commission(
                property_no_agent,
                500000.00,
                'sale'
            )
