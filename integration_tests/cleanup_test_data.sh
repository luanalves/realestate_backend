#!/usr/bin/env bash
# Feature 010 E2E Tests - Test Data Cleanup Script
# Cleans up test data created during integration tests
#
# Usage:
#   ./cleanup_test_data.sh [options]
#
# Options:
#   --all         Clean all test data (default)
#   --profiles    Clean only profiles
#   --users       Clean only users
#   --agents      Clean only agents
#   --followers   Clean only mail followers
#   --dry-run     Show what would be deleted without deleting

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="${SCRIPT_DIR}/../18.0"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DRY_RUN=false
CLEAN_PROFILES=false
CLEAN_USERS=false
CLEAN_AGENTS=false
CLEAN_FOLLOWERS=false

# Parse arguments
if [ $# -eq 0 ]; then
    CLEAN_PROFILES=true
    CLEAN_USERS=true
    CLEAN_AGENTS=true
    CLEAN_FOLLOWERS=true
else
    while [[ $# -gt 0 ]]; do
        case $1 in
            --all)
                CLEAN_PROFILES=true
                CLEAN_USERS=true
                CLEAN_AGENTS=true
                CLEAN_FOLLOWERS=true
                shift
                ;;
            --profiles)
                CLEAN_PROFILES=true
                shift
                ;;
            --users)
                CLEAN_USERS=true
                shift
                ;;
            --agents)
                CLEAN_AGENTS=true
                shift
                ;;
            --followers)
                CLEAN_FOLLOWERS=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Usage: $0 [--all|--profiles|--users|--agents|--followers] [--dry-run]"
                exit 1
                ;;
        esac
    done
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Feature 010 - Test Data Cleanup${NC}"
echo -e "${BLUE}========================================${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN MODE - No data will be deleted${NC}"
fi

echo ""

# Helper function to execute SQL
exec_sql() {
    local sql="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN] Would execute: $description${NC}"
        # Show count
        local count_sql="SELECT COUNT(*) FROM ${sql#DELETE FROM }"
        count_sql="${count_sql%%;}"
        local count=$(docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db psql -U odoo -d realestate -t -A -c "$count_sql" 2>/dev/null || echo "0")
        echo -e "${BLUE}  Would delete: $count records${NC}"
    else
        echo -e "${GREEN}Executing: $description${NC}"
        local result=$(docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T db psql -U odoo -d realestate -c "$sql" 2>&1)
        echo "  $result"
    fi
}

# Clean test users (created by tests with @test.com emails)
if [ "$CLEAN_USERS" = true ]; then
    echo -e "${BLUE}Cleaning test users...${NC}"
    exec_sql \
        "DELETE FROM res_users WHERE id >= 180 OR login LIKE '%@test.com' OR login LIKE '%@example.com';" \
        "Delete test users"
    echo ""
fi

# Clean test agents (linked to test profiles)
if [ "$CLEAN_AGENTS" = true ]; then
    echo -e "${BLUE}Cleaning test agents...${NC}"
    exec_sql \
        "DELETE FROM real_estate_agent WHERE profile_id IN (
            SELECT id FROM thedevkitchen_estate_profile 
            WHERE document LIKE '123%' OR document LIKE '111%' OR document LIKE '999%' 
               OR document LIKE '555%' OR email LIKE '%@test.com'
        );" \
        "Delete agents linked to test profiles"
    exec_sql \
        "DELETE FROM real_estate_agent WHERE id >= 20;" \
        "Delete agents created during tests (ID >= 20)"
    echo ""
fi

# Clean mail followers (to prevent FK constraint issues)
if [ "$CLEAN_FOLLOWERS" = true ]; then
    echo -e "${BLUE}Cleaning mail followers...${NC}"
    exec_sql \
        "DELETE FROM mail_followers WHERE res_model IN ('real.estate.agent', 'thedevkitchen.estate.profile');" \
        "Delete mail followers for agents and profiles"
    echo ""
fi

# Clean test profiles
if [ "$CLEAN_PROFILES" = true ]; then
    echo -e "${BLUE}Cleaning test profiles...${NC}"
    
    # Document patterns used in tests
    declare -a patterns=(
        "123%"      # T26, T27, T28 (main test pattern)
        "111%"      # T26 (old pattern)
        "999%"      # T28 (compound unique tests)
        "555%"      # T26 (agent tests)
    )
    
    for pattern in "${patterns[@]}"; do
        exec_sql \
            "DELETE FROM thedevkitchen_estate_profile WHERE document LIKE '$pattern';" \
            "Delete profiles with document pattern: $pattern"
    done
    
    # Email-based cleanup (all test emails)
    exec_sql \
        "DELETE FROM thedevkitchen_estate_profile WHERE email LIKE '%@test.com';" \
        "Delete profiles with test email addresses"
    
    # ID-based cleanup (profiles created during tests)
    exec_sql \
        "DELETE FROM thedevkitchen_estate_profile WHERE id >= 100;" \
        "Delete profiles created during tests (ID >= 100)"
    
    echo ""
fi

echo -e "${GREEN}========================================${NC}"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN completed - No data was deleted${NC}"
else
    echo -e "${GREEN}Cleanup completed successfully!${NC}"
fi
echo -e "${GREEN}========================================${NC}"
