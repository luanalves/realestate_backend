# Fluxo Completo de Propriedades — Spec 016

Este documento descreve como os endpoints de **Propriedades** devem ser usados depois da spec 016 — Property Mapping Fields API Completion. O foco desta spec é completar o contrato REST de propriedades para cobrir os campos mapeados da aba `Mapping_Property`, preservando os endpoints existentes, o isolamento por imobiliaria, RBAC e a documentacao dinamica do Swagger.

A propriedade continua sendo a entidade central do cadastro imobiliario. O fluxo principal e: consultar opcoes de dominio, criar ou atualizar a propriedade com os campos do formulario, consultar detalhe para confirmar persistencia e listar propriedades com schema consistente para telas, cache e integracoes.

> **Escopo:** Esta spec atua nos endpoints REST de propriedades. Ela nao altera propostas, leads, atendimentos, locacoes, vendas, ficha cadastral ou outros dominios.

---

## Mapa dos Endpoints

| Endpoint | Finalidade |
|---|---|
| `GET /api/v1/properties/options` | Retorna opcoes de campos de selecao usados pelo formulario de propriedades. |
| `GET /api/v1/property-types` | Retorna tipos de propriedade usados em `property_type_id`. |
| `GET /api/v1/properties` | Lista propriedades com paginacao, filtros e campos de mapeamento. |
| `POST /api/v1/properties` | Cria propriedade com os campos principais e campos faltantes da spec 016. |
| `GET /api/v1/properties/{id}` | Consulta detalhe completo da propriedade. |
| `PUT /api/v1/properties/{id}` | Atualiza parcialmente a propriedade sem limpar campos omitidos. |
| `DELETE /api/v1/properties/{id}` | Remove propriedade, restrito a manager/admin. |
| `GET /api/v1/agents/{id}/properties` | Lista propriedades atribuidas a um corretor. |
| `GET /api/v1/companies/{id}/properties` | Lista propriedades de uma imobiliaria especifica. |

---

## Ciclo de Uso da API

```
GET /properties/options
GET /property-types
        │
        ▼
POST /properties
        │
        ▼
GET /properties/{id}
        │
        ├── PUT /properties/{id}
        │       │
        │       ▼
        │   GET /properties/{id}
        │
        ├── GET /properties
        │
        ├── GET /agents/{id}/properties
        │
        └── GET /companies/{id}/properties
```

```
[propriedade existente]
        │
        ▼
DELETE /properties/{id}
        │
        ▼
[removida]
```

> **Obs.:** A exclusao e irreversivel no endpoint atual e exige permissao de manager/admin.

---

## Jornadas

### J1 — Cliente externo monta formulario de cadastro

Antes de criar uma propriedade, o cliente da API precisa conhecer os valores validos para selects e ids auxiliares.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `GET /api/v1/properties/options` | Recupera opcoes como status, finalidade, situacao, zoneamento e outros campos de selecao. |
| 2 | `GET /api/v1/property-types` | Recupera ids e nomes dos tipos de propriedade. |
| 3 | `GET /api/v1/amenities` | Recupera comodidades quando o formulario usar `amenities`. |
| 4 | `GET /api/v1/tags` | Recupera tags disponiveis quando o formulario usar `tag_ids` ou `tags`. |

> `properties/options` e o endpoint preferido para descobrir opcoes de campos multi-selecao/selecao da propriedade. `property-types`, `amenities` e `tags` continuam sendo master data de apoio.

---

### J2 — Criacao de propriedade com campos da spec 016

Owner, manager ou usuario autorizado cria uma propriedade preenchendo o formulario completo. O payload usa `snake_case` e pode incluir os campos adicionados pela spec 016.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `POST /api/v1/properties` | Cria a propriedade com dados principais, endereco, areas, contatos, status, publicacao, chaves, placas, comissoes e documentacao. |
| 2 | `GET /api/v1/properties/{id}` | Confirma que os valores foram persistidos e serializados no detalhe. |
| 3 | `GET /api/v1/properties` | Confirma que a listagem retorna o mesmo bloco de campos de mapeamento por item. |

Campos representativos do payload:

```json
{
  "name": "Casa Moderna em Sao Jose dos Campos",
  "property_type_id": 2,
  "company_ids": [1],
  "price": 850000,
  "rent_price": 4200,
  "area": 180.5,
  "total_area": 250,
  "private_area": 160,
  "land_area": 300,
  "num_rooms": 4,
  "num_suites": 1,
  "num_bathrooms": 3,
  "num_parking": 2,
  "owner_email": "owner@example.com",
  "owner_home_phone": "+55 12 3000-1000",
  "owner_business_phone": "+55 12 3000-2000",
  "owner_mobile_phone": "+55 12 99999-0000",
  "source_medium": "site",
  "send_activities_to_owner": true,
  "registered_by": "API",
  "alternative_reference": "ALT-2026-001",
  "intention": "sale",
  "exclusivity": true,
  "property_situation": "available",
  "key_location": "front desk",
  "advertise": true,
  "featured_property": true,
  "virtual_tour": "https://example.com/tour",
  "sign_on_site": true,
  "super_featured": false,
  "youtube_video": "https://youtube.com/watch?v=demo",
  "commission_type": "percentage",
  "included_in_commission_date": "2026-05-05",
  "commercial_condition": "Condição comercial padrão",
  "iptu_code": "IPTU-123",
  "registration_number": "MAT-12345",
  "electricity_network_code": "ENE-123",
  "water_network_code": "WAT-123",
  "approved_environmental_agency": true,
  "approved_project": true,
  "documentation_observations": "Documentacao conferida"
}
```

> Imagens (`property_images`) foram deixadas fora da validacao E2E desta entrega porque terao uma tarefa propria. Quando houver midia associada, respostas devem expor metadados, nunca binario inline.

---

### J3 — Atualizacao parcial de propriedade

O usuario altera apenas alguns campos do formulario. Campos omitidos nao devem ser apagados.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `GET /api/v1/properties/{id}` | Le estado atual antes da edicao. |
| 2 | `PUT /api/v1/properties/{id}` | Envia somente campos alterados. |
| 3 | `GET /api/v1/properties/{id}` | Confirma campos alterados e preservacao dos demais. |

Exemplo:

```json
{
  "price": 875000,
  "rent_price": 4500,
  "internal_comments": "Valor revisado pelo proprietario",
  "sign_notes": "Placa instalada na entrada principal",
  "authorization_start_date": "2026-05-05",
  "authorization_end_date": "2026-11-05"
}
```

---

### J4 — Listagem e filtros de propriedades

Tela de propriedades, integracoes e caches consomem a listagem paginada. Cada item precisa manter schema estavel para evitar consultas desnecessarias de detalhe.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `GET /api/v1/properties?company_ids=1&limit=20&offset=0` | Lista propriedades da imobiliaria com paginacao por `limit`/`offset`. |
| 2 | `GET /api/v1/properties?property_type_id=2&city=Sao Jose dos Campos` | Filtra por tipo e cidade. |
| 3 | `GET /api/v1/properties?min_price=500000&max_price=900000` | Filtra por faixa de preco. |
| 4 | `GET /api/v1/properties/{id}` | Usa detalhe apenas quando a tela precisa do cadastro completo de um item. |

> A listagem preserva links de paginacao e isolamento por `company_ids`.

---

### J5 — Consulta por corretor

Gestor ou integracao precisa ver quais propriedades estao vinculadas a um corretor.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `GET /api/v1/agents/{id}/properties` | Lista propriedades atualmente atribuidas ao corretor. |
| 2 | `GET /api/v1/agents/{id}/properties?active_only=false` | Inclui atribuicoes inativas quando suportado. |
| 3 | `GET /api/v1/properties/{property_id}` | Abre detalhe completo da propriedade retornada. |

---

### J6 — Consulta por imobiliaria

Owner/manager precisa consultar propriedades de uma imobiliaria especifica respeitando RBAC e multi-tenancy.

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `GET /api/v1/companies/{id}/properties?page=1&page_size=20` | Lista propriedades da empresa. |
| 2 | `GET /api/v1/companies/{id}/properties?property_status=available&for_sale=true` | Filtra por status e finalidade. |
| 3 | `GET /api/v1/companies/{id}/properties?order_by=price` | Ordena por campo permitido. |

> Usuario sem acesso a empresa recebe resposta anti-enumeracao equivalente a nao encontrado.

---

### J7 — Publicacao web, placas e SEO

Campos de publicacao controlam o que pode aparecer em portais, site e destaque interno.

| Area | Campos principais |
|---|---|
| Publicacao | `advertise`, `featured_property`, `super_featured`, `virtual_tour`, `youtube_video` |
| Placas | `sign_on_site`, `sign_type`, `sign_installation_date`, `sign_removal_date`, `sign_notes` |
| SEO | `meta_title`, `meta_description`, `meta_keywords`, `description_short` |

Fluxo recomendado:

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `PUT /api/v1/properties/{id}` | Atualiza flags e textos de publicacao. |
| 2 | `GET /api/v1/properties/{id}` | Confirma valores normalizados no detalhe. |
| 3 | `GET /api/v1/properties` | Confirma se a listagem expõe campos necessarios para cards/cache. |

---

### J8 — Documentacao e dados fiscais

Campos documentais ajudam a manter cadastros regulatorios e dados de concessionarias.

| Categoria | Campos |
|---|---|
| IPTU/seguro | `iptu_code`, `iptu_payment_condition`, `iptu_value`, `iptu_annual`, `insurance_value`, `fire_insurance`, `rental_guarantee_insurance` |
| Registro | `registration_number`, `titles_rights`, `approved_environmental_agency`, `approved_project` |
| Redes | `electricity_network_code`, `water_network_code` |
| Observacoes | `documentation_observations`, `internal_comments` |

| Passo | Endpoint | Descricao |
|---|---|---|
| 1 | `PUT /api/v1/properties/{id}` | Atualiza dados documentais e fiscais. |
| 2 | `GET /api/v1/properties/{id}` | Confirma persistencia. |

---

## Regras e Gates

| Regra | Detalhe |
|---|---|
| Autenticacao | Endpoints protegidos exigem JWT, sessao e contexto de empresa conforme endpoint. |
| Multi-tenancy | Usuario so pode ler/alterar propriedades de empresas permitidas. |
| RBAC | Criacao/atualizacao/exclusao preservam permissoes existentes; exclusao e manager/admin. |
| Atualizacao parcial | Campo omitido em `PUT` nao limpa valor existente. |
| Booleanos | Campos booleanos devem ser JSON boolean (`true`/`false`), nao strings ambiguas. |
| Datas | Datas usam ISO `YYYY-MM-DD`, por exemplo `included_in_commission_date`. |
| Email do proprietario | `owner_email` pode ser vazio/nulo; quando informado deve ser email valido. |
| Arrays | `tags`, `tag_ids`, `amenities`, `property_files` e campos similares devem ser arrays quando enviados. |
| Midia | Respostas retornam metadados (`id`, `name`, `mimetype`, `size`, `download_url`), nunca binario inline. |
| Empresa protegida | Payload nao pode burlar escopo de empresa/RBAC existente. |
| Erros | Validacoes devem retornar erro estruturado com campo e motivo sempre que possivel. |

---

## Cobertura dos Campos por Endpoint

| Grupo | `POST /properties` | `PUT /properties/{id}` | `GET /properties/{id}` | `GET /properties` |
|---|---:|---:|---:|---:|
| Dados principais, preco, areas e quartos | sim | sim | sim | sim |
| Contatos do proprietario | sim | sim | sim | sim |
| Status, finalidade e condicoes | sim | sim | sim | sim |
| Publicacao web, SEO e video/tour | sim | sim | sim | sim |
| Chaves e placas | sim | sim | sim | sim |
| Comissoes | sim | sim | sim | sim |
| Documentacao e redes | sim | sim | sim | sim |
| Tags/amenities | sim | parcial conforme endpoint | sim | sim |
| Imagens/arquivos | metadados/formato suportado | metadados/formato suportado | metadados | metadados |

---

## Swagger e Contrato

O Swagger nao deve conter exemplos manuais duplicados em `description`. Os exemplos de request/response devem viver em:

| Tipo | Origem |
|---|---|
| Request body | `request_schema` no XML do endpoint |
| Response body | `response_schema` no XML do endpoint |
| UI `/api/docs` | Gerada dinamicamente a partir do banco |
| Fonte de verdade | `quicksol_estate/data/api_endpoints.xml` sincronizado via upgrade do modulo |

Fluxo correto para atualizar documentacao:

```text
api_endpoints.xml -> upgrade quicksol_estate -> thedevkitchen_api_endpoint -> /api/v1/openapi.json -> /api/docs
```

---

## Validacao Recomendada

| Validacao | Comando / Evidencia |
|---|---|
| XML/JSON schemas validos | parse de `api_endpoints.xml` e `json.loads` dos schemas |
| Swagger sincronizado | upgrade do modulo `quicksol_estate` |
| OpenAPI sem exemplos manuais em propriedades | consultar `/api/v1/openapi.json` e checar descricoes dos paths de propriedades |
| API E2E | `integration_tests/test_us16_property_mapping_fields.sh` |
| Opcoes de campos | `integration_tests/test_us16_property_options.sh` |
| UI Odoo | Cypress `cypress/e2e/property-mapping-fields-ui.cy.js` |

