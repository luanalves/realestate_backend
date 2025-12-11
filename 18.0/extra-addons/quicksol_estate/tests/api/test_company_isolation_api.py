#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes de autenticação OAuth para isolamento de companies.
Execução manual: python3 test_company_isolation_api.py
"""
import os
import sys
import requests
from pathlib import Path


def load_env_file():
    """Carrega variáveis de ambiente do arquivo .env"""
    # Get project root: tests/api/../../../.. = 18.0/
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent.parent
    env_file = project_root / '.env'
    
    if env_file.exists():
        print(f"✓ Carregando variáveis de {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() and key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()
    else:
        print(f"✗ Arquivo .env não encontrado: {env_file}")
        sys.exit(1)


def test_01_oauth_token_creation(base_url, client_id, client_secret):
    """Test 1: Deve conseguir criar um token OAuth com client_credentials"""
    print("\n" + "="*70)
    print("TEST 1: Criação de token OAuth")
    print("="*70)
    
    response = requests.post(
        f'{base_url}/api/v1/auth/token',
        json={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"✗ FAIL: Esperado 200, recebido {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    if 'access_token' not in data:
        print("✗ FAIL: Resposta não contém 'access_token'")
        return False
    
    if 'token_type' not in data:
        print("✗ FAIL: Resposta não contém 'token_type'")
        return False
    
    if data['token_type'] != 'Bearer':
        print(f"✗ FAIL: Token type deveria ser 'Bearer', recebido '{data['token_type']}'")
        return False
    
    if len(data['access_token']) == 0:
        print("✗ FAIL: Access token está vazio")
        return False
    
    print("✓ PASS: Token OAuth criado com sucesso")
    print(f"  Token type: {data['token_type']}")
    print(f"  Token length: {len(data['access_token'])} chars")
    return True


def test_02_oauth_token_invalid_credentials(base_url):
    """Test 2: Deve rejeitar credenciais OAuth inválidas"""
    print("\n" + "="*70)
    print("TEST 2: Credenciais OAuth inválidas")
    print("="*70)
    
    response = requests.post(
        f'{base_url}/api/v1/auth/token',
        json={
            'grant_type': 'client_credentials',
            'client_id': 'invalid_client_id',
            'client_secret': 'invalid_secret'
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code not in [400, 401]:
        print(f"✗ FAIL: Esperado 400 ou 401, recebido {response.status_code}")
        return False
    
    print(f"✓ PASS: Credenciais inválidas rejeitadas (HTTP {response.status_code})")
    return True


def test_03_oauth_token_missing_grant_type(base_url, client_id, client_secret):
    """Test 3: Deve rejeitar request sem grant_type"""
    print("\n" + "="*70)
    print("TEST 3: Request sem grant_type")
    print("="*70)
    
    response = requests.post(
        f'{base_url}/api/v1/auth/token',
        json={
            'client_id': client_id,
            'client_secret': client_secret
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 400:
        print(f"✗ FAIL: Esperado 400, recebido {response.status_code}")
        return False
    
    print(f"✓ PASS: Request sem grant_type rejeitado (HTTP {response.status_code})")
    return True


def test_04_login_user_a(base_url, user_a_email, user_a_password):
    """Test 4: Login do User A (Company A)"""
    print("\n" + "="*70)
    print("TEST 4: Login User A (Company A)")
    print("="*70)
    print(f"  Email: {user_a_email}")
    
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
        print(f"✗ FAIL: Esperado 200, recebido {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    if 'error' in data:
        print(f"✗ FAIL: Erro no login")
        print(f"Error: {data['error']}")
        return False
    
    result = data.get('result', {})
    
    if not result.get('uid'):
        print(f"✗ FAIL: UID não retornado")
        print(f"Result: {result}")
        return False
    
    print(f"✓ PASS: User A autenticado com sucesso")
    print(f"  UID: {result.get('uid')}")
    print(f"  Username: {result.get('username')}")
    print(f"  Session ID: {result.get('session_id', 'N/A')[:20]}...")
    return True


def test_05_login_user_b(base_url, user_b_email, user_b_password):
    """Test 5: Login do User B (Company B)"""
    print("\n" + "="*70)
    print("TEST 5: Login User B (Company B)")
    print("="*70)
    print(f"  Email: {user_b_email}")
    
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
        print(f"✗ FAIL: Esperado 200, recebido {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    data = response.json()
    
    if 'error' in data:
        print(f"✗ FAIL: Erro no login")
        print(f"Error: {data['error']}")
        return False
    
    result = data.get('result', {})
    
    if not result.get('uid'):
        print(f"✗ FAIL: UID não retornado")
        print(f"Result: {result}")
        return False
    
    print(f"✓ PASS: User B autenticado com sucesso")
    print(f"  UID: {result.get('uid')}")
    print(f"  Username: {result.get('username')}")
    print(f"  Session ID: {result.get('session_id', 'N/A')[:20]}...")
    return True


def test_06_login_invalid_credentials(base_url):
    """Test 6: Login com credenciais inválidas"""
    print("\n" + "="*70)
    print("TEST 6: Login com credenciais inválidas")
    print("="*70)
    
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
        print(f"✗ FAIL: Esperado 200 (Odoo retorna 200 mesmo com erro), recebido {response.status_code}")
        return False
    
    data = response.json()
    
    # Odoo retorna erro dentro do JSON
    if 'error' not in data and data.get('result', {}).get('uid'):
        print(f"✗ FAIL: Credenciais inválidas foram aceitas")
        return False
    
    print(f"✓ PASS: Credenciais inválidas rejeitadas")
    return True


def main():
    """Função principal"""
    print("\n" + "="*70)
    print("TESTES DE AUTENTICAÇÃO OAUTH - COMPANY ISOLATION")
    print("="*70)
    
    # Carrega variáveis de ambiente
    load_env_file()
    
    # Obtém configurações
    base_url = os.getenv('ODOO_BASE_URL', 'http://localhost:8069')
    client_id = os.getenv('OAUTH_CLIENT_ID')
    client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    user_a_email = os.getenv('TEST_USER_A_EMAIL')
    user_a_password = os.getenv('TEST_USER_A_PASSWORD')
    user_b_email = os.getenv('TEST_USER_B_EMAIL')
    user_b_password = os.getenv('TEST_USER_B_PASSWORD')
    
    print(f"\nConfigurações:")
    print(f"  Base URL: {base_url}")
    print(f"  Client ID: {client_id}")
    print(f"  Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
    print(f"  User A Email: {user_a_email}")
    print(f"  User B Email: {user_b_email}")
    
    if not client_id or not client_secret:
        print("\n✗ ERRO: OAUTH_CLIENT_ID ou OAUTH_CLIENT_SECRET não configurados no .env")
        sys.exit(1)
    
    if not user_a_email or not user_a_password or not user_b_email or not user_b_password:
        print("\n✗ ERRO: Credenciais de usuários de teste não configuradas no .env")
        print("  Necessário: TEST_USER_A_EMAIL, TEST_USER_A_PASSWORD, TEST_USER_B_EMAIL, TEST_USER_B_PASSWORD")
        sys.exit(1)
    
    # Executa testes
    results = []
    results.append(test_01_oauth_token_creation(base_url, client_id, client_secret))
    results.append(test_02_oauth_token_invalid_credentials(base_url))
    results.append(test_03_oauth_token_missing_grant_type(base_url, client_id, client_secret))
    results.append(test_04_login_user_a(base_url, user_a_email, user_a_password))
    results.append(test_05_login_user_b(base_url, user_b_email, user_b_password))
    results.append(test_06_login_invalid_credentials(base_url))
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATÓRIO FINAL")
    print("="*70)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"Total de testes: {total}")
    print(f"✓ Aprovados: {passed}")
    print(f"✗ Falhados: {failed}")
    
    if failed == 0:
        print("\n✓ Todos os testes passaram!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} teste(s) falharam")
        sys.exit(1)


if __name__ == '__main__':
    main()
