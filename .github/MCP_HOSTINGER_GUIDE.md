# Guia de Uso: MCP Hostinger no VS Code

## ✅ Verificação Rápida

Após reiniciar o VS Code, verifique se o servidor está ativo:

1. Abra o **GitHub Copilot Chat** (Ctrl+Shift+I ou Cmd+Shift+I)
2. Digite: **"Busque ferramentas do Hostinger"**
3. Você deve ver ferramentas como:
   - `mcp_hostinger_list_websites`
   - `mcp_hostinger_list_databases`
   - `mcp_hostinger_list_emails`
   - Entre outras

## 🚀 Comandos de Exemplo

### Websites

```plaintext
# Listar todos os websites
Listar todos os meus websites na Hostinger

# Obter detalhes de um website específico
Mostrar detalhes do website example.com

# Verificar status de SSL
Verificar status do certificado SSL para meusite.com
```

### E-mails

```plaintext
# Listar contas de e-mail
Listar todas as contas de e-mail do domínio example.com

# Criar nova conta
Criar e-mail: contato@example.com com senha segura

# Obter uso de quota
Verificar quota de armazenamento das contas de e-mail
```

### Bancos de Dados

```plaintext
# Listar databases
Listar todos os bancos de dados MySQL

# Criar novo database
Criar banco de dados chamado "prod_realestate" com usuário "app_user"

# Verificar tamanho
Mostrar tamanho dos bancos de dados
```

### Arquivos FTP

```plaintext
# Listar arquivos
Listar arquivos em public_html/

# Upload de arquivo
Fazer upload do arquivo local config.php para /public_html/

# Backup
Criar backup dos arquivos em /public_html/
```

### Métricas e Recursos

```plaintext
# Uso de recursos
Mostrar uso atual de CPU, RAM e storage

# Estatísticas de tráfego
Obter estatísticas de bandwidth do último mês

# Logs de acesso
Mostrar últimas 50 linhas do log de acesso
```

## 🎯 Casos de Uso Reais

### Caso 1: Deploy Automático

```plaintext
Você: Preciso fazer deploy da aplicação Odoo na Hostinger.
      Verifique se há espaço suficiente no servidor e me mostre
      os websites configurados.

Copilot: [usa mcp_hostinger_list_websites e mcp_hostinger_get_resources]
         Aqui estão seus websites e recursos disponíveis...
```

### Caso 2: Gerenciamento de E-mails

```plaintext
Você: Criar e-mails para a equipe:
      - admin@realestate.com.br
      - vendas@realestate.com.br
      - suporte@realestate.com.br

Copilot: [usa mcp_hostinger_create_email para cada conta]
         Contas criadas com sucesso...
```

### Caso 3: Monitoramento

```plaintext
Você: O site está lento. Verificar uso de recursos e 
      últimos logs de erro da aplicação.

Copilot: [usa mcp_hostinger_get_metrics e mcp_hostinger_get_logs]
         Detectei alto uso de CPU (85%)...
```

### Caso 4: Backup Antes de Update

```plaintext
Você: Vou atualizar o Odoo. Fazer backup completo dos arquivos
      e database antes.

Copilot: [usa mcp_hostinger_backup_database e mcp_hostinger_create_backup]
         Backup criado: backup_20260323_143022.tar.gz
```

## 🔍 Descobrir Ferramentas Disponíveis

Para ver TODAS as ferramentas do Hostinger:

```plaintext
# No Copilot Chat:
Listar todas as ferramentas MCP do servidor Hostinger com descrição
```

Ou use tool_search_tool_regex:
```plaintext
Use tool_search_tool_regex com pattern "mcp_hostinger" e mostre todas as ferramentas
```

## 🐛 Troubleshooting

### As ferramentas não aparecem

1. **Verificar token**:
   ```bash
   echo $HOSTINGER_API_TOKEN
   ```

2. **Reiniciar VS Code completamente** (não apenas reload):
   - macOS: Cmd+Q → Reabrir
   - Windows: Alt+F4 → Reabrir

3. **Verificar logs do Copilot**:
   - Command Palette (Cmd+Shift+P)
   - "Developer: Show Logs"
   - Selecionar "GitHub Copilot"

4. **Testar manualmente o servidor**:
   ```bash
   export API_TOKEN="$HOSTINGER_API_TOKEN"
   npx hostinger-api-mcp@latest
   ```

### Erro "Unauthorized" ou "Invalid Token"

- Token expirado ou inválido
- Gere novo token em: https://hpanel.hostinger.com.br/api-keys
- Atualize a variável de ambiente

### Servidor não inicia

- Verificar se Node.js está instalado: `node --version`
- Verificar se npx funciona: `which npx`
- Limpar cache do npm: `npm cache clean --force`

## 📚 Recursos

- [Hostinger MCP Server (GitHub)](https://github.com/tomaszstankowski/hostinger-api-mcp)
- [Hostinger API Docs](https://developers.hostinger.com/)
- [VS Code MCP Documentation](https://code.visualstudio.com/docs/copilot/copilot-extensibility-overview)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)

## 💡 Dicas Pro

1. **Combine com outras ferramentas**: Use MCP Hostinger + GitHub MCP + GitKraken MCP
2. **Automatize workflows**: "Deploy para staging, testar, e fazer backup se tudo ok"
3. **Use linguagem natural**: Não precisa decorar nomes de ferramentas
4. **Contexto importa**: "Verificar logs do domínio X" vs "Verificar logs" (mais específico)

## 🔐 Segurança

- ⚠️ **NUNCA** compartilhe o output que contém tokens ou senhas
- ⚠️ Use senhas fortes ao criar contas de e-mail
- ⚠️ Revogue tokens antigos que não usa mais
- ⚠️ Monitore acessos no painel da Hostinger
