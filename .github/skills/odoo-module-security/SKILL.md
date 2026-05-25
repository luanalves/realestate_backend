---
name: odoo-module-security
description: "Configure Odoo module security (ir.model.access.csv, menuitem groups, res.groups hierarchy) for thedevkitchen modules that extend quicksol_estate. TRIGGER KEYWORDS: menu not visible, menu não aparece, access error, access denied, acesso negado, grupo, group, ir.model.access, menuitem, groups, group_real_estate_user, group_real_estate_owner, group_real_estate_manager, group_real_estate_agent, perfil, profile, RBAC, security, segurança, permissão, permission, ir.ui.menu, parent menu, app separado. COVERS: (1) ir.model.access.csv must include ALL 9 RBAC groups, (2) menuitem must be nested under Real Estate app with all role groups, (3) res.groups hierarchy — role groups do NOT imply group_real_estate_user, (4) checklist for new thedevkitchen modules. USE WHEN: creating new thedevkitchen_ modules, debugging menu visibility, fixing access errors in Odoo UI."
---

# Odoo Module Security — thedevkitchen Modules

> **Consultar sempre** ao criar um novo módulo `thedevkitchen_*` ou ao debugar erros de acesso/menu invisível.

## Contexto do Problema

Os 9 perfis RBAC do projeto usam grupos **separados** em `quicksol_estate`:

| XML ID | Display Name | Nível |
|--------|-------------|-------|
| `group_real_estate_owner` | Real Estate Owner | Administrativo |
| `group_real_estate_manager` | Real Estate Company Manager | Administrativo |
| `group_real_estate_director` | Real Estate Director | Administrativo |
| `group_real_estate_agent` | Real Estate Agent | Operacional |
| `group_real_estate_financial` | Real Estate Financial | Operacional |
| `group_real_estate_legal` | Real Estate Legal | Operacional |
| `group_real_estate_receptionist` | Real Estate Receptionist | Operacional |
| `group_real_estate_prospector` | Real Estate Prospector | Operacional |
| `group_real_estate_portal_user` | Real Estate Portal User | Externo |
| `group_real_estate_user` | Real Estate User | Base (legado) |

**⚠️ CRÍTICO**: `group_real_estate_owner/manager/agent` **NÃO implicam** `group_real_estate_user`.  
São grupos irmãos, sem relação de herança. Um seed user em `group_real_estate_owner` **não tem** acesso a modelos que só listam `group_real_estate_user`.

---

## Regra 1 — ir.model.access.csv

Todo módulo `thedevkitchen_*` que expõe models para usuários RE deve incluir **todos os grupos operacionais** no CSV.

### Template Obrigatório

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
# --- Grupo base (legado) ---
access_<model>_user,User: <Label>,model_<model>,quicksol_estate.group_real_estate_user,1,1,1,1
# --- Perfis administrativos ---
access_<model>_owner,Owner: <Label>,model_<model>,quicksol_estate.group_real_estate_owner,1,1,1,1
access_<model>_manager,Manager: <Label>,model_<model>,quicksol_estate.group_real_estate_manager,1,1,1,1
access_<model>_director,Director: <Label>,model_<model>,quicksol_estate.group_real_estate_director,1,1,1,1
# --- Perfis operacionais ---
access_<model>_agent,Agent: <Label>,model_<model>,quicksol_estate.group_real_estate_agent,1,1,1,1
access_<model>_financial,Financial: <Label>,model_<model>,quicksol_estate.group_real_estate_financial,1,1,1,1
access_<model>_receptionist,Receptionist: <Label>,model_<model>,quicksol_estate.group_real_estate_receptionist,1,1,1,1
# --- Admin Odoo ---
access_<model>_admin,Admin: <Label>,model_<model>,base.group_system,1,1,1,1
```

### Permissões por Perfil (padrão CMS como referência)

| Perfil | read | write | create | unlink |
|--------|------|-------|--------|--------|
| owner, manager, director | 1 | 1 | 1 | 1 |
| agent, financial, receptionist | 1 | 1 | 1 | 1* |
| portal_user | 0 | 0 | 0 | 0 |
| base.group_system | 1 | 1 | 1 | 1 |

> *O RBAC fino (quem pode deletar, publicar, etc.) é responsabilidade do **controller** via `resolve_role()`. O CSV apenas abre o acesso ORM.

### Singleton (sem delete)
Para models tipo configuração (singleton por empresa), usar `perm_unlink=0` para todos exceto `base.group_system`.

---

## Regra 2 — cms_menus.xml (menuitem)

### ✅ Correto — Menu aninhado no app Real Estate

```xml
<menuitem
    id="menu_<module>_root"
    name="<Module Name>"
    parent="quicksol_estate.menu_real_estate_root"
    sequence="90"
    groups="quicksol_estate.group_real_estate_user,quicksol_estate.group_real_estate_owner,quicksol_estate.group_real_estate_manager,quicksol_estate.group_real_estate_agent,quicksol_estate.group_real_estate_director,quicksol_estate.group_real_estate_financial,quicksol_estate.group_real_estate_receptionist"
/>
```

### ❌ Errado — Menu sem parent

```xml
<!-- SEM parent → vira app separado no launcher, invisível na barra RE -->
<menuitem
    id="menu_<module>_root"
    name="<Module Name>"
    sequence="90"
    groups="quicksol_estate.group_real_estate_user"
/>
```

### ❌ Errado — Apenas group_real_estate_user

```xml
<!-- owners/managers/agents NÃO têm group_real_estate_user → menu oculto -->
<menuitem groups="quicksol_estate.group_real_estate_user" />
```

---

## Regra 3 — Hierarquia de grupos (res.groups)

No `quicksol_estate`, os grupos RBAC são **planos** (sem herança entre si):

```
group_real_estate_owner  ─┐
group_real_estate_manager ─┤─ NÃO implicam ──► group_real_estate_user
group_real_estate_agent  ─┘
```

Se quiser que um grupo herde de outro, declare `implied_ids` no XML:

```xml
<!-- NO quicksol_estate/security/groups.xml -->
<record id="group_real_estate_owner" model="res.groups">
    <field name="implied_ids" eval="[(4, ref('group_real_estate_user'))]"/>
</record>
```

> ⚠️ Modificar `quicksol_estate` requer upgrade de todos os módulos dependentes. Prefira **listar todos os grupos explicitamente** no `ir.model.access.csv` e `menuitem groups` de cada módulo filho.

---

## Regra 4 — Upgrade após mudanças de segurança

Qualquer alteração em `ir.model.access.csv`, `groups.xml`, ou `*_menus.xml` **exige upgrade do módulo**:

```bash
# Parar o container para evitar lock no DB
docker compose stop odoo

# Rodar upgrade
docker compose run --rm odoo odoo -u <module_name> -d realestate --stop-after-init --log-level=warn

# Reiniciar
docker compose up -d odoo
```

### Verificar se aplicou no banco

```bash
# Verificar regras de acesso
docker exec db psql -U odoo -d realestate -tAc "
SELECT ima.name FROM ir_model_access ima
JOIN ir_model m ON m.id=ima.model_id
WHERE m.model='<model.name>'
ORDER BY ima.name;"

# Verificar grupos do menu
docker exec db psql -U odoo -d realestate -tAc "
SELECT count(*) FROM ir_ui_menu_group_rel mgr
JOIN ir_ui_menu m ON m.id=mgr.menu_id
WHERE m.name::text LIKE '%<MenuName>%' AND m.parent_id IS NULL;"
```

---

## Checklist para novo módulo thedevkitchen_*

```
[ ] ir.model.access.csv inclui os 8 grupos RE + base.group_system
[ ] menuitem root tem parent="quicksol_estate.menu_real_estate_root"
[ ] menuitem root tem todos os grupos RE no atributo groups
[ ] Módulo upgraded após qualquer mudança de segurança
[ ] Testado com owner@seed.com.br (group_real_estate_owner)
[ ] Testado com manager@seed.com.br (group_real_estate_manager)
[ ] Testado com agent@seed.com.br (group_real_estate_agent)
```

---

## Referências

- [ADR-019: RBAC Perfis de Acesso Multi-Tenancy](../../../docs/adr/ADR-019-rbac-perfis-acesso-multi-tenancy.md)
- [ADR-001: Development Guidelines for Odoo Screens](../../../docs/adr/ADR-001-development-guidelines-for-odoo-screens.md)
- [ADR-008: API Security Multi-Tenancy](../../../docs/adr/ADR-008-api-security-multi-tenancy.md)
- Exemplo implementado: `18.0/extra-addons/thedevkitchen_cms/security/ir.model.access.csv`
- Exemplo implementado: `18.0/extra-addons/thedevkitchen_cms/views/cms_menus.xml`
