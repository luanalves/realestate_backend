# Database Best Practices - Boas Práticas para Banco de Dados Relacional

## 🎯 Objetivo

Este documento estabelece padrões e boas práticas para design de banco de dados relacional que garantam:

- Integridade e consistência dos dados
- Performance e escalabilidade
- Facilidade de manutenção e evolução
- Clareza e legibilidade do modelo

⚠️ **Importante:** Estas são práticas **independentes de tecnologia ou framework**, aplicáveis a qualquer projeto com banco de dados relacional (PostgreSQL, MySQL, SQL Server, Oracle, etc.).

---

## 1. Normalização

### Regra: Aplicar no mínimo a Terceira Forma Normal (3NF)

A normalização reduz redundância e garante integridade dos dados.

#### Primeira Forma Normal (1NF)
- Cada coluna deve conter valores atômicos (indivisíveis)
- Cada coluna deve conter apenas um tipo de dado
- Cada linha deve ser única (ter uma chave primária)

#### ❌ Não Fazer
```sql
-- Valores não atômicos
CREATE TABLE pedido (
    id INT PRIMARY KEY,
    produtos VARCHAR(500)  -- "Produto1, Produto2, Produto3"
);
```

#### ✅ Fazer
```sql
CREATE TABLE pedido (
    id INT PRIMARY KEY,
    data_pedido TIMESTAMP NOT NULL
);

CREATE TABLE pedido_item (
    id INT PRIMARY KEY,
    pedido_id INT NOT NULL REFERENCES pedido(id),
    produto_id INT NOT NULL REFERENCES produto(id),
    quantidade INT NOT NULL
);
```

#### Segunda Forma Normal (2NF)
- Estar em 1NF
- Todos os atributos não-chave devem depender totalmente da chave primária

#### ❌ Não Fazer
```sql
-- nome_produto depende apenas de produto_id, não da chave composta
CREATE TABLE pedido_item (
    pedido_id INT,
    produto_id INT,
    quantidade INT,
    nome_produto VARCHAR(100),  -- Dependência parcial!
    PRIMARY KEY (pedido_id, produto_id)
);
```

#### ✅ Fazer
```sql
CREATE TABLE produto (
    id INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE pedido_item (
    pedido_id INT,
    produto_id INT REFERENCES produto(id),
    quantidade INT,
    PRIMARY KEY (pedido_id, produto_id)
);
```

#### Terceira Forma Normal (3NF)
- Estar em 2NF
- Nenhum atributo não-chave deve depender de outro atributo não-chave (dependência transitiva)

#### ❌ Não Fazer
```sql
-- cidade e estado têm dependência transitiva via cep
CREATE TABLE cliente (
    id INT PRIMARY KEY,
    nome VARCHAR(100),
    cep VARCHAR(10),
    cidade VARCHAR(100),  -- Depende do CEP, não do id!
    estado VARCHAR(2)     -- Depende do CEP, não do id!
);
```

#### ✅ Fazer
```sql
CREATE TABLE endereco (
    cep VARCHAR(10) PRIMARY KEY,
    cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL
);

CREATE TABLE cliente (
    id INT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cep VARCHAR(10) REFERENCES endereco(cep)
);
```

---

## 2. Convenções de Nomenclatura

### Regra: Usar snake_case em minúsculas para todos os objetos

```sql
-- ✅ Fazer
CREATE TABLE pedido_item (
    id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    preco_unitario DECIMAL(10,2)
);

-- ❌ Não Fazer
CREATE TABLE PedidoItem (...)      -- PascalCase
CREATE TABLE pedidoItem (...)      -- camelCase
CREATE TABLE "Pedido Item" (...)   -- Espaços
CREATE TABLE PEDIDO_ITEM (...)     -- UPPER_CASE
```

### Regra: Usar singular para nomes de tabelas

```sql
-- ✅ Fazer
CREATE TABLE cliente (...);
CREATE TABLE pedido (...);
CREATE TABLE produto (...);

-- ❌ Não Fazer
CREATE TABLE clientes (...);
CREATE TABLE pedidos (...);
CREATE TABLE produtos (...);
```

**Justificativa**: Cada linha representa UMA instância da entidade. Também evita problemas com plurais irregulares (person/people, child/children).

### Regra: Nomenclatura para Primary Keys

```sql
-- ✅ Fazer - usar "id" como nome padrão
CREATE TABLE cliente (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100)
);
```

### Regra: Nomenclatura para Foreign Keys

Usar o nome da tabela referenciada + `_id`:

```sql
-- ✅ Fazer
CREATE TABLE pedido (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL REFERENCES cliente(id),  -- cliente + _id
    vendedor_id INT REFERENCES funcionario(id)       -- funcionario + _id
);
```

### Regra: Nomenclatura para colunas de data/hora

- Sufixo `_at` para timestamps: `created_at`, `updated_at`, `deleted_at`
- Sufixo `_date` para datas: `birth_date`, `expiration_date`
- Sufixo `_time` para horários: `start_time`, `end_time`

```sql
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    birth_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP  -- Soft delete
);
```

### Regra: Nomenclatura para colunas booleanas

Usar prefixo `is_`, `has_`, `can_`:

```sql
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    has_newsletter BOOLEAN DEFAULT false,
    can_login BOOLEAN DEFAULT true
);
```

### Regra: Nomenclatura para tabelas de relacionamento N:N

Usar os nomes das duas tabelas em ordem alfabética ou ordem de leitura lógica:

```sql
-- ✅ Fazer
CREATE TABLE usuario_perfil (  -- usuario + perfil
    usuario_id INT REFERENCES usuario(id),
    perfil_id INT REFERENCES perfil(id),
    PRIMARY KEY (usuario_id, perfil_id)
);

-- Ou com verbo descritivo
CREATE TABLE usuario_has_perfil (...);
```

### Regra: Nomenclatura para Constraints

```sql
-- Primary Key: {tabela}_pkey
CONSTRAINT cliente_pkey PRIMARY KEY (id)

-- Foreign Key: {tabela}_{coluna}_fkey
CONSTRAINT pedido_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES cliente(id)

-- Unique: {tabela}_{coluna}_key
CONSTRAINT usuario_email_key UNIQUE (email)

-- Check: {tabela}_{coluna}_check
CONSTRAINT produto_preco_check CHECK (preco > 0)

-- Index: {tabela}_{coluna}_idx
CREATE INDEX cliente_email_idx ON cliente(email);
```

---

## 3. Chaves Primárias

### Regra: Toda tabela DEVE ter uma chave primária

Nunca criar tabelas sem PK.

### Regra: Preferir chaves primárias surrogate (artificiais)

```sql
-- ✅ Fazer - Chave surrogate
CREATE TABLE cliente (
    id SERIAL PRIMARY KEY,  -- Chave artificial
    cpf VARCHAR(11) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL
);

-- ❌ Evitar - Chave natural como PK
CREATE TABLE cliente (
    cpf VARCHAR(11) PRIMARY KEY,  -- CPF pode mudar, tem formato complexo
    nome VARCHAR(100) NOT NULL
);
```

**Justificativa**:
- Chaves naturais podem mudar (email, CPF em casos de erro)
- Chaves compostas complicam joins e foreign keys
- Inteiros são mais eficientes para indexação

### Regra: Usar UUID quando necessário distribuição ou segurança

```sql
-- Para sistemas distribuídos ou quando IDs não devem ser sequenciais
CREATE TABLE pedido (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero VARCHAR(20) UNIQUE NOT NULL,  -- Número legível para usuários
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Foreign Keys e Integridade Referencial

### Regra: SEMPRE definir foreign keys explicitamente

```sql
-- ✅ Fazer
CREATE TABLE pedido (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL,
    CONSTRAINT pedido_cliente_id_fkey 
        FOREIGN KEY (cliente_id) REFERENCES cliente(id)
);

-- ❌ Não Fazer - FK implícita apenas no código
CREATE TABLE pedido (
    id SERIAL PRIMARY KEY,
    cliente_id INT NOT NULL  -- Sem constraint! Permite dados órfãos
);
```

### Regra: Definir ações ON DELETE e ON UPDATE apropriadas

```sql
-- CASCADE: Deleta/atualiza registros filhos automaticamente
FOREIGN KEY (pedido_id) REFERENCES pedido(id) ON DELETE CASCADE

-- SET NULL: Define como NULL quando pai é deletado
FOREIGN KEY (gerente_id) REFERENCES funcionario(id) ON DELETE SET NULL

-- RESTRICT (padrão): Impede deleção se houver filhos
FOREIGN KEY (categoria_id) REFERENCES categoria(id) ON DELETE RESTRICT

-- NO ACTION: Similar a RESTRICT, mas verificado no final da transação
FOREIGN KEY (departamento_id) REFERENCES departamento(id) ON DELETE NO ACTION
```

### Guia de escolha:

| Cenário | Ação Recomendada |
|---------|------------------|
| Itens de pedido quando pedido é deletado | CASCADE |
| Funcionário quando gerente sai da empresa | SET NULL |
| Cliente com pedidos ativos | RESTRICT |
| Dados de auditoria | NO ACTION |

---

## 5. Índices

### Regra: Criar índices para colunas frequentemente usadas em WHERE, JOIN, ORDER BY

```sql
-- Índice para buscas frequentes
CREATE INDEX cliente_email_idx ON cliente(email);

-- Índice para foreign keys (melhora performance de JOINs)
CREATE INDEX pedido_cliente_id_idx ON pedido(cliente_id);

-- Índice composto para queries com múltiplas condições
CREATE INDEX pedido_status_data_idx ON pedido(status, created_at);
```

### Regra: Ordem das colunas em índices compostos importa

```sql
-- Se a query mais comum é: WHERE status = ? AND created_at > ?
CREATE INDEX pedido_status_data_idx ON pedido(status, created_at);

-- Este índice NÃO será usado eficientemente para: WHERE created_at > ?
-- Porque status vem primeiro no índice
```

### Regra: Evitar índices desnecessários

- Cada índice consome espaço e torna INSERT/UPDATE mais lentos
- Não criar índices em tabelas pequenas (< 1000 linhas)
- Não criar índices em colunas com baixa cardinalidade (ex: boolean)

### Regra: Usar índices parciais quando apropriado

```sql
-- Índice apenas para pedidos ativos (muito menor que índice completo)
CREATE INDEX pedido_ativo_idx ON pedido(created_at) 
WHERE status = 'ativo';

-- Índice apenas para registros não deletados (soft delete)
CREATE INDEX usuario_email_ativo_idx ON usuario(email) 
WHERE deleted_at IS NULL;
```

### Regra: Considerar índices UNIQUE para constraints de unicidade

```sql
-- UNIQUE constraint cria índice automaticamente
ALTER TABLE usuario ADD CONSTRAINT usuario_email_key UNIQUE (email);

-- Equivalente a:
CREATE UNIQUE INDEX usuario_email_idx ON usuario(email);
```

---

## 6. Tipos de Dados

### Regra: Usar o tipo mais apropriado e específico

```sql
-- ✅ Fazer
CREATE TABLE produto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,       -- Limite definido
    preco DECIMAL(10,2) NOT NULL,     -- Precisão exata para dinheiro
    quantidade INT NOT NULL,          -- Inteiro para quantidades
    is_ativo BOOLEAN DEFAULT true,    -- Boolean para flags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ❌ Não Fazer
CREATE TABLE produto (
    id INT PRIMARY KEY,
    nome TEXT,                        -- Sem limite
    preco FLOAT,                      -- Impreciso para dinheiro!
    quantidade VARCHAR(10),           -- String para número!
    is_ativo VARCHAR(1),              -- 'S'/'N' ao invés de boolean
    created_at VARCHAR(20)            -- String para data!
);
```

### Tabela de tipos recomendados:

| Dado | Tipo Recomendado | Evitar |
|------|------------------|--------|
| ID | SERIAL, BIGSERIAL, UUID | INT sem AUTO_INCREMENT |
| Dinheiro | DECIMAL(p,s), NUMERIC | FLOAT, DOUBLE |
| Texto curto | VARCHAR(n) | TEXT sem limite, CHAR |
| Texto longo | TEXT | VARCHAR(MAX) |
| Data | DATE | VARCHAR, INT |
| Data/Hora | TIMESTAMP WITH TIME ZONE | VARCHAR, separar data/hora |
| Booleano | BOOLEAN | INT, VARCHAR, CHAR(1) |
| Enum | ENUM ou tabela de lookup | VARCHAR com valores fixos |
| JSON | JSONB (PostgreSQL) | TEXT |

### Regra: Usar TIMESTAMP WITH TIME ZONE para datas/horas

```sql
-- ✅ Fazer - Armazena em UTC, converte na exibição
CREATE TABLE evento (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    data_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
    data_fim TIMESTAMP WITH TIME ZONE NOT NULL
);

-- ❌ Não Fazer - Ambiguidade de timezone
CREATE TABLE evento (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100),
    data_inicio TIMESTAMP NOT NULL  -- Qual timezone?
);
```

---

## 7. Constraints

### Regra: Usar NOT NULL sempre que possível

```sql
-- ✅ Fazer - Explícito sobre obrigatoriedade
CREATE TABLE cliente (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(20)  -- Opcional, pode ser NULL
);
```

### Regra: Usar CHECK constraints para validações simples

```sql
CREATE TABLE produto (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    preco DECIMAL(10,2) NOT NULL,
    estoque INT NOT NULL DEFAULT 0,
    
    CONSTRAINT produto_preco_check CHECK (preco > 0),
    CONSTRAINT produto_estoque_check CHECK (estoque >= 0)
);

CREATE TABLE pedido (
    id SERIAL PRIMARY KEY,
    status VARCHAR(20) NOT NULL,
    
    CONSTRAINT pedido_status_check 
        CHECK (status IN ('pendente', 'aprovado', 'enviado', 'entregue', 'cancelado'))
);
```

### Regra: Usar DEFAULT para valores padrão

```sql
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    login_count INT NOT NULL DEFAULT 0
);
```

---

## 8. Tabelas de Relacionamento

### Regra: Para N:N, criar tabela de junção com chave composta ou surrogate

```sql
-- Opção 1: Chave composta (recomendado para relações simples)
CREATE TABLE usuario_perfil (
    usuario_id INT NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    perfil_id INT NOT NULL REFERENCES perfil(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, perfil_id)
);

-- Opção 2: Chave surrogate (quando relação tem atributos próprios)
CREATE TABLE inscricao (
    id SERIAL PRIMARY KEY,
    aluno_id INT NOT NULL REFERENCES aluno(id),
    curso_id INT NOT NULL REFERENCES curso(id),
    data_inscricao DATE NOT NULL DEFAULT CURRENT_DATE,
    nota_final DECIMAL(4,2),
    status VARCHAR(20) NOT NULL DEFAULT 'ativo',
    UNIQUE (aluno_id, curso_id)
);
```

---

## 9. Soft Delete

### Regra: Usar soft delete para dados que precisam de histórico

```sql
CREATE TABLE cliente (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP  -- NULL = ativo, preenchido = deletado
);

-- Índice parcial para queries de ativos
CREATE INDEX cliente_email_ativo_idx ON cliente(email) 
WHERE deleted_at IS NULL;

-- View para facilitar queries
CREATE VIEW cliente_ativo AS
SELECT * FROM cliente WHERE deleted_at IS NULL;
```

### Regra: Considerar hard delete para dados sem necessidade de histórico

Soft delete adiciona complexidade. Usar apenas quando necessário para:
- Auditoria
- Recuperação de dados
- Integridade referencial

---

## 10. Auditoria

### Regra: Incluir campos de auditoria em tabelas importantes

```sql
CREATE TABLE pedido (
    id SERIAL PRIMARY KEY,
    -- Campos de negócio
    cliente_id INT NOT NULL REFERENCES cliente(id),
    valor_total DECIMAL(10,2) NOT NULL,
    
    -- Campos de auditoria
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INT REFERENCES usuario(id),
    updated_at TIMESTAMP,
    updated_by INT REFERENCES usuario(id)
);
```

### Regra: Para auditoria completa, usar tabela de histórico

```sql
CREATE TABLE pedido_historico (
    id SERIAL PRIMARY KEY,
    pedido_id INT NOT NULL,
    operacao VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    dados_antigos JSONB,
    dados_novos JSONB,
    usuario_id INT REFERENCES usuario(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 11. Particionamento

### Regra: Considerar particionamento para tabelas muito grandes

```sql
-- Particionamento por range de data
CREATE TABLE log_acesso (
    id SERIAL,
    usuario_id INT,
    endpoint VARCHAR(255),
    created_at TIMESTAMP NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE log_acesso_2024_01 PARTITION OF log_acesso
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE log_acesso_2024_02 PARTITION OF log_acesso
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

---

## 12. Documentação

### Regra: Documentar o modelo com comentários

```sql
COMMENT ON TABLE cliente IS 'Cadastro de clientes da plataforma';
COMMENT ON COLUMN cliente.id IS 'Identificador único do cliente';
COMMENT ON COLUMN cliente.cpf IS 'CPF do cliente (apenas números)';
COMMENT ON COLUMN cliente.tipo IS 'Tipo: PF=Pessoa Física, PJ=Pessoa Jurídica';
```

### Regra: Manter diagrama ER atualizado

- Usar ferramentas como dbdiagram.io, Lucidchart, ou DBeaver
- Versionar junto com o código
- Atualizar a cada mudança de schema

---

## 13. Migrations

### Regra: Toda alteração de schema deve ser via migration

```sql
-- migrations/2024_01_15_001_add_telefone_to_cliente.sql

-- UP
ALTER TABLE cliente ADD COLUMN telefone VARCHAR(20);

-- DOWN
ALTER TABLE cliente DROP COLUMN telefone;
```

### Regra: Migrations devem ser reversíveis

Sempre incluir operação de rollback.

### Regra: Migrations devem ser idempotentes quando possível

```sql
-- ✅ Fazer - Verifica se já existe
CREATE INDEX IF NOT EXISTS cliente_email_idx ON cliente(email);

ALTER TABLE cliente ADD COLUMN IF NOT EXISTS telefone VARCHAR(20);
```

### Regra: Evitar migrations destrutivas em produção

- Nunca dropar colunas diretamente
- Usar processo de deprecação:
  1. Marcar coluna como deprecated no código
  2. Parar de escrever na coluna
  3. Migrar dados se necessário
  4. Remover referências no código
  5. Dropar coluna após período de segurança

---

## 14. Performance

### Regra: Usar EXPLAIN ANALYZE para otimizar queries

```sql
EXPLAIN ANALYZE 
SELECT c.nome, COUNT(p.id) as total_pedidos
FROM cliente c
LEFT JOIN pedido p ON p.cliente_id = c.id
WHERE c.created_at > '2024-01-01'
GROUP BY c.id;
```

### Regra: Evitar SELECT *

```sql
-- ❌ Não Fazer
SELECT * FROM cliente WHERE id = 1;

-- ✅ Fazer
SELECT id, nome, email FROM cliente WHERE id = 1;
```

### Regra: Limitar resultados

```sql
-- ✅ Fazer
SELECT nome, email FROM cliente 
ORDER BY created_at DESC 
LIMIT 100;
```

---

## 📋 Checklist Rápido

### Ao criar uma nova tabela:

- [ ] Nome da tabela em singular e snake_case
- [ ] Chave primária definida (preferir `id SERIAL`)
- [ ] Foreign keys com constraints explícitas
- [ ] Ações ON DELETE/UPDATE definidas
- [ ] Colunas com tipos apropriados
- [ ] NOT NULL onde aplicável
- [ ] DEFAULT values onde apropriado
- [ ] CHECK constraints para validações
- [ ] Campos de auditoria (`created_at`, `updated_at`)
- [ ] Índices planejados (FKs, buscas frequentes)
- [ ] Comentários documentando a tabela
- [ ] Migration criada e testada
- [ ] Diagrama ER atualizado

### Ao criar índices:

- [ ] Índice necessário? (tabela > 1000 linhas)
- [ ] Coluna usada em WHERE/JOIN/ORDER BY?
- [ ] Ordem correta em índices compostos
- [ ] Considerar índice parcial se aplicável
- [ ] Nomeação seguindo padrão `{tabela}_{coluna}_idx`

### Ao fazer migrations:

- [ ] Migration possui UP e DOWN
- [ ] Migration é idempotente (IF EXISTS/IF NOT EXISTS)
- [ ] Não é destrutiva em produção
- [ ] Testada em ambiente de desenvolvimento
- [ ] Documentada no commit

---

## 🔗 Referências

- [Database Normalization](https://en.wikipedia.org/wiki/Database_normalization)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQL Style Guide](https://www.sqlstyle.guide/)
- [Use The Index, Luke!](https://use-the-index-luke.com/) - Guia completo sobre índices

---

## 🎯 Resumo das Regras de Ouro

1. **Normalização**: Mínimo 3NF para evitar redundância
2. **Nomenclatura**: snake_case, singular, consistente
3. **Primary Keys**: Sempre definir, preferir surrogate keys
4. **Foreign Keys**: Sempre explicitar, definir ON DELETE/UPDATE
5. **Índices**: Criar para colunas em WHERE/JOIN/ORDER BY
6. **Tipos**: Usar tipos apropriados (DECIMAL para dinheiro, TIMESTAMP WITH TIME ZONE)
7. **Constraints**: NOT NULL, CHECK, UNIQUE onde aplicável
8. **Auditoria**: created_at, updated_at em tabelas importantes
9. **Migrations**: Versionadas, reversíveis, idempotentes
10. **Performance**: EXPLAIN ANALYZE, evitar SELECT *, usar LIMIT
