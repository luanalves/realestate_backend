- criar teste e2e para validar se o menu imobiliario esta ativo, validar se o menu técnico esta aparecendo
- usar uuid para identificar imóveis ao invés de id sequencial
- criar teste e2e para criar usuários com níveis diferentes de rbac e testar os endpoints
- colocar as api's no padrão restfull com HATEOAS - https://medium.com/@mellomaths/a-import%C3%A2ncia-do-hateoas-em-apis-restful-1ca2dc081288
- SWAGGER
Criar funções auxiliares para gerar schemas comuns automaticamente
Validar sincronização entre documentação e implementação via testes automatizados
- integrar modulo de imobiliaria com company do odoo
- usuários administradores não devem acessar as api's dos usuários finais, somente usuários de imobiliarias devem poder fazer login e logout
- integrar mensageria (/opt/homebrew/var/www/realestate/odoo-docker/PLANO-CELERY-RABBITMQ.md)
- validar se tem arquivos duplicados no repositório e remover /opt/homebrew/var/www/realestate/odoo-docker/18.0/extra-addons/quicksol_estate/tests/api
- Configurar cors nos endpoints, mas a configuração deve ser dinamica
- o processo de login tem algumas formas de melhorar a performance, porque esta utilizando recursos do banco de dados, podemos substituir por cache na memoria (redis/memcached), também podemos utilizar tokens JWT para evitar consultas ao banco de dados.
- repassar limites da tabela thedevkitchen_api_session, falta indice e validar se faz sentido ter o ID porque o session_id já é unico e o id pode ser limitador para grandes volumes de dados
- incluir a consulta do session_id e do JWT no redis, para ganho de performance. Aproveitar e validar as melhorias das tabelas que gerenciam estas ações