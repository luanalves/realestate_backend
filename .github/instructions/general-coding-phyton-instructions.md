---
applyTo: "**/*.py"
---
# Project coding standards for Python

## Code Style and Quality
- Follow the PEP 8 style guide for Python.
- Always prioritize readability and clarity.
- Write clear and concise comments for each function.
- Ensure functions have descriptive names and include type hints.
- Maintain proper indentation (use 4 spaces for each level of indentation).

## Object-Oriented Programming (OOP) Best Practices

All Python code must follow OOP principles and best practices:

### SOLID Principles

1. **Single Responsibility Principle (SRP)**
   - Each class should have only one reason to change
   - Separate concerns into different classes
   - Example: Separate validation, business logic, and data access

2. **Open/Closed Principle (OCP)**
   - Classes should be open for extension but closed for modification
   - Use inheritance and composition over modifying existing code
   - Leverage Odoo's inheritance mechanisms (`_inherit`, `_inherits`)

3. **Liskov Substitution Principle (LSP)**
   - Subclasses must be substitutable for their base classes
   - Maintain consistent behavior in overridden methods
   - Respect parent class contracts

4. **Interface Segregation Principle (ISP)**
   - Don't force classes to depend on methods they don't use
   - Create specific, focused interfaces
   - Use mixins for shared functionality

5. **Dependency Inversion Principle (DIP)**
   - Depend on abstractions, not concrete implementations
   - Use dependency injection when possible
   - Leverage Odoo's service-oriented architecture

### Class Design Guidelines

**Proper Class Structure:**
```python
class EstateProperty(models.Model):
    """Real Estate Property Model.
    
    This model manages property listings including their lifecycle,
    pricing, and associated agents.
    """
    _name = 'estate.property'
    _description = 'Real Estate Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    # Fields definition
    name = fields.Char(required=True, index=True)
    
    # Computed fields
    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        """Compute the best offer for this property."""
        for record in self:
            record.best_offer = max(record.offer_ids.mapped('price'), default=0.0)
    
    # Constraints
    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        """Ensure selling price is not below 90% of expected price."""
        for record in self:
            if record.selling_price < record.expected_price * 0.9:
                raise ValidationError("Selling price too low")
    
    # Business methods
    def action_sell(self):
        """Mark property as sold."""
        self.ensure_one()
        self.state = 'sold'
        return True
```

### Encapsulation

- **Use private methods** (prefix with `_`) for internal logic:
  ```python
  def _validate_offer(self, offer_price):
      """Private method to validate offer logic."""
      return offer_price >= self.expected_price * 0.9
  ```

- **Protect data integrity** with computed fields and constraints
- **Avoid direct field access** from outside the class when possible
- **Use properties** for controlled access to attributes

### Inheritance Best Practices

**Model Inheritance in Odoo:**
```python
# Classic inheritance (_inherit with same _name)
class EstatePropertyExtended(models.Model):
    _inherit = 'estate.property'
    
    additional_field = fields.Char()
    
    def action_sell(self):
        """Extend parent method."""
        # Call parent method
        res = super().action_sell()
        # Add custom logic
        self._notify_sale()
        return res

# Delegation inheritance (_inherits)
class EstatePropertyWithAddress(models.Model):
    _name = 'estate.property.with.address'
    _inherits = {'res.partner': 'partner_id'}
    
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
```

### Composition Over Inheritance

- Prefer composition when relationship is "has-a" rather than "is-a"
- Use Many2one and One2many fields to compose complex objects
- Example:
  ```python
  class EstateProperty(models.Model):
      _name = 'estate.property'
      
      # Composition: Property HAS offers, not IS an offer
      offer_ids = fields.One2many('estate.property.offer', 'property_id')
      agent_id = fields.Many2one('res.partner')
  ```

### Polymorphism

- Use method overriding appropriately
- Maintain consistent method signatures
- Leverage Odoo's `@api` decorators correctly
- Example:
  ```python
  class PropertyOffer(models.Model):
      _name = 'estate.property.offer'
      
      def action_accept(self):
          """Base acceptance logic."""
          self.state = 'accepted'
      
  class PremiumPropertyOffer(models.Model):
      _inherit = 'estate.property.offer'
      
      def action_accept(self):
          """Premium offers have additional validation."""
          if not self._validate_premium_criteria():
              raise ValidationError("Premium criteria not met")
          return super().action_accept()
  ```

### Abstract Base Classes

Use abstract models for shared functionality:
```python
class PropertyMixin(models.AbstractModel):
    _name = 'estate.property.mixin'
    _description = 'Common Property Functionality'
    
    active = fields.Boolean(default=True)
    notes = fields.Text()
    
    def archive(self):
        """Common archive functionality."""
        self.active = False
```

### Design Patterns to Use

1. **Factory Pattern**: For creating different types of objects
2. **Strategy Pattern**: For interchangeable algorithms
3. **Observer Pattern**: Use Odoo's computed fields and onchange
4. **Decorator Pattern**: Leverage Python decorators and `@api` decorators
5. **Singleton Pattern**: Use `@tools.ormcache` for cached computations

### Code Smells to Avoid

- **God Classes**: Classes that do too much
- **Long Methods**: Break down into smaller, focused methods
- **Too Many Parameters**: Use objects or keyword arguments
- **Duplicate Code**: Extract to shared methods or mixins
- **Deep Nesting**: Refactor complex conditionals
- **Magic Numbers**: Use constants or configuration

### Pylint OOP-Specific Checks

Ensure these Pylint messages are addressed:
- `too-few-public-methods`: Ensure classes have sufficient functionality
- `too-many-instance-attributes`: Refactor overly complex classes
- `too-many-arguments`: Simplify method signatures
- `no-self-use`: Convert to static/class methods or remove
- `protected-access`: Avoid accessing protected members from outside

## Python Linting and Code Quality Tools

All Python files MUST pass linting and quality checks before being committed. Use the following tools:

### 1. **Flake8** (Style Guide Enforcement)
- Check for PEP 8 compliance
- Detect common programming errors
- Configuration: `.flake8` or `setup.cfg`
- Run: `flake8 <file_or_directory>`
- Maximum line length: 88 characters (Black compatible)

### 2. **Black** (Code Formatter)
- Automatic code formatting
- Ensures consistent style across the codebase
- Run: `black <file_or_directory>`
- Check without modifying: `black --check <file_or_directory>`

### 3. **isort** (Import Sorting)
- Automatically sort and organize imports
- Ensures consistent import order
- Run: `isort <file_or_directory>`
- Check without modifying: `isort --check-only <file_or_directory>`

### 4. **Pylint** (Advanced Static Analysis)
- Comprehensive code analysis
- Detects code smells, bugs, and style issues
- Run: `pylint <file_or_directory>`
- Minimum acceptable score: 8.0/10

### 5. **mypy** (Type Checking)
- Static type checking for Python
- Ensures type hints are used correctly
- Run: `mypy <file_or_directory>`

## Pre-commit Checklist

Before committing Python code, ensure:

1. **Format code**: `black .`
2. **Sort imports**: `isort .`
3. **Check style**: `flake8 .`
4. **Analyze code**: `pylint <changed_files>`
5. **Type check**: `mypy <changed_files>`
6. **Run tests**: Ensure all unit tests pass

## Recommended Configuration

### .flake8
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = __pycache__, .git, */migrations/*, */tests/*
```

### pyproject.toml (for Black and isort)
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 88
```

### .pylintrc
```ini
[MASTER]
ignore=migrations,tests

[MESSAGES CONTROL]
disable=C0111,R0903

[FORMAT]
max-line-length=88
```

## IDE Integration

Configure your IDE to run these tools automatically:
- **VS Code**: Install Python extension and configure settings
- **PyCharm**: Enable inspections and configure external tools
- Set up format-on-save for Black and isort

## Continuous Integration

All Python code must pass linting in CI/CD pipeline before merge.
