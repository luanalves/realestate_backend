# Real Estate Management Module (quicksol_estate)

Complete real estate management solution for Odoo 18.0 with multi-tenancy support, REST API, and comprehensive agent management.

## Features

### 🏢 Multi-Tenant Company Management
- Isolated data per real estate company
- Company-specific branding and settings
- CNPJ validation for Brazilian companies

### 🏠 Property Management
- Comprehensive property CRUD with 50+ fields
- Multiple property types (residential, commercial, land)
- Photo gallery with automatic image optimization
- Document management (contracts, titles, certificates)
- Location management with CEP integration
- Amenities, tags, and custom markers
- Key control and authorization periods

### 👥 Agent Management (Phase 8 - NEW!)
- **Agent Registration**: CPF validation, CRECI tracking, user account sync
- **Performance Metrics**: Total sales, commissions, active properties (computed fields)
- **Commission Rules**: Percentage/fixed/tiered structures, transaction filters, validity periods
- **Property Assignments**: Primary/support agent roles, kanban board view
- **Smart Buttons**: Quick access to agent properties and commission transactions
- **Multi-Tenant**: Automatic company isolation, cross-company validation

### 💰 Commission System
- Flexible commission structures (percentage, fixed, tiered)
- Transaction-based calculations (sales, rentals)
- Min/max value filters
- Validity period management
- Automatic commission transaction generation
- Commission history tracking

### 🔐 Security & Multi-Tenancy
- Row-level security (record rules)
- JWT token authentication for API endpoints
- Session-based authentication for web UI
- Cross-company data isolation
- ADR-008 compliant security architecture

### 🛡️ Role-Based Access Control (RBAC) - NEW!
**9 Predefined User Profiles** with granular permissions:

| Profile | Code | Access Level | Key Permissions |
|---------|------|--------------|-----------------|
| **Owner** | `group_real_estate_owner` | Full Control | Manage companies, assign users, full CRUD |
| **Director** | `group_real_estate_director` | Executive | All Manager permissions + BI dashboards, financial reports |
| **Manager** | `group_real_estate_manager` | Supervisory | Manage all company data, assign agents, approve commissions |
| **User** | `group_real_estate_user` | Standard | Basic CRUD within assigned companies |
| **Agent** | `group_real_estate_agent` | Field Staff | Manage own properties, view own commissions |
| **Prospector** | `group_real_estate_prospector` | Lead Generation | Track prospected properties, view split commissions |
| **Receptionist** | `group_real_estate_receptionist` | Front Desk | Read-only: properties, sales, leases |
| **Financial** | `group_real_estate_financial` | Accounting | Read sales/leases, CRUD commissions |
| **Legal** | `group_real_estate_legal` | Compliance | Read-only contracts, add legal notes |
| **Portal User** | `group_real_estate_portal_user` | Client Access | View own contracts only (partner-level isolation) |

**Security Features**:
- **Multi-Tenancy**: All users restricted by `estate_company_ids` (Many2many)
- **Record Rules**: 42 active rules enforcing row-level security
- **Audit Logging**: LGPD-compliant logging of all permission changes
- **Event-Driven**: SecurityGroupAuditObserver tracks group changes
- **Defense-in-Depth**: ACLs + Record Rules + Field-level security

**Commission Split**:
- Prospectors receive 30% of sale commission (configurable)
- Agents receive 70% of sale commission
- Automatic split calculation via Observer pattern
- Event: `sale.created` → CommissionSplitObserver → Transaction records

### 🌐 REST API
- OpenAPI 3.0 documentation
- JWT authentication
- HATEOAS hypermedia links
- Multi-tenant isolation
- Endpoints:
  - `/api/v1/agents` - Agent CRUD operations
  - `/api/v1/properties` - Property management
  - `/api/v1/commissions` - Commission tracking

### 🎨 User Interface
- **Odoo 18 Native Views**:
  - Agent tree view with performance metrics
  - Agent form with 4 notebook tabs (Performance, Rules, Assignments, History)
  - Commission rule tree/form views
  - Assignment kanban board (grouped by responsibility type)
  - Search views with filters and grouping
- **Smart Buttons**: Quick navigation between related records
- **Portuguese (pt_BR) translations**: Complete i18n support

## Installation

### Prerequisites
- Docker & Docker Compose
- Odoo 18.0
- PostgreSQL 16+
- Redis 7+ (for session caching)

### Setup

1. **Clone the repository**:
   ```bash
   cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
   ```

2. **Start services**:
   ```bash
   docker compose up -d
   ```

3. **Install module**:
   - Access Odoo: http://localhost:8069
   - Login with admin credentials
   - Go to Apps → Update Apps List
   - Search for "Real Estate Management"
   - Click Install

4. **Load demo data** (optional):
   - 5 sample agents with CRECI registration
   - 3 real estate companies
   - Multiple properties with full details

## Configuration

### Environment Variables
```env
# Database
POSTGRES_DB=realestate
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo

# Redis Cache
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
```

### Odoo Configuration
```ini
[options]
# Redis session storage
enable_redis = True
redis_host = redis
redis_port = 6379
redis_dbindex = 1
redis_pass = False

# API Gateway
api_gateway_enabled = True
jwt_secret_key = your-secret-key-here
```

## Usage

### Agent Management

**Create Agent**:
1. Navigate to Real Estate → Agents
2. Click Create
3. Fill in required fields:
   - Name, CPF, Email
   - CRECI State & Number
   - Company assignment
4. Optionally link to Odoo user account

**Configure Commission Rules**:
1. Open Agent form view
2. Go to "Commission Rules" tab
3. Add rules with:
   - Transaction type (Sale/Rental)
   - Structure (Percentage/Fixed/Tiered)
   - Min/Max values
   - Validity period

**Assign Properties**:
1. Open Agent form view
2. Go to "Assignments" tab
3. Click Add a line
4. Select property and responsibility type (Primary/Support)

**View Performance**:
- "Performance" tab shows:
  - Total sales count
  - Total commissions earned
  - Average commission per transaction
  - Active properties count

### API Usage

**Authentication**:
```bash
curl -X POST http://localhost:8069/api/v1/oauth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

**List Agents**:
```bash
curl http://localhost:8069/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Create Agent**:
```bash
curl -X POST http://localhost:8069/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "João Silva",
    "cpf": "12345678901",
    "email": "joao@example.com",
    "creci_state": "SP",
    "creci_number": "123456"
  }'
```

## Testing

Run the test suite:
```bash
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
docker compose run --rm odoo --test-enable --test-tags=quicksol_estate --stop-after-init
```

Current test coverage:
- **160 total tests**
- **75 passing** (46.9%)
- Focus areas: Agent CRUD, Commission calculations, Multi-tenancy isolation

## Database Schema

### Core Models
- `real.estate.agent` - Agent registration with CRECI
- `real.estate.commission.rule` - Commission configuration
- `real.estate.agent.property.assignment` - Property-agent relationships
- `real.estate.commission.transaction` - Commission history
- `real.estate.property` - Property master data
- `thedevkitchen.estate.company` - Multi-tenant companies

### Key Constraints
- Unique CRECI per state/company
- Unique user account per agent
- One active primary assignment per property/agent
- Company isolation via record rules

## Architecture

### ADR Compliance
- **ADR-004**: Nomenclatura de módulos e tabelas (Portuguese table names)
- **ADR-008**: Multi-tenancy & API security
- **ADR-009**: Headless authentication (JWT + session)
- **ADR-011**: Controller security (require_jwt + require_session decorators)

### Technology Stack
- **Backend**: Odoo 18.0 (Python 3.11)
- **Database**: PostgreSQL 16
- **Cache**: Redis 7 (AOF persistence)
- **API**: REST with OpenAPI 3.0
- **Authentication**: JWT + Session-based
- **Frontend**: Odoo Web Client (JavaScript)

## Development

### Project Structure
```
quicksol_estate/
├── __manifest__.py          # Module metadata
├── models/                  # Business logic
│   ├── agent.py            # Agent model (35 fields)
│   ├── commission_rule.py  # Commission config (21 fields)
│   ├── assignment.py       # Property assignments (8 fields)
│   └── ...
├── views/                   # UI definitions
│   ├── agent_views.xml     # Agent CRUD views (218 lines)
│   ├── commission_rule_views.xml
│   ├── assignment_views.xml
│   └── real_estate_menus.xml
├── data/                    # Seed data
│   ├── agent_seed.xml      # 5 demo agents
│   └── ...
├── controllers/             # REST API endpoints
├── tests/                   # Unit & integration tests
├── security/                # Access control
│   ├── groups.xml
│   ├── record_rules.xml    # Multi-tenant isolation
│   └── ir.model.access.csv
└── i18n/                    # Translations
    └── pt_BR.po            # Portuguese (906 lines)
```

### Adding New Features
1. Create model in `models/`
2. Add views in `views/`
3. Define security rules in `security/`
4. Register in `__manifest__.py`
5. Add tests in `tests/`
6. Update translations in `i18n/`

## Troubleshooting

### Common Issues

**Module not loading**:
```bash
# Check Odoo logs
docker compose logs -f odoo

# Restart with upgrade
docker compose run --rm odoo -u quicksol_estate --stop-after-init
```

**Database connection error**:
- Verify PostgreSQL is running: `docker compose ps`
- Check credentials in `odoo.conf`

**API authentication failing**:
- Ensure `thedevkitchen_apigateway` module is installed
- Verify JWT secret key configuration
- Check token expiration (default: 1 hour)

**Tests failing**:
- Some property tests require `zip_code` field (NotNull constraint)
- Agent user sync tests may fail without proper user setup
- Run specific test: `--test-tags=quicksol_estate.test_agent_crud`

## Changelog

### Version 1.2.0 (Phase 8 - January 2026)
- ✨ NEW: Agent management UI (tree, form, search views)
- ✨ NEW: Commission rule configuration views
- ✨ NEW: Property assignment kanban board
- ✨ NEW: Smart buttons for quick navigation
- ✨ NEW: 5 demo agents with company assignments
- 🔧 FIX: Odoo 18 compatibility (`<tree>` → `<list>`)
- 🔧 FIX: Deprecated `attrs` attribute removed
- 📚 DOC: Portuguese translations (pt_BR)
- 🧪 TEST: 160 automated tests (75 passing)

### Version 1.1.0 (Phase 7 - January 2026)
- Performance metrics for agents (computed fields)
- Commission transaction tracking
- SQL optimizations for large datasets

### Version 1.0.0 (Phases 1-6)
- Initial release with property management
- Multi-tenant architecture
- REST API with JWT authentication

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow ADR guidelines (see `docs/adr/`)
4. Add tests for new features
5. Update documentation
6. Submit pull request

## License

LGPL-3.0

## Support

- **Documentation**: `/docs` directory
- **API Docs**: http://localhost:8069/api/v1/docs (when running)
- **Issues**: Create GitHub issue with logs and reproduction steps

## Credits

**Author**: Quicksol Technologies  
**Website**: https://quicksol.ca  
**Odoo Version**: 18.0  
**Last Updated**: January 2026
