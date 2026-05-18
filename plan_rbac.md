# Plano RBAC - Regras Seguras Para Frontend

## Objetivo

Criar uma camada segura para expor ao frontend quais menus, rotas e acoes o usuario logado pode visualizar ou acionar, sem revelar detalhes internos de seguranca do Odoo.

Este plano cobre somente a exposicao controlada de autorizacao para UX. A autorizacao real deve continuar sendo aplicada no backend por decorators, record rules, validacoes de dominio e regras especificas de negocio.

## Decisao Atual

O frontend deve usar CASL (`@casl/ability` e `@casl/react`) para avaliar permissoes na interface. Portanto, o backend deve retornar regras seguras no formato de produto, orientadas a `action` e `subject`.

Nao implementar o contrato inicial de booleanos como fonte principal:

```json
{
  "capabilities": {
    "properties.view": true
  }
}
```

O contrato alvo deve ser:

```json
{
  "rules": [
    { "action": "view", "subject": "Property" },
    { "action": "create", "subject": "Property" }
  ]
}
```

Essas regras sao "CASL-safe": descrevem capacidades de produto, nao detalhes internos do Odoo.

## Contexto Atual

O backend ja possui uma base de seguranca com:

- autenticacao JWT para a aplicacao;
- sessao para identificar o usuario logado;
- isolamento por empresa via `@require_company`;
- perfis RBAC do modulo `quicksol_estate`;
- regras de acesso Odoo por grupos e record rules;
- validacoes especificas em controllers e helpers.

Tambem existe o endpoint `GET /api/v1/me`, que retorna dados basicos do usuario logado, como `role`, empresas e `is_admin`.

O que ainda falta e uma representacao segura e padronizada das regras de UI do usuario para o frontend.

## Principio de Seguranca

O frontend nao deve receber:

- XML IDs de grupos Odoo;
- record rules;
- domains Odoo;
- nomes internos de models sensiveis;
- detalhes tecnicos de por que uma regra permitiu ou negou acesso;
- regras condicionais completas, como dominios baseados em `company_id`, `agent_id` ou `user_id`.

O frontend deve receber apenas regras de produto:

```json
{
  "action": "view",
  "subject": "Property"
}
```

Essas regras servem para montar a interface. Elas nao substituem seguranca backend.

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
- substituicao das validacoes atuais dos endpoints;
- regras condicionais CASL com campos sensiveis do backend.

## Endpoint Proposto

Criar um novo endpoint:

```http
GET /api/v1/me/capabilities
```

Manter o nome `capabilities` para clareza de produto, mas a resposta deve usar `rules` para integrar com CASL no frontend.

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
  "rules": [
    { "action": "view", "subject": "MenuCRM" },
    { "action": "view", "subject": "Dashboard" },

    { "action": "view", "subject": "Property" },
    { "action": "create", "subject": "Property" },
    { "action": "update", "subject": "Property" },

    { "action": "view", "subject": "Lead" },
    { "action": "create", "subject": "Lead" },
    { "action": "update", "subject": "Lead" },

    { "action": "view", "subject": "Service" },
    { "action": "create", "subject": "Service" },
    { "action": "update", "subject": "Service" },

    { "action": "view", "subject": "Proposal" },
    { "action": "create", "subject": "Proposal" },

    { "action": "view", "subject": "Settings" }
  ]
}
```

Para acoes negadas, preferir omitir a regra. O CASL deve interpretar ausencia de regra como negado.

## Subjects e Actions Iniciais

Subjects de menu:

```text
MenuCRM
MenuAdmin
MenuCMS
```

Subjects de dominio:

```text
Dashboard
Property
Lead
Service
Proposal
Agent
Company
Settings
Appointment
Report
Goal
CMSPage
CMSMedia
```

Actions iniciais:

```text
view
create
update
delete
reassign
approve
cancel
export
manage
```

Usar `manage` com parcimonia. Prefira actions explicitas quando o frontend precisa distinguir botoes ou rotas.

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
- mapear perfis para regras CASL-safe de produto;
- retornar somente a whitelist de regras permitidas para exposicao;
- centralizar a logica usada pelo endpoint `/api/v1/me/capabilities`.

Importante: o servico deve ser declarativo e conservador. Se houver duvida, nao retornar a regra.

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
ROLE_RULES = {
    "owner": [
        {"action": "view", "subject": "MenuCRM"},
        {"action": "view", "subject": "MenuAdmin"},
        {"action": "manage", "subject": "Property"},
        {"action": "manage", "subject": "Agent"},
        {"action": "view", "subject": "Company"},
        {"action": "update", "subject": "Company"},
    ],
    "agent": [
        {"action": "view", "subject": "MenuCRM"},
        {"action": "view", "subject": "Dashboard"},
        {"action": "view", "subject": "Property"},
        {"action": "create", "subject": "Property"},
        {"action": "update", "subject": "Property"},
        {"action": "view", "subject": "Lead"},
        {"action": "create", "subject": "Lead"},
        {"action": "update", "subject": "Lead"},
    ],
}
```

## Menus

As regras de menu devem ser explicitas:

```json
{ "action": "view", "subject": "MenuCRM" }
{ "action": "view", "subject": "MenuAdmin" }
{ "action": "view", "subject": "MenuCMS" }
```

Submenus podem usar regras do dominio:

```json
{ "action": "view", "subject": "Property" }
{ "action": "view", "subject": "Lead" }
{ "action": "view", "subject": "Service" }
{ "action": "view", "subject": "Proposal" }
{ "action": "view", "subject": "Agent" }
{ "action": "view", "subject": "Company" }
```

O frontend deve filtrar itens de menu usando CASL, sem depender de `role`, `is_admin` ou nome tecnico de grupo.

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

As regras devem ser calculadas para a empresa ativa da sessao/request.

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

Se futuramente houver troca de empresa no frontend, as regras devem ser recarregadas apos a troca.

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

Nesta primeira fase, o frontend pode buscar as regras no login e ao recarregar a aplicacao. O cache HTTP/fetch deve ficar no frontend com TanStack Query.

## Integracao Frontend Esperada

O frontend deve usar:

```text
@casl/ability
@casl/react
@tanstack/react-query
```

Fluxo esperado:

```text
/api/v1/me/capabilities
        |
        v
TanStack Query cacheia a resposta
        |
        v
Adapter monta Ability CASL com as rules
        |
        v
AbilityProvider disponibiliza ability
        |
        v
Menus, rotas e botoes usam ability.can()
```

Exemplos no frontend:

```ts
ability.can("view", "MenuAdmin")
ability.can("create", "Property")
ability.can("reassign", "Service")
```

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
- owner recebe regra para `view MenuAdmin`;
- agent nao recebe regra para `view MenuAdmin`;
- manager recebe regras gerenciais;
- ausencia de regra equivale a acesso negado;
- nenhuma resposta contem XML IDs de grupos Odoo;
- nenhuma resposta contem record rules ou domains.

Frontend, quando implementado:

- menu admin fica oculto para agent;
- propriedades aparece para quem tem `view Property`;
- botao de criar propriedade aparece somente com `create Property`;
- acesso direto por URL a rota sem regra redireciona ou exibe tela de acesso negado;
- endpoint protegido continua retornando `403` mesmo se a UI for manipulada manualmente.

## Criterios de Aceite

- Existe `GET /api/v1/me/capabilities`.
- O endpoint exige JWT, sessao e empresa.
- A resposta expoe `rules` CASL-safe.
- O backend nao vaza grupos tecnicos, domains ou record rules.
- Acoes negadas nao sao retornadas como detalhes tecnicos.
- O frontend consegue montar menus usando CASL, sem usar `role` diretamente.
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
frontend/plan_rbac.md
frontend/src/config/api.ts
frontend/src/lib/auth.ts
frontend/src/services/authService.ts
frontend/src/permissions/
frontend/src/components/crm/DashboardLayout.tsx
frontend/src/App.tsx
```

## Observacao Final

Este plano melhora a transparencia e a experiencia de uso, mas nao deve ser tratado como mecanismo de autorizacao final.

A regra de ouro e:

```text
Frontend usa CASL para UX.
Backend usa RBAC, record rules e validacoes para seguranca.
```
