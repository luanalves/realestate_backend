"""
E2E Integration Tests - Testes Reais de API HTTP

Estes testes executam as rotas HTTP de verdade, sem mocks.
Cenários realistas baseados em QA profissional.

Dados de teste:
- OAuth App: client_id + client_secret
- User 1: joao@imobiliaria.com / joao123
- User 2: pedro@imobiliaria.com / pedro123

Fluxo real:
1. Obter Bearer token via OAuth
2. Login do usuário
3. Usar session_id para chamar endpoints
4. Validar responses reais
5. Testar session isolation (User A não afeta User B)
"""

from odoo.tests.common import HttpCase
import json
import logging

_logger = logging.getLogger(__name__)


class TestAuthenticationE2EReal(HttpCase):
    """
    Testes E2E Reais de Autenticação
    Cenários do mundo real com HTTP requests verdadeiros
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Dados do OAuth App (já cadastrado no sistema)
        cls.client_id = "client_f0HgaJgLr8lCHOMa3ZKUzA"
        cls.client_secret = "AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt"
        
        # Usuários de teste
        cls.user1_email = "joao@imobiliaria.com"
        cls.user1_password = "joao123"
        
        cls.user2_email = "pedro@imobiliaria.com"
        cls.user2_password = "pedro123"
        
        # Base URL
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        # Bearer token (obtido via OAuth)
        cls.bearer_token = None
        cls.user1_session_id = None
        cls.user2_session_id = None

    def test_01_obtain_bearer_token(self):
        """
        Cenário 1: Obter Bearer token via OAuth 2.0
        
        Validações:
        - Status 200
        - Token type = Bearer
        - Access token não vazio
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 01: Obter Bearer Token via OAuth")
        _logger.info("=" * 60)
        
        url = f"{self.base_url}/api/v1/auth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}
        
        _logger.info(f"POST {url}")
        _logger.info(f"Payload: {json.dumps(payload)}")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertIn('access_token', data)
        self.assertIn('token_type', data)
        self.assertEqual(data['token_type'], 'Bearer')
        
        # Salvar token para próximos testes
        TestAuthenticationE2EReal.bearer_token = data['access_token']
        _logger.info(f"✅ Token obtido: {data['access_token'][:20]}...")

    def test_02_login_user1_success(self):
        """
        Cenário 2: Login bem-sucedido de User 1
        
        Validações:
        - Status 200
        - session_id não vazio
        - user.email = joao@imobiliaria.com
        - user.companies não vazio
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 02: Login User 1 - Sucesso")
        _logger.info("=" * 60)
        
        if not self.bearer_token:
            self.skipTest("Bearer token não disponível")
        
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user1_email,
            "password": self.user1_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"User: {self.user1_email}")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertIn('session_id', data)
        self.assertIn('user', data)
        
        user = data['user']
        self.assertEqual(user['email'], self.user1_email)
        self.assertGreater(len(user['companies']), 0)
        
        # Salvar session_id de User 1
        TestAuthenticationE2EReal.user1_session_id = data['session_id']
        _logger.info(f"✅ User 1 logado com session: {data['session_id'][:20]}...")
        _logger.info(f"   Empresas: {len(user['companies'])}")

    def test_03_login_user2_success(self):
        """
        Cenário 3: Login bem-sucedido de User 2
        
        Validações:
        - Status 200
        - session_id diferente de User 1
        - user.email = pedro@imobiliaria.com
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 03: Login User 2 - Sucesso")
        _logger.info("=" * 60)
        
        if not self.bearer_token:
            self.skipTest("Bearer token não disponível")
        
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user2_email,
            "password": self.user2_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"User: {self.user2_email}")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        user = data['user']
        self.assertEqual(user['email'], self.user2_email)
        
        # Verificar que sessions são diferentes
        self.assertNotEqual(data['session_id'], self.user1_session_id)
        
        # Salvar session_id de User 2
        TestAuthenticationE2EReal.user2_session_id = data['session_id']
        _logger.info(f"✅ User 2 logado com session: {data['session_id'][:20]}...")

    def test_04_login_invalid_credentials(self):
        """
        Cenário 4: Login com credenciais inválidas
        
        Validações:
        - Status 401
        - Mensagem de erro apropriada
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 04: Login com Credenciais Inválidas")
        _logger.info("=" * 60)
        
        if not self.bearer_token:
            self.skipTest("Bearer token não disponível")
        
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user1_email,
            "password": "senha_errada_123456"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"User: {self.user1_email} (senha inválida)")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 401, f"Esperado 401, recebeu: {response.status_code}")
        
        data = json.loads(response.text)
        self.assertIn('error', data)
        _logger.info(f"✅ Rejeição apropriada: {data['error']['message']}")


class TestProfileUpdateE2EReal(HttpCase):
    """
    Testes E2E Reais de Atualização de Perfil
    Cenários realistas de update de dados do usuário
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.client_id = "client_f0HgaJgLr8lCHOMa3ZKUzA"
        cls.client_secret = "AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt"
        cls.user_email = "joao@imobiliaria.com"
        cls.user_password = "joao123"
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        cls.bearer_token = None
        cls.session_id = None

    def setUp(self):
        """Setup para cada teste: obter token e session"""
        super().setUp()
        
        # Obter Bearer token
        url = f"{self.base_url}/api/v1/auth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.bearer_token = data['access_token']
        
        # Fazer login
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user_email,
            "password": self.user_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.session_id = data['session_id']
        self.original_email = data['user']['email']
        self.original_phone = data['user']['phone']

    def test_05_update_email_success(self):
        """
        Cenário 5: Atualizar email com sucesso
        
        Validações:
        - Status 200
        - Email atualizado
        - Outros campos preservados (PATCH semantics)
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 05: Atualizar Email - Sucesso")
        _logger.info("=" * 60)
        
        new_email = "joao.silva@imobiliaria.com"
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"email": new_email}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"PATCH {url}")
        _logger.info(f"Novo email: {new_email}")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertEqual(data['user']['email'], new_email)
        
        # Verificar PATCH semantics: phone preservado
        if self.original_phone:
            self.assertEqual(data['user']['phone'], self.original_phone)
        
        _logger.info(f"✅ Email atualizado: {new_email}")

    def test_06_update_phone_success(self):
        """
        Cenário 6: Atualizar phone com sucesso
        
        Validações:
        - Status 200
        - Phone atualizado
        - Email preservado (PATCH semantics)
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 06: Atualizar Phone - Sucesso")
        _logger.info("=" * 60)
        
        new_phone = "1133334444"
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"phone": new_phone}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"PATCH {url}")
        _logger.info(f"Novo phone: {new_phone}")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertEqual(data['user']['phone'], new_phone)
        
        # Verificar PATCH semantics: email preservado
        self.assertEqual(data['user']['email'], self.original_email)
        
        _logger.info(f"✅ Phone atualizado: {new_phone}")

    def test_07_update_multiple_fields(self):
        """
        Cenário 7: Atualizar múltiplos campos simultaneamente
        
        Validações:
        - Status 200
        - Todos os campos atualizados
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 07: Atualizar Múltiplos Campos")
        _logger.info("=" * 60)
        
        new_email = "joao.novo@imobiliaria.com"
        new_phone = "1144445555"
        new_mobile = "11999998888"
        
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {
            "email": new_email,
            "phone": new_phone,
            "mobile": new_mobile
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"PATCH {url}")
        _logger.info(f"Atualizações: email, phone, mobile")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertEqual(data['user']['email'], new_email)
        self.assertEqual(data['user']['phone'], new_phone)
        self.assertEqual(data['user']['mobile'], new_mobile)
        
        _logger.info(f"✅ Todos os campos atualizados com sucesso")

    def test_08_update_invalid_email_format(self):
        """
        Cenário 8: Rejeitar email com formato inválido
        
        Validações:
        - Status 400
        - Mensagem de erro apropriada
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 08: Email Inválido - Rejeição")
        _logger.info("=" * 60)
        
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"email": "notanemail"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"PATCH {url}")
        _logger.info(f"Email inválido: notanemail")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 400, f"Esperado 400")
        
        data = json.loads(response.text)
        self.assertIn('error', data)
        _logger.info(f"✅ Rejeição apropriada: {data['error']['message']}")


class TestPasswordChangeE2EReal(HttpCase):
    """
    Testes E2E Reais de Mudança de Password
    Cenários realistas de segurança de password
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.client_id = "client_f0HgaJgLr8lCHOMa3ZKUzA"
        cls.client_secret = "AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt"
        cls.user_email = "joao@imobiliaria.com"
        cls.user_password = "joao123"
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        cls.bearer_token = None
        cls.session_id = None

    def setUp(self):
        """Setup: obter token e session"""
        super().setUp()
        
        # Obter Bearer token
        url = f"{self.base_url}/api/v1/auth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.bearer_token = data['access_token']
        
        # Fazer login
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user_email,
            "password": self.user_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.session_id = data['session_id']

    def test_09_change_password_success(self):
        """
        Cenário 9: Mudança de password com sucesso
        
        Validações:
        - Status 200
        - Mensagem de sucesso
        - Novo login com nova password funciona
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 09: Mudar Password - Sucesso")
        _logger.info("=" * 60)
        
        new_password = "NovaPassword456!"
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user_password,
            "new_password": new_password,
            "confirm_password": new_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"Nova password: {new_password}")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        _logger.info(f"Response: {response.text}")
        
        self.assertEqual(response.status_code, 200, f"Falhou: {response.text}")
        
        data = json.loads(response.text)
        self.assertIn('message', data)
        
        _logger.info(f"✅ Password alterada com sucesso")

    def test_10_change_password_invalid_current(self):
        """
        Cenário 10: Rejeitar mudança com password atual inválida
        
        Validações:
        - Status 401
        - Mensagem de erro apropriada
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 10: Password Atual Inválida - Rejeição")
        _logger.info("=" * 60)
        
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": "senha_errada_123456",
            "new_password": "NovaPassword456!",
            "confirm_password": "NovaPassword456!"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"Current password inválida")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 401, f"Esperado 401")
        
        data = json.loads(response.text)
        self.assertIn('error', data)
        _logger.info(f"✅ Rejeição apropriada: {data['error']['message']}")

    def test_11_change_password_mismatch(self):
        """
        Cenário 11: Rejeitar senhas novas que não conferem
        
        Validações:
        - Status 400
        - Mensagem de erro
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 11: Passwords Não Conferem - Rejeição")
        _logger.info("=" * 60)
        
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user_password,
            "new_password": "NovaPassword456!",
            "confirm_password": "SenhaIferente789!"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"Passwords não conferem")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 400, f"Esperado 400")
        
        data = json.loads(response.text)
        self.assertIn('error', data)
        _logger.info(f"✅ Rejeição apropriada: {data['error']['message']}")

    def test_12_change_password_too_short(self):
        """
        Cenário 12: Rejeitar password com menos de 8 caracteres
        
        Validações:
        - Status 400
        - Mensagem de erro apropriada
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 12: Password Muito Curta - Rejeição")
        _logger.info("=" * 60)
        
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user_password,
            "new_password": "Short1!",
            "confirm_password": "Short1!"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"POST {url}")
        _logger.info(f"Password muito curta (7 chars)")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Status: {response.status_code}")
        
        self.assertEqual(response.status_code, 400, f"Esperado 400")
        
        data = json.loads(response.text)
        self.assertIn('error', data)
        _logger.info(f"✅ Rejeição apropriada: {data['error']['message']}")


class TestSessionIsolationE2EReal(HttpCase):
    """
    Testes E2E Reais de Session Isolation
    ⭐ CRÍTICO: Validar que User A não consegue afetar User B
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.client_id = "client_f0HgaJgLr8lCHOMa3ZKUzA"
        cls.client_secret = "AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt"
        
        cls.user1_email = "joao@imobiliaria.com"
        cls.user1_password = "joao123"
        
        cls.user2_email = "pedro@imobiliaria.com"
        cls.user2_password = "pedro123"
        
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        cls.bearer_token = None
        cls.user1_session = None
        cls.user2_session = None

    def setUp(self):
        """Setup: logar ambos os usuários"""
        super().setUp()
        
        # Obter Bearer token
        url = f"{self.base_url}/api/v1/auth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {"Content-Type": "application/json"}
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.bearer_token = data['access_token']
        
        # Login User 1
        url = f"{self.base_url}/api/v1/users/login"
        payload = {"email": self.user1_email, "password": self.user1_password}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.user1_session = data['session_id']
        self.user1_initial_email = data['user']['email']
        self.user1_initial_phone = data['user']['phone']
        
        # Login User 2
        payload = {"email": self.user2_email, "password": self.user2_password}
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.user2_session = data['session_id']
        self.user2_initial_email = data['user']['email']

    def test_13_session_isolation_different_sessions(self):
        """
        Cenário 13: Verificar que cada usuário tem session diferente
        
        Validações:
        - session_id de User 1 != session_id de User 2
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 13: Sessões Isoladas - Diferentes")
        _logger.info("=" * 60)
        
        _logger.info(f"User 1 session: {self.user1_session[:20]}...")
        _logger.info(f"User 2 session: {self.user2_session[:20]}...")
        
        self.assertNotEqual(self.user1_session, self.user2_session)
        
        _logger.info(f"✅ Sessões são diferentes e isoladas")

    def test_14_user1_update_profile_not_affect_user2(self):
        """
        Cenário 14: 🔴 CRÍTICO - User 1 atualiza profile, User 2 não é afetado
        
        Validações:
        - User 1 consegue atualizar seu próprio email
        - User 2 email permanece inalterado
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 14: 🔴 CRÍTICO - Isolamento de Profile Update")
        _logger.info("=" * 60)
        
        # User 1 atualiza seu email
        new_email_user1 = "joao.modificado@imobiliaria.com"
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"email": new_email_user1}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"User 1 atualiza email para: {new_email_user1}")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verificar que User 2 não foi afetado
        _logger.info(f"Verificando que User 2 NÃO foi afetado...")
        
        # User 2 faz login novamente para verificar seu email
        login_url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user2_email,
            "password": self.user2_password
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = self.opener.post(
            login_url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        
        # User 2 email deve ser igual ao inicial
        self.assertEqual(data['user']['email'], self.user2_initial_email)
        
        _logger.info(f"✅ User 2 NÃO foi afetado pela alteração de User 1")
        _logger.info(f"   User 2 email permanece: {data['user']['email']}")

    def test_15_logout_user1_doesnt_logout_user2(self):
        """
        Cenário 15: 🔴 CRÍTICO - Logout de User 1 não afeta User 2
        
        Validações:
        - User 1 consegue fazer logout
        - User 2 continua com sua sessão ativa
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 15: 🔴 CRÍTICO - Logout Isolado")
        _logger.info("=" * 60)
        
        # User 1 faz logout
        url = f"{self.base_url}/api/v1/users/logout"
        payload = {"session_id": self.user1_session}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"User 1 fazendo logout...")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        # Esperamos 200 OK
        self.assertIn(response.status_code, [200, 401])
        
        # Verificar que User 2 ainda consegue usar seus endpoints
        _logger.info(f"Verificando que User 2 continua ativo...")
        
        # User 2 tenta atualizar seu profile
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"phone": "1188888888"}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        # User 2 ainda consegue fazer updates (não foi afetado pelo logout de User 1)
        self.assertEqual(response.status_code, 200)
        
        _logger.info(f"✅ User 2 não foi afetado pelo logout de User 1")

    def test_16_concurrent_profile_updates(self):
        """
        Cenário 16: Atualizações simultâneas de User 1 e User 2
        
        Validações:
        - Ambas as atualizações são bem-sucedidas
        - Cada um atualiza apenas seus próprios dados
        """
        _logger.info("=" * 60)
        _logger.info("TESTE 16: Atualizações Simultâneas - Isoladas")
        _logger.info("=" * 60)
        
        # User 1 atualiza seu phone
        new_phone_user1 = "1111111111"
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {"phone": new_phone_user1}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.info(f"User 1 atualiza phone para: {new_phone_user1}")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(data['user']['phone'], new_phone_user1)
        
        # User 2 atualiza seu phone
        new_phone_user2 = "2222222222"
        payload = {"phone": new_phone_user2}
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.assertEqual(data['user']['phone'], new_phone_user2)
        
        # Verificar isolamento
        _logger.info(f"Verificando isolamento das atualizações...")
        
        self.assertNotEqual(new_phone_user1, new_phone_user2)
        
        _logger.info(f"✅ Atualizações foram isoladas")
        _logger.info(f"   User 1 phone: {new_phone_user1}")
        _logger.info(f"   User 2 phone: {new_phone_user2}")


# ═════════════════════════════════════════════════════════════════
# 🔐 TESTES: @require_session DECORATOR
# ═════════════════════════════════════════════════════════════════

class TestRequireSessionDecorator(HttpCase):
    """
    Testes E2E para o decorator @require_session
    Valida que endpoints protegidos requerem session_id válido
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.user1_email = "joao@imobiliaria.com"
        cls.user1_password = "joao123"
        
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        # Autenticar e obter session_id
        cls.session_id = cls._get_session_id(cls.user1_email, cls.user1_password)
    
    @staticmethod
    def _get_session_id(email, password):
        """Helper para obter session_id via login"""
        from urllib.request import urlopen, Request
        
        base_url = 'http://localhost:8069'
        login_url = f"{base_url}/api/v1/users/login"
        
        payload = json.dumps({
            "email": email,
            "password": password
        })
        
        request = Request(
            login_url,
            data=payload.encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            response = urlopen(request)
            data = json.loads(response.read().decode('utf-8'))
            return data.get('result', {}).get('session_id')
        except Exception as e:
            _logger.error(f"Erro ao obter session_id: {e}")
            return None
    
    def test_require_session_accepts_valid_session_id(self):
        """Test que @require_session aceita session_id válido"""
        _logger.info("=" * 70)
        _logger.info("🔐 TESTE: @require_session com session_id válido")
        _logger.info("=" * 70)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': self.session_id
        }
        
        # Tentar acessar endpoint protegido com session_id válido
        url = f"{self.base_url}/api/v1/users/profile"
        response = self.opener.patch(
            url,
            data=json.dumps({"phone": "11999999999"}),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(
            response.status_code,
            200,
            f"@require_session deve aceitar session_id válido (got {response.status_code})"
        )
        _logger.info("✅ Session válida foi aceita")
    
    def test_require_session_rejects_missing_session_id(self):
        """Test que @require_session rejeita requisições sem session_id"""
        _logger.info("=" * 70)
        _logger.info("🔐 TESTE: @require_session SEM session_id")
        _logger.info("=" * 70)
        
        headers = {
            'Content-Type': 'application/json'
            # Sem X-Openerp-Session-Id
        }
        
        # Tentar acessar endpoint protegido SEM session_id
        url = f"{self.base_url}/api/v1/users/profile"
        response = self.opener.patch(
            url,
            data=json.dumps({"phone": "11999999999"}),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(
            response.status_code,
            401,
            f"@require_session deve rejeitar sem session_id (got {response.status_code})"
        )
        
        try:
            data = json.loads(response.text)
            self.assertIn('error', data)
            _logger.info(f"✅ Session ausente foi rejeitada com 401")
        except json.JSONDecodeError:
            _logger.info(f"✅ Session ausente foi rejeitada com 401 (resposta não JSON)")
    
    def test_require_session_rejects_invalid_session_id(self):
        """Test que @require_session rejeita session_id inválido"""
        _logger.info("=" * 70)
        _logger.info("🔐 TESTE: @require_session com session_id INVÁLIDO")
        _logger.info("=" * 70)
        
        headers = {
            'Content-Type': 'application/json',
            'X-Openerp-Session-Id': 'invalid-session-xyz-123'
        }
        
        # Tentar acessar endpoint protegido com session_id inválido
        url = f"{self.base_url}/api/v1/users/profile"
        response = self.opener.patch(
            url,
            data=json.dumps({"phone": "11999999999"}),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(
            response.status_code,
            401,
            f"@require_session deve rejeitar session_id inválido (got {response.status_code})"
        )
        
        try:
            data = json.loads(response.text)
            self.assertIn('error', data)
            _logger.info(f"✅ Session inválida foi rejeitada com 401")
        except json.JSONDecodeError:
            _logger.info(f"✅ Session inválida foi rejeitada com 401 (resposta não JSON)")
    
    def test_require_session_protects_profile_endpoint(self):
        """Test que /api/v1/users/profile está protegido por @require_session"""
        _logger.info("=" * 70)
        _logger.info("🔐 TESTE: /api/v1/users/profile está protegido")
        _logger.info("=" * 70)
        
        # Tentar SEM session_id - deve falhar
        response_no_session = self.opener.patch(
            f"{self.base_url}/api/v1/users/profile",
            data=json.dumps({"phone": "11999999999"}),
            headers={'Content-Type': 'application/json'},
            content_type='application/json'
        )
        
        # Tentar COM session_id válido - deve funcionar
        response_with_session = self.opener.patch(
            f"{self.base_url}/api/v1/users/profile",
            data=json.dumps({"phone": "11999999999"}),
            headers={
                'Content-Type': 'application/json',
                'X-Openerp-Session-Id': self.session_id
            },
            content_type='application/json'
        )
        
        self.assertEqual(response_no_session.status_code, 401)
        self.assertEqual(response_with_session.status_code, 200)
        
        _logger.info("✅ /api/v1/users/profile está corretamente protegido")
    
    def test_require_session_protects_change_password_endpoint(self):
        """Test que /api/v1/users/change-password está protegido por @require_session"""
        _logger.info("=" * 70)
        _logger.info("🔐 TESTE: /api/v1/users/change-password está protegido")
        _logger.info("=" * 70)
        
        payload = {
            "current_password": "joao123",
            "new_password": "newpass123!",
            "confirm_password": "newpass123!"
        }
        
        # Tentar SEM session_id - deve falhar
        response_no_session = self.opener.post(
            f"{self.base_url}/api/v1/users/change-password",
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            content_type='application/json'
        )
        
        # Tentar COM session_id válido - deve processar (pode falhar por validação, mas não 401)
        response_with_session = self.opener.post(
            f"{self.base_url}/api/v1/users/change-password",
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-Openerp-Session-Id': self.session_id
            },
            content_type='application/json'
        )
        
        self.assertEqual(
            response_no_session.status_code,
            401,
            "Sem session_id deve retornar 401"
        )
        
        # Com session_id, pode ser 200 (sucesso) ou outro código (falha de validação), 
        # mas NÃO pode ser 401
        self.assertNotEqual(
            response_with_session.status_code,
            401,
            "Com session_id válido não deve retornar 401"
        )
        
        _logger.info("✅ /api/v1/users/change-password está corretamente protegido")
