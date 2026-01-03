#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Testes de autenticação OAuth
"""
import os
import sys
import requests
from utils import load_env_file, print_test_header, print_test_result, print_summary


def test_01_oauth_token_creation(base_url, client_id, client_secret):
    """Test 1: Criação de token OAuth com credenciais válidas"""
    print_test_header(1, "Criação de token OAuth")
    
    try:
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
            return print_test_result(False, f"Esperado 200, recebido {response.status_code}")
        
        data = response.json()
        
        if 'access_token' not in data:
            return print_test_result(False, "Token não retornado na resposta")
        
        token = data['access_token']
        token_type = data.get('token_type', 'N/A')
        
        print(f"  Token type: {token_type}")
        print(f"  Token length: {len(token)} chars")
        
        return print_test_result(True, "Token OAuth criado com sucesso")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_02_oauth_token_invalid_credentials(base_url):
    """Test 2: Deve rejeitar credenciais OAuth inválidas"""
    print_test_header(2, "Credenciais OAuth inválidas")
    
    try:
        response = requests.post(
            f'{base_url}/api/v1/auth/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': 'invalid_client',
                'client_secret': 'invalid_secret'
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 400:
            return print_test_result(False, f"Esperado 400, recebido {response.status_code}")
        
        return print_test_result(True, f"Credenciais inválidas rejeitadas (HTTP {response.status_code})")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def test_03_oauth_token_missing_grant_type(base_url, client_id, client_secret):
    """Test 3: Deve rejeitar request sem grant_type"""
    print_test_header(3, "Request sem grant_type")
    
    try:
        response = requests.post(
            f'{base_url}/api/v1/auth/token',
            json={
                'client_id': client_id,
                'client_secret': client_secret
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 400:
            return print_test_result(False, f"Esperado 400, recebido {response.status_code}")
        
        return print_test_result(True, f"Request sem grant_type rejeitado (HTTP {response.status_code})")
        
    except Exception as e:
        return print_test_result(False, f"Exceção: {str(e)}")


def main():
    """Executa todos os testes de OAuth"""
    print("="*70)
    print("TESTES DE AUTENTICAÇÃO OAUTH")
    print("="*70)
    
    # Carrega variáveis de ambiente
    load_env_file()
    
    # Obtém configurações
    base_url = os.getenv('ODOO_BASE_URL', 'http://localhost:8069')
    client_id = os.getenv('OAUTH_CLIENT_ID')
    client_secret = os.getenv('OAUTH_CLIENT_SECRET')
    
    print(f"\nConfigurações:")
    print(f"  Base URL: {base_url}")
    print(f"  Client ID: {client_id}")
    print(f"  Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
    
    if not client_id or not client_secret:
        print("\n✗ ERRO: OAUTH_CLIENT_ID ou OAUTH_CLIENT_SECRET não configurados no .env")
        sys.exit(1)
    
    # Executa testes
    results = []
    results.append(test_01_oauth_token_creation(base_url, client_id, client_secret))
    results.append(test_02_oauth_token_invalid_credentials(base_url))
    results.append(test_03_oauth_token_missing_grant_type(base_url, client_id, client_secret))
    
    # Relatório final
    success = print_summary(results)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
