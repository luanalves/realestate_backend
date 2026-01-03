#!/bin/bash
# Script to run Flake8 linting on Odoo custom addons
# Usage: ./lint.sh [addon_name]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Flake8 Code Quality Check ===${NC}\n"

# Check if running inside container or host
if [ -d "/mnt/extra-addons" ]; then
    ADDONS_PATH="/mnt/extra-addons"
else
    ADDONS_PATH="./extra-addons"
fi

# Check if flake8 is installed
if ! command -v flake8 &> /dev/null; then
    echo -e "${RED}Error: flake8 is not installed${NC}"
    echo "Please install it: pip3 install flake8"
    exit 1
fi

# If addon name is provided, check only that addon
if [ ! -z "$1" ]; then
    ADDON_NAME=$1
    TARGET="${ADDONS_PATH}/${ADDON_NAME}"
    
    if [ ! -d "$TARGET" ]; then
        echo -e "${RED}Error: Addon '${ADDON_NAME}' not found in ${ADDONS_PATH}${NC}"
        exit 1
    fi
    
    echo -e "Checking addon: ${GREEN}${ADDON_NAME}${NC}\n"
    flake8 "$TARGET"
    flake_status=$?
else
    # Check all addons
    echo -e "Checking all addons in: ${GREEN}${ADDONS_PATH}${NC}\n"
    flake8 "$ADDONS_PATH"
    flake_status=$?
fi

# Check exit status
if [ $flake_status -eq 0 ]; then
    echo -e "\n${GREEN}✓ All checks passed!${NC}"
else
    echo -e "\n${RED}✗ Flake8 found issues. Please fix them before committing.${NC}"
    exit 1
fi
