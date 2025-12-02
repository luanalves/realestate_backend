# Fase 0 - Guia de Boas Práticas para Desenvolvedor Junior

## 🎯 Antes de Começar

### Preparação do Ambiente

```bash
# 1. Navegue até a pasta do projeto
cd /opt/homebrew/var/www/realestate/odoo-docker/18.0

# 2. Certifique-se que os containers estão rodando
docker compose ps

# 3. Se não estiverem, inicie
docker compose up -d

# 4. Verifique os logs
docker compose logs -f odoo
```

### Ferramentas Úteis

1. **Editor de Código:** VS Code, PyCharm, ou Cursor
2. **Terminal:** iTerm2 ou terminal padrão do Mac
3. **Teste de API:** Postman, Insomnia, ou curl
4. **Visualizador JSON:** jq (instalar: `brew install jq`)

---

## 📝 Seguindo as ADRs

### ADR-001: Diretrizes de Desenvolvimento

**O que significa na prática:**

✅ **FAZER:**
- Criar arquivos separados para cada classe/serviço
- Usar nomes descritivos (ex: `rate_limiter.py`, não `utils.py`)
- Métodos pequenos (máximo 20-30 linhas)
- Código auto-explicativo

❌ **NÃO FAZER:**
- Colocar tudo em um único arquivo gigante
- Usar nomes genéricos (ex: `helper.py`, `utils.py`)
- Métodos com mais de 50 linhas
- Comentários explicando código ruim

**Exemplo ruim:**
```python
# utils.py
def do_stuff(x, y, z, a, b, c):  # Muitos parâmetros!
    # Faz login
    # Valida dados
    # Gera token
    # Salva no banco
    # Envia email
    # ... 200 linhas depois ...
    return result
```

**Exemplo bom:**
```python
# rate_limiter.py
class RateLimiter:
    @classmethod
    def check(cls, ip, email):
        # Apenas 15 linhas focadas em uma coisa
        pass

# token_generator.py
class TokenGenerator:
    @staticmethod
    def create_for_user(user):
        # Apenas 25 linhas focadas em gerar token
        pass
```

### ADR-003: Cobertura de Testes Obrigatória

**Meta:** 80% de cobertura mínima

**Como atingir:**

1. **Cada classe = 1 arquivo de teste**
   ```
   services/rate_limiter.py → tests/test_rate_limiter.py
   services/token_generator.py → tests/test_token_generator.py
   ```

2. **Cada método público = pelo menos 1 teste**
   ```python
   class RateLimiter:
       def check(self):  # → test_allows_first_attempt()
           pass          # → test_blocks_after_5_attempts()
       
       def clear(self):  # → test_clears_attempts()
           pass
   ```

3. **Testar casos de sucesso E falha**
   ```python
   def test_login_success(self):  # ✅ Caminho feliz
       pass
   
   def test_login_invalid_password(self):  # ❌ Erro
       pass
   
   def test_login_user_inactive(self):  # ❌ Edge case
       pass
   ```

---

## 🔧 Dicas Práticas

### 1. Sempre Testar Localmente Antes de Commitar

```bash
# Seu fluxo de trabalho deve ser:

# 1. Faz a mudança
vim services/rate_limiter.py

# 2. Atualiza módulo
docker compose exec odoo odoo -u thedevkitchen_apigateway -d realestate --stop-after-init

# 3. Roda os testes
docker compose exec odoo odoo --test-enable --stop-after-init \
  --test-tags /thedevkitchen_apigateway.test_rate_limiter -d realestate

# 4. Testa manualmente (se for endpoint)
curl -X POST http://localhost:8069/api/v1/auth/login ...

# 5. Se tudo passou, commita
git add .
git commit -m "feat: add rate limiter service"
```

### 2. Entendendo Erros Comuns

#### Erro: `ModuleNotFoundError: No module named 'services'`

**Causa:** Faltou criar `__init__.py`

**Solução:**
```bash
# Criar arquivo vazio
touch 18.0/extra-addons/thedevkitchen_apigateway/services/__init__.py

# OU com conteúdo
echo "from . import rate_limiter" > services/__init__.py
```

#### Erro: `Field 'estate_company_ids' does not exist`

**Causa:** Modelo `res.users` não tem o campo (módulo quicksol_estate não instalado)

**Solução:**
```bash
# Instalar módulo de imobiliária
docker compose exec odoo odoo -i quicksol_estate -d realestate --stop-after-init
```

#### Erro: `KeyError: 'email'` no login

**Causa:** Request não tem o parâmetro `email`

**Solução:**
```python
# Sempre validar parâmetros
email = data.get('email')
if not email:
    return {'error': {'message': 'Email is required'}}
```

#### Erro: Test falhando com `AssertionError`

**Exemplo:**
```
FAIL: test_generates_valid_jwt
AssertionError: 'jwt' not in {}
```

**Debugging:**
```python
def test_generates_valid_jwt(self):
    result = TokenGenerator.create_for_user(self.user)
    
    # Adicionar print para debug
    print(f"Result: {result}")  # Ver o que realmente retornou
    
    self.assertIn('jwt', result)
```

### 3. Debugando com Logs

#### Adicionar logs temporários

```python
import logging
_logger = logging.getLogger(__name__)

def login(self, email, password):
    _logger.info(f"Login attempt for: {email}")  # Debug
    
    uid = request.session.authenticate(...)
    
    _logger.info(f"Authentication result: {uid}")  # Debug
```

#### Ver logs em tempo real

```bash
docker compose logs -f odoo | grep "Login attempt"
```

### 4. Testando com Curl

#### Login básico

```bash
curl -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
      "email": "admin",
      "password": "admin"
    },
    "id": 1
  }' | jq
```

#### Salvar token em variável

```bash
TOKEN=$(curl -s -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {"email": "admin", "password": "admin"},
    "id": 1
  }' | jq -r '.result.access_token')

echo "Token salvo: $TOKEN"
```

#### Usar token em outra requisição

```bash
curl -X POST http://localhost:8069/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {},
    "id": 1
  }' | jq
```

---

## 📊 Checklist de Qualidade

Antes de marcar um passo como concluído:

### ✅ Código
- [ ] Código está em arquivo separado (não misturado)
- [ ] Nomes de classes/métodos são descritivos
- [ ] Não há código comentado (deletar, não comentar)
- [ ] Imports estão organizados (stdlib → odoo → local)
- [ ] Não usa `.sudo()` em queries de dados de usuário

### ✅ Testes
- [ ] Teste criado para cada método público
- [ ] Teste de caso de sucesso
- [ ] Teste de caso de erro
- [ ] Todos os testes passando (verde)
- [ ] Sem warnings no log de teste

### ✅ Funcionalidade
- [ ] Testado manualmente com curl
- [ ] Retorna resposta esperada
- [ ] Erros retornam status code correto (401, 403, 500)
- [ ] Logs de auditoria funcionando

### ✅ Documentação
- [ ] Docstring na classe/método
- [ ] Exemplo de uso no README (se for endpoint)
- [ ] Comentários apenas onde realmente necessário

---

## 🐛 Debugging Avançado

### Acessar shell do container

```bash
docker compose exec odoo bash

# Dentro do container
cd /mnt/extra-addons/thedevkitchen_apigateway
ls -la
python3 -c "from services.rate_limiter import RateLimiter; print(RateLimiter)"
```

### Acessar shell Python do Odoo

```bash
docker compose exec odoo odoo shell -d realestate

# Dentro do shell
>>> user = env['res.users'].browse(2)
>>> print(user.name)
>>> print(user.estate_company_ids)
>>> exit()
```

### Verificar estrutura do banco

```bash
docker compose exec db psql -U odoo -d realestate

-- Dentro do psql
\dt  -- Lista todas as tabelas
\d thedevkitchen_oauth_token  -- Descreve tabela
SELECT * FROM thedevkitchen_oauth_token LIMIT 5;
\q  -- Sair
```

---

## 🎓 Conceitos para Estudar

### 1. JWT (JSON Web Token)

**O que é:** Token assinado que contém dados do usuário

**Estrutura:**
```
eyJhbGc... (Header) . eyJzdWI... (Payload) . SflKxwRJ... (Signature)
```

**Decodificar:** https://jwt.io

### 2. OAuth 2.0 Password Grant

**Fluxo:**
```
Cliente → POST /login {email, password}
Servidor → Valida credenciais
Servidor → Gera JWT com user_id
Servidor → Retorna JWT
Cliente → Usa JWT em todas as requisições (Authorization: Bearer ...)
```

### 3. Rate Limiting

**Por que?** Prevenir ataques de força bruta

**Como?** Contar tentativas por IP/email em janela de tempo

**Exemplo:** 5 tentativas em 15 minutos

### 4. Odoo Environment

```python
request.env  # Environment atual
request.env.user  # Usuário autenticado
request.env['res.users']  # Modelo Users
request.env(user=outro_user)  # Trocar contexto
```

### 5. Odoo ORM

```python
# Buscar
user = env['res.users'].browse(123)  # Por ID
users = env['res.users'].search([('login', '=', 'admin')])  # Por filtro

# Criar
new_user = env['res.users'].create({'name': 'João', 'login': 'joao'})

# Atualizar
user.write({'name': 'Novo Nome'})

# Deletar
user.unlink()
```

---

## 📞 Quando Pedir Ajuda

**Pedir ajuda É BOM!** Não fique travado.

### Antes de pedir ajuda:

1. ✅ Li a mensagem de erro completa
2. ✅ Tentei pesquisar no Google
3. ✅ Reli o passo que estou fazendo
4. ✅ Verifiquei se todos os arquivos necessários existem
5. ✅ Tentei reiniciar o container (`docker compose restart odoo`)

### Como pedir ajuda de forma eficiente:

**❌ Ruim:**
```
"Não funciona, me ajuda"
```

**✅ Bom:**
```
"Estou no Passo 3 (Token Generator).
Quando rodo o teste test_generates_valid_jwt, recebo este erro:

AssertionError: 'jwt' not in {}

Código que escrevi:
[colar código]

Log completo:
[colar log]

Já tentei:
- Reiniciar container
- Atualizar módulo
- Verificar imports

O que pode estar errado?"
```

---

## 🏆 Dicas de Produtividade

### 1. Atalhos de Terminal

```bash
# Histórico
Ctrl + R  # Buscar comando anterior

# Aliases úteis (adicionar no ~/.zshrc)
alias dc='docker compose'
alias dcl='docker compose logs -f odoo'
alias dce='docker compose exec odoo'
alias test-odoo='docker compose exec odoo odoo --test-enable --stop-after-init'
```

### 2. Snippets de Código

Criar templates para acelerar:

**Teste unitário:**
```python
def test_NOME_DO_TESTE(self):
    """Deve FAZER_ALGO"""
    # Arrange
    
    # Act
    
    # Assert
```

**Endpoint:**
```python
@http.route('/api/v1/RECURSO', type='json', auth='none', methods=['POST'], csrf=False, cors='*')
def NOME(self, **kwargs):
    """Descrição"""
    try:
        # Lógica
        return {'result': data}
    except Exception as e:
        return {'error': {'status': 500, 'message': str(e)}}
```

### 3. Git Commits Semânticos

```bash
feat: add login endpoint
fix: correct rate limiting logic
test: add test for token generator
docs: update README with login examples
refactor: split auth controller into services
```

---

## 📚 Recursos Extras

### Documentação Oficial

- **Odoo 18:** https://www.odoo.com/documentation/18.0/
- **Odoo ORM:** https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html
- **JWT:** https://jwt.io/introduction
- **OAuth 2.0:** https://oauth.net/2/

### Tutoriais Recomendados

1. **Python basics:** https://docs.python.org/3/tutorial/
2. **HTTP/REST APIs:** https://restfulapi.net/
3. **Docker basics:** https://docs.docker.com/get-started/

### Comunidade

- **Odoo Forum:** https://www.odoo.com/forum
- **Stack Overflow:** Tag `odoo`
- **GitHub Issues:** Projetos similares

---

## 🎯 Resumo dos 10 Passos

1. ✅ **Passo 1:** Campo `user_id` em OAuth Token (5min)
2. ✅ **Passo 2:** Serviço Rate Limiter (30min)
3. ✅ **Passo 3:** Serviço Token Generator (45min)
4. ✅ **Passo 4:** Serviço Audit Logger (20min)
5. ✅ **Passo 5:** Endpoint de Login (60min)
6. ✅ **Passo 6:** Endpoint de Logout (30min)
7. ✅ **Passo 7:** Atualizar Middleware (20min)
8. ✅ **Passo 8:** Testes Unitários (60min)
9. ✅ **Passo 9:** Testes de API (30min)
10. ✅ **Passo 10:** Validação e Docs (30min)

**Total:** 4-6 horas

---

**Boa sorte! 🚀**
