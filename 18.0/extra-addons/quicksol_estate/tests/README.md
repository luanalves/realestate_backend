# Real Estate Management - Unit Tests

This directory contains comprehensive unit tests for the `quicksol_estate` module. All tests use **mocks** to avoid database dependencies, ensuring fast execution and isolation.

## 📁 Test Structure

```
tests/
├── __init__.py                # Test package initialization
├── base_validation_test.py    # Base class for validation tests with utilities
├── base_company_test.py       # Company-specific base class with CNPJ utilities  
├── base_agent_test.py         # Agent-specific base class with user sync utilities
├── test_validations.py        # Email, date, and CNPJ validation tests
├── test_company_unit.py       # Company model business logic tests
├── test_agent_unit.py         # Agent model and user synchronization tests
└── README.md                 # This file
```

## 🧪 Test Categories

### 1. **Validation Tests** (`test_validations.py`)

#### EmailValidations
- ✅ **Agent email validation** using `email_normalize`
- ✅ **Tenant email validation** using regex patterns
- ✅ **Valid/invalid email formats** comprehensive coverage
- ✅ **Empty email handling** (optional fields)

#### DateValidations  
- ✅ **Lease date ranges** (end_date > start_date)
- ✅ **Invalid date combinations** error detection
- ✅ **Edge cases** (same dates, None values)

#### CnpjValidations
- ✅ **CNPJ formatting** (14 digits to XX.XXX.XXX/XXXX-XX)
- ✅ **Length validation** (must be 14 digits)
- ✅ **Invalid formats** handling
- ✅ **Already formatted** CNPJ processing

#### FieldRequiredValidations
- ✅ **Required fields** enforcement simulation
- ✅ **Optional fields** handling
- ✅ **Default values** application

---

### 2. **Company Model Tests** (`test_company_unit.py`)

#### TestCompanyUnit
- ✅ **Company creation** with valid data
- ✅ **Computed fields** (property_count, agent_count, lease_count, sale_count)
- ✅ **CNPJ formatting** automatic processing
- ✅ **Action methods** (view_properties, view_agents, view_leases, view_sales)
- ✅ **Many2many relationships** with other models
- ✅ **Default values** and data integrity

#### TestCompanyBusinessLogic
- ✅ **Active filtering** logic
- ✅ **Data integrity** constraints
- ✅ **String representation** display names

---

### 3. **Agent Model Tests** (`test_agent_unit.py`)

#### TestAgentUnit
- ✅ **Agent creation** with user synchronization
- ✅ **onchange user_id** data sync logic
- ✅ **Email validation** using `email_normalize`
- ✅ **Write method** company synchronization
- ✅ **Safe access** for missing user attributes
- ✅ **Relationship integrity** companies and properties

#### TestAgentBusinessLogic
- ✅ **Company assignment** workflows
- ✅ **User integration** scenarios
- ✅ **Data validation** and integrity checks
- ✅ **Edge cases** boundary conditions

---

## 🏗️ Base Test Classes

### BaseValidationTest (`base_validation_test.py`)
Provides utilities for validation-related tests:
- ✅ **Email validation helpers** (valid/invalid test cases)
- ✅ **Date range validation** utilities  
- ✅ **Validation error assertion** methods
- ✅ **Mock record creation** for validation tests

### BaseCompanyTest (`base_company_test.py`)  
Specialized base class for company-related tests:
- ✅ **CNPJ validation/formatting** utilities
- ✅ **Company mock data** setup
- ✅ **Company model mocking** methods
- ✅ **Domain-specific test helpers**

### BaseAgentTest (`base_agent_test.py`)
Specialized base class for agent-related tests:
- ✅ **User synchronization** test utilities
- ✅ **Agent/User mock data** setup  
- ✅ **Email validation helpers** for agents
- ✅ **User-agent relationship** mocking

---

## 🚀 Running Tests

### Using Odoo's Built-in Test Command (Recommended)

```bash
# Navigate to the Odoo Docker directory
cd 18.0/

# Run all tests for the quicksol_estate module
docker compose exec odoo python3 -m odoo --test-tags quicksol_estate -d realestate --stop-after-init

# Run tests with specific tag
docker compose exec odoo python3 -m odoo --test-tags quicksol_estate.validations -d realestate --stop-after-init

# Run tests with verbose output
docker compose exec odoo python3 -m odoo --test-tags quicksol_estate -d realestate --stop-after-init --log-level=test

# Run from host (if Odoo installed locally)
python3 -m odoo --test-tags quicksol_estate -d database_name --stop-after-init
```

### Alternative: Using unittest directly (for development)

```bash
# From the quicksol_estate module directory
cd 18.0/extra-addons/quicksol_estate/

# Run all tests in a module
python3 -m unittest tests.test_validations

# Run specific test class
python3 -m unittest tests.test_validations.TestEmailValidations

# Run specific test method  
python3 -m unittest tests.test_validations.TestEmailValidations.test_agent_email_validation_valid

# Run with verbose output
python3 -m unittest tests.test_validations -v
```

---

## 🎯 Test Philosophy

### **Why Mock-Based Unit Tests?**

1. **🚀 Speed**: No database I/O, tests run in milliseconds
2. **🔄 Isolation**: Each test is completely independent
3. **🎯 Focus**: Tests only the Python logic, not Odoo framework
4. **🛡️ Reliability**: No external dependencies or database state
5. **🧪 Control**: Can simulate any scenario, including edge cases

### **What We Test:**

- ✅ **Business Logic**: Validation methods, computed fields, workflows
- ✅ **Data Integrity**: Field constraints, required fields, defaults
- ✅ **Method Behavior**: onchange, write, create method logic
- ✅ **Edge Cases**: Boundary conditions, error handling
- ✅ **Integration Logic**: User-agent sync, company assignments

### **What We Don't Test:**

- ❌ **Database Operations**: Create, read, update, delete (tested in integration)
- ❌ **Odoo Framework**: ORM behavior, recordset operations
- ❌ **UI Components**: Views, actions, menus (tested separately)
- ❌ **External APIs**: Third-party integrations

---

## 📊 Test Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| **Validations** | 100% | ✅ Complete |
| **Company Model** | 90% | ✅ Complete |
| **Agent Model** | 90% | ✅ Complete |
| **Tenant Model** | 85% | 📋 Planned |
| **Property Model** | 85% | 📋 Planned |
| **Lease Model** | 85% | 📋 Planned |
| **Sale Model** | 85% | 📋 Planned |

---

## 🔧 Writing New Tests

### Base Test Class Usage

```python
from .base_test import BaseRealEstateTest

class TestMyModel(BaseRealEstateTest):
    
    def test_my_functionality(self):
        # Use pre-configured test data
        company = self.create_mock_record('thedevkitchen.estate.company', 
                                        self.mock_company_data)
        
        # Test your logic
        self.assertEqual(company.name, 'Test Real Estate Company')
```

### Mock Validation Helper

```python
def test_my_validation(self):
    # Use validation helpers
    self.assert_validation_error(my_validation_function, invalid_data)
    self.assert_no_validation_error(my_validation_function, valid_data)
```

### Custom Mock Records

```python
def test_custom_scenario(self):
    # Create custom mock with methods
    custom_methods = {
        'my_method': Mock(return_value='test_result')
    }
    
    record = self.create_mock_record('my.model', data, methods=custom_methods)
    result = record.my_method()
    self.assertEqual(result, 'test_result')
```

---

## 🐛 Debugging Tests

### Verbose Output
```bash
# Using Odoo test command
docker compose exec odoo python3 -m odoo --test-tags quicksol_estate -d realestate --stop-after-init --log-level=test

# Using unittest directly  
python3 -m unittest tests.test_validations -v
```

### Single Test Debugging
```bash
python3 -m unittest tests.test_validations.TestEmailValidations.test_agent_email_validation_valid -v
```

### Print Debugging in Tests
```python
def test_debug_example(self):
    result = my_function(test_data)
    print(f"DEBUG: Result = {result}")  # Will show in verbose mode
    self.assertEqual(result, expected)
```

---

## 🎉 Benefits Achieved

### **Development Benefits:**
- 🔍 **Early Bug Detection**: Catch issues before deployment
- 🛡️ **Refactoring Safety**: Change code with confidence
- 📚 **Living Documentation**: Tests document expected behavior
- 🚀 **Fast Feedback**: Run tests in seconds, not minutes

### **Maintenance Benefits:**
- 🎯 **Regression Prevention**: Ensure new changes don't break existing functionality
- 🧪 **Edge Case Coverage**: Test scenarios that are hard to reproduce manually
- 📊 **Quality Metrics**: Measure code quality objectively
- 🔄 **CI/CD Ready**: Integrate with automated pipelines

---

## 📝 Adding More Tests

To extend the test suite:

1. **Create new test file**: `tests/test_new_model.py`
2. **Choose appropriate base class**: 
   - `BaseValidationTest` for validation-focused tests
   - `BaseCompanyTest` for company-related tests  
   - `BaseAgentTest` for agent-related tests
3. **Add comprehensive test cases**: Cover main functionality and edge cases
4. **Update** `tests/__init__.py`: Import your new test module

---

## 🎯 Next Steps

### Planned Additions:
- [ ] **Tenant Model Tests**: Email validation, data integrity
- [ ] **Property Model Tests**: Price validation, status workflows  
- [ ] **Lease Model Tests**: Date validation, relationship integrity
- [ ] **Sale Model Tests**: Business logic, data validation
- [ ] **Integration Tests**: Multi-model workflows
- [ ] **Performance Tests**: Large dataset handling

### Future Enhancements:
- [ ] **Coverage Reports**: Automated coverage measurement
- [ ] **CI/CD Integration**: GitHub Actions workflow
- [ ] **Mutation Testing**: Test quality validation
- [ ] **Property-Based Testing**: Hypothesis-driven tests

---

*Happy Testing! 🧪*