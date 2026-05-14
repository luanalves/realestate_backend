# Deploy de Novo Módulo em Produção

## Regra Obrigatória

**Todo novo módulo (`extra-addons/<nome>/`) criado no projeto DEVE ser adicionado à variável `ODOO_INIT_MODULES` antes do deploy.**

Se o módulo não estiver nessa lista, o `odoo-init` não irá instalá-lo — o código existirá no disco e no container, mas ficará com `state = uninstalled` no banco. As rotas, models e dados do módulo não estarão disponíveis.

---

## Onde configurar

**Arquivo:** `18.0/docker-compose-production.yml`

```yaml
ODOO_INIT_MODULES: ${ODOO_INIT_MODULES:-modulo_a,modulo_b,novo_modulo}
```

O `odoo-init.sh` usa essa variável para decidir quais módulos instalar (`-i`) ou atualizar (`--update`) durante o deploy:

- **Banco novo (primeira instalação):** executa `-i <MODULES>`
- **Banco existente (redeploy):** executa `--update <MODULES>`

Módulos **ausentes** da lista não recebem `--update` → alterações de model, data e controllers não são aplicadas.

---

## Checklist ao criar um novo módulo

- [ ] Criar o diretório em `18.0/extra-addons/<nome_modulo>/`
- [ ] Criar `__manifest__.py` com `name`, `version`, `depends`
- [ ] **Adicionar o nome do módulo em `ODOO_INIT_MODULES`** no `docker-compose-production.yml`
- [ ] Fazer commit das duas alterações juntas no mesmo PR
- [ ] Após redeploy, confirmar `state = installed` no banco:
  ```sql
  SELECT name, state, latest_version FROM ir_module_module WHERE name = 'nome_modulo';
  ```

---

## Diagnóstico rápido ("módulo não refletiu no deploy")

```bash
# 1. Verificar se o módulo está montado no container
docker exec <odoo-container> ls /mnt/extra-addons/ | grep <nome>

# 2. Verificar o state no banco
docker exec <db-container> psql -U <user> -d <db> -c \
  "SELECT name, state FROM ir_module_module WHERE name = '<nome>';"

# 3. Verificar a variável ODOO_INIT_MODULES no compose em uso
grep ODOO_INIT_MODULES docker-compose-production.yml
```

Se `state = uninstalled` → módulo não está em `ODOO_INIT_MODULES`. Adicionar, commitar e fazer redeploy pelo Dokploy.

---

## Módulos ativos atualmente (produção)

| Módulo                              | Descrição                              |
| ----------------------------------- | -------------------------------------- |
| `quicksol_estate`                   | Core do sistema imobiliário            |
| `thedevkitchen_branding`            | Customização de marca                  |
| `thedevkitchen_apigateway`          | Autenticação JWT + OAuth2              |
| `thedevkitchen_user_onboarding`     | Onboarding de usuários                 |
| `thedevkitchen_estate_credit_check` | Análise de crédito                     |
| `thedevkitchen_estate_goals`        | Metas e resultados (adicionado em 019) |
