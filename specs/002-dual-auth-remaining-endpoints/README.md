# Spec 002: Dual Authentication for Remaining API Endpoints

## 🎯 Status: Ready for Execution

**Branch**: `002-dual-auth-remaining-endpoints`  
**Priority**: High (Security)  
**Estimated Effort**: 1-2 days (reduced from 3-4)

---

## 📊 Executive Summary

### Situation
After implementing dual authentication (Bearer Token + Session) for User Authentication endpoints in spec 001, we need to ensure consistent security across the entire API surface.

### Discovered State
✅ **GOOD NEWS**: All business endpoints already have `@require_jwt` + `@require_session` decorators!

- **Agents**: 11 endpoints - ✅ All protected
- **Properties**: 4 endpoints - ✅ All protected  
- **Assignments**: 2 endpoints - ✅ All protected
- **Commissions**: 4 endpoints - ✅ All protected
- **Performance**: 2 endpoints - ✅ All protected

**Total**: 23 endpoints already secured 🎉

### Remaining Work

Since the decorators are already in place, this spec now focuses on:

1. **Code Quality** (Priority 1)
   - Remove 4 debug log statements from middleware
   - Add session_id length validation
   - Improve error messages

2. **Postman Collection** (Priority 2)
   - File is currently empty (0 bytes)
   - Need to create/restore complete collection
   - Fix session_id capture bug from login script
   - Add session_id to all endpoint requests

3. **Documentation** (Priority 3)
   - Document User-Agent consistency requirement
   - Update API authentication guide
   - Create troubleshooting guide

4. **Testing** (Priority 4)
   - Validate existing decorators work correctly
   - Add E2E tests for each domain
   - Verify session hijacking prevention

### Impact

**Effort Reduction**: From 3-4 days to 1-2 days (60% reduction)  
**Risk Reduction**: Low risk since decorators already exist  
**Value**: Complete, consistent API security across all endpoints

---

## 📁 Spec Files

- [spec.md](spec.md) - Complete feature specification
- [plan.md](plan.md) - Implementation plan (needs update for new scope)
- [tasks.md](tasks.md) - Granular task breakdown (needs update)
- [research.md](research.md) - Endpoint inventory and current state
- **This file** - Quick reference and status

---

## 🔍 Key Findings

### Endpoint Inventory

**agent_api.py** (11 endpoints):
```python
GET    /api/v1/agents                      ✅ @require_jwt + @require_session
POST   /api/v1/agents                      ✅ @require_jwt + @require_session
GET    /api/v1/agents/{id}                 ✅ @require_jwt + @require_session
PUT    /api/v1/agents/{id}                 ✅ @require_jwt + @require_session
POST   /api/v1/agents/{id}/deactivate      ✅ @require_jwt + @require_session
POST   /api/v1/agents/{id}/reactivate      ✅ @require_jwt + @require_session
GET    /api/v1/agents/{id}/properties      ✅ @require_jwt + @require_session
POST   /api/v1/agents/{id}/commission-rules ✅ @require_jwt + @require_session
GET    /api/v1/agents/{id}/commission-rules ✅ @require_jwt + @require_session
GET    /api/v1/agents/{id}/performance     ✅ @require_jwt + @require_session
GET    /api/v1/agents/ranking              ✅ @require_jwt + @require_session
```

**property_api.py** (4 endpoints):
```python
POST   /api/v1/properties           ✅ @require_jwt + @require_session
GET    /api/v1/properties/{id}      ✅ @require_jwt + @require_session
PUT    /api/v1/properties/{id}      ✅ @require_jwt + @require_session
DELETE /api/v1/properties/{id}      ✅ @require_jwt + @require_session
```

**Assignments** (2 endpoints):
```python
POST   /api/v1/assignments            ✅ @require_jwt + @require_session
GET    /api/v1/assignments/{id}       ✅ @require_jwt + @require_session
```

**Additional Endpoints Found** (6):
```python
PUT    /api/v1/commission-rules/{id}  ✅ @require_jwt + @require_session
POST   /api/v1/commission-transactions ✅ @require_jwt + @require_session
```

### Debug Logs to Remove

**File**: `18.0/extra-addons/thedevkitchen_apigateway/middleware.py`

```python
Line 159: _logger.info(f'[SESSION DEBUG] Found session_id in kwargs...')
Line 168: _logger.info(f'[SESSION DEBUG] Found session_id in JSON body...')
Line 170: _logger.warning(f'[SESSION DEBUG] Error reading JSON data...')
Line 179: _logger.info(f'[SESSION DEBUG] Using session_id from headers/cookies...')
```

### Test Credentials

**File**: `18.0/.env`

```bash
# OAuth 2.0 Credentials
OAUTH_CLIENT_ID=<see .env file>
OAUTH_CLIENT_SECRET=<see .env file>

# Test Users
TEST_USER_A_EMAIL=<see .env file>
TEST_USER_A_PASSWORD=<see .env file>

TEST_USER_B_EMAIL=<see .env file>
TEST_USER_B_PASSWORD=<see .env file>

# Odoo Base URL
ODOO_BASE_URL=http://localhost:8069
```

> **⚠️ Note**: Real OAuth credentials, test user email addresses, and passwords are stored in the `18.0/.env` file. For security reasons, they are not exposed in this documentation. Always retrieve actual values from the `.env` file or your secure credential management system.

---

## ✅ Updated Implementation Checklist

### Phase 1: Code Quality (1-2 hours)
- [ ] Remove 4 debug log lines from middleware.py
- [ ] Add session_id length validation (60-100 chars)
- [ ] Improve error messages for invalid session format
- [ ] Add docstrings documenting User-Agent requirement

### Phase 2: Postman Collection (3-4 hours)
- [ ] Investigate why collection file is empty
- [ ] Restore/recreate Postman collection
- [ ] Add session_id parameter to all 23 endpoint requests
- [ ] Fix login script to capture from body (not cookies)
- [ ] Test all endpoints manually

### Phase 3: Documentation (2-3 hours)
- [ ] Create API authentication guide
- [ ] Document User-Agent consistency requirement
- [ ] Create troubleshooting guide for session issues
- [ ] Update IMPLEMENTATION_STATUS.md

### Phase 4: Testing (2-3 hours)
- [ ] Validate all decorators work correctly
- [ ] Create E2E test for Agents domain
- [ ] Create E2E test for Properties domain
- [ ] Create E2E test for Assignments domain
- [ ] Create E2E test for Commissions domain
- [ ] Create E2E test for Performance domain
- [ ] Test session hijacking prevention

### Phase 5: Validation (1 hour)
- [ ] Run all tests
- [ ] Manual Postman testing
- [ ] Code review
- [ ] Git commit and push

**Total Time**: ~9-13 hours (1-2 days)

---

## 🚀 Quick Start

To begin implementation:

```bash
# 1. Ensure you're on the right branch
git checkout 002-dual-auth-remaining-endpoints

# 2. Start with code quality (quickest win)
# Remove debug logs from middleware.py

# 3. Then tackle Postman collection
# Investigate why file is empty and restore/recreate

# 4. Add documentation
# Create authentication guide

# 5. Finally, add tests
# Create E2E tests for each domain
```

---

## 📚 Related Documents

- **Spec 001**: [Bearer Token Validation](../001-bearer-token-validation/) - Reference implementation
- **ADR-011**: [Controller Security](../../docs/adr/ADR-011-controller-security-authentication-storage.md)
- **Middleware**: [middleware.py](../../18.0/extra-addons/thedevkitchen_apigateway/middleware.py)

---

## 💡 Key Insights

1. **Decorators Already Applied**: Previous work already secured all endpoints
2. **Reduced Scope**: Main work is now documentation and testing
3. **Postman Issue**: Collection file is empty - needs investigation
4. **Quick Wins**: Debug log removal can be done immediately
5. **Testing Focus**: Since decorators exist, focus on validation tests

---

## 📞 Questions?

- Check [spec.md](spec.md) for detailed requirements
- See [research.md](research.md) for endpoint inventory
- Review [plan.md](plan.md) for implementation strategy
