# Auditoria Automática - Guia de Uso

## 🎯 O Que Foi Implementado

O módulo `auditlog` foi modificado para oferecer **auditoria automática e transparente** de todas as operações do backoffice, sem necessidade de criar regras manualmente para cada modelo.

## ⚙️ Como Ativar a Auditoria Automática

### Passo 1: Acessar Configurações

1. Faça login no Odoo: `http://localhost:8069`
2. Navegue para: **Definições** (Settings)
3. Role até o final da página e ative o **Modo Desenvolvedor** (se ainda não estiver ativo)
4. Procure pela seção **"Audit Log"**

### Passo 2: Configurar Auditoria Automática

Na seção **Audit Log**, você encontrará as seguintes opções:

#### ✅ **Auto-create Audit Rules**
- Ative esta opção para habilitar auditoria automática
- Quando ativada, o sistema criará regras automaticamente para todos os modelos

#### 📝 **Operações para Logar** (aparecem quando a opção acima está ativa)
- **Auto-log Create Operations**: ☑️ Recomendado - Loga criação de registros
- **Auto-log Write Operations**: ☑️ Recomendado - Loga alterações em registros
- **Auto-log Delete Operations**: ☑️ Recomendado - Loga exclusões
- **Auto-log Read Operations**: ⬜ NÃO recomendado - Impacto em performance

#### 🚫 **Modelos Excluídos**
Lista de padrões de modelos que NÃO serão auditados (separados por vírgula):

```
ir.%,base.%,mail.%,bus.%,web.%,report.%,auditlog.%
```

**Por que excluir estes modelos?**
- `ir.%` - Modelos técnicos internos do Odoo
- `base.%` - Modelos base do sistema
- `mail.%` - Sistema de mensagens (muita atividade)
- `bus.%` - Sistema de notificações (muita atividade)
- `web.%` - Interface web (muita atividade)
- `report.%` - Geração de relatórios temporários
- `auditlog.%` - Próprio módulo de auditoria (evita recursão)

### Passo 3: Salvar e Reiniciar

1. Clique em **"Salvar"** na página de configurações
2. **Reinicie o Odoo**:
   ```bash
   cd /opt/homebrew/var/www/realestate/odoo-docker/18.0
   docker compose restart odoo
   ```

### Passo 4: Verificar Funcionamento

1. Faça login novamente
2. Vá em qualquer módulo (exemplo: **Imobiliária**)
3. Abra um registro existente (exemplo: um imóvel)
4. Faça uma alteração (exemplo: mude o preço)
5. Salve

6. Verifique os logs:
   - **Definições → Técnico → Audit → Logs**
   - Você verá o registro da alteração com:
     - Usuário que fez a alteração
     - Data e hora
     - Modelo alterado
     - Registro específico
     - Campos que mudaram (valor antigo → valor novo)

## 📊 Como Visualizar os Logs

### Via Interface

1. **Definições → Técnico → Audit → Logs**
2. Use os filtros para:
   - Filtrar por usuário
   - Filtrar por modelo
   - Filtrar por data
   - Ver detalhes completos de cada alteração

### Via Banco de Dados

```bash
docker compose exec db psql -U odoo -d realestate
```

```sql
-- Ver total de logs
SELECT COUNT(*) FROM auditlog_log;

-- Ver últimos 10 logs
SELECT 
    l.create_date,
    u.login as usuario,
    m.model as modelo,
    l.res_id as registro_id,
    l.method as operacao
FROM auditlog_log l
JOIN res_users u ON l.user_id = u.id
JOIN ir_model m ON l.model_id = m.id
ORDER BY l.create_date DESC
LIMIT 10;

-- Ver detalhes de alterações (campos modificados)
SELECT 
    l.create_date,
    ll.field_description as campo,
    ll.old_value_text as valor_antigo,
    ll.new_value_text as valor_novo
FROM auditlog_log l
JOIN auditlog_log_line ll ON ll.log_id = l.id
ORDER BY l.create_date DESC
LIMIT 20;
```

## 🔧 Personalização

### Excluir Modelos Específicos

Se você quiser excluir modelos específicos do seu projeto:

1. Vá em **Definições → Audit Log**
2. No campo **"Excluded Models"**, adicione:
   ```
   ir.%,base.%,mail.%,bus.%,web.%,report.%,auditlog.%,meu.modelo.customizado
   ```

### Auditar Apenas Modelos Específicos

Se preferir auditar APENAS alguns modelos:

1. **Desative** a auditoria automática
2. Crie regras manualmente para os modelos desejados:
   - **Definições → Técnico → Audit → Rules**
   - Clique em **"Novo"**
   - Selecione o modelo
   - Configure as operações
   - Clique em **"Subscribe"**

## ⚠️ Considerações de Performance

### Recomendações:
- ✅ **Sempre ative**: Create, Write, Unlink
- ⚠️ **Cuidado com Read**: Pode impactar muito a performance em modelos com muitas consultas
- ✅ **Exclua modelos técnicos**: ir.%, base.%, mail.%, etc.
- ✅ **Use "Fast log"**: Melhor performance (configurado automaticamente)

### Impacto Estimado:
- **Create/Write/Unlink**: ~5-10% overhead (aceitável)
- **Read operations**: ~20-50% overhead (evite em produção)

## 🎯 Modelos do Seu Projeto que Serão Auditados

Com a configuração padrão, os seguintes modelos do projeto `quicksol_estate` serão automaticamente auditados:

```
✅ real.estate.agent
✅ real.estate.amenity
✅ real.estate.lease
✅ real.estate.property
✅ real.estate.property.building
✅ real.estate.property.commission
✅ real.estate.property.document
✅ real.estate.property.email
✅ real.estate.property.image
✅ real.estate.property.key
✅ real.estate.property.owner
✅ real.estate.property.phone
✅ real.estate.property.photo
✅ real.estate.property.tag
✅ real.estate.property.type
✅ real.estate.sale
✅ real.estate.tenant
```

## 🔍 Troubleshooting

### Logs não estão sendo criados?

1. Verifique se a auditoria automática está **ativada** nas Configurações
2. **Reinicie o Odoo** após ativar
3. Verifique se o modelo não está na lista de exclusão
4. Confira se há regras criadas: **Definições → Técnico → Audit → Rules**

### Muitas regras criadas?

Se foram criadas regras demais:

```bash
docker compose exec odoo odoo shell -d realestate
```

```python
# Remover todas as regras auto-criadas
env['auditlog.rule'].search([('name', 'like', 'Auto:')]).unlink()
```

## 📚 Referências

- Documentação oficial OCA: https://github.com/OCA/server-tools/tree/18.0/auditlog
- Código modificado: `/opt/homebrew/var/www/realestate/odoo-docker/18.0/extra-addons/auditlog/`

## ✅ Resumo

✨ **Antes**: Você tinha que criar uma regra manual para cada modelo  
✨ **Agora**: Ative um checkbox e TODOS os modelos de negócio são auditados automaticamente!

💪 **O módulo se adapta a você, não o contrário!**
