# ADR-005: OpenAPI 3.0 com Request Body e Response Schemas Obrigatórios

## Status
Aceito

## Contexto

A API REST do projeto utiliza documentação Swagger/OpenAPI para documentar os endpoints disponíveis. Atualmente, a especificação está declarada como OpenAPI 3.0, porém a implementação está inconsistente:

- Alguns endpoints possuem `requestBody` e `responses` completamente documentados (ex: `POST /api/v1/properties`, `POST /api/v1/auth/token`)
- Outros endpoints estão apenas parcialmente documentados, sem schemas detalhados para request/response
- Parâmetros de query e path carecem de exemplos práticos
- Não existe um schema padronizado para respostas de erro
- A falta de schemas completos impossibilita o teste direto dos endpoints via Swagger UI

**Forças em jogo:**
- Ferramentas de geração de código (OpenAPI Generator, Swagger Codegen) dependem de schemas completos
- Testes automatizados da API se beneficiam de validação de contratos (contract testing)
- A documentação precisa ser uma fonte confiável da verdade (single source of truth)
- Manutenção da API fica mais complexa sem documentação adequada

**Restrições:**
- A geração da documentação é feita dinamicamente no arquivo `swagger_controller.py`
- Endpoints são registrados no modelo `thedevkitchen.api.endpoint`
- O sistema já utiliza OpenAPI 3.0, então não há breaking changes em relação à especificação

## Decisão

Todos os endpoints da API devem seguir o padrão OpenAPI 3.0 completo com as seguintes exigências obrigatórias:

### 1. Responses Documentadas

### 1. Responses Documentadas

Todo endpoint deve documentar todas as respostas HTTP possíveis com schemas apropriados:

```python
"responses": {
    "200": {
        "description": "Success",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/PropertyResponse"}
            }
        }
    },
    "400": {"$ref": "#/components/responses/BadRequest"},
    "401": {"$ref": "#/components/responses/Unauthorized"},
    "404": {"$ref": "#/components/responses/NotFound"}
}
```

### 2. Request Body para Métodos POST/PUT/PATCH

Endpoints que recebem dados devem ter `requestBody` com schema:

```python
"requestBody": {
    "required": True,
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/PropertyCreate"}
        }
    }
}
```

### 3. Schemas Reutilizáveis

Todos os schemas devem estar em `components/schemas` para reutilização:

```python
spec["components"]["schemas"]["PropertyCreate"] = {
    "type": "object",
    "required": ["name", "property_type_id", "area"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Property name",
            "example": "Apartamento Moderno no Centro"
        }
        # ... outros campos com exemplos obrigatórios
    }
}
```

### 4. Exemplos Obrigatórios

Todos os campos de schema devem ter `example` para facilitar testes no Swagger UI.

### 5. Schema de Erro Padronizado

Todas as respostas de erro devem usar o schema `ErrorResponse`:

```python
spec["components"]["schemas"]["ErrorResponse"] = {
    "type": "object",
    "properties": {
        "error": {"type": "string", "example": "validation_error"},
        "message": {"type": "string", "example": "Missing required field: name"},
        "code": {"type": "integer", "example": 400}
    }
}
```

### 6. Parâmetros com Exemplos

Parâmetros de path e query devem ter `example`:

```python
"parameters": [
    {
        "name": "id",
        "in": "path",
        "required": True,
        "schema": {"type": "integer", "example": 42}
    }
]
```

### 7. Padrão de Nomenclatura

- **Create schemas**: `{Model}Create` (ex: `PropertyCreate`)
- **Update schemas**: `{Model}Update` (ex: `PropertyUpdate`)
- **Response schemas**: `{Model}Response` (ex: `PropertyResponse`)
- **List responses**: `{Model}ListResponse` (ex: `PropertyListResponse`)

## Consequências

### Positivas

1. **Testabilidade total**: Todos os endpoints podem ser testados diretamente no Swagger UI usando o botão "Try it out"
2. **Documentação sempre atualizada**: Schemas são gerados do código, garantindo sincronização
3. **Developer Experience melhorada**: Desenvolvedores sabem exatamente quais dados enviar/receber
4. **Geração automática de SDKs**: Ferramentas como OpenAPI Generator podem criar clientes automaticamente
5. **Contract testing facilitado**: Testes podem validar se API está de acordo com a especificação
6. **Onboarding mais rápido**: Novos desenvolvedores entendem a API pela documentação interativa
7. **Consistência**: Todos os endpoints seguem o mesmo padrão de documentação

## Arquitetura de Geração Dinâmica

### Como Funciona

O Swagger é **gerado dinamicamente** pelo controller `swagger_controller.py` (módulo `thedevkitchen_apigateway`), que:

1. **Lê da tabela do banco de dados** `thedevkitchen_api_endpoint` para obter a lista de endpoints registrados
2. Constrói a especificação OpenAPI 3.0 com base nos registros encontrados
3. Serve a documentação via endpoints `/api/docs` (Swagger UI) e `/api/v1/openapi.json` (spec JSON)

### Persistência de Dados

**⚠️ IMPORTANTE**: Os registros na tabela `thedevkitchen_api_endpoint` **persistem no banco de dados independentemente dos arquivos XML de dados**.

#### Implicações Práticas

- **Instalação inicial**: Arquivos XML em `data/api_endpoints.xml` criam os registros durante a instalação do módulo
- **Upgrades**: Arquivos XML atualizam/criam registros durante upgrades do módulo
- **Remoção de código**: Remover um controller e seu arquivo XML **NÃO remove automaticamente** os registros do banco
- **Swagger UI**: Continua exibindo endpoints removidos até que os registros sejam deletados manualmente do banco

#### Processo de Remoção de Endpoints

Quando remover endpoints (ex: deprecação de APIs), realize as seguintes etapas:

```bash
# 1. Remover o código (controller)
rm controllers/deprecated_api.py

# 2. Remover o arquivo XML de dados
# Editar ou remover: data/api_endpoints.xml

# 3. Limpar registros do banco (OBRIGATÓRIO)
docker compose exec db psql -U odoo -d realestate -c "
DELETE FROM thedevkitchen_api_endpoint 
WHERE path LIKE '%deprecated_path%';
"

# 4. Verificar Swagger UI
# Acessar http://localhost:8069/api/docs
# Confirmar que endpoints removidos não aparecem mais
```

#### Verificação de Sincronização

Para verificar se há endpoints órfãos no banco:

```sql
-- Listar todos os endpoints registrados
SELECT id, name, path, method, active 
FROM thedevkitchen_api_endpoint 
ORDER BY path;

-- Verificar endpoints de um módulo específico
SELECT id, name, path, method 
FROM thedevkitchen_api_endpoint 
WHERE path LIKE '/api/v1/tenants%';
```

### Caso Real: Limpeza de Endpoints Órfãos

Durante a Feature 010 (Profile Unification), os endpoints da API de Tenants foram removidos do código e dos arquivos XML. No entanto, os 6 registros na tabela `thedevkitchen_api_endpoint` permaneceram ativos, fazendo com que o Swagger UI continuasse exibindo os endpoints removidos.

**Solução aplicada**: Limpeza manual via DELETE no banco de dados após identificação pelo comando SQL acima.

## Referências

- [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3)
- [JSON Schema Specification](https://json-schema.org/)
- [ADR-018: Input Validation and Schema Validation for REST APIs](ADR-018-input-validation-schema-validation-rest-apis.md) - Complementa ADR-005 com validação runtime dos schemas
