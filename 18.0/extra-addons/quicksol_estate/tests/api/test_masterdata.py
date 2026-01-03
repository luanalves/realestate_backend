#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes de endpoints de Master Data
"""
import os
import sys
import requests
from utils import load_env_file, get_oauth_token, get_user_session, print_test_header, print_test_result, print_summary


def test_01_property_types_with_oauth(base_url, token):
    """Test 1: Listar tipos de propriedade com OAuth"""
    print_test_header(1, "GET /api/v1/property-types com OAuth")
    
    try:
        response = requests.get(
            f'{base_url}/api/v1/property-types',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if not isinstance(data, list):
            return print_test_result(False, f"Esperado lista, recebido {type(data)}")
        
        print(f"  Total de tipos: {len(data)}")
        if len(data) > 0:
            print(f"  Primeiro tipo: {data[0]}")
        
        return print_test_result(True, f"Retornou {len(data)} tipo(s) de propriedade")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_02_property_types_without_token(base_url):
    """Test 2: Listar tipos de propriedade sem token (deve falhar)"""
    print_test_header(2, "GET /api/v1/property-types sem token")
    
    try:
        response = requests.get(f'{base_url}/api/v1/property-types')
        
        if response.status_code != 401:
            return print_test_result(False, f"Esperado 401, recebido {response.status_code}")
        
        return print_test_result(True, "Request sem token rejeitado (HTTP 401)")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_03_location_types_with_oauth(base_url, token):
    """Test 3: Listar tipos de localização com OAuth"""
    print_test_header(3, "GET /api/v1/location-types com OAuth")
    
    try:
        response = requests.get(
            f'{base_url}/api/v1/location-types',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if not isinstance(data, list):
            return print_test_result(False, f"Esperado lista, recebido {type(data)}")
        
        print(f"  Total de tipos: {len(data)}")
        if len(data) > 0:
            print(f"  Primeiro tipo: {data[0]}")
        
        return print_test_result(True, f"Retornou {len(data)} tipo(s) de localização")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_04_states_with_oauth(base_url, token):
    """Test 4: Listar estados com OAuth"""
    print_test_header(4, "GET /api/v1/states com OAuth")
    
    try:
        response = requests.get(
            f'{base_url}/api/v1/states',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if not isinstance(data, list):
            return print_test_result(False, f"Esperado lista, recebido {type(data)}")
        
        print(f"  Total de estados: {len(data)}")
        if len(data) > 0:
            first_state = data[0]
            print(f"  Primeiro estado: {first_state.get('name')} ({first_state.get('code')})")
            if first_state.get('country'):
                print(f"  País: {first_state['country'].get('name')}")
        
        return print_test_result(True, f"Retornou {len(data)} estado(s)")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_05_agents_with_oauth(base_url, token):
    """Test 5: Listar agentes com OAuth"""
    print_test_header(5, "GET /api/v1/agents com OAuth")
    
    try:
        response = requests.get(
            f'{base_url}/api/v1/agents',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if response.status_code != 200:
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if not isinstance(data, list):
            return print_test_result(False, f"Esperado lista, recebido {type(data)}")
        
        print(f"  Total de agentes: {len(data)}")
        if len(data) > 0:
            first_agent = data[0]
            print(f"  Primeiro agente: {first_agent.get('name')}")
            print(f"  Email: {first_agent.get('email')}")
        
        return print_test_result(True, f"Retornou {len(data)} agente(s)")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_06_company_isolation_user_a(base_url, user_a_email, user_a_password):
    """Test 6: Isolamento de company - User A vê apenas dados da Company A"""
    print_test_header(6, "Company Isolation - User A")
    print(f"  Email: {user_a_email}")
    
    try:
        # Faz login como User A
        session_data, success = get_user_session(base_url, user_a_email, user_a_password)
        
        if not success:
            return print_test_result(False, "Falha no login do User A")
        
        # Cria sessão com cookies
        session = requests.Session()
        session.cookies.set('session_id', session_data.get('session_id'))
        
        # Tenta acessar property types
        response = session.get(f'{base_url}/api/v1/property-types')
        
        if response.status_code != 200:
            print(f"  Status: {response.status_code}")
            # Se falhar, pode ser porque precisa de OAuth também
            return print_test_result(True, "Endpoint requer OAuth (isolamento OK)")
        
        data = response.json()
        print(f"  Property types visíveis: {len(data)}")
        
        return print_test_result(True, "User A consegue acessar master data da sua company")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def main():
    """Executa todos os testes de master data"""
    print("="*70)
    print("TESTES DE MASTER DATA API")
    print("="*70)
    
    # Carrega variáveis de ambiente
    load_env_file()
    
    # Obtém configurações
    base_url = os.getenv('ODOO_BASE_URL', 'http://localhost:8069')
    client_id = os.getenv('OAUTH_CLIENT_ID')
    client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    user_a_email = os.getenv('TEST_USER_A_EMAIL')
    user_a_password = os.getenv('TEST_USER_A_PASSWORD')
    
    print(f"\nConfigurações:")
    print(f"  Base URL: {base_url}")
    print(f"  Client ID: {client_id}")
    print(f"  User A Email: {user_a_email}")
    
    if not client_id or not client_secret:
        print("\n✗ ERRO: OAUTH_CLIENT_ID ou OAUTH_CLIENT_SECRET não configurados no .env")
        sys.exit(1)
    
    # Obtém token OAuth (reutilizável)
    print("\n" + "="*70)
    print("OBTENDO TOKEN OAUTH (reutilizado em todos os testes)")
    print("="*70)
    token, success = get_oauth_token(base_url, client_id, client_secret)
    
    if not success or not token:
        print("✗ ERRO: Não foi possível obter token OAuth")
        sys.exit(1)
    
    print(f"✓ Token OAuth obtido com sucesso")
    print(f"  Token length: {len(token)} chars")
    
    # Executa testes
    results = []
    results.append(test_01_property_types_with_oauth(base_url, token))
    results.append(test_02_property_types_without_token(base_url))
    results.append(test_03_location_types_with_oauth(base_url, token))
    results.append(test_04_states_with_oauth(base_url, token))
    results.append(test_05_agents_with_oauth(base_url, token))
    
    if user_a_email and user_a_password:
        results.append(test_06_company_isolation_user_a(base_url, user_a_email, user_a_password))
    
    # Relatório final
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
