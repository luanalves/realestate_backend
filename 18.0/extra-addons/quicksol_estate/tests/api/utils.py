#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for API tests
"""
import os
import sys
import requests
from pathlib import Path


def load_env_file():
    """Carrega variáveis do arquivo .env"""
    env_path = Path(__file__).parent.parent.parent.parent.parent / '.env'
    
    if not env_path.exists():
        print(f"✗ Arquivo .env não encontrado em: {env_path}")
        sys.exit(1)
    
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    
    print(f"✓ Carregando variáveis de {env_path}")


def get_oauth_token(base_url, client_id, client_secret):
    """
    Obtém token OAuth válido
    Returns: (token, success)
    """
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
        
        if response.status_code == 200:
            data = response.json()
            return data.get('access_token'), True
        return None, False
    except Exception as e:
        print(f"✗ Erro ao obter token OAuth: {e}")
        return None, False


def get_user_session(base_url, email, password):
    """
    Faz login e retorna dados da sessão
    Returns: (session_data, success)
    """
    try:
        response = requests.post(
            f'{base_url}/web/session/authenticate',
            json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': 'realestate',
                    'login': email,
                    'password': password
                },
                'id': 1
            },
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data and data.get('result', {}).get('uid'):
                return data['result'], True
        return None, False
    except Exception as e:
        print(f"✗ Erro ao fazer login: {e}")
        return None, False


def print_test_header(test_number, test_name):
    """Imprime cabeçalho do teste"""
    print("\n" + "="*70)
    print(f"TEST {test_number}: {test_name}")
    print("="*70)


def print_test_result(passed, message):
    """Imprime resultado do teste"""
    if passed:
        print(f"✓ PASS: {message}")
    else:
        print(f"✗ FAIL: {message}")
    return passed


def print_summary(results):
    """Imprime relatório final"""
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
    else:
        print(f"\n✗ {failed} teste(s) falharam!")
    
    return failed == 0
