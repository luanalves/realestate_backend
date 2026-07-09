---
name: odoo-module-security
description: "Use when configuring Odoo module security (ir.model.access.csv, menuitem groups, res.groups hierarchy) for thedevkitchen_* modules that extend quicksol_estate, or when a menu isn't visible or an access-denied error shows up. Triggers: menu not visible, menu não aparece, access error, access denied, acesso negado, grupo, group, ir.model.access, menuitem, groups, group_real_estate_user, group_real_estate_owner, group_real_estate_manager, group_real_estate_agent, perfil, profile, RBAC, security, segurança, permissão, permission, ir.ui.menu, parent menu, app separado."
---

# Odoo Module Security — thedevkitchen Modules

> **Always consult** when creating a new `thedevkitchen_*` module or debugging access errors / invisible menus.

## The Problem

The project's 9 RBAC profiles use **separate** groups in `quicksol_estate`:

| XML ID | Display Name | Level |
|--------|-------------|-------|
| `group_real_estate_owner` | Real Estate Owner | Administrative |
| `group_real_estate_manager` | Real Estate Company Manager | Administrative |
| `group_real_estate_director` | Real Estate Director | Administrative |
| `group_real_estate_agent` | Real Estate Agent | Operational |
| `group_real_estate_financial` | Real Estate Financial | Operational |
| `group_real_estate_legal` | Real Estate Legal | Operational |
| `group_real_estate_receptionist` | Real Estate Receptionist | Operational |
| `group_real_estate_prospector` | Real Estate Prospector | Operational |
| `group_real_estate_portal_user` | Real Estate Portal User | External |
| `group_real_estate_user` | Real Estate User | Base (legacy) |

**⚠️ CRITICAL**: `group_real_estate_owner`/`manager`/`agent` **do NOT imply** `group_real_estate_user`.
They are sibling groups with no inheritance relationship. A seed user in `group_real_estate_owner` **does not have** access to models that only list `group_real_estate_user`.

---

## Rule 1 — `ir.model.access.csv`

Every `thedevkitchen_*` module that exposes models to RE users must include **all operational groups** in the CSV.

### Required Template

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
# --- Base group (legacy) ---
access_<model>_user,User: <Label>,model_<model>,quicksol_estate.group_real_estate_user,1,1,1,1
# --- Administrative profiles ---
access_<model>_owner,Owner: <Label>,model_<model>,quicksol_estate.group_real_estate_owner,1,1,1,1
access_<model>_manager,Manager: <Label>,model_<model>,quicksol_estate.group_real_estate_manager,1,1,1,1
access_<model>_director,Director: <Label>,model_<model>,quicksol_estate.group_real_estate_director,1,1,1,1
# --- Operational profiles ---
access_<model>_agent,Agent: <Label>,model_<model>,quicksol_estate.group_real_estate_agent,1,1,1,1
access_<model>_financial,Financial: <Label>,model_<model>,quicksol_estate.group_real_estate_financial,1,1,1,1
access_<model>_receptionist,Receptionist: <Label>,model_<model>,quicksol_estate.group_real_estate_receptionist,1,1,1,1
# --- Odoo Admin ---
access_<model>_admin,Admin: <Label>,model_<model>,base.group_system,1,1,1,1
```

### Permissions by Profile (CMS module as reference pattern)

| Profile | read | write | create | unlink |
|--------|------|-------|--------|--------|
| owner, manager, director | 1 | 1 | 1 | 1 |
| agent, financial, receptionist | 1 | 1 | 1 | 1* |
| portal_user | 0 | 0 | 0 | 0 |
| base.group_system | 1 | 1 | 1 | 1 |

> *Fine-grained RBAC (who can delete, publish, etc.) is the **controller's** responsibility via `resolve_role()`. The CSV only opens ORM-level access.

### Singleton models (no delete)

For config-like models (singleton per company), use `perm_unlink=0` for everyone except `base.group_system`.

---

## Rule 2 — `*_menus.xml` (`menuitem`)

### ✅ Correct — menu nested under the Real Estate app

```xml
<menuitem
    id="menu_<module>_root"
    name="<Module Name>"
    parent="quicksol_estate.menu_real_estate_root"
    sequence="90"
    groups="quicksol_estate.group_real_estate_user,quicksol_estate.group_real_estate_owner,quicksol_estate.group_real_estate_manager,quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_director,quicksol_estate.group_real_estate_financial,quicksol_estate.group_real_estate_receptionist"
/>
```

### ❌ Wrong — menu without a parent

```xml
<!-- No parent → becomes a separate app in the launcher, invisible in the RE bar -->
<menuitem
    id="menu_<module>_root"
    name="<Module Name>"
    sequence="90"
    groups="quicksol_estate.group_real_estate_user"
/>
```

### ❌ Wrong — only `group_real_estate_user`

```xml
<!-- owners/managers/agents do NOT have group_real_estate_user → menu hidden -->
<menuitem groups="quicksol_estate.group_real_estate_user" />
```

---

## Rule 3 — Group Hierarchy (`res.groups`)

In `quicksol_estate`, the RBAC groups are **flat** (no inheritance between them):

```
group_real_estate_owner  ─┐
group_real_estate_manager ─┤─ do NOT imply ──► group_real_estate_user
group_real_estate_agent  ─┘
```

To make a group inherit from another, declare `implied_ids` in the XML:

```xml
<!-- IN quicksol_estate/security/groups.xml -->
<record id="group_real_estate_owner" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
</record>
```

> ⚠️ Modifying `quicksol_estate` requires upgrading every dependent module. Prefer **listing all groups explicitly** in each child module's `ir.model.access.csv` and `menuitem groups`.

---

## Rule 4 — Upgrade After Security Changes

Any change to `ir.model.access.csv`, `groups.xml`, or `*_menus.xml` **requires a module upgrade**:

```bash
# Stop the container to avoid a DB lock
docker compose stop odoo

# Run the upgrade
docker compose run --rm odoo odoo -u <module_name> -d realestate --stop-after-init --log-level=warn

# Restart
docker compose up -d odoo
```

### Verify it applied in the database

```bash
# Check access rules
docker exec db psql -U odoo -d realestate -tAc "
SELECT ima.name FROM ir_model_access ima
JOIN ir_model m ON m.id=ima.model_id
WHERE m.model='<model.name>'
ORDER BY ima.name;"

# Check menu groups
docker exec db psql -U odoo -d realestate -tAc "
SELECT count(*) FROM ir_ui_menu_group_rel mgr
JOIN ir_ui_menu m ON m.id=mgr.menu_id
WHERE m.name::text LIKE '%<MenuName>%' AND m.parent_id IS NULL;"
```

---

## Checklist for a New `thedevkitchen_*` Module

- [ ] `ir.model.access.csv` includes the 8 RE groups + `base.group_system`
- [ ] Root `menuitem` has `parent="quicksol_estate.menu_real_estate_root"`
- [ ] Root `menuitem` has all RE groups in the `groups` attribute
- [ ] Module upgraded after any security change
- [ ] Tested with `owner@seed.com.br` (`group_real_estate_owner`)
- [ ] Tested with `manager@seed.com.br` (`group_real_estate_manager`)
- [ ] Tested with `agent@seed.com.br` (`group_real_estate_agent`)

---

## References

- `docs/adr/ADR-019-rbac-perfis-acesso-multi-tenancy.md`
- `docs/adr/ADR-001-development-guidelines-for-odoo-screens.md`
- `docs/adr/ADR-008-api-security-multi-tenancy.md`
- Implemented example: `18.0/extra-addons/thedevkitchen_cms/security/ir.model.access.csv`
- Implemented example: `18.0/extra-addons/thedevkitchen_cms/views/cms_menus.xml`

## Related Skills

- `development-best-practices` — naming/security decorator conventions for the controllers behind these models
