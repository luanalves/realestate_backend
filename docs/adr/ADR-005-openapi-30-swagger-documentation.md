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
