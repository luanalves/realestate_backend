# ADR 006: Adoção do Git Flow como fluxo de trabalho

## Status
Aceito

## Contexto

Foi definido utilizar Git Flow como fluxo de trabalho padrão para gerenciamento de branches e commits no projeto.

O Git Flow é um modelo de branching criado por Vincent Driessen que organiza o desenvolvimento através de branches com propósitos específicos.

## Decisão

Utilizar **Git Flow** como fluxo de trabalho padrão para gerenciamento de branches e commits no projeto.

### Estrutura de Branches

#### Branches Principais (permanentes)

- **`main`** (ou `master`): Contém o código de produção estável. Todas as alterações nesta branch devem estar prontas para deploy e devem ser marcadas com tags de versão.

- **`develop`**: Branch de integração onde o código do próximo release é consolidado. Todas as features desenvolvidas são mescladas aqui antes de irem para produção.

#### Branches de Suporte (temporárias)

- **`feature/*`**: Branches para desenvolvimento de novas funcionalidades
  - Criadas a partir de: `develop`
  - Mescladas em: `develop`
  - Convenção de nomenclatura: `feature/nome-da-funcionalidade`
  - Exemplo: `feature/property-management`, `feature/oauth-integration`

- **`release/*`**: Branches de preparação para uma nova versão em produção
  - Criadas a partir de: `develop`
  - Mescladas em: `main` e `develop`
  - Convenção de nomenclatura: `release/x.y.z`
  - Exemplo: `release/1.0.0`, `release/1.1.0`
  - Devem ser marcadas com tag após merge em `main`

- **`hotfix/*`**: Branches para correções emergenciais em produção
  - Criadas a partir de: `main`
  - Mescladas em: `main` e `develop`
  - Convenção de nomenclatura: `hotfix/descricao-do-bug`
  - Exemplo: `hotfix/fix-authentication-error`
  - Devem ser marcadas com tag após merge em `main`

### Fluxo de Trabalho

#### Desenvolvimento de Features

```bash
# Criar nova feature
git checkout develop
git checkout -b feature/nova-funcionalidade

# Desenvolver e commitar
git add .
git commit -m "feat: implementa nova funcionalidade"

# Finalizar feature
git checkout develop
git merge feature/nova-funcionalidade
git branch -d feature/nova-funcionalidade
```

#### Preparação de Release

```bash
# Criar release
git checkout develop
git checkout -b release/1.0.0

# Ajustes finais, testes e correções
git commit -m "chore: prepara release 1.0.0"

# Finalizar release
git checkout main
git merge release/1.0.0
git tag -a v1.0.0 -m "Release 1.0.0"

git checkout develop
git merge release/1.0.0
git branch -d release/1.0.0
```

#### Correções de Emergência

```bash
# Criar hotfix
git checkout main
git checkout -b hotfix/correcao-critica

# Corrigir e commitar
git commit -m "fix: corrige bug crítico"

# Finalizar hotfix
git checkout main
git merge hotfix/correcao-critica
git tag -a v1.0.1 -m "Hotfix 1.0.1"

git checkout develop
git merge hotfix/correcao-critica
git branch -d hotfix/correcao-critica
```

### Versionamento Semântico

Seguiremos o [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):
- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Novas funcionalidades mantendo compatibilidade
- **PATCH**: Correções de bugs mantendo compatibilidade

### Ferramentas

Recomenda-se o uso da CLI `git-flow` para simplificar os comandos:

```bash
# Instalação (macOS)
brew install git-flow

# Inicialização
git flow init

# Comandos simplificados
git flow feature start nome-funcionalidade
git flow feature finish nome-funcionalidade

git flow release start 1.0.0
git flow release finish 1.0.0

git flow hotfix start correcao-critica
git flow hotfix finish correcao-critica
```

## Consequências

### Positivas

1. **Desenvolvimento Paralelo**: Múltiplos desenvolvedores podem trabalhar simultaneamente em diferentes features sem conflitos, pois cada funcionalidade fica isolada em sua própria branch.

2. **Organização Clara**: A estrutura de branches deixa explícito o propósito de cada alteração e o estado atual do projeto (desenvolvimento, homologação, produção).

3. **Releases Controladas**: A branch `release` permite um ambiente de homologação onde testes finais podem ser realizados antes do deploy em produção.

4. **Correções de Emergência**: Hotfixes podem ser aplicados rapidamente em produção sem interferir no trabalho em andamento na branch `develop`.

5. **Rastreabilidade**: Tags de versão facilitam a identificação de qual código está em produção e permitem rollback se necessário.

6. **Colaboração Facilitada**: Branches de feature permitem que múltiplos desenvolvedores colaborem em uma mesma funcionalidade de forma organizada.

7. **Histórico Limpo**: O histórico do Git fica mais organizado e fácil de entender, facilitando auditorias e investigações de bugs.

### Negativas

1. **Complexidade Inicial**: A curva de aprendizado pode ser íngreme para desenvolvedores não familiarizados com o fluxo.

2. **Branches de Longa Duração**: Features grandes podem criar branches de longa duração, potencialmente aumentando conflitos de merge.

3. **Overhead de Gerenciamento**: Requer disciplina da equipe para seguir o fluxo corretamente e manter branches atualizadas.

4. **Não Ideal para CI/CD Agressivo**: Pode dificultar práticas de deploy contínuo muito frequente (múltiplas vezes ao dia).

5. **Rebase Limitado**: O uso de `git rebase` deve ser evitado para manter a integridade do histórico compartilhado.

### Mitigações

- Realizar treinamento da equipe sobre Git Flow
- Documentar exemplos práticos no README do projeto
- Utilizar Pull Requests para revisão de código antes de merges
- Manter features pequenas e com ciclo de desenvolvimento curto
- Realizar merges frequentes da `develop` nas branches de feature para minimizar conflitos
- Utilizar ferramentas de integração contínua para validar branches automaticamente

### Referências

- [Artigo original do Git Flow por Vincent Driessen](https://nvie.com/posts/a-successful-git-branching-model/)
- [Git Flow: o que é, como e quando utilizar - Alura](https://www.alura.com.br/artigos/git-flow-o-que-e-como-quando-utilizar)
- [Semantic Versioning](https://semver.org/)
