# ADR 004: Nomenclatura de Módulos e Tabelas com Prefixo thedevkitchen_

## Status
Aceito

## Contexto

No desenvolvimento de módulos Odoo customizados, existe o risco de conflito de nomes com módulos de terceiros ou da comunidade Odoo. Módulos com nomes genéricos como `api_gateway`, `estate`, `property` podem colidir com outros módulos instalados no sistema, causando problemas de:

- **Conflitos de nomenclatura**: Tabelas e modelos com nomes idênticos de diferentes módulos
- **Dificuldade de identificação**: Impossibilidade de identificar rapidamente quais tabelas/modelos pertencem ao projeto
- **Problemas de manutenção**: Dificuldade em rastrear dados no banco de dados em ambientes com múltiplos módulos
- **Risco de sobrescrita**: Módulos diferentes podem sobrescrever acidentalmente modelos um do outro

Atualmente, o projeto possui módulos sem padronização de nomenclatura:
- `api_gateway` (nome genérico)
- `quicksol_estate` (prefixo `quicksol_` que não representa a empresa atual)

Exemplos de problemas potenciais:
- Tabela `oauth_application` pode conflitar com outros módulos OAuth
- Modelo `estate.property` é extremamente genérico
- Difícil identificar no banco quais tabelas são do projeto vs. módulos de terceiros

## Decisão

**Todos os módulos customizados desenvolvidos para este projeto DEVEM seguir a nomenclatura padronizada com o prefixo `thedevkitchen_`.**

### Regras de Nomenclatura

#### 1. **Nome do Módulo (Diretório)**
- Formato: `thedevkitchen_<nome_funcional>`
- Exemplos:
  - `thedevkitchen_apigateway`
  - `thedevkitchen_estate`
  - `thedevkitchen_crm`

#### 2. **Nome do Modelo Odoo (_name)**
- Formato: `thedevkitchen.<categoria>.<entidade>`
- Exemplos:
  - `thedevkitchen.oauth.application`
  - `thedevkitchen.oauth.token`
  - `thedevkitchen.estate.property`
  - `thedevkitchen.estate.agent`

#### 3. **Nome da Tabela no Banco de Dados**
- Gerado automaticamente pelo Odoo a partir do `_name`
- Formato: `thedevkitchen_<categoria>_<entidade>`
- Exemplos:
  - `thedevkitchen_oauth_application`
  - `thedevkitchen_oauth_token`
  - `thedevkitchen_estate_property`
  - `thedevkitchen_estate_agent`

#### 4. **XML IDs (ir.model.data)**
- Formato: `<modulo>.<identificador>`
- Exemplos:
  - `thedevkitchen_apigateway.action_oauth_application`
  - `thedevkitchen_estate.view_property_form`

#### 5. **Arquivos de Security (CSV)**
- IDs devem ser claros e únicos
- Formato: `access_<modelo>_<grupo>`
- Exemplo: `access_thedevkitchen_oauth_application_manager`

### Módulos Afetados

Todos os módulos customizados devem ser renomeados:

| Módulo Atual | Módulo Novo | Status |
|--------------|-------------|---------|
| `api_gateway` | `thedevkitchen_apigateway` | ✅ Implementado |
| `quicksol_estate` | `thedevkitchen_estate` | 📋 Planejado |

### Processo de Migração

Para módulos existentes, a migração deve seguir o processo:

1. **Renomear diretório** do módulo
2. **Atualizar manifesto** (`__manifest__.py`)
3. **Atualizar modelos** (alterar `_name` em todos os models)
4. **Atualizar controllers** (alterar `self.env['modelo']`)
5. **Atualizar views XML** (alterar `model=""` em todas as views)
6. **Atualizar security** (CSV e XML)
7. **Atualizar testes** (unitários e E2E)
8. **Criar script SQL de migração** para renomear tabelas e metadados
9. **Executar testes** (validar 100% de aprovação)
10. **Deploy** com script de migração

## Consequências

### Positivas

✅ **Identificação clara**: Todas as tabelas do projeto são facilmente identificáveis no banco de dados pelo prefixo `thedevkitchen_`

✅ **Zero conflitos**: Eliminação completa de risco de conflito com módulos de terceiros ou da comunidade

✅ **Manutenibilidade**: Facilita debug, análise de dados e troubleshooting em produção

✅ **Profissionalismo**: Nomenclatura reflete a marca/empresa (TheDevKitchen) de forma consistente

✅ **Escalabilidade**: Padrão permite crescimento do projeto sem preocupações de nomenclatura

✅ **Queries SQL diretas**: DBAs podem facilmente identificar e trabalhar com tabelas do projeto

### Negativas

⚠️ **Migração necessária**: Módulos existentes precisam ser migrados (trabalho pontual)

⚠️ **Nomes mais longos**: Tabelas e modelos terão nomes maiores (trade-off aceitável)

⚠️ **Breaking change**: Integrações externas que referenciem modelos antigos precisam ser atualizadas

⚠️ **Downtime mínimo**: Migração em produção requer janela de manutenção (mitigado por scripts automatizados)

### Mitigações

- **Scripts de migração SQL** automatizam renomeação de tabelas e metadados
- **Testes abrangentes** (unitários + E2E) garantem zero regressão
- **Documentação completa** do processo de migração
- **Rollback planejado** em caso de problemas (backups + scripts reversos)

### Impacto em Integrações

APIs e integrações que referenciem modelos diretamente precisarão atualizar:
- URLs de ações: `/web#action=api_gateway.xxx` → `/web#action=thedevkitchen_apigateway.xxx`
- Referências de modelo em código externo: `oauth.application` → `thedevkitchen.oauth.application`
- Queries SQL diretas devem usar novos nomes de tabela

### Exemplo de Implementação

**Antes:**
```python
class OAuthApplication(models.Model):
    _name = 'oauth.application'
    # ...
```

**Depois:**
```python
class OAuthApplication(models.Model):
    _name = 'thedevkitchen.oauth.application'
    # ...
```

**Resultado no Banco:**
- Tabela: `thedevkitchen_oauth_application` (automaticamente criada pelo Odoo)
- Identificável, sem conflitos, manutenível

### Referências

- [Odoo Model Naming Best Practices](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- Plano de migração: `docs/PLANO_RENOMEACAO_API_GATEWAY.md`
- Scripts: `scripts/migrate_api_gateway_to_thedevkitchen.sql`
