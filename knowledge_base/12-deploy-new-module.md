# Deploy de Novo Módulo em Produção

## Regra Obrigatória

**Todo novo módulo (`extra-addons/<nome>/`) criado no projeto DEVE ser adicionado à variável `ODOO_INIT_MODULES` antes do deploy.**

Se o módulo não estiver nessa lista, o `odoo-init` não irá instalá-lo — o código existirá no disco e no container, mas ficará com `state = uninstalled` no banco. As rotas, models e dados do módulo não estarão disponíveis.

---

## Onde configurar

**São obrigatórias alterações em DOIS arquivos:**

### 1. `18.0/docker-compose-production.yml`

```yaml
ODOO_INIT_MODULES: ${ODOO_INIT_MODULES:-modulo_a,modulo_b,novo_modulo}
```

Este é o valor que o Dokploy injeta como variável de ambiente no container `odoo-init`. **É o arquivo que efetivamente controla o deploy em produção.**

### 2. `18.0/odoo-init.sh`

```bash
MODULES="${ODOO_INIT_MODULES:-modulo_a,modulo_b,novo_modulo}"
```

Este é o fallback usado quando `ODOO_INIT_MODULES` não está definido como variável de ambiente (ex: execução local ou manual). Deve sempre estar em sincronia com o compose.

> ⚠️ **Erro clássico:** adicionar o módulo apenas no `odoo-init.sh` e esquecer o `docker-compose-production.yml`. O compose tem precedência — se `ODOO_INIT_MODULES` está definido nele, o valor do `.sh` é ignorado em produção.

O `odoo-init.sh` usa essa variável para decidir quais módulos instalar (`-i`) ou atualizar (`--update`) durante o deploy:

- **Banco novo (primeira instalação):** executa `-i <MODULES>`
- **Banco existente (redeploy):** executa `--update <MODULES>`

Módulos **ausentes** da lista não recebem `--update` → alterações de model, data e controllers não são aplicadas.

---

## Checklist ao criar um novo módulo

- [ ] Criar o diretório em `18.0/extra-addons/<nome_modulo>/`
- [ ] Criar `__manifest__.py` com `name`, `version`, `depends`
- [ ] **Adicionar o nome do módulo em `ODOO_INIT_MODULES`** no `18.0/docker-compose-production.yml`
- [ ] **Adicionar o nome do módulo no fallback de `MODULES`** no `18.0/odoo-init.sh`
- [ ] Respeitar a ordem de dependências: módulos base antes dos que dependem deles
- [ ] Fazer commit das **três** alterações juntas no mesmo PR (`__manifest__.py`, compose e `.sh`)
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

| Módulo                              | Descrição                                        |
| ----------------------------------- | ------------------------------------------------ |
| `auditlog`                          | Auditoria de acessos e alterações (OCA)          |
| `thedevkitchen_branding`            | Customização de marca                            |
| `thedevkitchen_observability`       | Tracing distribuído via OpenTelemetry            |
| `thedevkitchen_apigateway`          | Autenticação JWT + OAuth2                        |
| `thedevkitchen_user_onboarding`     | Onboarding de usuários                           |
| `quicksol_estate`                   | Core do sistema imobiliário                      |
| `thedevkitchen_estate_credit_check` | Análise de crédito                               |
| `thedevkitchen_estate_goals`        | Metas e resultados (adicionado em 019)           |
| `thedevkitchen_cms`                 | CMS (adicionado em 021)                          |

> A ordem da tabela acima reflete a ordem de instalação em `ODOO_INIT_MODULES` — módulos base primeiro, dependentes depois.
