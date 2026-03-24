#!/bin/bash
# =============================================================================
# Observability Stack - Startup Script
# =============================================================================
# Este script facilita o gerenciamento da stack de observabilidade.
#
# Uso:
#   ./start-observability.sh [comando]
#
# Comandos:
#   start      - Sobe toda a stack (aplicação + observabilidade)
#   stop       - Para toda a stack
#   restart    - Reinicia toda a stack
#   logs       - Mostra logs de todos os serviços
#   status     - Verifica status e saúde dos serviços
#   dashboards - Lista URLs de acesso
#   clean      - Remove todos os dados (cuidado!)
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Arquivos compose
COMPOSE_APP="docker-compose.yml"
COMPOSE_OBS="docker-compose.observability.yml"

# -----------------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------------

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker não está instalado!"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose não está instalado!"
        exit 1
    fi
    
    print_success "Docker e Docker Compose estão instalados"
}

check_env_file() {
    if [ ! -f ".env" ]; then
        print_warning "Arquivo .env não encontrado!"
        print_info "Copiando de .env.example..."
        cp .env.example .env
        print_error "ATENÇÃO: Configure as senhas em .env antes de continuar!"
        print_info "Edite o arquivo .env e substitua TROCAR_* por valores reais"
        exit 1
    fi
    
    # Verificar se tem senhas padrão
    if grep -q "TROCAR_" .env; then
        print_error "Arquivo .env contém valores TROCAR_* não configurados!"
        print_info "Configure todas as senhas antes de continuar"
        exit 1
    fi
    
    print_success "Arquivo .env configurado"
}

# -----------------------------------------------------------------------------
# Comandos principais
# -----------------------------------------------------------------------------

cmd_start() {
    print_header "Iniciando Stack Completa"
    
    check_docker
    check_env_file
    
    # Criar rede se não existir
    print_info "Verificando rede odoo-net..."
    if ! docker network inspect odoo-net &> /dev/null; then
        print_info "Criando rede odoo-net..."
        docker network create odoo-net -d bridge
        print_success "Rede criada"
    else
        print_success "Rede já existe"
    fi
    
    # Subir aplicação primeiro
    print_info "Subindo aplicação..."
    docker compose -f "$COMPOSE_APP" up -d
    print_success "Aplicação iniciada"
    
    # Aguardar database estar ready
    print_info "Aguardando PostgreSQL..."
    sleep 10
    
    # Subir observabilidade
    print_info "Subindo observabilidade..."
    docker compose -f "$COMPOSE_OBS" up -d
    print_success "Observabilidade iniciada"
    
    echo ""
    print_success "Stack completa iniciada com sucesso!"
    echo ""
    
    cmd_dashboards
}

cmd_stop() {
    print_header "Parando Stack Completa"
    
    print_info "Parando observabilidade..."
    docker compose -f "$COMPOSE_OBS" down
    
    print_info "Parando aplicação..."
    docker compose -f "$COMPOSE_APP" down
    
    print_success "Stack parada"
}

cmd_restart() {
    print_header "Reiniciando Stack Completa"
    
    cmd_stop
    sleep 2
    cmd_start
}

cmd_logs() {
    SERVICE=$1
    
    if [ -z "$SERVICE" ]; then
        print_header "Logs de Todos os Serviços"
        print_info "Aplicação:"
        docker compose -f "$COMPOSE_APP" logs --tail=20
        echo ""
        print_info "Observabilidade:"
        docker compose -f "$COMPOSE_OBS" logs --tail=20
    else
        print_header "Logs: $SERVICE"
        if docker compose -f "$COMPOSE_APP" ps | grep -q "$SERVICE"; then
            docker compose -f "$COMPOSE_APP" logs -f "$SERVICE"
        else
            docker compose -f "$COMPOSE_OBS" logs -f "$SERVICE"
        fi
    fi
}

cmd_status() {
    print_header "Status dos Serviços"
    
    echo -e "${BLUE}Aplicação:${NC}"
    docker compose -f "$COMPOSE_APP" ps
    echo ""
    
    echo -e "${BLUE}Observabilidade:${NC}"
    docker compose -f "$COMPOSE_OBS" ps
    echo ""
    
    print_header "Healthchecks"
    
    # PostgreSQL
    if docker compose -f "$COMPOSE_APP" exec -T db pg_isready &> /dev/null; then
        print_success "PostgreSQL: Healthy"
    else
        print_error "PostgreSQL: Unhealthy"
    fi
    
    # Redis
    if docker compose -f "$COMPOSE_APP" exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis: Healthy"
    else
        print_error "Redis: Unhealthy"
    fi
    
    # Prometheus
    if curl -sf http://localhost:9090/-/healthy &> /dev/null; then
        print_success "Prometheus: Healthy"
    else
        print_error "Prometheus: Unhealthy"
    fi
    
    # Loki
    if curl -sf http://localhost:3100/ready &> /dev/null; then
        print_success "Loki: Healthy"
    else
        print_error "Loki: Unhealthy"
    fi
    
    # Tempo
    if curl -sf http://localhost:3200/ready &> /dev/null; then
        print_success "Tempo: Healthy"
    else
        print_error "Tempo: Unhealthy"
    fi
    
    # Grafana
    if curl -sf http://localhost:3000/api/health &> /dev/null; then
        print_success "Grafana: Healthy"
    else
        print_error "Grafana: Unhealthy"
    fi
    
    echo ""
}

cmd_dashboards() {
    print_header "Dashboards e URLs"
    
    echo -e "${GREEN}Aplicação:${NC}"
    echo "  Odoo:           http://localhost:8069"
    echo "  RabbitMQ:       http://localhost:15672 (guest/guest)"
    echo ""
    
    echo -e "${GREEN}Observabilidade:${NC}"
    echo "  Grafana:        http://localhost:3000"
    echo "  Prometheus:     http://localhost:9090"
    echo "  Loki:           http://localhost:3100"
    echo "  Tempo:          http://localhost:3200"
    echo "  cAdvisor:       http://localhost:8080"
    echo ""
    
    echo -e "${YELLOW}Credenciais:${NC}"
    echo "  Grafana:        admin / (ver .env GRAFANA_ADMIN_PASSWORD)"
    echo "  Odoo:           admin / (ver .env ODOO_NEW_ADMIN_PASSWORD)"
    echo ""
    
    echo -e "${BLUE}Dashboards Recomendados (importar no Grafana):${NC}"
    echo "  Node Exporter:       1860"
    echo "  PostgreSQL:          9628"
    echo "  Redis:               11835"
    echo "  Docker Containers:   193"
    echo ""
}

cmd_clean() {
    print_header "Limpeza Completa"
    print_warning "CUIDADO: Isso vai remover TODOS os dados!"
    print_warning "Volumes de dados serão deletados permanentemente!"
    echo ""
    
    read -p "Tem certeza? Digite 'sim' para confirmar: " -r
    echo
    
    if [[ ! $REPLY =~ ^sim$ ]]; then
        print_info "Operação cancelada"
        exit 0
    fi
    
    print_info "Parando containers..."
    docker compose -f "$COMPOSE_OBS" down -v
    docker compose -f "$COMPOSE_APP" down -v
    
    print_info "Removendo volumes..."
    docker volume rm -f 180_odoo18-db 180_odoo18-data 180_odoo18-redis || true
    docker volume rm -f 180_prometheus-data 180_loki-data 180_tempo-data 180_grafana-data || true
    
    print_success "Limpeza concluída"
}

cmd_help() {
    cat << EOF
Uso: $0 [comando]

Comandos disponíveis:
  start       - Sobe toda a stack (aplicação + observabilidade)
  stop        - Para toda a stack
  restart     - Reinicia toda a stack
  logs [svc]  - Mostra logs (opcionalmente de um serviço específico)
  status      - Verifica status e saúde dos serviços
  dashboards  - Lista URLs de acesso
  clean       - Remove todos os dados (CUIDADO!)
  help        - Mostra esta ajuda

Exemplos:
  $0 start                 # Inicia tudo
  $0 logs odoo             # Logs do Odoo
  $0 logs grafana          # Logs do Grafana
  $0 status                # Status geral
  $0 stop                  # Para tudo

EOF
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

case "${1:-help}" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    logs)
        cmd_logs "$2"
        ;;
    status)
        cmd_status
        ;;
    dashboards)
        cmd_dashboards
        ;;
    clean)
        cmd_clean
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        print_error "Comando desconhecido: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac
