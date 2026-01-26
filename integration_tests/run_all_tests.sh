#!/bin/bash

echo "========================================"
echo "EXECUTANDO TODOS OS 21 TESTES E2E"
echo "========================================"
echo ""

PASSED=0
FAILED=0
TESTS_RUN=0
LOG_DIR="./test_logs"

# Criar diretório de logs se não existir
mkdir -p "$LOG_DIR"

for test in test_us*.sh; do
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "[$TESTS_RUN/21] Executando $test..."
    
    LOG_FILE="$LOG_DIR/${test%.sh}.log"
    
    # Executar teste e capturar resultado
    if bash "$test" > "$LOG_FILE" 2>&1; then
        if grep -q "TEST PASSED" "$LOG_FILE"; then
            echo "  ✅ PASSOU"
            PASSED=$((PASSED + 1))
        else
            echo "  ❌ FALHOU (sem mensagem de sucesso)"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  ❌ FALHOU (erro na execução)"
        FAILED=$((FAILED + 1))
    fi
    echo ""
done

echo "========================================"
echo "RESUMO DOS TESTES"
echo "========================================"
echo "Total executados: $TESTS_RUN"
echo "Passou: $PASSED"
echo "Falhou: $FAILED"
echo "Taxa de sucesso: $(( PASSED * 100 / TESTS_RUN ))%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "🎉 TODOS OS TESTES PASSARAM!"
    exit 0
else
    echo "⚠️  $FAILED teste(s) falharam. Veja os logs em $LOG_DIR/"
    echo ""
    echo "Testes que falharam:"
    for test in test_us*.sh; do
        LOG_FILE="$LOG_DIR/${test%.sh}.log"
        if [ -f "$LOG_FILE" ] && ! grep -q "TEST PASSED" "$LOG_FILE"; then
            echo "  - $test (log: $LOG_FILE)"
        fi
    done
    exit 1
fi
