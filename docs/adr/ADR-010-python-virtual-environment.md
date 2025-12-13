# ADR 010: Ambiente Virtual Python (.venv)

## Status
Aceito

## Contexto

O projeto utiliza scripts Python externos ao container Odoo para testes E2E de API (como `test_user_login.py` usando a biblioteca `requests`). Estes scripts necessitam de dependências instaladas localmente no ambiente de desenvolvimento.

Instalar pacotes Python globalmente no sistema operacional pode causar:

- **Conflitos de versões**: Diferentes projetos podem requerer versões incompatíveis da mesma biblioteca
- **Poluição do ambiente global**: Dezenas de pacotes instalados sem controle de quais projetos realmente os utilizam
- **Problemas de reprodutibilidade**: Desenvolvedores podem ter versões diferentes instaladas, causando bugs intermitentes
- **Dificuldade de manutenção**: Sem `requirements.txt`, é difícil saber quais dependências são necessárias
- **Conflitos com sistema**: Pacotes do sistema operacional podem ser sobrescritos acidentalmente

A ausência de um ambiente virtual padronizado resultava em:
- Solicitações repetidas para instalar `requests` toda vez que testes eram executados
- Falta de documentação sobre dependências do projeto
- Inconsistência entre ambientes de desenvolvimento

## Decisão

**Adotar ambiente virtual Python `.venv` como padrão para todos os scripts externos ao container Odoo.**

O ambiente virtual `.venv` já está configurado e ativo no diretório `18.0/` com as seguintes dependências instaladas:

```
requests>=2.31.0      # Testes E2E de API REST
python-dotenv>=1.0.0  # Gerenciamento de variáveis de ambiente
```

**Estrutura de Diretórios:**

```
18.0/
├── .venv/              # Ambiente virtual Python (excluído do Git)
├── extra-addons/
│   └── quicksol_estate/
│       └── tests/
│           └── api/
│               └── test_user_login.py
```

**Uso:**

Os testes devem ser executados diretamente usando o Python do ambiente virtual:

```bash
cd 18.0
.venv/bin/python extra-addons/quicksol_estate/tests/api/test_user_login.py
```

**Configuração Git:**

O arquivo `.gitignore` exclui ambientes virtuais do controle de versão:

```gitignore
# Python virtual environments
.venv/
venv/
env/
ENV/
*.egg-info/
```

## Consequências

**Positivas:**

- ✅ **Isolamento de dependências**: Cada projeto tem suas próprias versões de bibliotecas sem conflitos
- ✅ **Reprodutibilidade**: Ambiente idêntico pode ser replicado por qualquer desenvolvedor
- ✅ **Documentação implícita**: Presença do `.venv` indica que scripts Python externos são suportados
- ✅ **Sem poluição global**: Sistema operacional permanece limpo
- ✅ **Compatibilidade CI/CD**: Ambientes virtuais são padrão em pipelines automatizados
- ✅ **Onboarding simplificado**: Novos desenvolvedores sabem que `.venv` existe e está pronto

**Negativas:**

- ⚠️ **Espaço em disco**: ~50-100MB por ambiente virtual (aceitável considerando benefícios)
- ⚠️ **Path absoluto**: Necessário usar `.venv/bin/python` em vez de apenas `python` (mitigado por scripts ou alias)

1. **Instalar globalmente:** Rejeitado - causa poluição e conflitos
2. **Usar Poetry/Pipenv:** Rejeitado - complexidade adicional desnecessária para este projeto
3. **Docker para testes:** Rejeitado - overhead para testes simples de API

## Conformidade

- [ ] Criar `.venv` em `18.0/`
- [ ] Adicionar `requirements.txt` em `18.0/`
- [ ] Atualizar `.gitignore` com padrões de venv
- [ ] Documentar no README como configurar ambiente
- [ ] Atualizar scripts CI/CD se existirem

## Referências

- [PEP 405 - Python Virtual Environments](https://www.python.org/dev/peps/pep-0405/)
- [venv — Creation of virtual environments](https://docs.python.org/3/library/venv.html)
- ADR-003 - Mandatory Test Coverage (menciona .venv em exclusões do flake8)

## Data
2025-12-12

## Autores
Sistema de Desenvolvimento
