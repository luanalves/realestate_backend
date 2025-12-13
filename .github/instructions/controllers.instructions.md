---
applyTo: "18.0/extra-addons/**/controllers/**/*.py"
---

Instruções específicas para arquivos de controlador (controllers):

- Quando modificar arquivos correspondentes a `controllers/**/*.py`, NÃO remova nem substitua `@require_session` ou `@require_jwt` em funções que exponham `@http.route`.
- `require_jwt` valida o token de autenticação; `require_session` garante a identificação/estado do usuário (sessão). Trate-os como conceitos distintos.
- Se o endpoint for realmente público, marque claramente com `# public endpoint` acima do `@http.route`.

Exemplo aceitável:

```py
@http.route('/api/v1/example', type='http', auth='none')
@require_jwt
@require_session
def example(self, **kwargs):
    ...
```

Exemplo não aceitável:

```py
@http.route('/api/v1/example', type='http', auth='none')
# Copilot removed require_session -> não permitido
@require_jwt
def example(...):
    ...
```

Se desejar que estas instruções não sejam usadas por um agente específico, adicione `excludeAgent` ao frontmatter.
