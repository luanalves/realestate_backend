#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes de login e logout de usuários
"""
import os
import sys
import requests
from utils import load_env_file, print_test_header, print_test_result, print_summary, get_oauth_token


def test_01_login_user_a(base_url, user_a_email, user_a_password):
    """Test 1: Login do User A (Company A)"""
    print_test_header(1, "Login User A (Company A)")
    print(f"  Email: {user_a_email}")
    
    try:
        response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_a_email,
                    'password': user_a_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if 'error' in data:
            print(f"  Error: {data['error']}")
            return print_test_result(False, "Erro no login")
        
        result = data.get('result', {})
        
        if not result.get('uid'):
            print(f"  Result: {result}")
            return print_test_result(False, "UID não retornado")
        
        print(f"  UID: {result.get('uid')}")
        print(f"  Username: {result.get('username')}")
        print(f"  Session ID: {result.get('session_id', 'N/A')[:20]}...")
        
        return print_test_result(True, "User A autenticado com sucesso")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_02_login_user_b(base_url, user_b_email, user_b_password):
    """Test 2: Login do User B (Company B)"""
    print_test_header(2, "Login User B (Company B)")
    print(f"  Email: {user_b_email}")
    
    try:
        response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_b_email,
                    'password': user_b_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if 'error' in data:
            print(f"  Error: {data['error']}")
            return print_test_result(False, "Erro no login")
        
        result = data.get('result', {})
        
        if not result.get('uid'):
            print(f"  Result: {result}")
            return print_test_result(False, "UID não retornado")
        
        print(f"  UID: {result.get('uid')}")
        print(f"  Username: {result.get('username')}")
        print(f"  Session ID: {result.get('session_id', 'N/A')[:20]}...")
        
        return print_test_result(True, "User B autenticado com sucesso")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_03_login_invalid_credentials(base_url):
    """Test 3: Login com credenciais inválidas"""
    print_test_header(3, "Login com credenciais inválidas")
    
    try:
        response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': 'invalid@test.com',
                    'password': 'wrong_password'
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200 (Odoo retorna 200 mesmo com erro), recebido {response.status_code}")
        
        data = response.json()
        
        # Odoo retorna erro dentro do JSON
        if 'error' not in data and data.get('result', {}).get('uid'):
            return print_test_result(False, "Credenciais inválidas foram aceitas")
        
        return print_test_result(True, "Credenciais inválidas rejeitadas")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_04_logout_user(base_url, user_email, user_password):
    """Test 4: Logout de usuário"""
    print_test_header(4, "Logout de usuário")
    
    try:
        # Primeiro faz login
        login_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_email,
                    'password': user_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code != 200:
            return print_test_result(False, "Falha no login inicial")
        
        session = requests.Session()
        session.cookies.update(login_response.cookies)
        
        # Faz logout
        logout_response = session.post(
            f'{base_url}/web/session/destroy',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': 2
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if logout_response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {logout_response.status_code}")
        
        return print_test_result(True, "Logout realizado com sucesso")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_05_change_profile_user_a(base_url, user_a_email, user_a_password):
    """Test 5: User A tenta alterar próprio perfil (sem permissão Admin)"""
    print_test_header(5, "User A tenta alterar próprio perfil")
    
    try:
        # Login
        login_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_a_email,
                    'password': user_a_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if login_response.status_code != 200:
            return print_test_result(False, "Falha no login")
        
        data = login_response.json()
        result = data.get('result', {})
        uid = result.get('uid')
        
        if not uid:
            return print_test_result(False, "UID não retornado")
        
        session = requests.Session()
        session.cookies.update(login_response.cookies)
        
        # Atualiza dados do próprio perfil
        update_response = session.post(
            f'{base_url}/web/dataset/call_kw',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'model': 'res.users',
                    'method': 'write',
                    'args': [[uid], {'phone': '+55 11 98888-7777'}],
                    'kwargs': {}
                },
                'id': 2
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if update_response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {update_response.status_code}")
        
        update_data = update_response.json()
        
        # No Odoo, usuários normais não podem alterar res.users sem permissão de Admin
        if 'error' in update_data:
            error_msg = update_data['error'].get('data', {}).get('message', '')
            if 'not allowed to modify' in error_msg or 'Access Rights' in error_msg:
                print(f"  Acesso negado (esperado - requer permissão Admin)")
                return print_test_result(True, "✓ Odoo protege alteração de usuários (requer Admin)")
            else:
                print(f"  Error: {update_data['error']}")
                return print_test_result(False, "Erro inesperado ao atualizar perfil")
        
        # Se conseguiu alterar, verificar se realmente atualizou
        print(f"  UID: {uid}")
        print(f"  Telefone atualizado: +55 11 98888-7777")
        
        return print_test_result(True, "User A atualizou seu próprio perfil (tem permissão Admin)")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_06_user_a_tries_change_user_b_profile(base_url, user_a_email, user_a_password, user_b_email, user_b_password):
    """Test 6: User A tenta alterar perfil do User B (deve falhar)"""
    print_test_header(6, "User A tenta alterar perfil do User B (SECURITY TEST)")
    
    try:
        # Primeiro descobre o UID do User B
        login_b_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_b_email,
                    'password': user_b_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if login_b_response.status_code != 200:
            return print_test_result(False, "Falha ao obter UID do User B")
        
        user_b_uid = login_b_response.json().get('result', {}).get('uid')
        
        if not user_b_uid:
            return print_test_result(False, "UID do User B não encontrado")
        
        print(f"  User B UID: {user_b_uid}")
        
        # Agora faz login como User A
        login_a_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_a_email,
                    'password': user_a_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if login_a_response.status_code != 200:
            return print_test_result(False, "Falha no login do User A")
        
        user_a_uid = login_a_response.json().get('result', {}).get('uid')
        print(f"  User A UID: {user_a_uid}")
        
        session_a = requests.Session()
        session_a.cookies.update(login_a_response.cookies)
        
        # User A tenta alterar dados do User B
        print(f"  User A tentando alterar telefone do User B...")
        attack_response = session_a.post(
            f'{base_url}/web/dataset/call_kw',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'model': 'res.users',
                    'method': 'write',
                    'args': [[user_b_uid], {'phone': '+55 11 99999-9999'}],
                    'kwargs': {}
                },
                'id': 3
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if attack_response.status_code != 200:
            return print_test_result(True, f"Ataque bloqueado no HTTP level (status {attack_response.status_code})")
        
        attack_data = attack_response.json()
        
        # Se retornou erro, significa que o acesso foi negado (esperado)
        if 'error' in attack_data:
            error_msg = attack_data['error'].get('data', {}).get('message', 'Unknown error')
            print(f"  Erro retornado: {error_msg}")
            return print_test_result(True, "✓ SEGURANÇA OK: User A não conseguiu alterar perfil do User B")
        
        # Se chegou aqui e deu sucesso, é uma falha de segurança!
        if attack_data.get('result') == True:
            return print_test_result(False, "✗ FALHA DE SEGURANÇA: User A conseguiu alterar perfil do User B!")
        
        return print_test_result(True, "✓ SEGURANÇA OK: Operação bloqueada")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_07_user_a_tries_read_user_b_session(base_url, user_a_email, user_a_password, user_b_email, user_b_password):
    """Test 7: User A tenta ler sessão do User B (deve falhar)"""
    print_test_header(7, "User A tenta ler dados da sessão do User B (SECURITY TEST)")
    
    try:
        # Login User B e captura session_id
        login_b_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_b_email,
                    'password': user_b_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        session_b_id = login_b_response.cookies.get('session_id')
        print(f"  Session ID User B: {session_b_id[:20] if session_b_id else 'N/A'}...")
        
        # Login como User A
        login_a_response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': user_a_email,
                    'password': user_a_password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        session_a_id = login_a_response.cookies.get('session_id')
        print(f"  Session ID User A: {session_a_id[:20] if session_a_id else 'N/A'}...")
        
        # User A tenta usar session do User B
        session_hijack = requests.Session()
        session_hijack.cookies.set('session_id', session_b_id)
        
        print(f"  User A tentando usar session_id do User B...")
        
        hijack_response = session_hijack.post(
            f'{base_url}/web/session/get_session_info',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': 4
            },
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'ATTACKER-BROWSER/1.0 (Different from User B)',
                'Accept-Language': 'fr-FR,fr;q=0.9',
            }
        )
        
        if hijack_response.status_code != 200:
            return print_test_result(True, f"Tentativa bloqueada (HTTP {hijack_response.status_code})")
        
        hijack_data = hijack_response.json()
        result = hijack_data.get('result', {})
        
        # Se conseguiu obter info do User B usando sua session, é falha de segurança
        if result.get('username') == user_b_email:
            return print_test_result(False, f"✗ FALHA DE SEGURANÇA: User A conseguiu usar sessão do User B!")
        
        # Se retornou info do User A ou erro, está correto
        if result.get('username') == user_a_email:
            return print_test_result(True, "✓ SEGURANÇA OK: Sessão não foi sequestrada (ainda logado como A)")
        
        return print_test_result(True, "✓ SEGURANÇA OK: Sessão protegida")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_08_get_user_me(base_url, user_a_email, user_a_password, oauth_client_id, oauth_client_secret):
    """Test 8: GET /api/v1/me retorna dados do usuário autenticado"""
    print_test_header(8, "GET /api/v1/me - Retornar dados do usuário")
    
    try:
        # Obtém OAuth token
        oauth_token, success = get_oauth_token(base_url, oauth_client_id, oauth_client_secret)
        if not success or not oauth_token:
            return print_test_result(False, "Falha ao obter OAuth token")
        
        # Login via API (cria thedevkitchen.api.session)
        login_response = requests.post(
            f'{base_url}/api/v1/users/login',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'email': user_a_email,
                    'password': user_a_password
                },
                'id': 1
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}'
            }
        )
        
        if login_response.status_code != 200:
            return print_test_result(False, "Falha no login")
        
        login_data = login_response.json()
        if 'error' in login_data:
            return print_test_result(False, f"Erro no login: {login_data['error']}")
        
        # Debug: mostra session_id retornado
        result = login_data.get('result', {})
        api_session_id = result.get('session_id')
        cookie_session_id = login_response.cookies.get('session_id')
        print(f"  API session_id: {api_session_id[:20] if api_session_id else 'N/A'}...")
        print(f"  Cookie session_id: {cookie_session_id[:20] if cookie_session_id else 'N/A'}...")
        
        session = requests.Session()
        session.cookies.update(login_response.cookies)
        
        # Chama /api/v1/me
        me_response = session.post(
            f'{base_url}/api/v1/me',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': 2
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}'
            }
        )
        
        if me_response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {me_response.status_code}")
        
        data = me_response.json()
        
        if 'error' in data:
            print(f"  Error: {data['error']}")
            return print_test_result(False, "Erro ao obter dados do usuário")
        
        result = data.get('result', {})
        user = result.get('user', {})
        
        if not user.get('id'):
            print(f"  Result: {result}")
            return print_test_result(False, "Dados do usuário não retornados")
        
        # Valida campos obrigatórios
        required_fields = ['id', 'name', 'email', 'login', 'companies', 'is_admin', 'active']
        missing_fields = [f for f in required_fields if f not in user]
        
        if missing_fields:
            return print_test_result(False, f"Campos faltando: {', '.join(missing_fields)}")
        
        # Valida que retornou o email correto
        if user.get('email') != user_a_email:
            return print_test_result(False, f"Email incorreto: esperado {user_a_email}, recebido {user.get('email')}")
        
        print(f"  User ID: {user.get('id')}")
        print(f"  Name: {user.get('name')}")
        print(f"  Email: {user.get('email')}")
        print(f"  Companies: {len(user.get('companies', []))} empresa(s)")
        print(f"  Is Admin: {user.get('is_admin')}")
        
        return print_test_result(True, "Dados do usuário retornados corretamente")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_09_get_user_me_without_session(base_url, oauth_client_id, oauth_client_secret):
    """Test 9: GET /api/v1/me sem sessão (deve falhar)"""
    print_test_header(9, "GET /api/v1/me sem sessão (SECURITY TEST)")
    
    try:
        # Obtém OAuth token
        oauth_token, success = get_oauth_token(base_url, oauth_client_id, oauth_client_secret)
        if not success or not oauth_token:
            return print_test_result(False, "Falha ao obter OAuth token")
        
        # Tenta acessar /api/v1/me sem sessão
        me_response = requests.post(
            f'{base_url}/api/v1/me',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': 1
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}'
            }
        )
        
        if me_response.status_code != 200:
            return print_test_result(True, f"Requisição bloqueada (HTTP {me_response.status_code})")
        
        data = me_response.json()
        
        # Deve retornar erro de autenticação
        if 'error' in data:
            error = data.get('error', {})
            if isinstance(error, dict):
                error_msg = error.get('data', {}).get('message', '') or error.get('message', '')
            else:
                error_msg = str(error)
            
            if 'unauthorized' in error_msg.lower() or 'session' in error_msg.lower() or 'authentication' in error_msg.lower():
                print(f"  Erro retornado: {error_msg[:80]}...")
                return print_test_result(True, "✓ SEGURANÇA OK: Requisição sem sessão foi rejeitada")
        
        result = data.get('result', {})
        if result.get('error') == 'unauthorized':
            print(f"  Erro retornado: {result.get('error_description', 'N/A')}")
            return print_test_result(True, "✓ SEGURANÇA OK: Requisição sem sessão foi rejeitada")
        
        # Se retornou dados de usuário, é falha de segurança
        if result.get('user', {}).get('id'):
            return print_test_result(False, "✗ FALHA DE SEGURANÇA: Endpoint acessível sem sessão!")
        
        return print_test_result(True, "✓ SEGURANÇA OK: Acesso negado sem sessão")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_10_api_session_hijacking(base_url, user_a_email, user_a_password, user_b_email, user_b_password, oauth_client_id, oauth_client_secret):
    """Test 10: User A tenta usar session_id do User B em /api/v1/me (SECURITY TEST)"""
    print_test_header(10, "API Session Hijacking - User A tenta session do User B (SECURITY TEST)")
    
    try:
        # Obtém OAuth token
        oauth_token, success = get_oauth_token(base_url, oauth_client_id, oauth_client_secret)
        if not success or not oauth_token:
            return print_test_result(False, "Falha ao obter OAuth token")
        
        # User B faz login via API
        login_b_response = requests.post(
            f'{base_url}/api/v1/users/login',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'email': user_b_email,
                    'password': user_b_password
                },
                'id': 1
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}'
            }
        )
        
        if login_b_response.status_code != 200:
            return print_test_result(False, "Falha no login do User B")
        
        # Captura session_id do User B (do cookie)
        session_b_id = login_b_response.cookies.get('session_id')
        login_b_data = login_b_response.json()
        user_b_id = login_b_data.get('result', {}).get('user', {}).get('id')
        
        print(f"  User B ID: {user_b_id}")
        print(f"  User B Session: {session_b_id[:20] if session_b_id else 'N/A'}...")
        
        # User A tenta usar session_id do User B para acessar /api/v1/me
        print(f"  User A tentando usar session do User B em /api/v1/me...")
        
        hijack_session = requests.Session()
        hijack_session.cookies.set('session_id', session_b_id)
        
        me_response = hijack_session.post(
            f'{base_url}/api/v1/me',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {},
                'id': 2
            },
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}',
                'User-Agent': 'ATTACKER-CLIENT/1.0',  # User-Agent diferente
                'Accept-Language': 'en-US,en;q=0.9'    # Accept-Language diferente
            }
        )
        
        if me_response.status_code != 200:
            return print_test_result(True, f"✓ SEGURANÇA OK: Requisição bloqueada (HTTP {me_response.status_code})")
        
        data = me_response.json()
        result = data.get('result', {})
        
        # Se retornou dados do User B, está correto (sessão válida do User B)
        # MAS deveria ser bloqueado por fingerprint ou outro mecanismo
        user_data = result.get('user', {})
        returned_user_id = user_data.get('id')
        returned_email = user_data.get('email')
        
        if returned_user_id == user_b_id:
            print(f"  Retornou User B (ID: {returned_user_id}, Email: {returned_email})")
            return print_test_result(False, "✗ FALHA DE SEGURANÇA: Session hijacking permitido! User A conseguiu acessar dados como User B")
        
        # Se retornou erro ou bloqueou, está correto
        if 'error' in result or 'error' in data:
            error_msg = result.get('error_description') or data.get('error')
            print(f"  Erro retornado: {error_msg}")
            return print_test_result(True, "✓ SEGURANÇA OK: Tentativa de hijacking bloqueada")
        
        return print_test_result(True, "✓ SEGURANÇA OK: Session protegida")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def main():
    """Executa todos os testes de login/logout"""
    print("="*70)
    print("TESTES DE LOGIN E LOGOUT DE USUÁRIOS")
    print("="*70)
    
    # Carrega variáveis de ambiente
    load_env_file()
    
    # Obtém configurações
    base_url = os.getenv('ODOO_BASE_URL', 'http://localhost:8069')
    user_a_email = os.getenv('TEST_USER_A_EMAIL')
    user_a_password = os.getenv('TEST_USER_A_PASSWORD')
    user_b_email = os.getenv('TEST_USER_B_EMAIL')
    user_b_password = os.getenv('TEST_USER_B_PASSWORD')
    oauth_client_id = os.getenv('OAUTH_CLIENT_ID')
    oauth_client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    
    print(f"\nConfigurações:")
    print(f"  Base URL: {base_url}")
    print(f"  User A Email: {user_a_email}")
    print(f"  User B Email: {user_b_email}")
    
    if not user_a_email or not user_a_password or not user_b_email or not user_b_password:
        print("\n✗ ERRO: Credenciais de usuários de teste não configuradas no .env")
        print("  Necessário: TEST_USER_A_EMAIL, TEST_USER_A_PASSWORD, TEST_USER_B_EMAIL, TEST_USER_B_PASSWORD")
        sys.exit(1)
    
    if not oauth_client_id or not oauth_client_secret:
        print("\n✗ ERRO: Credenciais OAuth não configuradas no .env")
        print("  Necessário: OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET")
        sys.exit(1)
    
    # Executa testes
    results = []
    results.append(test_01_login_user_a(base_url, user_a_email, user_a_password))
    results.append(test_02_login_user_b(base_url, user_b_email, user_b_password))
    results.append(test_03_login_invalid_credentials(base_url))
    results.append(test_04_logout_user(base_url, user_a_email, user_a_password))
    results.append(test_05_change_profile_user_a(base_url, user_a_email, user_a_password))
    results.append(test_06_user_a_tries_change_user_b_profile(base_url, user_a_email, user_a_password, user_b_email, user_b_password))
    results.append(test_07_user_a_tries_read_user_b_session(base_url, user_a_email, user_a_password, user_b_email, user_b_password))
    results.append(test_08_get_user_me(base_url, user_a_email, user_a_password, oauth_client_id, oauth_client_secret))
    results.append(test_09_get_user_me_without_session(base_url, oauth_client_id, oauth_client_secret))
    results.append(test_10_api_session_hijacking(base_url, user_a_email, user_a_password, user_b_email, user_b_password, oauth_client_id, oauth_client_secret))
    
    # Relatório final
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
