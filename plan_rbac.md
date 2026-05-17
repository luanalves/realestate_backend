# Plano RBAC - Capacidades do Usuario Logado

## Objetivo

Criar uma camada segura para expor ao frontend quais menus, rotas e acoes o usuario logado pode visualizar ou acionar, sem revelar detalhes internos de seguranca do Odoo.

Este plano cobre somente a exposicao controlada de capacidades para UX. A autorizacao real deve continuar sendo aplicada nos endpoints backend por decorators, record rules, validacoes de dominio e regras especificas de negocio.

## Contexto Atual

O backend ja possui uma base de seguranca com:

- autenticacao JWT para a aplicacao;
- sessao para identificar o usuario logado;
- isolamento por empresa via `@require_company`;
- perfis RBAC do modulo `quicksol_estate`;
- regras de acesso Odoo por grupos e record rules;
- validacoes especificas em controllers e helpers.

Tambem existe o endpoint `GET /api/v1/me`, que retorna dados basicos do usuario logado, como `role`, empresas e `is_admin`.

O que ainda falta e uma representacao segura e padronizada das capacidades do usuario para o frontend.

## Principio de Seguranca

O frontend nao deve receber:

- XML IDs de grupos Odoo;
- record rules;
- domains Odoo;
- nomes internos de models sensiveis;
- detalhes tecnicos de por que uma regra permitiu ou negou acesso;
- regras condicionais completas, como dominios baseados em `company_id`, `agent_id` ou `user_id`.

O frontend deve receber apenas capacidades de produto, em formato simples:

```json
{
  "capabilities": {
    "menu.crm": true,
    "menu.admin": false,
    "properties.view": true,
    "properties.create": true,
    "properties.delete": false
  }
}
```

Essas capacidades servem para montar a interface. Elas nao substituem seguranca backend.

## Escopo Inicial

Neste primeiro momento, o objetivo e permitir que o frontend controle:

- menus principais;
- submenus;
- rotas visiveis;
- botoes de acao;
- acoes contextuais em telas.

Fora do escopo inicial:

- tela publica "Minhas permissoes";
- explicacao detalhada de negacao;
- alteracao dinamica de regras pelo usuario;
- exposicao de permissoes tecnicas;
- substituicao das validacoes atuais dos endpoints.

## Endpoint Proposto

Criar um novo endpoint:

```http
GET /api/v1/me/capabilities
```

Decorators obrigatorios:

```python
@require_jwt
@require_session
@require_company
```

Resposta sugerida:

```json
{
  "user": {
    "id": 42,
    "role": "agent",
    "company_id": 5
  },
  "capabilities": {
    "menu.crm": true,
    "menu.admin": false,
    "menu.cms": false,

    "dashboard.view": true,

    "properties.view": true,
    "properties.create": true,
    "properties.update": true,
    "properties.delete": false,

    "leads.view": true,
    "leads.create": true,
    "leads.update": true,
    "leads.delete": false,

    "services.view": true,
    "services.create": true,
    "services.update": true,
    "services.reassign": false,

    "proposals.view": true,
    "proposals.create": true,
    "proposals.approve": false,

    "agents.view": false,
    "agents.create": false,
    "agents.update": false,

    "companies.view": false,
    "companies.update": false,

    "settings.view": true
  }
}
```

## Servico Backend

Criar um servico dedicado, por exemplo:

```text
quicksol_estate/services/capability_service.py
```

Classe sugerida:

```text
UserCapabilityService
```

Responsabilidades:

- receber `env`, `user` e empresa ativa;
- identificar o papel seguro do usuario;
- mapear perfis para capacidades de produto;
- retornar somente a whitelist de capacidades permitidas para exposicao;
- centralizar a logica usada pelo endpoint `/api/v1/me/capabilities`.

Importante: o servico deve ser declarativo e conservador. Se houver duvida, a capacidade deve ser `false`.

## Mapeamento Inicial Fixo

Neste primeiro momento, usar um mapeamento fixo por perfil.

Perfis conhecidos:

- `owner`
- `director`
- `manager`
- `agent`
- `prospector`
- `receptionist`
- `financial`
- `legal`
- `property_owner`
- `tenant`

O endpoint `/api/v1/me` ja possui um `role_map`. A implementacao pode reutilizar a mesma ideia, mas deve evitar duplicacao excessiva no longo prazo.

Exemplo conceitual:

```python
ROLE_CAPABILITIES = {
    "owner": {
        "menu.crm": True,
        "menu.admin": True,
        "properties.view": True,
        "properties.create": True,
        "properties.update": True,
        "properties.delete": True,
        "agents.view": True,
        "agents.create": True,
    },
    "agent": {
        "menu.crm": True,
        "menu.admin": False,
        "properties.view": True,
        "properties.create": True,
        "properties.update": True,
        "properties.delete": False,
        "agents.view": False,
        "agents.create": False,
    },
}
```

Todas as capacidades conhecidas devem existir na resposta final, mesmo quando `false`. Isso simplifica o frontend e evita comportamento ambiguo.

## Menus

As capacidades de menu devem ser explicitas:

```text
menu.crm
menu.admin
menu.cms
```

Submenus podem usar capacidades do dominio:

```text
properties.view
leads.view
services.view
proposals.view
agents.view
companies.view
settings.view
```

O frontend deve filtrar itens de menu usando essas chaves, sem depender de `role`, `is_admin` ou nome tecnico de grupo.

## Relacao Com Seguranca Real

Este endpoint e somente uma camada de UX.

Mesmo que o frontend esconda um menu ou botao, o backend deve continuar validando:

- JWT valido;
- sessao valida;
- empresa ativa;
- permissao Odoo;
- record rules;
- regras especificas do dominio;
- ownership/assignment quando aplicavel.

Nenhum controller existente deve remover validacoes por causa deste endpoint.

## Multiempresa

As capacidades devem ser calculadas para a empresa ativa da sessao/request.

Um usuario pode ter papeis ou escopos diferentes em empresas diferentes. Portanto, a resposta deve incluir a empresa considerada:

```json
{
  "user": {
    "id": 42,
    "role": "manager",
    "company_id": 5
  }
}
```

Se futuramente houver troca de empresa no frontend, as capacidades devem ser recarregadas apos a troca.

## Cache e Invalidador Futuro

Nao implementar obrigatoriamente nesta primeira etapa, mas deixar preparado para evoluir.

Campo futuro:

```json
{
  "permissions_hash": "sha256:...",
  "permissions_version": "2026-05-17T14:20:00Z"
}
```

Uso futuro:

- detectar mudanca de perfil;
- invalidar cache frontend;
- evitar menu stale apos alteracao de grupo;
- permitir ETag ou conditional request.

Nesta primeira fase, o frontend pode buscar as capacidades no login e ao recarregar a aplicacao.

## Integracao Frontend Esperada

O frontend deve criar uma camada equivalente a:

```text
PermissionsProvider
can(capability: string): boolean
```

Exemplo:

```ts
can("properties.create")
can("menu.admin")
can("services.reassign")
```

Os menus devem declarar a capacidade necessaria:

```ts
{
  label: "Propriedades",
  href: "/properties",
  capability: "properties.view"
}
```

Se `can(item.capability)` for `false`, o item nao aparece.

## Tratamento de Erros

Se o endpoint falhar:

- o frontend deve assumir permissao minima;
- menus sensiveis nao devem ser exibidos;
- a sessao pode ser revalidada chamando `/api/v1/me`;
- em caso de `401` ou `403`, realizar logout ou redirecionar para login conforme padrao atual.

No backend, erros internos nao devem retornar detalhes de grupos, regras ou stack trace.

## Testes Recomendados

Backend:

- usuario sem sessao recebe `401`;
- usuario sem JWT recebe `401`;
- usuario sem company valida recebe `403`;
- owner recebe capacidades administrativas;
- manager recebe capacidades gerenciais;
- agent nao recebe menu admin nem acoes administrativas;
- todas as chaves conhecidas aparecem na resposta;
- nenhuma resposta contem XML IDs de grupos Odoo;
- nenhuma resposta contem record rules ou domains.

Frontend, quando implementado:

- menu admin fica oculto para agent;
- propriedades aparece para quem tem `properties.view`;
- botao de criar propriedade aparece somente com `properties.create`;
- acesso direto por URL a rota sem capacidade redireciona ou exibe tela de acesso negado;
- endpoint protegido continua retornando `403` mesmo se a UI for manipulada manualmente.

## Criterios de Aceite

- Existe `GET /api/v1/me/capabilities`.
- O endpoint exige JWT, sessao e empresa.
- A resposta expoe apenas capacidades seguras de produto.
- O backend nao vaza grupos tecnicos, domains ou record rules.
- Todas as capacidades conhecidas sao retornadas como boolean.
- O frontend consegue montar menus sem usar `role` diretamente.
- Nenhuma validacao de seguranca existente e removida.

## Arquivos Provaveis

Backend:

```text
18.0/extra-addons/thedevkitchen_apigateway/controllers/me_controller.py
18.0/extra-addons/quicksol_estate/services/capability_service.py
18.0/extra-addons/quicksol_estate/services/__init__.py
18.0/extra-addons/quicksol_estate/tests/
```

Frontend, em etapa posterior:

```text
frontend/src/config/api.ts
frontend/src/lib/auth.ts
frontend/src/services/authService.ts
frontend/src/components/crm/DashboardLayout.tsx
```

## Observacao Final

Este plano melhora a transparencia e a experiencia de uso, mas nao deve ser tratado como mecanismo de autorizacao final.

A regra de ouro e:

```text
Frontend usa capabilities para UX.
Backend usa RBAC, record rules e validacoes para seguranca.
```
