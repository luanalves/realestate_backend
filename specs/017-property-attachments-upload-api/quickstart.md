# Quickstart: Property Attachments Upload API (017)

**Feature**: 017 — Property Attachments Upload API | **Branch**: `017-property-attachments-upload-api`

## Pré-requisitos

- Docker + Docker Compose instalados
- Branch `017-property-attachments-upload-api` ativo
- Odoo 18.0 rodando localmente (`cd 18.0 && docker compose up -d`)

## Setup: Dependência libmagic1

A feature requer `libmagic1` (biblioteca C usada pelo `python-magic`). Já deve estar declarada no Dockerfile, mas se rodar sem rebuild:

```bash
# Verificar se libmagic está disponível no container
docker compose exec odoo python3 -c "import magic; print('OK')"

# Se falhar, rebuild da imagem:
cd 18.0
docker compose down
docker compose build --no-cache odoo
docker compose up -d
```

### Verificação da instalação

```bash
docker compose exec odoo python3 -c "
import magic
result = magic.from_buffer(b'\xff\xd8\xff', mime=True)
print('JPEG detectado:', result)  # esperado: image/jpeg
"
```

## Instalar Módulo

```bash
# Instalar/atualizar quicksol_estate (inclui o novo controller)
docker compose exec odoo odoo -d realestate -u quicksol_estate --stop-after-init

# Verificar logs
docker compose logs --tail=50 odoo | grep -E "error|ERROR|Module.*quicksol"
```

## Configuração do Limite de Upload

O limite padrão é 128 MB. Para alterar:

```bash
# Via psql
docker compose exec db psql -U odoo -d realestate -c "
UPDATE ir_config_parameter
SET value = '52428800'   -- 50 MB
WHERE key = 'web.max_file_upload_size';
"

# Inserir se não existir (Odoo cria automaticamente, mas para garantir):
docker compose exec db psql -U odoo -d realestate -c "
INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
SELECT 'web.max_file_upload_size', '134217728', 1, 1, now(), now()
WHERE NOT EXISTS (
  SELECT 1 FROM ir_config_parameter WHERE key = 'web.max_file_upload_size'
);
"
```

## Rodar Testes Unitários

```bash
# Testes unitários via Odoo test runner
docker compose exec odoo odoo -d realestate \
  --test-enable \
  --test-file=/opt/odoo/extra-addons/quicksol_estate/tests/unit/test_property_attachments_unit.py \
  --stop-after-init \
  2>&1 | grep -E "PASS|FAIL|ERROR|Ran"
```

## Rodar Testes de Integração E2E

```bash
# Configurar variáveis de ambiente (ou usar .env)
export BASE_URL="http://localhost:8069"
export JWT_TOKEN="<seu-token-jwt>"
export SESSION_ID="<seu-session-id>"
export COMPANY_ID="1"
export PROPERTY_ID="<id-de-propriedade-existente>"

# Rodar script E2E
cd integration_tests
bash test_property_attachments_api.sh
```

## Teste Manual Rápido (curl)

```bash
BASE="http://localhost:8069"
TOKEN="<jwt>"
SESSION="<session_id>"
PROPERTY_ID=7

# 1. Upload de imagem
curl -X POST "$BASE/api/v1/properties/$PROPERTY_ID/attachments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: session_id=$SESSION" \
  -F "file=@/tmp/test.jpg;type=image/jpeg" \
  -F "attachment_type=image"

# 2. Listar attachments
curl -X GET "$BASE/api/v1/properties/$PROPERTY_ID/attachments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: session_id=$SESSION"

# 3. Listar apenas imagens
curl -X GET "$BASE/api/v1/properties/$PROPERTY_ID/attachments?attachment_type=image" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: session_id=$SESSION"

# 4. Download (substitua 42 pelo ID retornado no upload)
curl -X GET "$BASE/api/v1/properties/$PROPERTY_ID/attachments/42/download" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: session_id=$SESSION" \
  -o /tmp/downloaded.jpg

# 5. Delete
curl -X DELETE "$BASE/api/v1/properties/$PROPERTY_ID/attachments/42" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Cookie: session_id=$SESSION"
```

## Verificar Registros no Banco

```bash
docker compose exec db psql -U odoo -d realestate -c "
SELECT id, name, mimetype, description, file_size, store_fname, company_id
FROM ir_attachment
WHERE res_model = 'real.estate.property'
  AND description IN ('image', 'document')
ORDER BY create_date DESC
LIMIT 10;
"
```

## Arquivos Relevantes

| Arquivo | Descrição |
|---------|-----------|
| [18.0/Dockerfile](../../../18.0/Dockerfile) | Deve conter `libmagic1` no apt-get |
| [controllers/property_attachments_controller.py](../../../18.0/extra-addons/quicksol_estate/controllers/property_attachments_controller.py) | Controller principal — 4 endpoints |
| [controllers/utils/serializers.py](../../../18.0/extra-addons/quicksol_estate/controllers/utils/serializers.py) | `serialize_property_mapping_fields` — atualização Phase 4 |
| [tests/unit/test_property_attachments_unit.py](../../../18.0/extra-addons/quicksol_estate/tests/unit/test_property_attachments_unit.py) | Testes unitários |
| [integration_tests/test_property_attachments_api.sh](../../../integration_tests/test_property_attachments_api.sh) | Testes E2E |

## Troubleshooting

### ImportError: failed to find libmagic

```
ImportError: failed to find libmagic.  Check your installation
```

**Solução**: Rebuild da imagem Docker com `libmagic1` instalado.

### Upload retorna 415 com arquivo válido

Verifique se o arquivo realmente tem magic bytes corretos:
```bash
docker compose exec odoo python3 -c "
import magic
with open('/tmp/test.jpg', 'rb') as f:
    content = f.read(2048)
print(magic.from_buffer(content, mime=True))
"
```

### download_url aponta para /web/content/

Verifique se o controller está sendo carregado corretamente (restart Odoo + update módulo).
