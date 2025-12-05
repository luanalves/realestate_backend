# ADR 008: Segurança de APIs em Ambiente Multi-Tenancy

## Status
Aceito

## Contexto

O sistema opera em modelo **multi-tenancy** onde múltiplas imobiliárias (companies) compartilham a mesma infraestrutura. Cada usuário está vinculado a uma ou mais empresas via `estate_company_ids` no modelo `res.users`.

**Problema:** A implementação atual da API REST possui vulnerabilidades que permitem:
- Usuário A acessar dados da Company B via IDOR (Insecure Direct Object Reference)
- Criação de registros vinculados a empresas não autorizadas (Mass Assignment)
- Bypass de record rules do Odoo via uso de `.sudo()`
- Alteração de `company_ids` em updates sem validação
- Ausência de auditoria de tentativas de acesso não autorizado

**Risco:** Vazamento de dados entre imobiliárias, violando isolamento multi-tenant e conformidade com LGPD/GDPR.

## Decisão

Adotar **5 princípios de segurança obrigatórios** para todos os endpoints de API que manipulam dados transacionais:

### 1. Filtro Obrigatório no ORM
- **NUNCA** usar `.sudo()` em queries de dados transacionais
- **SEMPRE** aplicar filtro de empresa no domínio da query ANTES de executar
- Usar `request.env` (contexto de usuário), não `.sudo()`

### 2. Validação de Company IDs
- **VALIDAR** que usuário tem acesso a TODAS as empresas especificadas ANTES de CREATE
- **REJEITAR** requisições que tentem atribuir empresas não autorizadas
- **AUTO-ATRIBUIR** empresa padrão do usuário se `company_ids` não fornecido

### 3. Imutabilidade de Company IDs
- **PROIBIR** alteração de `company_ids` via UPDATE/PATCH na API
- Transferências entre empresas devem ser feitas apenas via interface administrativa

### 4. Auditoria Obrigatória
- **LOGAR** todas as tentativas de acesso (sucesso e falha)
- Registrar: usuário, recurso, operação, timestamp, IP, resultado

### 5. Respostas Genéricas
- **RETORNAR** 404 para recursos inexistentes OU inacessíveis
- **NÃO REVELAR** se recurso existe mas usuário não tem acesso (previne enumeração)

## Regras de Implementação

### ✅ SEMPRE

- Filtrar queries por empresa: `domain + self._get_company_domain(user)`
- Usar `request.env` (contexto de usuário), não `.sudo()`
- Validar `company_ids` antes de CREATE
- Proibir alteração de `company_ids` em UPDATE
- Logar todas as tentativas de acesso (sucesso e falha)
- Retornar 404 genérico para recursos inacessíveis
- Auto-atribuir empresa padrão quando `company_ids` não fornecido

### ❌ NUNCA

- Usar `.sudo()` em queries de dados transacionais
- Buscar registro antes de aplicar filtro de empresa
- Aceitar `company_ids` do cliente sem validação
- Incluir `company_ids` em whitelist de campos editáveis
- Retornar mensagens que revelem existência de recursos inacessíveis (usar 404, não 403)
- Ignorar logging de tentativas de acesso falhadas

---

## Consequências

### Positivas

- **Isolamento garantido** - Dados de diferentes imobiliárias completamente segregados
- **Conformidade LGPD/GDPR** - Auditoria rastreável de todos os acessos
- **Prevenção de IDOR** - Impossível enumerar recursos de outras empresas
- **Detecção de ataques** - Logs permitem identificar tentativas de invasão
- **Padrão replicável** - Modelo seguro aplicável a todos os endpoints

### Negativas

- **Overhead de ~10-20ms/request** - Validações e logging adicionam latência (aceitável)
- **Crescimento de logs** - Tabela de auditoria requer política de retenção (90 dias)
- **Transferências via admin apenas** - API não permite mover recursos entre empresas
- **Complexidade aumentada** - Mais código de validação em cada endpoint

### Riscos Mitigados

- **IDOR** (OWASP A01:2021 - Broken Access Control)
- **Mass Assignment** (OWASP A01:2021)
- **Information Disclosure** (OWASP A01:2021)
- **Insufficient Logging** (OWASP A09:2021)

## Referências

- OWASP Top 10 2021: https://owasp.org/Top10/
- OWASP API Security: https://owasp.org/API-Security/
- CWE-639: Authorization Bypass Through User-Controlled Key
- ADR-003: Mandatory Test Coverage
- Odoo Security: https://www.odoo.com/documentation/18.0/developer/reference/backend/security.html
