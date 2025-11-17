# -*- coding: utf-8 -*-
"""
Testes de Integração para API OAuth

Estes testes validam os endpoints da API diretamente,
sem precisar de browser ou interface gráfica.

Comparação com Cypress:
- Cypress (tokens-lifecycle.cy.js): ~7 segundos, precisa de browser
- Pytest (este arquivo): <1 segundo, não precisa de browser

Execução:
    cd 18.0/extra-addons/api_gateway
    python -m pytest tests/integration/test_oauth_endpoints.py -v
"""

import json
import requests
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install', 'api_integration')
class TestOAuthEndpoints(HttpCase):
    """
    Testes de integração para endpoints OAuth
    
    Equivalente aos testes em cypress/e2e/tokens-lifecycle.cy.js
    mas muito mais rápido e sem dependência de browser.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Criar aplicação OAuth para testes
        cls.oauth_app = cls.env['oauth.application'].create({
            'name': 'Pytest Integration Test App',
            'description': 'Aplicação para testes de integração via Pytest',
            'active': True
        })
        
        cls.client_id = cls.oauth_app.client_id
        cls.client_secret = cls.oauth_app.client_secret
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
    
    @classmethod
    def tearDownClass(cls):
        """Limpar dados de teste"""
        # Revogar todos os tokens criados
        tokens = cls.env['oauth.token'].search([('application_id', '=', cls.oauth_app.id)])
        tokens.unlink()
        
        # Deletar aplicação
        cls.oauth_app.unlink()
        
        super().tearDownClass()

    # ==========================================
    # 1. GERAÇÃO DE TOKENS
    # ==========================================

    def test_01_generate_token_success(self):
        """
        Testa geração bem-sucedida de access_token e refresh_token
        
        Equivalente a: Cypress "Deve gerar access_token e refresh_token"
        """
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 200, "Deve retornar status 200")
        
        data = json.loads(response.content)
        self.assertIn('access_token', data, "Deve conter access_token")
        self.assertIn('refresh_token', data, "Deve conter refresh_token")
        self.assertEqual(data['token_type'], 'Bearer', "Token type deve ser Bearer")
        self.assertEqual(data['expires_in'], 3600, "Deve expirar em 3600 segundos")
        
        # Validar formato JWT (3 partes separadas por ponto)
        access_token = data['access_token']
        parts = access_token.split('.')
        self.assertEqual(len(parts), 3, "JWT deve ter 3 partes (header.payload.signature)")

    def test_02_reject_missing_client_id(self):
        """
        Testa rejeição quando client_id está ausente
        
        Equivalente a: Cypress "Deve rejeitar geração sem client_id"
        """
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 400, "Deve retornar status 400 Bad Request")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")
        self.assertEqual(data['error'], 'invalid_request', "Erro deve ser 'invalid_request'")

    def test_03_reject_missing_client_secret(self):
        """
        Testa rejeição quando client_secret está ausente
        
        Equivalente a: Cypress "Deve rejeitar geração sem client_secret"
        """
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 400, "Deve retornar status 400 Bad Request")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")

    def test_04_reject_invalid_credentials(self):
        """
        Testa rejeição de credenciais inválidas
        
        Equivalente a: Cypress "Deve rejeitar credenciais inválidas"
        """
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': 'invalid_client_id',
                'client_secret': 'invalid_client_secret'
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 401, "Deve retornar status 401 Unauthorized")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")
        self.assertEqual(data['error'], 'invalid_client', "Erro deve ser 'invalid_client'")

    def test_05_reject_invalid_grant_type(self):
        """
        Testa rejeição de grant_type inválido
        
        Equivalente a: Cypress "Deve rejeitar grant_type inválido"
        """
        response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'invalid_grant_type',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 400, "Deve retornar status 400 Bad Request")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")
        self.assertEqual(data['error'], 'unsupported_grant_type', "Erro deve ser 'unsupported_grant_type'")

    # ==========================================
    # 2. USO DE TOKENS VÁLIDOS
    # ==========================================

    def test_06_access_protected_endpoint_with_valid_token(self):
        """
        Testa acesso a endpoint protegido com token válido
        
        Equivalente a: Cypress "Deve acessar endpoint protegido com token válido"
        """
        # Primeiro, gerar token
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        access_token = json.loads(token_response.content)['access_token']
        
        # Agora, acessar endpoint protegido
        response = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        self.assertEqual(response.status_code, 200, "Deve retornar status 200")
        
        data = json.loads(response.content)
        self.assertIn('message', data, "Deve conter mensagem")
        self.assertIn('authenticated', data, "Deve conter flag de autenticação")
        self.assertTrue(data['authenticated'], "Usuário deve estar autenticado")

    def test_07_reject_access_without_authorization_header(self):
        """
        Testa rejeição de acesso sem Authorization header
        
        Equivalente a: Cypress "Deve rejeitar acesso sem Authorization header"
        """
        response = self.url_open('/api/v1/test/protected')
        
        self.assertEqual(response.status_code, 401, "Deve retornar status 401 Unauthorized")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")

    def test_08_reject_malformed_token(self):
        """
        Testa rejeição de token malformado
        
        Equivalente a: Cypress "Deve rejeitar token malformado"
        """
        response = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': 'Bearer malformed_token_xyz'}
        )
        
        self.assertEqual(response.status_code, 401, "Deve retornar status 401 Unauthorized")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")

    def test_09_reject_authorization_without_bearer(self):
        """
        Testa rejeição de Authorization header sem Bearer
        
        Equivalente a: Cypress "Deve rejeitar Authorization header sem Bearer"
        """
        response = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': 'InvalidScheme some_token'}
        )
        
        self.assertEqual(response.status_code, 401, "Deve retornar status 401 Unauthorized")

    # ==========================================
    # 3. RENOVAÇÃO DE TOKENS
    # ==========================================

    def test_10_refresh_access_token(self):
        """
        Testa renovação de access_token usando refresh_token
        
        Equivalente a: Cypress "Deve renovar access_token usando refresh_token"
        """
        # Gerar token inicial
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        token_data = json.loads(token_response.content)
        original_access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        
        # Renovar token
        refresh_response = self.url_open(
            '/api/v1/auth/refresh',
            data=json.dumps({
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(refresh_response.status_code, 200, "Deve retornar status 200")
        
        refresh_data = json.loads(refresh_response.content)
        new_access_token = refresh_data['access_token']
        
        # Validar que é um novo token
        self.assertNotEqual(
            original_access_token, 
            new_access_token, 
            "Novo access_token deve ser diferente do original"
        )
        
        # Validar que o novo token funciona
        protected_response = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {new_access_token}'}
        )
        
        self.assertEqual(protected_response.status_code, 200, "Novo token deve funcionar")

    def test_11_reject_invalid_refresh_token(self):
        """
        Testa rejeição de refresh_token inválido
        
        Equivalente a: Cypress "Deve rejeitar refresh_token inválido"
        """
        response = self.url_open(
            '/api/v1/auth/refresh',
            data=json.dumps({
                'grant_type': 'refresh_token',
                'refresh_token': 'invalid_refresh_token_xyz'
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(response.status_code, 401, "Deve retornar status 401 Unauthorized")
        
        data = json.loads(response.content)
        self.assertIn('error', data, "Deve conter campo 'error'")

    # ==========================================
    # 4. REVOGAÇÃO DE TOKENS
    # ==========================================

    def test_12_revoke_token_via_authorization_header(self):
        """
        Testa revogação de token via Authorization header
        
        Equivalente a: Cypress "Deve revogar token via Authorization header"
        """
        # Gerar token
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        access_token = json.loads(token_response.content)['access_token']
        
        # Revogar token
        revoke_response = self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({}),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        self.assertEqual(revoke_response.status_code, 200, "Deve retornar status 200")

    def test_13_reject_revoked_token(self):
        """
        Testa que token revogado não pode ser usado
        
        Equivalente a: Cypress "Não deve permitir uso de token revogado"
        """
        # Gerar token
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        access_token = json.loads(token_response.content)['access_token']
        
        # Revogar token
        self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({}),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        
        # Tentar usar token revogado
        protected_response = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        self.assertEqual(protected_response.status_code, 401, "Deve retornar status 401")
        
        data = json.loads(protected_response.content)
        self.assertIn('error', data, "Deve conter erro")

    def test_14_revoke_token_via_body_json(self):
        """
        Testa revogação de token via corpo JSON
        
        Equivalente a: Cypress "Deve revogar token via body JSON"
        """
        # Gerar token
        token_response = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        access_token = json.loads(token_response.content)['access_token']
        
        # Revogar via body
        revoke_response = self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({'token': access_token}),
            headers={'Content-Type': 'application/json'}
        )
        
        self.assertEqual(revoke_response.status_code, 200, "Deve retornar status 200")

    def test_15_revoke_nonexistent_token_success_rfc7009(self):
        """
        Testa que revogar token inexistente retorna sucesso (RFC 7009)
        
        Equivalente a: Cypress "Deve retornar sucesso mesmo para token inexistente"
        """
        response = self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({'token': 'nonexistent_token_xyz'}),
            headers={'Content-Type': 'application/json'}
        )
        
        # RFC 7009: Servidor deve retornar sucesso mesmo para tokens inválidos
        self.assertEqual(response.status_code, 200, "Deve retornar status 200 (RFC 7009)")

    # ==========================================
    # 5. MÚLTIPLOS TOKENS
    # ==========================================

    def test_16_allow_multiple_active_tokens(self):
        """
        Testa que aplicação pode ter múltiplos tokens ativos
        
        Equivalente a: Cypress "Deve permitir múltiplos tokens ativos"
        """
        # Gerar primeiro token
        response1 = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        token1 = json.loads(response1.content)['access_token']
        
        # Gerar segundo token
        response2 = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        
        token2 = json.loads(response2.content)['access_token']
        
        # Tokens devem ser diferentes
        self.assertNotEqual(token1, token2, "Tokens devem ser diferentes")
        
        # Ambos devem funcionar
        protected1 = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {token1}'}
        )
        
        protected2 = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {token2}'}
        )
        
        self.assertEqual(protected1.status_code, 200, "Token 1 deve funcionar")
        self.assertEqual(protected2.status_code, 200, "Token 2 deve funcionar")

    def test_17_revoke_only_specified_token(self):
        """
        Testa que revogar um token não afeta outros
        
        Equivalente a: Cypress "Deve revogar apenas o token especificado"
        """
        # Gerar dois tokens
        response1 = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        token1 = json.loads(response1.content)['access_token']
        
        response2 = self.url_open(
            '/api/v1/auth/token',
            data=json.dumps({
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }),
            headers={'Content-Type': 'application/json'}
        )
        token2 = json.loads(response2.content)['access_token']
        
        # Revogar apenas token1
        self.url_open(
            '/api/v1/auth/revoke',
            data=json.dumps({'token': token1}),
            headers={'Content-Type': 'application/json'}
        )
        
        # Token1 deve estar revogado
        protected1 = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {token1}'}
        )
        self.assertEqual(protected1.status_code, 401, "Token1 deve estar revogado")
        
        # Token2 deve continuar funcionando
        protected2 = self.url_open(
            '/api/v1/test/protected',
            headers={'Authorization': f'Bearer {token2}'}
        )
        self.assertEqual(protected2.status_code, 200, "Token2 deve continuar funcionando")
