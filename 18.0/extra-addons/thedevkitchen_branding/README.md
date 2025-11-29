# TheDevKitchen Branding

Módulo de customização visual e branding para aplicações Odoo.

## Funcionalidades

Este módulo customiza a interface do Odoo removendo elementos padrão desnecessários:

### Tela de Login
- ✅ Remove o link "Manage Databases"
- ✅ Remove o texto "Powered by Odoo"
- ✅ Remove o link "Choose a user"
- ✅ Interface de login limpa e profissional

## Instalação

### 1. O módulo já está no diretório de addons

O módulo está localizado em:
```
18.0/extra-addons/thedevkitchen_branding/
```

### 2. Reiniciar o Odoo

```bash
cd 18.0
docker compose restart odoo
```

### 3. Ativar modo desenvolvedor

1. Acesse o Odoo: http://localhost:8069
2. Faça login com usuário `admin` / senha `admin`
3. Vá em **Settings** (Configurações)
4. No canto inferior direito, clique em **Activate the developer mode**

### 4. Atualizar lista de módulos

1. Vá em **Apps** (Aplicações)
2. Clique no menu (☰) e selecione **Update Apps List**
3. Confirme a atualização

### 5. Instalar o módulo

1. Ainda em **Apps**, remova o filtro "Apps" da busca
2. Busque por "TheDevKitchen Branding"
3. Clique em **Install**

### 6. Fazer logout e visualizar

1. Faça logout da aplicação
2. A tela de login agora estará customizada sem os elementos removidos

## Estrutura do Módulo

```
thedevkitchen_branding/
├── __init__.py
├── __manifest__.py
├── README.md
├── views/
│   └── webclient_templates.xml    # Templates XML que sobrescrevem a view de login
└── static/
    └── src/
        └── scss/
            └── login.scss          # Estilos CSS customizados
```

## Desenvolvimento

Para adicionar mais customizações:

1. **Templates XML**: Edite `views/webclient_templates.xml`
2. **Estilos CSS**: Edite `static/src/scss/login.scss`
3. **Após modificações**: Reinicie o Odoo e atualize o módulo em Apps

## Notas Técnicas

- O módulo herda templates do módulo `web`
- Usa `xpath` para remover elementos específicos do DOM
- Aplica CSS adicional via assets do frontend
- Compatível com Odoo 18.0

## Autor

TheDevKitchen - https://www.thedevkitchen.com

## Licença

LGPL-3
