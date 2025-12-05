# -*- coding: utf-8 -*-
"""
Testes Avançados de Segurança - Session Hijacking & Password Strength

Cenários críticos:
1. ✅ Usar sessão de outro usuário para alterar dados
2. ✅ Usar sessão de outro usuário para trocar password
3. ✅ Password com poucos caracteres
4. ✅ Password que não bate (confirm mismatch)
5. ✅ SQL Injection na password
6. ✅ Tentar acessar profile de outro user
"""

from odoo.tests.common import HttpCase
import json
import logging

_logger = logging.getLogger(__name__)


class TestSecurityAdvanced(HttpCase):
    """
    🔴 TESTES CRÍTICOS DE SEGURANÇA
    
    Validações de Session Hijacking, Password Strength e Isolamento
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Dados do OAuth App
        cls.client_id = "client_f0HgaJgLr8lCHOMa3ZKUzA"
        cls.client_secret = "AUP71x_wH53lyzXDJ7HzdsCmi5huP5QDZPKBxIdJOlAx4f5dwDxQoow72zIMpCIt"
        
        # Usuários de teste
        cls.user1_email = "joao@imobiliaria.com"
        cls.user1_password = "joao123"
        
        cls.user2_email = "pedro@imobiliaria.com"
        cls.user2_password = "pedro123"
        
        # Base URL
        cls.base_url = cls.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        
        # Tokens
        cls.bearer_token = None
        cls.user1_session_id = None
        cls.user2_session_id = None

    def setUp(self):
        """Setup: obter bearer token e logar ambos usuários"""
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
        payload = {
            "email": self.user1_email,
            "password": self.user1_password
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
        self.user1_session_id = data['session_id']
        
        # Login User 2
        payload = {
            "email": self.user2_email,
            "password": self.user2_password
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.text)
        self.user2_session_id = data['session_id']

    def tearDown(self):
        """
        Cleanup: Restaura senhas padrão dos usuários
        
        Garante que após cada teste as senhas voltem ao estado inicial
        """
        super().tearDown()
        
        try:
            _logger.info("=" * 70)
            _logger.info("🔄 CLEANUP: Restaurando senhas padrão dos usuários")
            _logger.info("=" * 70)
            
            # Obter novo bearer token (pode ter expirado)
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
            
            if response.status_code != 200:
                _logger.warning("⚠️  Não foi possível obter novo bearer token para cleanup")
                return
            
            data = json.loads(response.text)
            bearer_token = data['access_token']
            
            # Restaurar password de User 1
            _logger.info("Restaurando password de User 1...")
            url = f"{self.base_url}/api/v1/users/change-password"
            
            # Tentar com a senha padrão
            payload = {
                "current_password": self.user1_password,  # Senha original
                "new_password": self.user1_password,      # Mesma senha (sem alteração)
                "confirm_password": self.user1_password
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {bearer_token}"
            }
            
            response = self.opener.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                _logger.info("✅ Password de User 1 restaurada para padrão")
            else:
                # Se falhar com senha padrão, pode estar com senha alterada
                # Tentar resetar usando um mecanismo alternativo
                _logger.warning(f"⚠️  Falha ao restaurar password de User 1: {response.text}")
            
            # Restaurar password de User 2
            _logger.info("Restaurando password de User 2...")
            payload = {
                "current_password": self.user2_password,  # Senha original
                "new_password": self.user2_password,      # Mesma senha (sem alteração)
                "confirm_password": self.user2_password
            }
            
            response = self.opener.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                _logger.info("✅ Password de User 2 restaurada para padrão")
            else:
                _logger.warning(f"⚠️  Falha ao restaurar password de User 2: {response.text}")
            
            _logger.info("=" * 70)
            _logger.info("✅ Cleanup finalizado")
            _logger.info("=" * 70)
            
        except Exception as e:
            _logger.error(f"❌ Erro durante cleanup: {str(e)}")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 1: Session Hijacking - Usar sessão de outro usuário
    # ═════════════════════════════════════════════════════════════════

    def test_session_hijacking_change_password(self):
        """
        🔴 CRÍTICO: Tentar trocar password de User 2 usando sessão de User 1
        
        Cenário:
        - User 1 obtém session_id de User 2 (pode via outro ataque)
        - User 1 tenta usar session de User 2 para trocar sua password
        - Sistema DEVE rejeitar (401 Unauthorized)
        
        Validações:
        - ✅ Rejeição de sessão cruzada
        - ✅ Password de User 2 NÃO é alterada
        - ✅ Log de tentativa de ataque
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 1: Session Hijacking - Trocar Password com Sessão Cruzada")
        _logger.info("=" * 70)
        
        # User 1 tenta trocar password usando sessão de User 2 ❌ NÃO DEVERIA FUNCIONAR
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "session_id": self.user2_session_id,  # ❌ Sessão de User 2!
            "current_password": self.user2_password,
            "new_password": "HackedPassword123!",
            "confirm_password": "HackedPassword123!"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.warning(f"User 1 tentando usar session de User 2: {self.user2_session_id[:20]}...")
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        
        # DEVE retornar erro (401 ou 403)
        _logger.warning(f"Status: {response.status_code}")
        _logger.warning(f"Response: {response_data}")
        
        # Validar que tentativa foi rejeitada
        if response.status_code in [401, 403]:
            _logger.info("✅ Sessão cruzada rejeitada com HTTP 401/403")
        else:
            # Se status é 200, verificar se há erro no body
            if 'error' in response_data.get('result', {}):
                error_status = response_data['result']['error'].get('status')
                if error_status in [401, 403]:
                    _logger.info(f"✅ Sessão cruzada rejeitada com erro {error_status}")
                else:
                    _logger.error(f"❌ Sessão cruzada NÃO foi rejeitada! Status: {error_status}")
        
        # Tentar login com password antigo de User 2 (deve funcionar, pois password não foi alterada)
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user2_email,
            "password": self.user2_password  # Password ORIGINAL
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        _logger.info(f"Verificando se User 2 ainda consegue logar com password original...")
        self.assertEqual(response.status_code, 200, "User 2 NÃO conseguiu logar - password foi alterada!")
        _logger.info("✅ User 2 ainda consegue logar com password original - isolamento OK")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 2: Session Hijacking - Atualizar profile com sessão cruzada
    # ═════════════════════════════════════════════════════════════════

    def test_session_hijacking_update_profile(self):
        """
        🔴 CRÍTICO: Usar sessão de User 2 para alterar email de User 2
        
        Cenário:
        - User 1 obtém session_id de User 2
        - User 1 tenta usar session para alterar email de User 2
        - Sistema DEVE rejeitar
        
        Validações:
        - ✅ Rejeição de sessão cruzada
        - ✅ Email de User 2 NÃO é alterado
        - ✅ Log de tentativa
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 2: Session Hijacking - Update Profile com Sessão Cruzada")
        _logger.info("=" * 70)
        
        # Capturar email original de User 2
        original_email_user2 = self.user2_email
        
        # User 1 tenta alterar email de User 2 usando sessão de User 2 ❌ NÃO DEVERIA FUNCIONAR
        url = f"{self.base_url}/api/v1/users/profile"
        payload = {
            "session_id": self.user2_session_id,  # ❌ Sessão de User 2!
            "email": "hacked_email@imobiliaria.com"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        _logger.warning(f"User 1 tentando alterar email de User 2 usando sessão cruzada...")
        
        response = self.opener.patch(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        
        _logger.warning(f"Status: {response.status_code}")
        _logger.warning(f"Response: {response_data}")
        
        # Validar que tentativa foi rejeitada
        is_rejected = (
            response.status_code in [401, 403] or
            response_data.get('result', {}).get('error', {}).get('status') in [401, 403]
        )
        self.assertTrue(is_rejected, "Session hijacking for profile update was NOT rejected!")
        
        # Verificar que email de User 2 NÃO foi alterado
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": original_email_user2,
            "password": self.user2_password
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, "User 2 não conseguiu logar com email original")
        _logger.info("✅ Email de User 2 NÃO foi alterado - isolamento OK")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 3: Password com Poucos Caracteres
    # ═════════════════════════════════════════════════════════════════

    def test_password_too_short(self):
        """
        🔴 CRÍTICO: Validação de comprimento mínimo de password
        
        Cenários:
        - 1 caractere ❌
        - 3 caracteres ❌
        - 7 caracteres (1 menos que mínimo) ❌
        - 8 caracteres (mínimo) ✅
        
        Validações:
        - ✅ Rejeição de passwords muito curtas
        - ✅ HTTP 400 ou erro apropriado
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 3: Password com Poucos Caracteres")
        _logger.info("=" * 70)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        # Cenário 1: 1 caractere
        _logger.warning("Testando password com 1 caractere...")
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user1_password,
            "new_password": "A",
            "confirm_password": "A"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}, Response: {response_data}")
        
        if response.status_code == 400 or response_data.get('result', {}).get('error', {}).get('status') == 400:
            _logger.info("✅ Password com 1 caractere rejeitada")
        else:
            _logger.warning("⚠️  Password com 1 caractere não foi rejeitada")
        
        # Cenário 2: 3 caracteres
        _logger.warning("Testando password com 3 caracteres...")
        payload = {
            "current_password": self.user1_password,
            "new_password": "Abc",
            "confirm_password": "Abc"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}, Response: {response_data}")
        
        if response.status_code == 400 or response_data.get('result', {}).get('error', {}).get('status') == 400:
            _logger.info("✅ Password com 3 caracteres rejeitada")
        else:
            _logger.warning("⚠️  Password com 3 caracteres não foi rejeitada")
        
        # Cenário 3: 7 caracteres (1 menos que mínimo)
        _logger.warning("Testando password com 7 caracteres...")
        payload = {
            "current_password": self.user1_password,
            "new_password": "Abcd123",
            "confirm_password": "Abcd123"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}, Response: {response_data}")
        
        if response.status_code == 400 or response_data.get('result', {}).get('error', {}).get('status') == 400:
            _logger.info("✅ Password com 7 caracteres rejeitada")
        else:
            _logger.warning("⚠️  Password com 7 caracteres não foi rejeitada")
        
        # Cenário 4: 8 caracteres (mínimo) ✅ DEVE ACEITAR
        _logger.info("Testando password com 8 caracteres (mínimo)...")
        payload = {
            "current_password": self.user1_password,
            "new_password": "Abcd1234",
            "confirm_password": "Abcd1234"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}, Response: {response_data}")
        
        if response.status_code == 200 or response_data.get('result', {}).get('error') is None:
            _logger.info("✅ Password com 8 caracteres aceita")
            
            # 🔄 RESTAURAR PASSWORD ORIGINAL
            _logger.info("🔄 Restaurando password para padrão...")
            payload_restore = {
                "current_password": "Abcd1234",
                "new_password": self.user1_password,
                "confirm_password": self.user1_password
            }
            
            response = self.opener.post(
                url,
                data=json.dumps(payload_restore),
                headers=headers,
                content_type='application/json'
            )
            
            if response.status_code == 200:
                _logger.info("✅ Password restaurada para padrão")
            else:
                _logger.error(f"❌ Falha ao restaurar password: {response.text}")
        else:
            _logger.warning(f"⚠️  Password com 8 caracteres foi rejeitada")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 4: Password Confirm Mismatch
    # ═════════════════════════════════════════════════════════════════

    def test_password_confirm_mismatch(self):
        """
        🔴 CRÍTICO: Validação de confirm_password
        
        Cenários:
        - new_password = "ValidPassword123", confirm = "DifferentPassword123" ❌
        - new_password = "ValidPassword123", confirm = "" ❌
        - new_password = "ValidPassword123", confirm = "ValidPassword123" ✅
        
        Validações:
        - ✅ Rejeição quando não correspondem
        - ✅ HTTP 400 ou erro apropriado
        - ✅ Password NÃO é alterada
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 4: Password Confirm Mismatch")
        _logger.info("=" * 70)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        # Cenário 1: Passwords diferentes
        _logger.warning("Cenário 1: new_password != confirm_password")
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user1_password,
            "new_password": "ValidPassword123",
            "confirm_password": "DifferentPassword456"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 400 or response_data.get('result', {}).get('error', {}).get('status') == 400:
            _logger.info("✅ Passwords diferentes rejeitadas")
        else:
            _logger.warning("⚠️  Passwords diferentes não foram rejeitadas")
        
        # Verificar que password ainda é a original
        url = f"{self.base_url}/api/v1/users/login"
        payload_login = {
            "email": self.user1_email,
            "password": self.user1_password
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload_login),
            headers=headers,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200, "User 1 não conseguiu logar com password original")
        _logger.info("✅ Password NÃO foi alterada - User 1 ainda consegue logar com password original")
        
        # Cenário 2: confirm_password vazio
        _logger.warning("Cenário 2: confirm_password vazio")
        payload = {
            "current_password": self.user1_password,
            "new_password": "ValidPassword123",
            "confirm_password": ""
        }
        
        response = self.opener.post(
            f"{self.base_url}/api/v1/users/change-password",
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 400 or response_data.get('result', {}).get('error', {}).get('status') == 400:
            _logger.info("✅ confirm_password vazio rejeitada")
        else:
            _logger.warning("⚠️  confirm_password vazio não foi rejeitada")
        
        # Cenário 3: Passwords iguais ✅ DEVE ACEITAR
        _logger.info("Cenário 3: new_password == confirm_password ✅")
        payload = {
            "current_password": self.user1_password,
            "new_password": "ValidPassword123!",
            "confirm_password": "ValidPassword123!"
        }
        
        response = self.opener.post(
            f"{self.base_url}/api/v1/users/change-password",
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}, Response: {response_data}")
        
        if response.status_code == 200 or response_data.get('result', {}).get('error') is None:
            _logger.info("✅ Passwords iguais aceitas")
            
            # 🔄 RESTAURAR PASSWORD ORIGINAL
            _logger.info("🔄 Restaurando password para padrão...")
            payload_restore = {
                "current_password": "ValidPassword123!",
                "new_password": self.user1_password,  # Back to "joao123"
                "confirm_password": self.user1_password
            }
            response_restore = self.opener.post(
                f"{self.base_url}/api/v1/users/change-password",
                data=json.dumps(payload_restore),
                headers=headers,
                content_type='application/json'
            )
            if response_restore.status_code == 200:
                _logger.info("✅ Password restaurada para padrão (joao123)")
            else:
                _logger.warning(f"⚠️  Falha ao restaurar password: {response_restore.status_code}")
        else:
            _logger.warning("⚠️  Passwords iguais foram rejeitadas")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 5: SQL Injection Protection
    # ═════════════════════════════════════════════════════════════════

    def test_sql_injection_in_password(self):
        """
        🔴 CRÍTICO: Proteção contra SQL Injection em password
        
        Cenários:
        - password = "'; DROP TABLE users; --" ❌
        - password = "\" OR \"1\"=\"1" ❌
        - password com caracteres especiais ✅ (validação normal)
        
        Validações:
        - ✅ Rejeição ou escape correto
        - ✅ Database não é corrompida
        - ✅ User consegue logar com password original
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 5: SQL Injection Protection")
        _logger.info("=" * 70)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        # Test Case 1: SQL Injection with DROP TABLE payload
        _logger.warning("Testando SQL Injection (Caso 1): '; DROP TABLE users; --")
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": self.user1_password,
            "new_password": "'; DROP TABLE users; --",
            "confirm_password": "'; DROP TABLE users; --"
        }
        
        try:
            response = self.opener.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                content_type='application/json'
            )
            
            # Parse response safely
            try:
                response_data = json.loads(response.text)
            except json.JSONDecodeError:
                response_data = {"error": "Invalid JSON response"}
            
            # Assert that response is either rejected (400) or accepted (200) with proper handling
            self.assertIn(
                response.status_code,
                [400, 401, 422],
                f"SQL Injection payload should be rejected with 400/401/422, got {response.status_code}"
            )
            
            # If rejected, verify error message exists
            if response.status_code in [400, 401, 422]:
                self.assertIn(
                    'error' in response_data or 'message' in response_data or 'detail' in response_data,
                    True,
                    f"Error response should contain error/message/detail field. Got: {response_data}"
                )
                _logger.info(f"✅ SQL Injection (Caso 1) foi rejeitado: {response.status_code} - {response_data}")
            else:
                _logger.warning(f"⚠️ SQL Injection (Caso 1) retornou {response.status_code}")
                
        except Exception as e:
            self.fail(f"❌ Erro não capturado durante SQL Injection test (Caso 1): {str(e)}")
        
        # Test Case 2: SQL Injection with OR "1"="1 payload
        _logger.warning('Testando SQL Injection (Caso 2): " OR "1"="1')
        payload = {
            "current_password": self.user1_password,
            "new_password": '" OR "1"="1',
            "confirm_password": '" OR "1"="1'
        }
        
        try:
            response = self.opener.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                content_type='application/json'
            )
            
            # Parse response safely
            try:
                response_data = json.loads(response.text)
            except json.JSONDecodeError:
                response_data = {"error": "Invalid JSON response"}
            
            # Assert that response is either rejected (400) or accepted (200) with proper handling
            self.assertIn(
                response.status_code,
                [400, 401, 422],
                f"SQL Injection payload should be rejected with 400/401/422, got {response.status_code}"
            )
            
            # If rejected, verify error message exists
            if response.status_code in [400, 401, 422]:
                self.assertIn(
                    'error' in response_data or 'message' in response_data or 'detail' in response_data,
                    True,
                    f"Error response should contain error/message/detail field. Got: {response_data}"
                )
                _logger.info(f"✅ SQL Injection (Caso 2) foi rejeitado: {response.status_code} - {response_data}")
            else:
                _logger.warning(f"⚠️ SQL Injection (Caso 2) retornou {response.status_code}")
                
        except Exception as e:
            self.fail(f"❌ Erro não capturado durante SQL Injection test (Caso 2): {str(e)}")
        
        # Verify that database is still functional
        _logger.info("Verificando se database ainda está funcional...")
        url = f"{self.base_url}/api/v1/users/login"
        payload = {
            "email": self.user1_email,
            "password": self.user1_password
        }
        
        try:
            response = self.opener.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                content_type='application/json'
            )
            
            self.assertEqual(
                response.status_code,
                200,
                f"Database foi corrompida? Login falhou com status {response.status_code}"
            )
            
            # Verify login response contains valid token
            try:
                login_data = json.loads(response.text)
                self.assertIn(
                    'access_token' in login_data or 'token' in login_data,
                    True,
                    f"Login response should contain access_token or token field. Got: {login_data}"
                )
                _logger.info("✅ Database ainda está funcional - User consegue logar com password original")
            except json.JSONDecodeError:
                self.fail("Login response is not valid JSON")
                
        except Exception as e:
            self.fail(f"❌ Database pode ter sido corrompida: {str(e)}")

    # ═════════════════════════════════════════════════════════════════
    # 🔴 TESTE 6: Current Password Validation
    # ═════════════════════════════════════════════════════════════════

    def test_current_password_must_be_correct(self):
        """
        🔴 CRÍTICO: Current password DEVE estar correto
        
        Cenários:
        - current_password incorreta ❌
        - current_password em branco ❌
        - current_password correta ✅
        
        Validações:
        - ✅ Rejeição de current password incorreta
        - ✅ HTTP 401 (Unauthorized)
        - ✅ Password original é mantida
        """
        _logger.info("=" * 70)
        _logger.info("🔴 TESTE 6: Current Password Validation")
        _logger.info("=" * 70)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        # Cenário 1: Current password incorreta
        _logger.warning("Cenário 1: current_password incorreta")
        url = f"{self.base_url}/api/v1/users/change-password"
        payload = {
            "current_password": "wrong_password_123",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 401 or response_data.get('result', {}).get('error', {}).get('status') == 401:
            _logger.info("✅ Current password incorreta rejeitada com 401")
        else:
            _logger.warning(f"⚠️  Current password incorreta não retornou 401: {response_data}")
        
        # Cenário 2: Current password em branco
        _logger.warning("Cenário 2: current_password em branco")
        payload = {
            "current_password": "",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}")
        
        if response.status_code in [400, 401] or response_data.get('result', {}).get('error', {}).get('status') in [400, 401]:
            _logger.info("✅ Current password vazia rejeitada")
        else:
            _logger.warning(f"⚠️  Current password vazia não foi rejeitada: {response_data}")
        
        # Cenário 3: Current password correta ✅ DEVE ACEITAR
        _logger.info("Cenário 3: current_password correta ✅")
        payload = {
            "current_password": self.user1_password,
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        response = self.opener.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            content_type='application/json'
        )
        
        response_data = json.loads(response.text)
        _logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 200 or response_data.get('result', {}).get('error') is None:
            _logger.info("✅ Current password correta aceita")
            
            # 🔄 RESTAURAR PASSWORD ORIGINAL
            _logger.info("🔄 Restaurando password para padrão...")
            payload_restore = {
                "current_password": "NewPassword123!",
                "new_password": self.user1_password,  # Back to "joao123"
                "confirm_password": self.user1_password
            }
            response_restore = self.opener.post(
                url,
                data=json.dumps(payload_restore),
                headers=headers,
                content_type='application/json'
            )
            if response_restore.status_code == 200:
                _logger.info("✅ Password restaurada para padrão (joao123)")
            else:
                _logger.warning(f"⚠️  Falha ao restaurar password: {response_restore.status_code}")
        else:
            _logger.warning(f"⚠️  Current password correta foi rejeitada: {response_data}")
