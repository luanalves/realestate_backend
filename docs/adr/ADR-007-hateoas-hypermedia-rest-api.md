# ADR-007: HATEOAS (Hypermedia as the Engine of Application State) para APIs REST

## Status
Aceito

## Contexto

APIs REST bem projetadas devem seguir os princípios da arquitetura REST, incluindo o uso de hypermedia como motor do estado da aplicação (HATEOAS). Atualmente, as APIs do projeto retornam dados sem fornecer links de navegação que permitam aos clientes descobrir dinamicamente as ações disponíveis e recursos relacionados.

**Problemas identificados:**
- Clientes precisam ter conhecimento prévio das URIs de todos os recursos
- URIs são hardcoded nas aplicações cliente, dificultando evoluções da API
- Falta de descoberta dinâmica de ações disponíveis para um recurso
- Não há indicação clara de quais operações são permitidas em determinado contexto
- Clientes precisam conhecer toda a estrutura da API antes de consumi-la

**Forças em jogo:**
- HATEOAS é uma das constraints fundamentais da arquitetura REST (Richardson Maturity Model - Nível 3)
- Permite que a API evolua sem quebrar clientes, pois os links são fornecidos dinamicamente
- Facilita a descoberta de recursos e ações disponíveis
- Melhora a experiência do desenvolvedor ao consumir a API
- Reduz acoplamento entre cliente e servidor

**Restrições:**
- As respostas JSON se tornam ligeiramente maiores devido aos links de hipermídia
- Requer padronização do formato de links em todas as respostas
- Necessita atualização da documentação OpenAPI existente

## Decisão

Todas as APIs REST do projeto devem implementar HATEOAS seguindo o padrão **RFC 5988 (Web Linking)** com links incluídos no corpo da resposta JSON.

### 1. Formato Padrão de Links

Cada resposta JSON deve incluir um array `links` ou `_links` contendo objetos com as seguintes propriedades:

```json
{
  "id": 123,
  "name": "Apartamento Moderno",
  "status": "available",
  "links": [
    {
      "href": "/api/v1/properties/123",
      "rel": "self",
      "type": "GET",
      "title": "Get property details"
    },
    {
      "href": "/api/v1/properties/123",
      "rel": "update",
      "type": "PUT",
      "title": "Update property"
    },
    {
      "href": "/api/v1/properties/123",
      "rel": "delete",
      "type": "DELETE",
      "title": "Delete property"
    },
    {
      "href": "/api/v1/properties/123/agents",
      "rel": "agents",
      "type": "GET",
      "title": "List property agents"
    },
    {
      "href": "/api/v1/properties/123/offers",
      "rel": "offers",
      "type": "GET",
      "title": "List property offers"
    }
  ]
}
```

**Propriedades obrigatórias de cada link:**
- `href`: URI completo ou relativo do recurso (string)
- `rel`: Tipo de relação do link (self, create, update, delete, collection, etc.)
- `type`: Método HTTP aplicável (GET, POST, PUT, PATCH, DELETE)

**Propriedades opcionais:**
- `title`: Descrição legível da ação (string)
- `hreflang`: Idioma do recurso vinculado
- `media`: Tipo de mídia do recurso

### 2. Relações de Link Padrão (rel)

Utilizar as seguintes relações padronizadas:

| Relação | Descrição | Exemplo |
|---------|-----------|---------|
| `self` | Link para o próprio recurso | `/api/v1/properties/123` |
| `collection` | Link para a coleção do recurso | `/api/v1/properties` |
| `create` | Link para criar um novo recurso | `/api/v1/properties` |
| `update` | Link para atualizar o recurso | `/api/v1/properties/123` |
| `delete` | Link para deletar o recurso | `/api/v1/properties/123` |
| `parent` | Link para o recurso pai | `/api/v1/agents/10` |
| `related` | Link para recurso relacionado | `/api/v1/properties/123/offers` |
| `next` | Próxima página em paginação | `/api/v1/properties?page=2` |
| `prev` | Página anterior em paginação | `/api/v1/properties?page=1` |
| `first` | Primeira página | `/api/v1/properties?page=1` |
| `last` | Última página | `/api/v1/properties?page=10` |

### 3. Respostas de Coleções

Listas e coleções devem incluir links de navegação e paginação:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Property 1",
      "links": [
        {"href": "/api/v1/properties/1", "rel": "self", "type": "GET"}
      ]
    }
  ],
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "total_pages": 5
  },
  "links": [
    {"href": "/api/v1/properties", "rel": "self", "type": "GET"},
    {"href": "/api/v1/properties", "rel": "create", "type": "POST"},
    {"href": "/api/v1/properties?page=1", "rel": "first", "type": "GET"},
    {"href": "/api/v1/properties?page=2", "rel": "next", "type": "GET"},
    {"href": "/api/v1/properties?page=5", "rel": "last", "type": "GET"}
  ]
}
```

### 4. Links Condicionais Baseados em Estado

Os links disponíveis devem refletir o estado atual do recurso e as permissões do usuário:

```python
def _generate_property_links(self, property_id, property_state, user_permissions):
    """Generate HATEOAS links based on property state and user permissions."""
    links = [
        {
            "href": f"/api/v1/properties/{property_id}",
            "rel": "self",
            "type": "GET",
            "title": "Get property details"
        }
    ]
    
    # Conditional links based on state
    if property_state == 'available' and 'update' in user_permissions:
        links.append({
            "href": f"/api/v1/properties/{property_id}",
            "rel": "update",
            "type": "PUT",
            "title": "Update property"
        })
    
    if property_state in ['available', 'pending'] and 'delete' in user_permissions:
        links.append({
            "href": f"/api/v1/properties/{property_id}",
            "rel": "delete",
            "type": "DELETE",
            "title": "Delete property"
        })
    
    if property_state == 'available':
        links.append({
            "href": f"/api/v1/properties/{property_id}/offers",
            "rel": "create-offer",
            "type": "POST",
            "title": "Create new offer"
        })
    
    return links
```

### 5. Documentação OpenAPI

Os schemas OpenAPI devem incluir a estrutura de links:

```python
spec["components"]["schemas"]["Link"] = {
    "type": "object",
    "required": ["href", "rel", "type"],
    "properties": {
        "href": {
            "type": "string",
            "description": "URI do recurso",
            "example": "/api/v1/properties/123"
        },
        "rel": {
            "type": "string",
            "description": "Tipo de relação do link",
            "example": "self"
        },
        "type": {
            "type": "string",
            "description": "Método HTTP",
            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            "example": "GET"
        },
        "title": {
            "type": "string",
            "description": "Descrição legível da ação",
            "example": "Get property details"
        }
    }
}

spec["components"]["schemas"]["PropertyResponse"] = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "example": 123},
        "name": {"type": "string", "example": "Apartamento Moderno"},
        "links": {
            "type": "array",
            "items": {"$ref": "#/components/schemas/Link"}
        }
    }
}
```

### 6. Ponto de Entrada da API (API Root)

A raiz da API (`/api/v1/`) deve retornar links para todas as coleções principais:

```json
{
  "version": "1.0",
  "links": [
    {"href": "/api/v1/properties", "rel": "properties", "type": "GET"},
    {"href": "/api/v1/agents", "rel": "agents", "type": "GET"},
    {"href": "/api/v1/offers", "rel": "offers", "type": "GET"},
    {"href": "/api/v1/auth/token", "rel": "authentication", "type": "POST"}
  ]
}
```

### 7. Implementação Gradual

A implementação do HATEOAS deve ser feita gradualmente:

1. **Fase 1**: Adicionar links básicos (`self`) em todas as respostas de recursos individuais
2. **Fase 2**: Adicionar links de navegação em coleções (paginação)
3. **Fase 3**: Implementar links condicionais baseados em estado e permissões
4. **Fase 4**: Criar API root com descoberta de recursos principais

### 8. Testes

Todos os testes E2E devem validar a presença e correção dos links HATEOAS:

```javascript
describe('HATEOAS Links', () => {
  it('should return self link in property response', () => {
    cy.request('GET', '/api/v1/properties/1').then((response) => {
      expect(response.body.links).to.be.an('array');
      const selfLink = response.body.links.find(link => link.rel === 'self');
      expect(selfLink).to.exist;
      expect(selfLink.href).to.include('/api/v1/properties/1');
      expect(selfLink.type).to.equal('GET');
    });
  });

  it('should include conditional action links based on state', () => {
    cy.request('GET', '/api/v1/properties/1').then((response) => {
      const updateLink = response.body.links.find(link => link.rel === 'update');
      if (response.body.status === 'available') {
        expect(updateLink).to.exist;
      }
    });
  });
});
```

## Consequências

### Positivas

1. **Descoberta Dinâmica**: Clientes podem descobrir recursos e ações disponíveis navegando pelos links
2. **Desacoplamento**: Clientes não precisam hardcoded URIs, permitindo evoluções da API sem quebrar clientes
3. **Maturidade REST**: Alcança o nível 3 do Richardson Maturity Model
4. **Melhor UX**: Desenvolvedores compreendem facilmente quais ações são possíveis em cada contexto
5. **Segurança**: Links condicionais impedem que clientes tentem ações não autorizadas
6. **Documentação Viva**: Os links servem como documentação em tempo de execução

### Negativas

1. **Tamanho de Resposta**: Respostas JSON ficam maiores devido aos links adicionais
2. **Complexidade Inicial**: Requer esforço de desenvolvimento para implementar geração de links
3. **Processamento Adicional**: Servidor precisa gerar links dinamicamente baseado em estado e permissões
4. **Curva de Aprendizado**: Desenvolvedores cliente precisam entender o conceito de HATEOAS

### Riscos Mitigados

- **Mudanças de URI**: Como os links são fornecidos pela API, mudanças de URI não quebram clientes
- **Ações Inválidas**: Clientes sabem exatamente quais ações estão disponíveis
- **Documentação Desatualizada**: Links são sempre atuais e refletem o estado real da API

### Próximos Passos

1. Criar helper/utility function para geração de links HATEOAS
2. Atualizar todos os controllers para incluir links nas respostas
3. Atualizar schemas OpenAPI com definição de Link
4. Criar testes E2E para validar presença de links
5. Documentar exemplos de uso de HATEOAS no README do projeto
6. Atualizar ADR-005 para incluir schemas de Link

## Referências

- [HATEOAS - RESTful API](https://restfulapi.net/hateoas/)
- [RFC 5988 - Web Linking](http://tools.ietf.org/html/rfc5988)
- [Richardson Maturity Model](https://restfulapi.net/richardson-maturity-model/)
- [JSON Hypermedia API Language (HAL)](https://en.wikipedia.org/wiki/Hypertext_Application_Language)
- [Roy Fielding's Dissertation on REST](http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm)
