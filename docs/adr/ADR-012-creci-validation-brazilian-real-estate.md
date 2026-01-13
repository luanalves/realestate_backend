# ADR-012: CRECI Validation for Brazilian Real Estate System

**Status**: Proposed  
**Created**: 2026-01-12  
**Context**: Agent Management Feature (004-agent-management)  
**Related**: ADR-003 (Mandatory Test Coverage), ADR-004 (Nomenclatura)

## Context

The Brazilian real estate system requires validation of CRECI (Conselho Regional de Corretores de Imóveis) numbers for licensed real estate brokers. CRECI is the professional license issued by regional councils in each Brazilian state, similar to a bar license for lawyers.

### Business Requirements

- **CRECI is optional**: Not all agents need CRECI (interns, assistants, administrative staff)
- **When provided, must be valid**: Format and uniqueness validation required
- **Flexible input formats**: Users enter CRECI in various formats, system must normalize
- **Multi-tenant uniqueness**: CRECI must be unique per company (not globally)
- **Audit trail**: Changes to CRECI must be logged

### Current State

From [spec.md](../../specs/004-agent-management/spec.md#L140):
> **FR-003**: System MUST validate CRECI format and uniqueness within the same company when provided (CRECI is optional to allow trainees/assistants without CRECI). System MUST accept flexible input formats and normalize to standard "CRECI/UF NNNNN"

## Decision

### 1. CRECI Format Standard

**Canonical Format**: `CRECI/UF NNNNN`

- **UF**: Two-letter Brazilian state code (27 valid states)
- **NNNNN**: 5-digit registration number (can be 4-6 digits depending on state/registration date)
- **Separator**: Forward slash `/` between "CRECI/UF" and space before number

**Examples**:
- `CRECI/SP 12345` (São Paulo)
- `CRECI/RJ 98765` (Rio de Janeiro)
- `CRECI/MG 4567` (Minas Gerais - 4 digits valid for older registrations)

### 2. Accepted Input Variations

The system MUST accept the following input formats and normalize to canonical format:

| Input Format | Example | Normalized Output |
|--------------|---------|-------------------|
| Standard | `CRECI/SP 12345` | `CRECI/SP 12345` |
| Dash separator | `CRECI-SP-12345` | `CRECI/SP 12345` |
| Space separator | `CRECI SP 12345` | `CRECI/SP 12345` |
| Number-State | `12345-SP` | `CRECI/SP 12345` |
| Number/State | `12345/SP` | `CRECI/SP 12345` |
| Compact | `CRECISP12345` | `CRECI/SP 12345` |
| Lowercase | `creci/sp 12345` | `CRECI/SP 12345` |
| Extra spaces | `CRECI / SP  12345` | `CRECI/SP 12345` |
| With suffix | `CRECI/SP 12345-F` | `CRECI/SP 12345` (F suffix ignored) |

### 3. Validation Rules

#### 3.1 UF (State) Validation

Valid Brazilian state codes (27 states):
```python
VALID_UF_CODES = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
    'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
    'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
]
```

#### 3.2 Number Format Validation

- **Length**: 4 to 6 digits (most common is 5)
- **Type**: Numeric only
- **Leading zeros**: Preserved (e.g., `01234` is valid)
- **No checksum**: CRECI numbers do NOT have check digits like CPF/CNPJ

#### 3.3 Uniqueness Constraint

- **Scope**: Per company (multi-tenant isolation)
- **Database constraint**: Unique index on `(creci, company_id)` where `creci IS NOT NULL`
- **Rationale**: The same CRECI number can exist in different companies (different broker working for different agencies)

#### 3.4 Optional Field Behavior

- **NULL allowed**: Agent can be created without CRECI
- **Empty string normalized to NULL**: `""` → `NULL` in database
- **Validation triggered only when provided**: Skip validation if `NULL`

### 4. Normalization Algorithm

```python
def normalize_creci(creci_input: str) -> str:
    """
    Normalize CRECI input to canonical format: CRECI/UF NNNNN
    
    Args:
        creci_input: Raw CRECI input from user
        
    Returns:
        Normalized CRECI string or None if empty
        
    Raises:
        ValueError: If format is invalid
    """
    if not creci_input or not creci_input.strip():
        return None
    
    # Remove extra whitespace and convert to uppercase
    creci_clean = re.sub(r'\s+', ' ', creci_input.strip().upper())
    
    # Pattern 1: CRECI/UF NNNNN, CRECI-UF-NNNNN, CRECI UF NNNNN
    pattern1 = r'^CRECI[\s/-]*([A-Z]{2})[\s/-]*(\d{4,6})(?:-[A-Z])?$'
    
    # Pattern 2: NNNNN-UF, NNNNN/UF
    pattern2 = r'^(\d{4,6})[\s/-]+([A-Z]{2})$'
    
    # Pattern 3: CRECIUFNNNNN (compact)
    pattern3 = r'^CRECI([A-Z]{2})(\d{4,6})$'
    
    match = re.match(pattern1, creci_clean)
    if match:
        uf, number = match.groups()
    else:
        match = re.match(pattern2, creci_clean)
        if match:
            number, uf = match.groups()
        else:
            match = re.match(pattern3, creci_clean)
            if match:
                uf, number = match.groups()
            else:
                raise ValueError(
                    f"Invalid CRECI format: '{creci_input}'. "
                    f"Expected formats: 'CRECI/SP 12345', 'CRECI-SP-12345', "
                    f"'12345-SP', etc."
                )
    
    # Validate UF
    VALID_UF_CODES = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    if uf not in VALID_UF_CODES:
        raise ValueError(f"Invalid UF code: '{uf}'. Must be a valid Brazilian state.")
    
    # Return canonical format
    return f"CRECI/{uf} {number}"
```

### 5. Implementation Approach

#### 5.1 Model Constraint (Odoo)

```python
# models/agent.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from ..services.creci_validator import CreciValidator

class Agent(models.Model):
    _name = 'real.estate.agent'
    _description = 'Real Estate Agent'
    
    creci = fields.Char(string='CRECI', help='Regional Council Registration Number')
    company_ids = fields.Many2many('thedevkitchen.estate.company', string='Companies')
    
    @api.constrains('creci', 'company_ids')
    def _validate_creci(self):
        """Validate CRECI format and uniqueness per company"""
        for record in self:
            if not record.creci:
                continue  # CRECI is optional
            
            try:
                # Normalize CRECI format
                normalized = CreciValidator.normalize(record.creci)
                if normalized != record.creci:
                    record.creci = normalized
                    
            except ValueError as e:
                raise ValidationError(str(e))
            
            # Check uniqueness per company
            for company in record.company_ids:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('creci', '=', record.creci),
                    ('company_ids', 'in', company.id)
                ], limit=1)
                
                if duplicate:
                    raise ValidationError(
                        f"CRECI {record.creci} is already registered for another "
                        f"agent in company {company.name}"
                    )
    
    _sql_constraints = [
        # Note: Partial unique index preferred over SQL constraint
        # due to multi-tenant many2many relationship
    ]
```

#### 5.2 Service Layer (CreciValidator)

```python
# services/creci_validator.py
import re
from typing import Optional, Tuple

class CreciValidator:
    """
    Service for validating and normalizing Brazilian CRECI numbers.
    
    CRECI (Conselho Regional de Corretores de Imóveis) is the professional
    license for real estate brokers in Brazil, issued by regional councils.
    """
    
    VALID_UF_CODES = [
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    ]
    
    @staticmethod
    def normalize(creci_input: str) -> Optional[str]:
        """
        Normalize CRECI to canonical format: CRECI/UF NNNNN
        
        Accepts variations:
        - CRECI/SP 12345
        - CRECI-SP-12345
        - CRECI SP 12345
        - 12345-SP
        - 12345/SP
        - CRECISP12345
        
        Returns None for empty/None input.
        Raises ValueError for invalid format.
        """
        if not creci_input or not creci_input.strip():
            return None
        
        # Implementation from normalize_creci() above
        # ... (full code from section 4)
        
    @staticmethod
    def validate(creci: str) -> Tuple[bool, Optional[str]]:
        """
        Validate CRECI format.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            normalized = CreciValidator.normalize(creci)
            return True, None
        except ValueError as e:
            return False, str(e)
    
    @staticmethod
    def extract_parts(creci: str) -> Tuple[str, str]:
        """
        Extract UF and number from normalized CRECI.
        
        Args:
            creci: Normalized CRECI string (CRECI/UF NNNNN)
            
        Returns:
            Tuple[str, str]: (uf, number)
        """
        if not creci:
            return None, None
        
        match = re.match(r'^CRECI/([A-Z]{2}) (\d{4,6})$', creci)
        if match:
            return match.groups()
        
        raise ValueError(f"CRECI not in normalized format: {creci}")
```

#### 5.3 API Controller Validation

```python
# controllers/agent_api.py
from odoo import http
from odoo.http import request
from ..services.creci_validator import CreciValidator

class AgentAPI(http.Controller):
    
    @http.route('/api/v1/agents', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
    @require_jwt
    @require_session
    @require_company
    def create_agent(self, **kwargs):
        """Create new agent"""
        data = request.jsonrequest
        
        # Normalize CRECI before creation
        if data.get('creci'):
            try:
                data['creci'] = CreciValidator.normalize(data['creci'])
            except ValueError as e:
                return error_response(400, str(e))
        
        # Create agent (model constraint will validate uniqueness)
        try:
            agent = request.env['real.estate.agent'].create(data)
            return success_response(201, agent.read()[0])
        except ValidationError as e:
            return error_response(400, str(e))
```

### 6. Database Schema

```sql
-- PostgreSQL migration
ALTER TABLE real_estate_agent 
ADD COLUMN creci VARCHAR(20);

-- Partial unique index (ignores NULL values)
CREATE UNIQUE INDEX idx_agent_creci_company 
ON real_estate_agent (creci, company_id) 
WHERE creci IS NOT NULL;

-- Index for lookups
CREATE INDEX idx_agent_creci 
ON real_estate_agent (creci) 
WHERE creci IS NOT NULL;
```

**Rationale for partial index**:
- Unique constraint only applies when CRECI is provided
- Allows multiple agents with NULL CRECI
- Enforces uniqueness per company (many-to-many handled in application logic)

### 7. Edge Cases & Special Scenarios

#### 7.1 Historical Registrations

**Problem**: Older CRECI numbers may have 4 digits instead of 5.

**Solution**: Accept 4-6 digits in validation, preserve as entered after normalization.

```python
# Valid examples:
"CRECI/SP 1234"   # 4 digits - old registration
"CRECI/SP 12345"  # 5 digits - standard
"CRECI/SP 123456" # 6 digits - newer/special registration
```

#### 7.2 CRECI with Suffixes (F, J, PF, PJ)

**Problem**: Some CRECI numbers have suffixes like `-F` (person), `-J` (company).

**Examples**:
- `CRECI/SP 12345-F` (Physical person)
- `CRECI/SP 12345-J` (Legal entity)

**Solution**: Strip suffix during normalization, store without suffix.

**Rationale**: Suffixes are administrative classifications, not part of the unique identifier.

#### 7.3 Multiple Agents with Same CRECI in Different Companies

**Scenario**: João has CRECI/SP 12345 and works for both Imobiliária A and Imobiliária B.

**Solution**: Create two separate agent records:
- Agent 1: João, CRECI/SP 12345, Company A
- Agent 2: João, CRECI/SP 12345, Company B

**Rationale**: Aligns with business rule that "one agent belongs to one company" (from [spec.md](../../specs/004-agent-management/spec.md#L13)).

#### 7.4 CRECI Update/Transfer

**Scenario**: Agent updates CRECI from temporary to permanent number.

**Solution**: Allow CRECI update via API, validate uniqueness on update.

```python
# API allows update
PUT /api/v1/agents/{id}
{
  "creci": "CRECI/SP 54321"  # Updated CRECI
}

# Validation ensures no duplicate in same company
```

#### 7.5 Empty String vs NULL

**Problem**: Frontend may send `""` instead of `null` for empty CRECI.

**Solution**: Normalize empty string to `NULL` before validation.

```python
@api.model
def create(self, vals):
    if 'creci' in vals and not vals['creci']:
        vals['creci'] = None
    return super().create(vals)
```

### 8. Testing Strategy

#### 8.1 Unit Tests (services/test_creci_validator.py)

```python
import unittest
from ..services.creci_validator import CreciValidator

class TestCreciValidator(unittest.TestCase):
    """Test CRECI normalization and validation"""
    
    def test_normalize_standard_format(self):
        """Test normalization of standard format"""
        result = CreciValidator.normalize('CRECI/SP 12345')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_dash_format(self):
        """Test normalization of dash-separated format"""
        result = CreciValidator.normalize('CRECI-SP-12345')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_reverse_format(self):
        """Test normalization of number-first format"""
        result = CreciValidator.normalize('12345-SP')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_compact_format(self):
        """Test normalization of compact format"""
        result = CreciValidator.normalize('CRECISP12345')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_lowercase(self):
        """Test normalization converts to uppercase"""
        result = CreciValidator.normalize('creci/sp 12345')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_extra_spaces(self):
        """Test normalization removes extra spaces"""
        result = CreciValidator.normalize('CRECI / SP  12345')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_with_suffix(self):
        """Test normalization strips suffix"""
        result = CreciValidator.normalize('CRECI/SP 12345-F')
        self.assertEqual(result, 'CRECI/SP 12345')
    
    def test_normalize_empty_returns_none(self):
        """Test empty input returns None"""
        self.assertIsNone(CreciValidator.normalize(''))
        self.assertIsNone(CreciValidator.normalize('   '))
        self.assertIsNone(CreciValidator.normalize(None))
    
    def test_validate_invalid_uf(self):
        """Test validation rejects invalid UF"""
        with self.assertRaises(ValueError):
            CreciValidator.normalize('CRECI/XY 12345')
    
    def test_validate_invalid_format(self):
        """Test validation rejects completely invalid format"""
        with self.assertRaises(ValueError):
            CreciValidator.normalize('ABC123')
    
    def test_validate_4_digit_number(self):
        """Test validation accepts 4-digit numbers (old registrations)"""
        result = CreciValidator.normalize('CRECI/SP 1234')
        self.assertEqual(result, 'CRECI/SP 1234')
    
    def test_validate_6_digit_number(self):
        """Test validation accepts 6-digit numbers"""
        result = CreciValidator.normalize('CRECI/SP 123456')
        self.assertEqual(result, 'CRECI/SP 123456')
    
    def test_extract_parts(self):
        """Test extracting UF and number from normalized CRECI"""
        uf, number = CreciValidator.extract_parts('CRECI/SP 12345')
        self.assertEqual(uf, 'SP')
        self.assertEqual(number, '12345')
```

#### 8.2 Integration Tests (tests/test_agent.py)

```python
from odoo.tests import TransactionCase
from odoo.exceptions import ValidationError

class TestAgentCreci(TransactionCase):
    """Test CRECI validation in Agent model"""
    
    def setUp(self):
        super().setUp()
        self.company = self.env['thedevkitchen.estate.company'].create({
            'name': 'Test Real Estate'
        })
    
    def test_create_agent_with_valid_creci(self):
        """Test creating agent with valid CRECI"""
        agent = self.env['real.estate.agent'].create({
            'name': 'João Silva',
            'creci': 'CRECI-SP-12345',
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        # Should normalize to standard format
        self.assertEqual(agent.creci, 'CRECI/SP 12345')
    
    def test_create_agent_without_creci(self):
        """Test creating agent without CRECI (optional)"""
        agent = self.env['real.estate.agent'].create({
            'name': 'Maria Santos',
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        self.assertIsNone(agent.creci)
    
    def test_duplicate_creci_same_company_raises_error(self):
        """Test duplicate CRECI in same company raises ValidationError"""
        self.env['real.estate.agent'].create({
            'name': 'João Silva',
            'creci': 'CRECI/SP 12345',
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        with self.assertRaises(ValidationError):
            self.env['real.estate.agent'].create({
                'name': 'Maria Santos',
                'creci': 'CRECI/SP 12345',
                'company_ids': [(6, 0, [self.company.id])]
            })
    
    def test_same_creci_different_companies_allowed(self):
        """Test same CRECI in different companies is allowed"""
        company2 = self.env['thedevkitchen.estate.company'].create({
            'name': 'Another Real Estate'
        })
        
        agent1 = self.env['real.estate.agent'].create({
            'name': 'João Silva',
            'creci': 'CRECI/SP 12345',
            'company_ids': [(6, 0, [self.company.id])]
        })
        
        agent2 = self.env['real.estate.agent'].create({
            'name': 'João Silva',
            'creci': 'CRECI/SP 12345',
            'company_ids': [(6, 0, [company2.id])]
        })
        
        self.assertNotEqual(agent1.id, agent2.id)
        self.assertEqual(agent1.creci, agent2.creci)
```

#### 8.3 API Tests (Cypress E2E)

```javascript
// cypress/e2e/agent-creci-validation.cy.js
describe('Agent CRECI Validation API', () => {
  
  it('Should accept and normalize CRECI in standard format', () => {
    cy.apiCreateAgent({
      name: 'João Silva',
      creci: 'CRECI/SP 12345'
    }).then((response) => {
      expect(response.body.creci).to.equal('CRECI/SP 12345');
    });
  });
  
  it('Should normalize CRECI from dash-separated format', () => {
    cy.apiCreateAgent({
      name: 'Maria Santos',
      creci: 'CRECI-RJ-98765'
    }).then((response) => {
      expect(response.body.creci).to.equal('CRECI/RJ 98765');
    });
  });
  
  it('Should normalize CRECI from reverse format', () => {
    cy.apiCreateAgent({
      name: 'Pedro Costa',
      creci: '54321-MG'
    }).then((response) => {
      expect(response.body.creci).to.equal('CRECI/MG 54321');
    });
  });
  
  it('Should reject invalid UF code', () => {
    cy.apiCreateAgent({
      name: 'Invalid Agent',
      creci: 'CRECI/XY 12345'
    }, { failOnStatusCode: false }).then((response) => {
      expect(response.status).to.equal(400);
      expect(response.body.error).to.include('Invalid UF code');
    });
  });
  
  it('Should reject duplicate CRECI in same company', () => {
    cy.apiCreateAgent({
      name: 'First Agent',
      creci: 'CRECI/SP 99999'
    });
    
    cy.apiCreateAgent({
      name: 'Second Agent',
      creci: 'CRECI/SP 99999'
    }, { failOnStatusCode: false }).then((response) => {
      expect(response.status).to.equal(400);
      expect(response.body.error).to.include('already registered');
    });
  });
  
  it('Should allow agent creation without CRECI', () => {
    cy.apiCreateAgent({
      name: 'Trainee Agent'
      // No CRECI field
    }).then((response) => {
      expect(response.status).to.equal(201);
      expect(response.body.creci).to.be.null;
    });
  });
});
```

## Alternatives Considered

### Alternative 1: External CRECI Validation API

**Approach**: Integrate with COFECI (Conselho Federal de Corretores de Imóveis) API to validate CRECI numbers against official registry.

**Pros**:
- Guarantees CRECI is real and active
- Could auto-fill broker name from registry

**Cons**:
- External dependency (API downtime blocks agent creation)
- Potential API rate limits
- Privacy concerns (sending user data externally)
- COFECI may not have public API
- Adds latency to every agent creation

**Decision**: Rejected. Format validation is sufficient for business needs. External validation would be a future enhancement if required by compliance.

### Alternative 2: Store CRECI as Structured Fields (UF + Number)

**Approach**: Store CRECI as two separate fields: `creci_uf` and `creci_number`.

**Pros**:
- Easier database queries by state
- Clearer data structure

**Cons**:
- More complex form validation
- Requires two fields in API
- User thinks of CRECI as single value
- More complex unique constraint (composite key)

**Decision**: Rejected. Single field with normalized format is simpler and aligns with user mental model.

### Alternative 3: Global Uniqueness (Not Per-Company)

**Approach**: CRECI must be globally unique across all companies.

**Pros**:
- Simpler database constraint
- Prevents accidental duplicates

**Cons**:
- Business rule: same person can work for multiple companies
- Would require separate agent records to share same CRECI
- Conflicts with real-world scenarios

**Decision**: Rejected. Business requirement explicitly allows agents to work for multiple companies (requires separate records).

### Alternative 4: Regex Validation Only (No Normalization)

**Approach**: Validate format but store as entered by user.

**Pros**:
- Preserves user input
- Simpler implementation

**Cons**:
- Duplicate detection fails (`CRECI/SP 12345` ≠ `12345-SP`)
- Inconsistent data format in reports
- Harder to search/filter

**Decision**: Rejected. Normalization is essential for data consistency and duplicate detection.

## Rationale

The chosen approach balances:

1. **User Experience**: Accepts common input formats users are familiar with
2. **Data Quality**: Normalizes to single canonical format for consistency
3. **Performance**: No external API calls, validation is instant
4. **Flexibility**: CRECI optional (allows interns/assistants)
5. **Multi-tenancy**: Uniqueness scoped per company
6. **Maintainability**: Clear separation of concerns (service layer for validation, model for constraints)
7. **Testability**: Each component independently testable

## Consequences

### Positive

- ✅ Improved user experience (flexible input formats)
- ✅ Data consistency (normalized storage format)
- ✅ Fast validation (no external dependencies)
- ✅ Clear error messages guide users
- ✅ Supports all business scenarios (optional, multi-company)
- ✅ Comprehensive test coverage possible

### Negative

- ⚠️ No verification against official CRECI registry (future enhancement)
- ⚠️ Manual deduplication needed if user enters same CRECI in different formats before validation
- ⚠️ Cannot detect fake/expired CRECI numbers

### Neutral

- 🔄 Migration needed for existing data (if any) to normalize format
- 🔄 Documentation needed for API consumers about accepted formats
- 🔄 Form UI should show normalized format after input blur

## Implementation Checklist

- [ ] Create `services/creci_validator.py` with `CreciValidator` class
- [ ] Add `_validate_creci()` constraint to `models/agent.py`
- [ ] Update `controllers/agent_api.py` to normalize CRECI on create/update
- [ ] Add database migration for `creci` field and unique index
- [ ] Write unit tests for `CreciValidator` (15+ test cases)
- [ ] Write integration tests for Agent model CRECI validation
- [ ] Write Cypress E2E tests for API CRECI validation
- [ ] Update API documentation (OpenAPI spec) with CRECI format examples
- [ ] Update user documentation with accepted CRECI formats
- [ ] Add form validation in Web UI to show normalized format on blur

## References

- [COFECI - Conselho Federal de Corretores de Imóveis](https://www.cofeci.gov.br/)
- [Spec: Agent Management Feature](../../specs/004-agent-management/spec.md)
- [ADR-003: Mandatory Test Coverage](./ADR-003-mandatory-test-coverage.md)
- [ADR-004: Nomenclatura Módulos e Tabelas](./ADR-004-nomenclatura-modulos-tabelas.md)
- [Brazilian States (UF codes)](https://www.ibge.gov.br/explica/codigos-dos-municipios.php)

## Revision History

| Date | Author | Changes |
|------|--------|---------|
| 2026-01-12 | GitHub Copilot | Initial draft with comprehensive validation strategy |
