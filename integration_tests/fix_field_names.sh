#!/bin/bash

################################################################################
# Fix Field Names in Legacy E2E Tests
# Corrects bedrooms → num_rooms, bathrooms → num_bathrooms, parking_spaces → num_parking
################################################################################

echo "=========================================="
echo "Fixing Field Names in Legacy E2E Tests"
echo "=========================================="
echo ""

cd /opt/homebrew/var/www/realestate/realestate_backend/integration_tests

# List of test files to fix
FILES=(
    "test_us2_s2_manager_menus.sh"
    "test_us2_s3_manager_assigns_properties.sh"
    "test_us2_s4_manager_isolation.sh"
    "test_us3_s1_agent_assigned_properties.sh"
    "test_us3_s2_agent_auto_assignment.sh"
    "test_us3_s3_agent_own_leads.sh"
)

# Backup original files
echo "Creating backups..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup"
        echo "  ✓ Backed up: $file → ${file}.backup"
    fi
done
echo ""

# Apply fixes
echo "Applying field name corrections..."
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  Processing: $file"
        
        # Use sed to replace field names
        sed -i '' \
            -e 's/"bedrooms":/"num_rooms":/g' \
            -e 's/"bathrooms":/"num_bathrooms":/g' \
            -e 's/"parking_spaces":/"num_parking":/g' \
            "$file"
        
        echo "    ✓ Fixed: bedrooms → num_rooms"
        echo "    ✓ Fixed: bathrooms → num_bathrooms"
        echo "    ✓ Fixed: parking_spaces → num_parking"
    else
        echo "  ⚠️  File not found: $file"
    fi
done

echo ""
echo "=========================================="
echo "✅ Field Name Corrections Complete"
echo "=========================================="
echo ""
echo "Changes applied:"
echo "  - bedrooms → num_rooms"
echo "  - bathrooms → num_bathrooms"
echo "  - parking_spaces → num_parking"
echo ""
echo "Backup files created with .backup extension"
echo ""
echo "To restore original files:"
echo "  for f in test_us*.sh.backup; do mv \"\$f\" \"\${f%.backup}\"; done"
echo ""
echo "To execute fixed tests:"
echo "  bash execute_refactored_tests.sh"
echo ""
