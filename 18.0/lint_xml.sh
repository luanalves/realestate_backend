#!/bin/bash
# Wrapper script for XML linting
# Usage: ./lint_xml.sh [path_to_check]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running inside container or host
if [ -d "/mnt/extra-addons" ]; then
    ADDONS_PATH="/mnt/extra-addons"
else
    ADDONS_PATH="./extra-addons"
fi

# Target path (use argument or default to all addons)
TARGET="${1:-$ADDONS_PATH}"

# Check if lxml is installed
if ! python3 -c "import lxml" 2>/dev/null; then
    echo -e "${RED}Error: lxml is not installed${NC}"
    echo "Please install it: pip3 install lxml"
    exit 1
fi

# Run the linter
python3 lint_xml.py "$TARGET" -v

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ XML linting passed!${NC}"
else
    echo -e "${RED}✗ XML linting failed. Please fix errors before committing.${NC}"
fi

exit $exit_code
