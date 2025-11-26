# QuickSol Estate - Módulo Imobiliário

Módulo Odoo para gestão de imóveis com API REST e autenticação OAuth 2.0.

## 📋 Estrutura de Testes

Este módulo possui dois tipos de testes distintos:

### ✅ Testes Unitários (`tests/`)

Executam com banco de dados real, testam lógica de negócio sem requisições HTTP:

```bash
# Executar todos os testes unitários
docker compose run --rm odoo python3 /usr/bin/odoo \
    -d realestate \
    --test-enable \
    --stop-after-init \
    --test-tags=quicksol_estate
```

**Arquivos:**
- `test_validations.py` - Validações de email, data, CNPJ
- `test_company_unit.py` - Testes unitários de Company
- `test_agent_unit.py` - Testes unitários de Agent  
- `test_odoo_bridge.py` - Testes de integração Odoo

### 🌐 Testes HTTP/API (`tests/api/`)

Testes de integração que fazem requisições HTTP reais para endpoints da API REST.
Executam APÓS instalação de todos os módulos (tag `post_install`):

```bash
# Executar apenas testes HTTP/API
docker compose run --rm odoo python3 /usr/bin/odoo \
    -d realestate \
    -i quicksol_estate \
    --test-tags=post_install \
    --stop-after-init

# Executar TODOS os testes (unitários + HTTP/API)
docker compose run --rm odoo python3 /usr/bin/odoo \
    -d realestate \
    -i quicksol_estate \
    --test-tags=quicksol_estate,post_install \
    --stop-after-init
```

**Arquivos:**
- `api/test_property_api.py` - Testes HTTP de controle de acesso CRUD
- `api/test_property_api_auth.py` - Testes de autenticação OAuth 2.0
- `api/test_master_data_api.py` - Testes de endpoints de dados mestres

## 🔧 Funcionalidades

### Modelos
- `real.estate.property` - Gestão de imóveis
- `real.estate.state` - Estados/províncias (suporte internacional)
- `real.estate.location.type` - Tipos de localização (Urbano, Rural, etc.)
- `real.estate.property.type` - Tipos de imóveis
- `real.estate.agent` - Agentes imobiliários
- `real.estate.company` - Empresas imobiliárias

### API REST

**Base URL:** `http://localhost:8069/api/v1`

**Autenticação:**
```bash
curl -X POST http://localhost:8069/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'
```

**Endpoints:**
- `GET /properties` - Listar imóveis
- `POST /properties` - Criar imóvel
- `GET /properties/{id}` - Buscar imóvel
- `PUT /properties/{id}` - Atualizar imóvel
- `DELETE /properties/{id}` - Deletar imóvel
- `GET /states?country_id=31` - Listar estados (filtro opcional por país)
- `GET /location-types` - Listar tipos de localização
- `GET /property-types` - Listar tipos de imóveis

## 📦 Dependências

- `thedevkitchen_apigateway` - OAuth 2.0 e JWT
- `auditlog` - Auditoria de alterações

## 🚀 Instalação

1. Adicione o módulo ao diretório `extra-addons/`
2. Atualize a lista de módulos no Odoo
3. Instale o módulo `quicksol_estate`

## 📝 Desenvolvimento

### Rodando Testes Durante Desenvolvimento

```bash
# 1. Testes unitários (rápido, não requer servidor)
docker compose run --rm odoo python3 /usr/bin/odoo \
    -d realestate \
    --test-enable \
    --stop-after-init \
    --test-tags=quicksol_estate

# 2. Testes HTTP/API (requer servidor rodando)
./run_http_tests.sh
```

### Estrutura de Diretórios

```
quicksol_estate/
├── models/          # Modelos de dados
├── controllers/     # Endpoints da API REST
├── views/           # Views XML do Odoo
├── security/        # Regras de acesso
├── data/            # Dados iniciais (estados, tipos, etc.)
├── tests/           # Testes unitários
│   └── api/         # Testes HTTP/API de integração
└── static/          # Recursos estáticos
```

## 📄 Licença

LGPL-3
