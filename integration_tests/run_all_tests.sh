#!/bin/bash

echo "========================================"
echo "EXECUTANDO TODOS OS TESTES E2E"
echo "========================================"
echo ""

# Pre-suite cleanup: remove test data from previous runs
echo "[SETUP] Cleaning test data from previous runs..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$SCRIPT_DIR/../18.0"

if [ -d "$COMPOSE_DIR" ] && command -v docker &> /dev/null; then
    cd "$COMPOSE_DIR"
    # Use separate transactions so one FK error doesn't roll back everything
    docker compose exec -T db psql -U odoo -d realestate <<'CLEANUP_SQL' 2>/dev/null
BEGIN; DELETE FROM real_estate_lead WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM real_estate_lead WHERE name LIKE '%Test%' OR name LIKE '%US6%' OR name LIKE '%us6%'; COMMIT;
BEGIN; DELETE FROM real_estate_property WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM real_estate_agent WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM real_estate_sale WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM real_estate_lease WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM thedevkitchen_estate_profile WHERE company_id > 5; COMMIT;
BEGIN; DELETE FROM thedevkitchen_estate_profile WHERE name LIKE '%Test%' OR name LIKE '%RBAC%' OR name LIKE '%Owner Creates%'; COMMIT;
BEGIN; DELETE FROM res_company_users_rel WHERE cid > 5; COMMIT;
BEGIN; DELETE FROM res_users WHERE company_id > 5 AND id > 21; COMMIT;
BEGIN; DELETE FROM res_users WHERE id > 21; COMMIT;
BEGIN; DELETE FROM res_partner WHERE company_id > 5 AND id NOT IN (SELECT partner_id FROM res_users WHERE partner_id IS NOT NULL); COMMIT;
BEGIN; DELETE FROM res_company WHERE id > 5; COMMIT;
CLEANUP_SQL
    echo "[SETUP] SQL cleanup completed"

    # Restart Odoo to clear ORM cache (SQL deletes don't invalidate in-memory caches)
    echo "[SETUP] Restarting Odoo to clear ORM cache..."
    docker compose restart odoo > /dev/null 2>&1
    echo "[SETUP] Waiting for Odoo to be ready..."
    for i in $(seq 1 30); do
        if curl -s -o /dev/null -w "" http://localhost:8069/web/login 2>/dev/null; then
            echo "[SETUP] Odoo is ready"
            break
        fi
        sleep 2
    done
    cd "$SCRIPT_DIR"
else
    echo "[SETUP] Warning: Could not run cleanup (docker not available or compose dir missing)"
fi
echo ""

PASSED=0
FAILED=0
TESTS_RUN=0
TOTAL_TESTS=$(ls test_us*.sh 2>/dev/null | wc -l | tr -d ' ')
LOG_DIR="./test_logs"

# Criar diretório de logs se não existir
mkdir -p "$LOG_DIR"

for test in test_us*.sh; do
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "[$TESTS_RUN/$TOTAL_TESTS] Executando $test..."
    
    LOG_FILE="$LOG_DIR/${test%.sh}.log"
    
    # Executar teste com timeout de 120s (macOS-compatible)
    bash "$test" > "$LOG_FILE" 2>&1 &
    TEST_PID=$!
    ( sleep 120 && kill $TEST_PID 2>/dev/null ) &
    WATCHDOG_PID=$!
    wait $TEST_PID 2>/dev/null
    TEST_EXIT=$?
    kill $WATCHDOG_PID 2>/dev/null
    wait $WATCHDOG_PID 2>/dev/null
    
    if [ $TEST_EXIT -eq 0 ]; then
        if grep -qiE "TEST PASSED|tests passed|PARTIAL PASS" "$LOG_FILE"; then
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
