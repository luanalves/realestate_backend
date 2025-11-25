- criar teste e2e para validar se o menu imobiliario esta ativo, validar se o menu técnico esta aparecendo
- usar uuid para identificar imóveis ao invés de id sequencial
- criar teste e2e para criar usuários com níveis diferentes de rbac e testar os endpoints
- colocar as api's no padrão restfull com HATEOAS - https://medium.com/@mellomaths/a-import%C3%A2ncia-do-hateoas-em-apis-restful-1ca2dc081288
- SWAGGER
Mitigações
Documentar endpoints incrementalmente, priorizando os mais utilizados
Criar funções auxiliares para gerar schemas comuns automaticamente
Considerar modularização em múltiplos arquivos se necessário
Validar sincronização entre documentação e implementação via testes automatizados