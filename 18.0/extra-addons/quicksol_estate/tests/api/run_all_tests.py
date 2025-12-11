#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Executa todos os testes de API em ordem
"""
import subprocess
import sys
from pathlib import Path


def run_test_file(test_file):
    """Executa um arquivo de teste e retorna o código de saída"""
    print("\n" + "🔵" * 35)
    print(f"EXECUTANDO: {test_file}")
    print("🔵" * 35)
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=Path(__file__).parent
    )
    
    return result.returncode


def main():
    """Executa todos os testes"""
    print("="*70)
    print("EXECUTANDO TODOS OS TESTES DE API")
    print("="*70)
    
    test_files = [
        'test_oauth.py',        # 3 testes: token, invalid credentials, missing grant_type
        'test_user_login.py',   # 7 testes: login A/B, invalid, logout, change profile, security tests
    ]
    
    results = {}
    
    for test_file in test_files:
        exit_code = run_test_file(test_file)
        results[test_file] = exit_code == 0
    
    # Relatório final
    print("\n" + "="*70)
    print("RELATÓRIO FINAL - TODOS OS TESTES")
    print("="*70)
    
    for test_file, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_file}")
    
    total = len(results)
    passed = sum(results.values())
    failed = total - passed
    
    print("\n" + "="*70)
    print(f"Total de arquivos: {total}")
    print(f"✓ Aprovados: {passed}")
    print(f"✗ Falhados: {failed}")
    
    if failed == 0:
        print("\n✓ SUCESSO: Todos os testes passaram!")
        sys.exit(0)
    else:
        print(f"\n✗ FALHA: {failed} arquivo(s) de teste falharam!")
        sys.exit(1)


if __name__ == '__main__':
    main()
